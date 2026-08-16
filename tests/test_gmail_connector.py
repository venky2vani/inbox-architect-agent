"""Tests for the Gmail connector."""

import base64
from datetime import datetime
from unittest.mock import MagicMock

from plugins.gmail_connector import GmailConnector


def test_parse_message_extracts_text_and_attachments():
    connector = GmailConnector.__new__(GmailConnector)
    connector.service = None

    body_text = "Hello, this is the email body."
    body_b64 = base64.urlsafe_b64encode(body_text.encode()).decode()

    msg = {
        "id": "msg123",
        "threadId": "thread123",
        "labelIds": ["INBOX", "UNREAD"],
        "internalDate": str(int(datetime.now().timestamp() * 1000)),
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Test subject"},
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": body_b64},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": base64.urlsafe_b64encode("<p>HTML</p>".encode()).decode()},
                },
            ],
        },
    }

    parsed = connector._parse_message(msg)
    assert parsed.id == "msg123"
    assert parsed.sender == "sender@example.com"
    assert parsed.subject == "Test subject"
    assert parsed.body_text == body_text
    assert parsed.body_html == "<p>HTML</p>"
    assert "INBOX" in parsed.labels


def test_extract_body_recurses_nested_parts():
    connector = GmailConnector.__new__(GmailConnector)
    text_b64 = base64.urlsafe_b64encode("Nested text".encode()).decode()

    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": text_b64}}
                ],
            }
        ],
    }

    text, html = connector._extract_body(payload)
    assert text == "Nested text"
    assert html is None


def test_mark_processed_creates_and_applies_labels():
    connector = GmailConnector.__new__(GmailConnector)

    mock_service = MagicMock()
    mock_service.users().labels().list().execute.return_value = {
        "labels": [{"name": "Invoice", "id": "label_invoice"}]
    }
    modify_return = MagicMock()
    modify_return.execute.return_value = {}
    mock_service.users.return_value.messages.return_value.modify.return_value = modify_return
    connector.service = mock_service

    assert connector.mark_processed("msg123", ["Invoice"]) is True
    mock_service.users().messages().modify.assert_called_once_with(
        userId="me", id="msg123", body={"addLabelIds": ["label_invoice"]}
    )
