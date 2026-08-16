"""Tests for the review-mode callback and rule suggestion."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from plugins.base import EmailMessage, ProcessedItem
from plugins.llm_processor import SmartInboxProcessor


def make_message(sender: str = "noreply@example.com", subject: str = "Test") -> EmailMessage:
    return EmailMessage(
        id="m1",
        thread_id="t1",
        sender=sender,
        subject=subject,
        body_text="This is a test email body.",
        body_html=None,
        received_at=datetime.now(),
    )


def make_llm_response(category: str = "reference", priority: int = 2) -> str:
    return json.dumps(
        {
            "category": category,
            "priority": priority,
            "summary": "test summary",
            "action_items": [],
            "extracted_data": {"type": "other"},
            "should_archive": False,
        }
    )


def test_process_with_llm_sets_llm_used_flag():
    with tempfile.TemporaryDirectory() as tmp:
        rules_path = Path(tmp) / "rules.json"
        processor = SmartInboxProcessor(
            api_key="fake",
            model="gpt-4o-mini",
            provider="openai",
            local_intelligence=None,
        )
        # Mock the LLM client so no network call is made.
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=make_llm_response()))]
        )
        processor.client = MagicMock()
        processor.client.chat.completions.create.return_value = fake_response

        msg = make_message()
        result = processor._process_with_llm(msg)

        assert result.extracted_data.get("_llm_used") is True


def test_on_llm_required_callback_is_invoked():
    with tempfile.TemporaryDirectory() as tmp:
        rules_path = Path(tmp) / "rules.json"
        callback = MagicMock()
        processor = SmartInboxProcessor(
            api_key="fake",
            model="gpt-4o-mini",
            provider="openai",
            local_intelligence=None,
            on_llm_required=callback,
        )
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=make_llm_response()))]
        )
        processor.client = MagicMock()
        processor.client.chat.completions.create.return_value = fake_response

        msg = make_message()
        processor._process_with_llm(msg)

        callback.assert_called_once()
        passed_message, passed_item = callback.call_args[0]
        assert passed_message.id == msg.id
        assert isinstance(passed_item, ProcessedItem)


def test_suggested_rule_prefers_sender_domain():
    from ui.review_runner import ReviewRunner

    runner = ReviewRunner.__new__(ReviewRunner)
    msg = make_message(sender="billing@saas-company.com", subject="Your invoice")
    item = ProcessedItem(
        original_id=msg.id,
        sender=msg.sender,
        subject=msg.subject,
        category="action_needed",
        priority=4,
        summary="Invoice",
        action_items=[],
    )

    suggestion = runner._suggest_rule(msg, item)

    assert suggestion["type"] == "sender_domain"
    assert suggestion["value"] == "saas-company.com"
    assert suggestion["category"] == "action_needed"
    assert suggestion["priority"] == 4
