"""Tests for dynamic label discovery system."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.dynamic_classifier import DynamicClassifier
from plugins.base import EmailMessage


class TestDynamicClassifierPatternDetection:
    """Test pattern detection in email clusters."""

    def test_cluster_by_sender(self):
        """Test grouping emails by sender domain."""
        classifier = DynamicClassifier()

        messages = [
            MagicMock(sender="user@coinbase.com", subject="Deposit", received_at="2026-08-16"),
            MagicMock(sender="user@coinbase.com", subject="Withdrawal", received_at="2026-08-15"),
            MagicMock(sender="user@steam.com", subject="Purchase", received_at="2026-08-14"),
        ]

        clusters = classifier._cluster_by_sender(messages)

        assert "coinbase.com" in clusters
        assert "steam.com" in clusters
        assert len(clusters["coinbase.com"]) == 2
        assert len(clusters["steam.com"]) == 1

    def test_extract_domain(self):
        """Test domain extraction from email addresses."""
        assert DynamicClassifier._extract_domain("user@example.com") == "example.com"
        assert DynamicClassifier._extract_domain("test@mail.co.uk") == "mail.co.uk"
        assert DynamicClassifier._extract_domain("invalid") is None

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        classifier = DynamicClassifier()

        # Large cluster with many keywords
        emails = [MagicMock(subject=f"Email {i}", body="", received_at="2026-08-16") for i in range(100)]
        keywords = ["deposit", "withdraw", "transaction", "balance", "security"]

        confidence = classifier._calculate_confidence(keywords, emails)

        assert 0.5 <= confidence <= 1.0  # Should be relatively high
        assert isinstance(confidence, float)

    def test_guess_category_crypto(self):
        """Test category guessing for crypto domains."""
        classifier = DynamicClassifier()

        result = classifier._guess_category(
            "coinbase.com",
            ["deposit", "withdrawal", "bitcoin"],
            []
        )

        assert result is not None
        assert result["label"] == "crypto_exchanges"
        assert "cryptocurrency" in result["description"].lower()

    def test_guess_category_gaming(self):
        """Test category guessing for gaming domains."""
        classifier = DynamicClassifier()

        result = classifier._guess_category(
            "steam.com",
            ["purchase", "game", "library"],
            []
        )

        assert result is not None
        assert result["label"] == "gaming"

    def test_guess_category_job_platforms(self):
        """Test category guessing for job board domains."""
        classifier = DynamicClassifier()

        result = classifier._guess_category(
            "linkedin.com",
            ["job", "application", "position"],
            []
        )

        assert result is not None
        assert result["label"] == "job_platforms"

    def test_guess_category_developer_tools(self):
        """Test category guessing for developer tool domains."""
        classifier = DynamicClassifier()

        result = classifier._guess_category(
            "github.com",
            ["repository", "commit", "code"],
            []
        )

        assert result is not None
        assert result["label"] == "developer_tools"

    def test_guess_category_ecommerce(self):
        """Test category guessing for e-commerce domains."""
        classifier = DynamicClassifier()

        result = classifier._guess_category(
            "amazon.com",
            ["order", "purchase", "delivery"],
            []
        )

        assert result is not None
        assert result["label"] == "ecommerce"

    def test_guess_category_social_media(self):
        """Test category guessing for social media domains."""
        classifier = DynamicClassifier()

        result = classifier._guess_category(
            "facebook.com",
            ["post", "like", "comment"],
            []
        )

        assert result is not None
        assert result["label"] == "social_media"


class TestDynamicClassifierAnalysis:
    """Test email analysis and suggestion generation."""

    def test_analyze_emails_min_cluster_size(self):
        """Test that small clusters are ignored."""
        classifier = DynamicClassifier()
        classifier.MIN_CLUSTER_SIZE = 50

        # Only 30 emails - below minimum
        messages = [
            MagicMock(sender="user@smalldomain.com", subject=f"Email {i}", body="test", received_at="2026-08-16")
            for i in range(30)
        ]

        suggestions = classifier.analyze_emails(messages)

        # Should not suggest anything for small cluster
        assert len(suggestions) == 0

    def test_analyze_emails_with_suggestions(self):
        """Test analysis that generates suggestions."""
        classifier = DynamicClassifier()
        classifier.MIN_CLUSTER_SIZE = 50
        classifier.CONFIDENCE_THRESHOLD = 0.40  # Lower threshold for test

        # 80 crypto emails
        messages = [
            MagicMock(
                sender="noreply@coinbase.com",
                subject=f"Transaction {i}: Deposit of $100",
                body="Your deposit has been confirmed",
                received_at="2026-08-16"
            )
            for i in range(80)
        ]

        suggestions = classifier.analyze_emails(messages)

        # Should suggest crypto_exchanges
        assert len(suggestions) > 0
        assert any("crypto" in s["suggested_label"].lower() for s in suggestions)

    def test_analyze_emails_confidence_threshold(self):
        """Test that low-confidence suggestions are filtered."""
        classifier = DynamicClassifier()
        classifier.MIN_CLUSTER_SIZE = 50
        classifier.CONFIDENCE_THRESHOLD = 0.75

        # 55 very generic emails (low confidence)
        messages = [
            MagicMock(
                sender="user@generic.com",
                subject=f"Update {i}",
                body="Generic content",
                received_at="2026-08-16"
            )
            for i in range(55)
        ]

        suggestions = classifier.analyze_emails(messages)

        # Low confidence suggestions should be filtered
        if suggestions:
            assert all(s["confidence"] >= classifier.CONFIDENCE_THRESHOLD for s in suggestions)


class TestDynamicClassifierPersistence:
    """Test configuration persistence and user actions."""

    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration."""
        config_path = tmp_path / "test_config.json"
        classifier = DynamicClassifier(str(config_path))

        # Modify data
        classifier.data["confirmed_labels"].append({
            "domain": "test.com",
            "label": "test_label",
            "confirmed_at": "2026-08-16T10:00:00"
        })
        classifier._save_config()

        # Load fresh instance
        classifier2 = DynamicClassifier(str(config_path))

        assert len(classifier2.data["confirmed_labels"]) == 1
        assert classifier2.data["confirmed_labels"][0]["domain"] == "test.com"

    def test_confirm_label(self, tmp_path):
        """Test confirming a suggested label."""
        config_path = tmp_path / "test_config.json"
        classifier = DynamicClassifier(str(config_path))

        classifier.confirm_label("coinbase.com", "crypto_exchanges")

        assert len(classifier.data["confirmed_labels"]) == 1
        assert classifier.data["confirmed_labels"][0]["domain"] == "coinbase.com"
        assert classifier.data["confirmed_labels"][0]["label"] == "crypto_exchanges"

    def test_reject_pattern(self, tmp_path):
        """Test rejecting a suggested pattern."""
        config_path = tmp_path / "test_config.json"
        classifier = DynamicClassifier(str(config_path))

        classifier.reject_pattern("random-domain.com")

        assert len(classifier.data["rejected_patterns"]) == 1
        assert classifier.data["rejected_patterns"][0]["domain"] == "random-domain.com"

    def test_confirmed_labels_excludes_rejected(self, tmp_path):
        """Test that rejected patterns are skipped in analysis."""
        config_path = tmp_path / "test_config.json"
        classifier = DynamicClassifier(str(config_path))
        classifier.MIN_CLUSTER_SIZE = 50

        # Reject a domain
        classifier.reject_pattern("badomain.com")

        # Create messages from that domain
        messages = [
            MagicMock(sender="user@badomain.com", subject=f"Email {i}", body="test", received_at="2026-08-16")
            for i in range(60)
        ]

        suggestions = classifier.analyze_emails(messages)

        # Should not suggest anything for rejected domain
        assert not any(s["domain"] == "badomain.com" for s in suggestions)


class TestDynamicClassifierExport:
    """Test exporting suggestions to files."""

    def test_export_suggestions_to_file(self, tmp_path):
        """Test exporting suggestions to markdown file."""
        output_path = tmp_path / "review.md"
        classifier = DynamicClassifier()

        suggestions = [
            {
                "domain": "coinbase.com",
                "suggested_label": "crypto_exchanges",
                "suggested_description": "Cryptocurrency transactions",
                "email_count": 85,
                "confidence": 0.92,
                "example_keywords": ["deposit", "withdrawal", "transaction"],
                "example_subjects": ["Deposit confirmed", "Withdrawal alert"],
                "first_seen": "2026-08-01",
                "last_seen": "2026-08-16",
            }
        ]

        classifier.export_suggestions_to_file(suggestions, str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "coinbase.com" in content
        assert "CRYPTO_EXCHANGES" in content  # Exported as uppercase heading
        assert "85" in content
        assert "92" in content  # Check for confidence percentage

    def test_get_confirmed_labels(self, tmp_path):
        """Test retrieving confirmed labels."""
        config_path = tmp_path / "test_config.json"
        classifier = DynamicClassifier(str(config_path))

        classifier.confirm_label("coinbase.com", "crypto_exchanges")
        classifier.confirm_label("steam.com", "gaming")

        confirmed = classifier.get_confirmed_labels()

        assert len(confirmed) == 2
        assert any(c["domain"] == "coinbase.com" for c in confirmed)
        assert any(c["domain"] == "steam.com" for c in confirmed)


class TestDynamicClassifierEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_email_list(self):
        """Test analysis with empty email list."""
        classifier = DynamicClassifier()
        suggestions = classifier.analyze_emails([])
        assert suggestions == []

    def test_extract_keywords_empty_messages(self):
        """Test keyword extraction with empty messages."""
        classifier = DynamicClassifier()
        messages = [
            MagicMock(subject="", body="", received_at="2026-08-16")
        ]

        keywords = classifier._extract_keywords(messages)

        assert isinstance(keywords, list)

    def test_tokenize(self):
        """Test tokenization."""
        text = "Hello, World! Test 123"
        tokens = DynamicClassifier._tokenize(text)

        # Tokenize returns words as-is (callers handle lowercasing)
        assert "Hello" in tokens or "hello" in tokens
        assert "World" in tokens or "world" in tokens
        assert "Test" in tokens or "test" in tokens
        assert len(tokens) == 4  # Hello, World, Test, 123

    def test_extract_domain_invalid(self):
        """Test domain extraction with invalid inputs."""
        assert DynamicClassifier._extract_domain("") is None
        assert DynamicClassifier._extract_domain("@invalid") is None
        assert DynamicClassifier._extract_domain("no-domain") is None

    def test_confidence_score_bounds(self):
        """Test that confidence scores are between 0 and 1."""
        classifier = DynamicClassifier()

        # Various configurations
        for num_emails in [10, 50, 100, 500]:
            for num_keywords in [0, 1, 5, 10, 20]:
                messages = [MagicMock(subject="test", body="", received_at="2026-08-16") for _ in range(num_emails)]
                keywords = [f"keyword{i}" for i in range(num_keywords)]

                confidence = classifier._calculate_confidence(keywords, messages)

                assert 0 <= confidence <= 1, f"Confidence out of bounds: {confidence}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
