"""Google Workspace persistence plugin.

Sheets  -> Metadata index (searchable, filterable)
Drive   -> Raw content + attachments (organized by date/category)
"""

import copy
import io
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from plugins.base import PersistencePlugin, ProcessedItem
from plugins.retry import retry_with_backoff, is_transient_google_error

logger = logging.getLogger(__name__)

google_retry = retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    exceptions=(Exception,),
    predicate=is_transient_google_error,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleWorkspacePersistence(PersistencePlugin):
    """Store email metadata in Google Sheets and attachments in Google Drive."""

    name = "google_workspace"

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        sheet_name: Optional[str] = None,
        drive_root_name: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"
        )
        self.token_path = token_path or os.getenv(
            "GOOGLE_TOKEN_PATH", "credentials/token.json"
        )
        self.sheet_name = sheet_name or os.getenv(
            "PERSISTENCE_SHEET_NAME", "Email Agent Index"
        )
        self.drive_root_name = drive_root_name or os.getenv(
            "PERSISTENCE_DRIVE_ROOT_NAME", "EmailAgent"
        )
        logger.info("Loading Google Workspace persistence credentials")
        self.creds = self._load_credentials()
        logger.info("Authorizing gspread and Drive service")
        self.sheets = gspread.authorize(self.creds)
        self.drive = build("drive", "v3", credentials=self.creds)

        logger.info("Opening or creating spreadsheet: %s", self.sheet_name)
        self.index_sheet = self._get_or_create_sheet(self.sheet_name)
        self._ensure_headers()
        logger.info("Opening or creating Drive folder: %s", self.drive_root_name)
        self.drive_root_id = self._get_or_create_drive_folder(self.drive_root_name)

    def copy_for_thread(self) -> "GoogleWorkspacePersistence":
        """Return a shallow copy with thread-local Sheets and Drive clients.

        gspread and googleapiclient both use httplib2.Http, which is not
        thread-safe. Each worker thread therefore needs its own clients.
        The credentials object and discovered folder/sheet IDs are shared
        read-only.
        """
        if self.creds is None:
            raise RuntimeError(
                "Persistence must be authenticated before creating thread-local copies."
            )
        new = copy.copy(self)
        new.sheets = gspread.authorize(self.creds)
        new.drive = build("drive", "v3", credentials=self.creds)
        return new

    @google_retry
    def _load_credentials(self) -> Credentials:
        """Load or refresh OAuth2 credentials for Sheets + Drive."""
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        else:
            creds = None

        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            logger.info("Refreshing expired Workspace token")
            start = time.perf_counter()
            creds.refresh(Request())
            logger.info("Workspace token refreshed in %.2fs", time.perf_counter() - start)
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
        elif not creds or not creds.valid:
            raise RuntimeError(
                f"Valid OAuth token not found at {self.token_path}. "
                "Run Gmail authentication first; the same token works here."
            )
        return creds

    @google_retry
    def _get_or_create_sheet(self, name: str):
        """Open an existing sheet or create a new one."""
        try:
            return self.sheets.open(name).sheet1
        except gspread.SpreadsheetNotFound:
            logger.info("Creating new spreadsheet: %s", name)
            sheet = self.sheets.create(name)
            return sheet.sheet1

    def _ensure_headers(self) -> None:
        """Ensure the metadata sheet has the expected header row."""
        headers = [
            "Date",
            "Email ID",
            "Sender",
            "Subject",
            "Category",
            "Priority",
            "Summary",
            "Action Items",
            "Tags",
            "Extracted Type",
            "Drive Link",
            "Status",
        ]
        current = self.index_sheet.row_values(1)
        if current != headers:
            self.index_sheet.clear()
            self.index_sheet.append_row(headers)

    @google_retry
    def _get_or_create_drive_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Return the ID of a Drive folder, creating it if necessary."""
        query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = self.drive.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]

        metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        folder = self.drive.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    @google_retry
    def store_index(self, items: List[ProcessedItem]) -> bool:
        """Append processed items to the Google Sheet index."""
        if not items:
            return True

        logger.info("Appending %d row(s) to sheet index", len(items))
        rows = []
        for item in items:
            tags = item.extracted_data.get("tags", [])
            extracted_type = item.extracted_data.get("type", "other")
            rows.append(
                [
                    datetime.now().isoformat(),
                    item.original_id,
                    item.sender,
                    item.subject,
                    item.category,
                    item.priority,
                    item.summary,
                    "\n".join(f"- {a}" for a in item.action_items),
                    ", ".join(tags),
                    extracted_type,
                    item.drive_link,
                    item.status,
                ]
            )
        start = time.perf_counter()
        self.index_sheet.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info("Sheet index updated in %.2fs", time.perf_counter() - start)
        return True

    @google_retry
    def store_attachment(
        self, email_id: str, attachment: Dict[str, Any], content_bytes: bytes
    ) -> str:
        """Upload an attachment to Google Drive under a date-stamped folder."""
        date_folder = datetime.now().strftime("%Y-%m-%d")
        logger.info("Storing attachment %s in folder %s", attachment["name"], date_folder)
        start = time.perf_counter()
        date_folder_id = self._get_or_create_drive_folder(
            date_folder, parent_id=self.drive_root_id
        )

        safe_email_id = email_id.replace("/", "_")
        safe_name = attachment["name"].replace("/", "_")
        file_name = f"{safe_email_id}_{safe_name}"

        file_metadata = {
            "name": file_name,
            "parents": [date_folder_id],
        }
        media = MediaIoBaseUpload(
            io.BytesIO(content_bytes),
            mimetype=attachment.get("mime_type", "application/octet-stream"),
            resumable=True,
        )
        uploaded = (
            self.drive.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )
        link = uploaded.get(
            "webViewLink", f"https://drive.google.com/file/d/{uploaded['id']}/view"
        )
        logger.info(
            "Attachment %s uploaded in %.2fs",
            attachment["name"],
            time.perf_counter() - start,
        )
        return link

    def get_daily_digest(self, date: datetime) -> List[ProcessedItem]:
        """Retrieve rows from the sheet for a specific date.

        Note: This is a lightweight implementation. For production use, consider
        querying Drive or a local cache instead of scanning the entire sheet.
        """
        date_str = date.strftime("%Y-%m-%d")
        rows = self.index_sheet.get_all_records()
        items: List[ProcessedItem] = []
        for row in rows:
            if row.get("Date", "").startswith(date_str):
                items.append(
                    ProcessedItem(
                        original_id=row.get("Email ID", ""),
                        sender=row.get("Sender", ""),
                        subject=row.get("Subject", ""),
                        category=row.get("Category", ""),
                        priority=int(row.get("Priority", 1)),
                        summary=row.get("Summary", ""),
                        action_items=row.get("Action Items", "").split("\n"),
                        drive_link=row.get("Drive Link", ""),
                        status=row.get("Status", "pending"),
                    )
                )
        return items
