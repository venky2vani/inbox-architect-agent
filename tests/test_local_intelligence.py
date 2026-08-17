"""Tests for the local intelligence rule cache."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from plugins.base import EmailMessage, ProcessedItem
from plugins.local_intelligence import LocalIntelligence


def make_message(sender: str, subject: str, body: str = "") -> EmailMessage:
    return EmailMessage(
        id="m1",
        thread_id="t1",
        sender=sender,
        subject=subject,
        body_text=body,
        body_html=None,
        received_at=datetime.now(),
    )


def make_item(category: str = "noise", priority: int = 1) -> ProcessedItem:
    return ProcessedItem(
        original_id="m1",
        sender="a@b.com",
        subject="Test",
        category=category,
        priority=priority,
        summary="summary",
        action_items=[],
    )


def test_classify_returns_none_when_no_rules():
    with tempfile.TemporaryDirectory() as tmp:
        intel = LocalIntelligence(rules_path=f"{tmp}/rules.json")
        msg = make_message("newsletter@example.com", "Weekly newsletter")
        assert intel.classify(msg) is None


def test_learn_creates_rules():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        intel = LocalIntelligence(rules_path=str(path))
        msg = make_message("newsletter@example.com", "Weekly newsletter")
        item = make_item(category="noise", priority=1)

        intel.learn(msg, item)

        data = json.loads(path.read_text())
        rules = data["rules"]
        assert len(rules) > 0
        assert any(r["type"] == "sender_domain" and r["value"] == "example.com" for r in rules)


def test_classify_returns_match_after_enough_hits():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        intel = LocalIntelligence(rules_path=str(path), confidence_threshold=0.8, min_hits=3)
        msg = make_message("newsletter@example.com", "Weekly newsletter")

        for _ in range(3):
            intel.learn(msg, make_item(category="noise", priority=1))

        result = intel.classify(msg)
        assert result is not None
        assert result.category == "noise"
        assert result.priority == 1
        assert result.extracted_data.get("_local_intelligence") is True


def test_mismatch_lowers_confidence():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        intel = LocalIntelligence(rules_path=str(path), confidence_threshold=0.8, min_hits=3)
        msg = make_message("newsletter@example.com", "Weekly newsletter")

        # Two consistent noise classifications.
        intel.learn(msg, make_item(category="noise", priority=1))
        intel.learn(msg, make_item(category="noise", priority=1))
        # One conflicting classification.
        intel.learn(msg, make_item(category="reference", priority=2))

        # Confidence is now 2/3 < 0.8, so classify should return None.
        assert intel.classify(msg) is None


def test_prune_removes_stale_rules():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        # min_hits=2 so a single-hit rule is not considered proven and can be pruned.
        intel = LocalIntelligence(rules_path=str(path), prune_after_days=0, min_hits=2)
        msg = make_message("old@example.com", "Old newsletter")
        intel.learn(msg, make_item(category="noise", priority=1))

        # Manually age all rules by setting last_used far in the past.
        data = json.loads(path.read_text())
        for rule in data["rules"]:
            rule["last_used"] = "2020-01-01T00:00:00+00:00"
        path.write_text(json.dumps(data))

        intel._load()
        intel.prune()

        assert len(intel.rules) == 0


def test_body_keywords_are_extracted():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        intel = LocalIntelligence(rules_path=str(path), confidence_threshold=0.8, min_hits=1)
        body = "Please review the attached invoice for payment due next week."
        msg = make_message("client@example.com", "Invoice", body)
        item = make_item(category="action_needed", priority=4)
        intel.learn(msg, item)

        result = intel.classify(msg)
        assert result is not None
        assert result.category == "action_needed"


def test_noisy_tokens_are_not_learned():
    """Generic boilerplate tokens should not become rules."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        intel = LocalIntelligence(rules_path=str(path))
        body = "Please click here to view the online version. Dear user, thanks."
        msg = make_message("newsletter@example.com", "Update", body)
        item = make_item(category="noise", priority=1)

        intel.learn(msg, item)

        data = json.loads(path.read_text())
        values = {r["value"] for r in data["rules"]}
        noisy_values = {"click", "please", "dear", "thanks", "view"}
        assert not values.intersection(noisy_values), f"Noisy tokens learned: {values}"


def test_low_confidence_rules_are_pruned():
    """Rules with many samples but low confidence should be removed by prune()."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        intel = LocalIntelligence(rules_path=str(path), min_hits=1)

        # Inject a manually-created rule with 3 hits and 7 misses (30%).
        intel.rules.append(
            {
                "id": "test-rule",
                "type": "subject_keyword",
                "value": "shaky",
                "category": "noise",
                "priority": 1,
                "should_archive": True,
                "hits": 3,
                "misses": 7,
                "created_at": "2026-08-17T00:00:00+00:00",
                "last_used": "2026-08-17T00:00:00+00:00",
            }
        )
        intel.prune()

        assert not any(r["value"] == "shaky" for r in intel.rules)


def test_per_type_min_confidence_excludes_noisy_rules():
    """Rules below their per-type confidence floor should not vote."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rules.json"
        intel = LocalIntelligence(
            rules_path=str(path), confidence_threshold=0.5, min_hits=1
        )
        msg = make_message("newsletter@example.com", "Weekly newsletter", body="payment")

        # Inject a body_keyword rule with 1 hit and 4 misses (20%).
        # The overall threshold is 0.5, but the body_keyword floor is 0.80.
        intel.rules.append(
            {
                "id": "test-rule",
                "type": "body_keyword",
                "value": "payment",
                "category": "action_needed",
                "priority": 4,
                "should_archive": False,
                "hits": 1,
                "misses": 4,
                "created_at": "2026-08-17T00:00:00+00:00",
                "last_used": "2026-08-17T00:00:00+00:00",
            }
        )

        result = intel.classify(msg)
        assert result is None
