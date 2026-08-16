"""Tests for the InboxArchitectAgent orchestrator."""

from datetime import datetime
from unittest.mock import MagicMock

from agent import InboxArchitectAgent
from plugins.base import EmailMessage, ProcessedItem


def make_message(msg_id: str, subject: str) -> EmailMessage:
    return EmailMessage(
        id=msg_id,
        thread_id=f"t{msg_id}",
        sender="test@example.com",
        subject=subject,
        body_text="This is a test email.",
        body_html=None,
        received_at=datetime.now(),
    )


def test_run_daily_digest_stores_and_archives_noise():
    agent = InboxArchitectAgent()

    connector = MagicMock()
    connector.name = "mock_gmail"
    connector._list_unread_ids.return_value = [
        {"id": "1", "threadId": "t1"},
        {"id": "2", "threadId": "t2"},
    ]
    connector.fetch_message_by_id.side_effect = [
        make_message("1", "Invoice #123"),
        make_message("2", "Weekly newsletter"),
    ]

    persistence = MagicMock()
    persistence.store_index.return_value = True
    persistence.store_attachment.return_value = "https://drive.google.com/test"

    processor = MagicMock()
    processor.process.side_effect = [
        ProcessedItem(
            original_id="1",
            sender="test@example.com",
            subject="Invoice #123",
            category="action_needed",
            priority=4,
            summary="Invoice to pay",
            action_items=["Pay invoice"],
        ),
        ProcessedItem(
            original_id="2",
            sender="test@example.com",
            subject="Weekly newsletter",
            category="noise",
            priority=1,
            summary="Newsletter",
            action_items=[],
        ),
    ]
    processor.local_hits = 0
    processor.llm_calls = 1

    agent.connectors = [connector]
    agent.persistence = persistence
    agent.processors = [processor]

    agent.run_daily_digest(limit=10, archive_noise=True, dry_run=False)

    connector._list_unread_ids.assert_called_once_with(10)
    persistence.store_index.assert_called_once()
    stored_items = persistence.store_index.call_args[0][0]
    assert len(stored_items) == 2
    assert stored_items[0].category == "action_needed"
    assert stored_items[1].category == "noise"

    # Noise should be archived; action item should not.
    connector.archive.assert_called_once_with("2")


def test_run_daily_digest_dry_run_does_not_store():
    agent = InboxArchitectAgent()

    connector = MagicMock()
    connector.name = "mock_gmail"
    connector._list_unread_ids.return_value = [{"id": "3", "threadId": "t3"}]
    connector.fetch_message_by_id.return_value = make_message("3", "Promo")

    persistence = MagicMock()
    processor = MagicMock()
    processor.process.return_value = ProcessedItem(
        original_id="3",
        sender="test@example.com",
        subject="Promo",
        category="noise",
        priority=1,
        summary="Promo",
        action_items=[],
    )
    processor.local_hits = 0
    processor.llm_calls = 0

    agent.connectors = [connector]
    agent.persistence = persistence
    agent.processors = [processor]

    agent.run_daily_digest(limit=10, archive_noise=True, dry_run=True)

    persistence.store_index.assert_not_called()
    persistence.store_attachment.assert_not_called()
    connector.archive.assert_not_called()
