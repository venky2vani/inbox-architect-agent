"""Base plugin interfaces for the Inbox Architect Agent."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class EmailMessage:
    """Normalized representation of an email message."""

    id: str
    thread_id: str
    sender: str
    subject: str
    body_text: str
    body_html: Optional[str]
    received_at: datetime
    labels: List[str] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedItem:
    """Result of processing an email message."""

    original_id: str
    sender: str
    subject: str
    category: str  # action_needed | waiting_for | reference | noise
    priority: int  # 1-5
    summary: str
    action_items: List[str] = field(default_factory=list)
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    destination: str = ""
    drive_link: str = ""
    status: str = "pending"


class EmailConnector(ABC):
    """Base class for all email sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the connector."""
        ...

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with the email service."""
        ...

    @abstractmethod
    def fetch_unread(self, limit: int = 50) -> List[EmailMessage]:
        """Fetch unread messages from the inbox."""
        ...

    @abstractmethod
    def archive(self, message_id: str) -> bool:
        """Archive a message (remove from inbox)."""
        ...

    @abstractmethod
    def mark_processed(self, message_id: str, labels: List[str], keep_unread: bool = False) -> bool:
        """Mark a message as processed.

        Args:
            message_id: Email ID to mark
            labels: List of labels to apply
            keep_unread: If True, preserve email as unread; if False, mark as read
        """
        ...

    def copy_for_thread(self) -> "EmailConnector":
        """Return a thread-safe copy of this plugin instance.

        Subclasses that wrap non-thread-safe network clients (e.g. the
        google-api-python-client service, which uses a non-thread-safe
        httplib2.Http instance) must override this so each worker thread gets
        its own client. The default implementation returns ``self`` and is
        therefore only safe when the subclass is already thread-safe.
        """
        return self


class PersistencePlugin(ABC):
    """Base class for storage backends."""

    @abstractmethod
    def store_index(self, items: List[ProcessedItem]) -> bool:
        """Store processed metadata in an index."""
        ...

    @abstractmethod
    def store_attachment(
        self, email_id: str, attachment: Dict[str, Any], content_bytes: bytes
    ) -> str:
        """Store an attachment and return a link/identifier."""
        ...

    @abstractmethod
    def get_daily_digest(self, date: datetime) -> List[ProcessedItem]:
        """Retrieve processed items for a specific date."""
        ...

    def copy_for_thread(self) -> "PersistencePlugin":
        """Return a thread-safe copy of this plugin instance.

        See :meth:`EmailConnector.copy_for_thread` for details.
        """
        return self


class ProcessorPlugin(ABC):
    """Base class for LLM/post-processing plugins."""

    @abstractmethod
    def process(self, message: EmailMessage) -> ProcessedItem:
        """Process a single email message into a structured item."""
        ...

    def copy_for_thread(self) -> "ProcessorPlugin":
        """Return a thread-safe copy of this plugin instance.

        See :meth:`EmailConnector.copy_for_thread` for details.
        """
        return self
