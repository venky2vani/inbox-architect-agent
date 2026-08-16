"""Basic tests for plugin interfaces and fallback processor."""

from datetime import datetime

from plugins.base import EmailMessage, ProcessedItem
from plugins.llm_processor import SmartInboxProcessor


def test_fallback_processor_detects_noise():
    processor = SmartInboxProcessor(api_key=None)
    msg = EmailMessage(
        id="123",
        thread_id="t123",
        sender="newsletter@example.com",
        subject="Weekly newsletter: unsubscribe here",
        body_text="This is a promotional email. Click to unsubscribe.",
        body_html=None,
        received_at=datetime.now(),
    )
    item = processor.process(msg)
    assert item.category == "noise"
    assert item.priority == 1
    assert item.status == "archived"


def test_fallback_processor_detects_action_needed():
    processor = SmartInboxProcessor(api_key=None)
    msg = EmailMessage(
        id="124",
        thread_id="t124",
        sender="boss@example.com",
        subject="Budget report",
        body_text="Please send the budget report by end of day.",
        body_html=None,
        received_at=datetime.now(),
    )
    item = processor.process(msg)
    assert item.category == "action_needed"
    assert item.status == "pending"


def test_extract_json_parses_markdown_and_empty():
    processor = SmartInboxProcessor(api_key=None)
    result, is_garbage = processor._extract_json('{"category": "noise"}')
    assert result["category"] == "noise"
    assert not is_garbage

    result, is_garbage = processor._extract_json('```json\n{"category": "reference"}\n```')
    assert result["category"] == "reference"
    assert not is_garbage

    result, is_garbage = processor._extract_json("")
    assert result == {}
    assert is_garbage

    result, is_garbage = processor._extract_json("not json")
    assert result == {}
    assert is_garbage


def test_processed_item_defaults():
    item = ProcessedItem(
        original_id="x",
        sender="a@b.com",
        subject="Test",
        category="reference",
        priority=2,
        summary="summary",
    )
    assert item.action_items == []
    assert item.extracted_data == {}
    assert item.destination == ""
    assert item.drive_link == ""
    assert item.status == "pending"
