"""Tests for the LLM-required pattern cache and analyze-patterns source behavior."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from plugins.base import EmailMessage, ProcessedItem
from plugins.dynamic_classifier import DynamicClassifier
from plugins.pattern_cache import PatternCache


class TestPatternCache:
    """Test cache persistence for LLM-required emails."""

    def test_record_and_load_message(self, tmp_path):
        """Cache a message and reconstruct it for analysis."""
        cache_path = tmp_path / "cache.json"
        cache = PatternCache(str(cache_path))

        message = EmailMessage(
            id="msg1",
            thread_id="t1",
            sender="noreply@example.com",
            subject="Test email",
            body_text="Some body text",
            body_html=None,
            received_at=datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc),
        )
        item = ProcessedItem(
            original_id="msg1",
            sender="noreply@example.com",
            subject="Test email",
            category="reference",
            priority=2,
            summary="summary",
        )

        cache.record(message, item)
        messages = cache.load_messages()

        assert len(messages) == 1
        assert messages[0].sender == "noreply@example.com"
        assert messages[0].subject == "Test email"
        assert messages[0].body_text == "Some body text"

    def test_count_and_reset(self, tmp_path):
        """Count records and clear the cache."""
        cache_path = tmp_path / "cache.json"
        cache = PatternCache(str(cache_path))

        message = EmailMessage(
            id="msg1",
            thread_id="t1",
            sender="noreply@example.com",
            subject="Test email",
            body_text="body",
            body_html=None,
            received_at=datetime.now(timezone.utc),
        )
        item = ProcessedItem(
            original_id="msg1",
            sender="noreply@example.com",
            subject="Test email",
            category="reference",
            priority=2,
            summary="summary",
        )

        cache.record(message, item)
        assert cache.count() == 1

        cache.reset()
        assert cache.count() == 0
        assert cache.load_messages() == []

    def test_load_messages_limit_and_order(self, tmp_path):
        """Most-recent records are returned first and limit is respected."""
        cache_path = tmp_path / "cache.json"
        cache = PatternCache(str(cache_path))

        for i in range(3):
            message = EmailMessage(
                id=f"msg{i}",
                thread_id="t1",
                sender=f"noreply{i}@example.com",
                subject=f"Test {i}",
                body_text="body",
                body_html=None,
                received_at=datetime(2026, 8, 16, 10, i, 0, tzinfo=timezone.utc),
            )
            item = ProcessedItem(
                original_id=f"msg{i}",
                sender=f"noreply{i}@example.com",
                subject=f"Test {i}",
                category="reference",
                priority=2,
                summary="summary",
            )
            cache.record(message, item)

        messages = cache.load_messages(limit=2)
        assert len(messages) == 2
        # Most recent first
        assert messages[0].id == "msg2"
        assert messages[1].id == "msg1"

    def test_body_text_truncated(self, tmp_path):
        """Very long bodies are truncated to avoid a bloated cache file."""
        cache_path = tmp_path / "cache.json"
        cache = PatternCache(str(cache_path))

        message = EmailMessage(
            id="msg1",
            thread_id="t1",
            sender="noreply@example.com",
            subject="Test",
            body_text="x" * 5000,
            body_html=None,
            received_at=datetime.now(timezone.utc),
        )
        item = ProcessedItem(
            original_id="msg1",
            sender="noreply@example.com",
            subject="Test",
            category="reference",
            priority=2,
            summary="summary",
        )

        cache.record(message, item)
        messages = cache.load_messages()
        assert len(messages[0].body_text) == 2000

    def test_json_file_created(self, tmp_path):
        """The cache file is written as JSON after recording."""
        cache_path = tmp_path / "cache.json"
        cache = PatternCache(str(cache_path))

        message = EmailMessage(
            id="msg1",
            thread_id="t1",
            sender="noreply@example.com",
            subject="Test",
            body_text="body",
            body_html=None,
            received_at=datetime.now(timezone.utc),
        )
        item = ProcessedItem(
            original_id="msg1",
            sender="noreply@example.com",
            subject="Test",
            category="reference",
            priority=2,
            summary="summary",
        )

        cache.record(message, item)
        assert cache_path.exists()

        data = json.loads(cache_path.read_text())
        assert len(data["records"]) == 1
        assert data["records"][0]["sender"] == "noreply@example.com"


class TestAnalyzePatternsSource:
    """Test analyze_patterns source selection."""

    def test_analyze_patterns_llm_required_source(self, tmp_path, monkeypatch):
        """Analyze patterns from the LLM-required cache without touching Gmail."""
        from agent import InboxArchitectAgent

        cache_path = tmp_path / "cache.json"
        agent = InboxArchitectAgent()
        agent.pattern_cache = PatternCache(str(cache_path))

        # Seed the cache with a cluster of LLM-required banking emails
        for i in range(60):
            message = EmailMessage(
                id=f"bank{i}",
                thread_id="t1",
                sender="alerts@newbank.in",
                subject="Account update",
                body_text="body",
                body_html=None,
                received_at=datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc),
            )
            item = ProcessedItem(
                original_id=f"bank{i}",
                sender="alerts@newbank.in",
                subject="Account update",
                category="banking_investment",
                priority=2,
                summary="summary",
            )
            agent.pattern_cache.record(message, item)

        # Should not need connectors
        agent.connectors = []

        # Capture suggestions via the printed output by inspecting the classifier
        suggestions = DynamicClassifier().analyze_emails(
            agent.pattern_cache.load_messages(limit=200)
        )

        # newbank.in should be suggested as banking_investment
        assert any(s["domain"] == "newbank.in" for s in suggestions)
        banking = next(s for s in suggestions if s["domain"] == "newbank.in")
        assert banking["suggested_label"] == "banking_investment"

    def test_analyze_patterns_gmail_source_requires_connector(self, tmp_path):
        """The Gmail source still requires a connector."""
        from agent import InboxArchitectAgent

        agent = InboxArchitectAgent()
        agent.connectors = []

        with pytest.raises(RuntimeError, match="No connectors available"):
            agent.analyze_patterns(limit=10, source="gmail")

    def test_record_llm_required_callback(self, tmp_path):
        """The agent callback writes to the pattern cache."""
        from agent import InboxArchitectAgent

        cache_path = tmp_path / "cache.json"
        agent = InboxArchitectAgent()
        agent.pattern_cache = PatternCache(str(cache_path))

        message = EmailMessage(
            id="msg1",
            thread_id="t1",
            sender="noreply@example.com",
            subject="Test",
            body_text="body",
            body_html=None,
            received_at=datetime.now(timezone.utc),
        )
        item = ProcessedItem(
            original_id="msg1",
            sender="noreply@example.com",
            subject="Test",
            category="reference",
            priority=2,
            summary="summary",
        )

        agent._record_llm_required(message, item)

        assert agent.pattern_cache.count() == 1
