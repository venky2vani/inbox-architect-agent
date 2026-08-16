"""Gmail connector plugin for the Inbox Architect Agent."""

import base64
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from plugins.base import EmailConnector, EmailMessage
from plugins.retry import retry_with_backoff, is_transient_google_error

logger = logging.getLogger(__name__)

google_retry = retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    exceptions=(Exception,),
    predicate=is_transient_google_error,
)

# Gmail API scope plus Sheets/Drive scopes so the same token can be reused
# by the Google Workspace persistence plugin.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GmailConnector(EmailConnector):
    """Fetch and manage emails from Gmail."""

    name = "gmail"

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        archive_label: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.getenv(
            "GMAIL_CREDENTIALS_PATH", "credentials/credentials.json"
        )
        self.token_path = token_path or os.getenv(
            "GMAIL_TOKEN_PATH", "credentials/token.json"
        )
        self.archive_label = archive_label or os.getenv(
            "GMAIL_ARCHIVE_LABEL", "NOISE"
        )
        self.creds: Optional[Credentials] = None
        self.service: Optional[Any] = None

    def _has_required_scopes(self) -> bool:
        """Check whether the loaded credentials cover all required scopes."""
        if not self.creds or not self.creds.scopes:
            return False
        token_scopes = set(self.creds.scopes)
        return set(SCOPES).issubset(token_scopes)

    def authenticate(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """Authenticate with Gmail using OAuth2.

        If a saved token exists, it is refreshed/used. Otherwise, an interactive
        flow is started using credentials/credentials.json. If the saved token
        is missing required scopes, it is discarded and the user is re-prompted.
        """
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(
                self.token_path, SCOPES
            )

        if self.creds and not self._has_required_scopes():
            logger.warning(
                "Saved token is missing required scopes; deleting token and re-authorizing."
            )
            try:
                os.remove(self.token_path)
            except FileNotFoundError:
                pass
            self.creds = None

        if self.creds and self.creds.expired and self.creds.refresh_token:
            logger.info("Refreshing expired OAuth token")
            start = time.perf_counter()
            self.creds.refresh(Request())
            logger.info("Token refreshed in %.2fs", time.perf_counter() - start)
        elif not self.creds or not self.creds.valid:
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(
                    f"Gmail credentials file not found: {self.credentials_path}"
                )
            logger.info("Starting interactive OAuth flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            self.creds = flow.run_local_server(port=0)

        # Persist the token for future runs.
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as token_file:
            token_file.write(self.creds.to_json())

        start_build = time.perf_counter()
        self.service = build("gmail", "v1", credentials=self.creds)
        logger.info("Gmail service built in %.2fs", time.perf_counter() - start_build)
        logger.info("Authenticated Gmail scopes: %s", self.creds.scopes)
        return True

    def _list_unread_ids(self, limit: int) -> List[Dict[str, str]]:
        """Return a list of unread message metadata (id, threadId)."""
        if not self.service:
            raise RuntimeError("Connector is not authenticated. Call authenticate() first.")

        logger.info("Listing unread inbox messages (limit=%d)", limit)
        start_list = time.perf_counter()
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q="is:unread in:inbox", maxResults=limit)
            .execute()
        )
        messages = results.get("messages", [])
        logger.info(
            "Listed %d unread message ID(s) in %.2fs",
            len(messages),
            time.perf_counter() - start_list,
        )
        return messages

    def _fetch_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch a single full message by ID."""
        if not self.service:
            raise RuntimeError("Connector is not authenticated.")
        return (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

    def fetch_unread(self, limit: int = 50) -> List[EmailMessage]:
        """Fetch unread messages from the inbox."""
        if not self.service:
            raise RuntimeError("Connector is not authenticated. Call authenticate() first.")

        message_ids = self._list_unread_ids(limit)
        messages: List[EmailMessage] = []
        total = len(message_ids)
        for idx, msg_meta in enumerate(message_ids, 1):
            start_get = time.perf_counter()
            try:
                full_msg = self._fetch_message(msg_meta["id"])
                messages.append(self._parse_message(full_msg))
                logger.debug(
                    "Fetched message %d/%d in %.2fs",
                    idx,
                    total,
                    time.perf_counter() - start_get,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to fetch message %s: %s", msg_meta["id"], exc)
        return messages

    def fetch_message_by_id(self, message_id: str) -> EmailMessage:
        """Fetch and parse a single message by ID."""
        full_msg = self._fetch_message(message_id)
        return self._parse_message(full_msg)

    def archive(self, message_id: str) -> bool:
        """Remove the INBOX label and apply the configured archive label."""
        if not self.service:
            raise RuntimeError("Connector is not authenticated.")
        try:
            archived_label_id = self._get_or_create_label(self.archive_label)
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": [archived_label_id],
                    "removeLabelIds": ["INBOX"],
                },
            ).execute()
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to archive message %s: %s", message_id, exc)
            return False

    @google_retry
    def _get_or_create_label(self, name: str) -> str:
        """Return the ID of a Gmail label, creating it if necessary."""
        if not self.service:
            raise RuntimeError("Connector is not authenticated.")
        results = self.service.users().labels().list(userId="me").execute()
        for label in results.get("labels", []):
            if label["name"] == name:
                return label["id"]
        created = (
            self.service.users()
            .labels()
            .create(userId="me", body={"name": name})
            .execute()
        )
        return created["id"]

    def mark_processed(self, message_id: str, labels: List[str]) -> bool:
        """Apply Gmail label names to a message, creating missing labels first."""
        if not self.service:
            raise RuntimeError("Connector is not authenticated.")
        if not labels:
            return True
        try:
            label_ids = [self._get_or_create_label(name) for name in labels]
            self.service.users().messages().modify(
                userId="me", id=message_id, body={"addLabelIds": label_ids}
            ).execute()
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to apply labels %s to %s: %s", labels, message_id, exc)
            return False

    def _parse_message(self, msg: Dict[str, Any]) -> EmailMessage:
        """Convert a Gmail API message into a normalized EmailMessage."""
        payload = msg["payload"]
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        body_text, body_html = self._extract_body(payload)
        attachments = self._extract_attachments(msg["id"], payload)

        # Parse internal date (milliseconds since epoch) into a datetime.
        received_ms = int(msg.get("internalDate", 0))
        received_at = datetime.fromtimestamp(received_ms / 1000.0)

        return EmailMessage(
            id=msg["id"],
            thread_id=msg["threadId"],
            sender=headers.get("From", ""),
            subject=headers.get("Subject", ""),
            body_text=body_text,
            body_html=body_html,
            received_at=received_at,
            labels=msg.get("labelIds", []),
            attachments=attachments,
            raw_metadata=msg,
        )

    def _extract_body(self, payload: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """Recursively extract plain text and HTML bodies from a message payload."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain" and "data" in payload.get("body", {}):
            return (
                base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                    "utf-8", errors="replace"
                ),
                None,
            )

        if mime_type == "text/html" and "data" in payload.get("body", {}):
            return (
                None,
                base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                    "utf-8", errors="replace"
                ),
            )

        text_body: Optional[str] = None
        html_body: Optional[str] = None
        for part in payload.get("parts", []):
            part_text, part_html = self._extract_body(part)
            if text_body is None and part_text is not None:
                text_body = part_text
            if html_body is None and part_html is not None:
                html_body = part_html
            if text_body and html_body:
                break

        return text_body or "", html_body

    def _extract_attachments(
        self, message_id: str, payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Download and return metadata for all attachments in a message."""
        attachments: List[Dict[str, Any]] = []

        for part in payload.get("parts", []):
            if part.get("filename"):
                att_id = part["body"].get("attachmentId")
                if not att_id:
                    continue
                try:
                    att_data = (
                        self.service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=message_id, id=att_id)
                        .execute()
                    )
                    content_bytes = base64.urlsafe_b64decode(
                        att_data["data"].encode("utf-8")
                    )
                    attachments.append(
                        {
                            "name": part["filename"],
                            "mime_type": part["mimeType"],
                            "size": int(part["body"].get("size", 0)),
                            "content_bytes": content_bytes,
                        }
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    print(f"Failed to download attachment from {message_id}: {exc}")
            else:
                # Recurse into nested multiparts.
                attachments.extend(self._extract_attachments(message_id, part))

        return attachments
