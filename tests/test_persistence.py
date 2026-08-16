"""Tests for Google Workspace persistence helpers."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from plugins.google_workspace_persistence import GoogleWorkspacePersistence


def test_clamp_priority():
    from plugins.llm_processor import SmartInboxProcessor

    assert SmartInboxProcessor._clamp_priority(0) == 1
    assert SmartInboxProcessor._clamp_priority(3) == 3
    assert SmartInboxProcessor._clamp_priority(6) == 5
    assert SmartInboxProcessor._clamp_priority("bad") == 3


def test_store_index_builds_rows():
    persistence = GoogleWorkspacePersistence.__new__(GoogleWorkspacePersistence)
    persistence.index_sheet = MagicMock()
    persistence.index_sheet.append_rows = MagicMock()

    from plugins.base import ProcessedItem

    items = [
        ProcessedItem(
            original_id="m1",
            sender="a@b.com",
            subject="Invoice",
            category="action_needed",
            priority=4,
            summary="Pay invoice",
            action_items=["Pay by Friday"],
            drive_link="https://drive.google.com/invoice",
            status="pending",
        )
    ]

    persistence.store_index(items)
    persistence.index_sheet.append_rows.assert_called_once()
    rows = persistence.index_sheet.append_rows.call_args[0][0]
    assert rows[0][4] == "action_needed"
    assert rows[0][5] == 4
    assert "Pay by Friday" in rows[0][7]


def test_store_attachment_uploads_to_drive():
    persistence = GoogleWorkspacePersistence.__new__(GoogleWorkspacePersistence)
    persistence.drive_root_id = "root123"

    mock_folder = MagicMock()
    mock_file = MagicMock()
    mock_file.get.return_value = {"webViewLink": "https://drive.google.com/test-file"}

    persistence._get_or_create_drive_folder = MagicMock(return_value=mock_folder)
    persistence.drive = MagicMock()
    persistence.drive.files().create().execute.return_value = {
        "id": "file123",
        "webViewLink": "https://drive.google.com/test-file",
    }

    link = persistence.store_attachment(
        "msg123", {"name": "report.pdf", "mime_type": "application/pdf"}, b"pdfdata"
    )
    assert link == "https://drive.google.com/test-file"
