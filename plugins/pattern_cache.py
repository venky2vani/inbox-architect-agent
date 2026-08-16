"""Cache for emails that required LLM classification.

This lightweight store lets --analyze-patterns focus on emails the system
actually struggled with, instead of re-scanning all unread Gmail messages.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins.base import EmailMessage, ProcessedItem

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = "data/llm_required_patterns.json"
MAX_BODY_SNIPPET = 2000


class PatternCache:
    """Persist and load emails that bypassed rules and reached the LLM."""

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path or os.getenv("PATTERN_CACHE_PATH", DEFAULT_CACHE_PATH))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load cached records from disk."""
        if not self.path.exists():
            return {"records": []}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load pattern cache %s: %s", self.path, exc)
            return {"records": []}

    def _save(self) -> None:
        """Persist cached records to disk."""
        try:
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
        except OSError as exc:
            logger.warning("Failed to save pattern cache %s: %s", self.path, exc)

    def record(self, message: EmailMessage, item: ProcessedItem) -> None:
        """Append a lightweight record for an LLM-classified email."""
        record = {
            "id": message.id,
            "thread_id": message.thread_id,
            "sender": message.sender,
            "subject": message.subject,
            "body_text": (message.body_text or "")[:MAX_BODY_SNIPPET],
            "received_at": (
                message.received_at.isoformat()
                if isinstance(message.received_at, datetime)
                else str(message.received_at)
            ),
            "category": item.category,
            "priority": item.priority,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._data["records"].append(record)
        self._save()

    def load_messages(self, limit: Optional[int] = None) -> List[EmailMessage]:
        """Reconstruct EmailMessage objects from the cache.

        Records are returned most-recent first. The optional ``limit`` caps
        the number of messages returned for analysis.
        """
        records = list(reversed(self._data.get("records", [])))
        if limit is not None:
            records = records[:limit]

        messages: List[EmailMessage] = []
        for record in records:
            received_str = record.get("received_at") or "1970-01-01T00:00:00"
            try:
                received_at = datetime.fromisoformat(received_str)
            except ValueError:
                received_at = datetime.fromtimestamp(0, tz=timezone.utc)

            messages.append(
                EmailMessage(
                    id=record.get("id", ""),
                    thread_id=record.get("thread_id", ""),
                    sender=record.get("sender", ""),
                    subject=record.get("subject", ""),
                    body_text=record.get("body_text", ""),
                    body_html=None,
                    received_at=received_at,
                    labels=[],
                    attachments=[],
                    raw_metadata={},
                )
            )
        return messages

    def count(self) -> int:
        """Return the total number of cached records."""
        return len(self._data.get("records", []))

    def reset(self) -> None:
        """Clear the cache."""
        self._data = {"records": []}
        self._save()
