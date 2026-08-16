"""Review-mode orchestrator for the Inbox Architect Agent.

Runs the daily digest one batch at a time, pauses when an email falls through
all local/dynamic rules and reaches the LLM, and exposes those emails plus
suggested rules for human review.
"""

import json
import logging
import os
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

from agent import InboxArchitectAgent, apply_config, load_config
from plugins.base import EmailMessage, ProcessedItem
from plugins.checkpoint import Checkpoint
from plugins.local_intelligence import LocalIntelligence

logger = logging.getLogger(__name__)


class _ListHandler(logging.Handler):
    """Capture log records into a list and an optional queue for live streaming."""

    def __init__(self, q: queue.Queue) -> None:
        super().__init__()
        self.q = q
        self.records: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:  # pylint: disable=broad-except
            msg = str(record.msg)
        self.records.append(msg)
        self.q.put(msg)


@dataclass
class ReviewItem:
    """A single email that required LLM classification."""

    message_id: str
    sender: str
    subject: str
    body_preview: str
    llm_category: str
    llm_priority: int
    llm_summary: str
    suggested_rule: Dict[str, Any]
    processed: ProcessedItem


@dataclass
class ReviewBatch:
    """State for one paused batch."""

    batch_number: int
    total_emails: int
    processed_count: int
    llm_required_count: int
    items: List[ReviewItem] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    status: str = "reviewing"  # running | reviewing | done | error
    error: Optional[str] = None


class ReviewRunner:
    """Orchestrate agent in interactive review mode."""

    def __init__(self, config_path: str = "config.yaml"):
        # Ensure INFO-level logs are emitted so the UI can capture and display them.
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            force=True,
        )
        self.config_path = config_path
        self.config = load_config(config_path)
        apply_config(self.config)
        self.agent = InboxArchitectAgent()
        self.agent.load_plugins()
        self._configure_credentials()
        self.agent.authenticate_connectors()

        self.review_items: List[ReviewItem] = []
        self.current_batch: Optional[ReviewBatch] = None
        self.message_ids: List[Dict[str, str]] = []
        self.total_fetched: int = 0
        self.batch_size: int = 50
        self.limit: int = 500
        self.archive_noise: bool = True
        self.dry_run: bool = False
        self.resume: bool = False
        self.checkpoint_path: Optional[str] = None
        self._authenticated = True

        # Async batch execution state for live log streaming.
        self._stream_queue: queue.Queue = queue.Queue()
        self._batch_running: bool = False
        self._batch_thread: Optional[threading.Thread] = None

        # Attach LLM callback to the first processor.
        if self.agent.processors:
            processor = self.agent.processors[0]
            processor.on_llm_required = self._on_llm_required

    def _configure_credentials(self) -> None:
        """Ensure credential env vars point at the credentials directory."""
        credentials_dir = os.getenv("CREDENTIALS_DIR", "credentials")
        os.environ.setdefault(
            "GMAIL_CREDENTIALS_PATH", f"{credentials_dir}/credentials.json"
        )
        os.environ.setdefault("GMAIL_TOKEN_PATH", f"{credentials_dir}/token.json")
        os.environ.setdefault(
            "GOOGLE_CREDENTIALS_PATH", f"{credentials_dir}/credentials.json"
        )
        os.environ.setdefault("GOOGLE_TOKEN_PATH", f"{credentials_dir}/token.json")

    def _extract_domain(self, sender: str) -> str:
        """Extract the email domain from a sender string."""
        match = re.search(r"[\w\.\-]+@([\w\.\-]+)", sender)
        return match.group(1).lower() if match else ""

    def _body_preview(self, body: Optional[str], max_chars: int = 300) -> str:
        """Return a short, clean preview of the email body."""
        if not body:
            return ""
        text = re.sub(r"\s+", " ", body).strip()
        return text[:max_chars] + ("..." if len(text) > max_chars else "")

    def _suggest_rule(
        self, message: EmailMessage, item: ProcessedItem
    ) -> Dict[str, Any]:
        """Suggest the most useful automation rule for this email."""
        domain = self._extract_domain(message.sender)
        if domain:
            return {
                "type": "sender_domain",
                "value": domain,
                "category": item.category,
                "priority": item.priority,
                "description": f"Emails from @{domain} → {item.category}",
            }

        # Fallback to subject keyword if domain extraction fails.
        intel = LocalIntelligence()
        keywords = intel._extract_keywords(message.subject, top_n=3)
        keyword = keywords[0] if keywords else ""
        return {
            "type": "subject_keyword",
            "value": keyword,
            "category": item.category,
            "priority": item.priority,
            "description": f"Subject contains '{keyword}' → {item.category}",
        }

    def _on_llm_required(
        self, message: EmailMessage, processed: ProcessedItem
    ) -> None:
        """Callback invoked by SmartInboxProcessor when it calls the LLM."""
        suggestion = self._suggest_rule(message, processed)
        review_item = ReviewItem(
            message_id=message.id,
            sender=message.sender,
            subject=message.subject,
            body_preview=self._body_preview(message.body_text),
            llm_category=processed.category,
            llm_priority=processed.priority,
            llm_summary=processed.summary,
            suggested_rule=suggestion,
            processed=processed,
        )
        self.review_items.append(review_item)

    def setup(
        self,
        limit: int = 500,
        batch_size: int = 50,
        archive_noise: bool = True,
        dry_run: bool = False,
        resume: bool = False,
    ) -> None:
        """Prepare message list and checkpoint for the review run."""
        self.limit = limit
        self.batch_size = batch_size
        self.archive_noise = archive_noise
        self.dry_run = dry_run
        self.resume = resume
        self.checkpoint_path = os.getenv(
            "CHECKPOINT_PATH", self.config.get("agent", {}).get("daily_digest", {}).get("checkpoint_path", "data/checkpoint.json")
        )

        digest_config = self.config.get("agent", {}).get("daily_digest", {})
        limit = limit if limit is not None else digest_config.get("limit", 500)
        archive_noise = (
            archive_noise
            if archive_noise is not None
            else digest_config.get("archive_noise", True)
        )
        batch_size = batch_size if batch_size is not None else digest_config.get("batch_size", 50)

        if resume:
            self.agent.checkpoint = Checkpoint(self.checkpoint_path)
        else:
            self.agent.checkpoint = None

        self.message_ids = []
        for connector in self.agent.connectors:
            ids = connector._list_unread_ids(limit)
            if resume and self.agent.checkpoint:
                ids = [
                    m for m in ids if not self.agent.checkpoint.is_processed(m["id"])
                ]
            self.message_ids.extend(ids)

        # Deduplicate by ID.
        seen: set = set()
        unique: List[Dict[str, str]] = []
        for m in self.message_ids:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)
        self.message_ids = unique
        self.total_fetched = len(self.message_ids)

    def _capture_logs(self, q: queue.Queue) -> _ListHandler:
        """Attach a list handler to the root logger and return it."""
        handler = _ListHandler(q)
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(handler)
        return handler

    def run_batch(self) -> ReviewBatch:
        """Process the next batch of emails and return a paused ReviewBatch."""
        if not self.message_ids:
            return ReviewBatch(
                batch_number=0,
                total_emails=0,
                processed_count=0,
                llm_required_count=0,
                status="done",
            )

        self.review_items = []
        batch_ids = self.message_ids[: self.batch_size]
        self.message_ids = self.message_ids[self.batch_size :]

        batch_number = (
            (self.total_fetched - len(self.message_ids) - 1) // self.batch_size
        ) + 1

        log_handler = self._capture_logs(self._stream_queue)
        try:
            processed = self.agent._process_batch(
                self.agent.connectors[0],
                batch_ids,
                self.archive_noise,
                self.dry_run,
            )
            if not self.dry_run and processed and self.agent.persistence:
                try:
                    self.agent.persistence.store_index(processed)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Failed to store batch index: %s", exc)

            # Persist intermediate checkpoint if enabled.
            if self.agent.checkpoint:
                self.agent.checkpoint._save()

            total_llm = len(self.review_items)
            self.current_batch = ReviewBatch(
                batch_number=batch_number,
                total_emails=self.total_fetched,
                processed_count=len(batch_ids) - len(self.agent.failed_ids),
                llm_required_count=total_llm,
                items=self.review_items,
                logs=log_handler.records,
                status="reviewing" if total_llm > 0 else "running",
            )
            return self.current_batch
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Batch failed")
            return ReviewBatch(
                batch_number=batch_number,
                total_emails=self.total_fetched,
                processed_count=0,
                llm_required_count=0,
                logs=log_handler.records,
                status="error",
                error=str(exc),
            )
        finally:
            logging.getLogger().removeHandler(log_handler)

    def run_batch_async(self) -> bool:
        """Start the next batch in a background thread for live log streaming.

        Returns True if a batch was started, False if already running or done.
        """
        if self._batch_running:
            return False
        if not self.message_ids:
            return False

        self._batch_running = True
        # Drain any stale log lines from previous runs.
        while not self._stream_queue.empty():
            try:
                self._stream_queue.get_nowait()
            except queue.Empty:
                break

        def _target() -> None:
            try:
                self.run_batch()
            except Exception:  # pylint: disable=broad-except
                logger.exception("Async batch failed")
            finally:
                self._batch_running = False
                self._stream_queue.put(None)  # sentinel

        self._batch_thread = threading.Thread(target=_target, daemon=True)
        self._batch_thread.start()
        return True

    def accept_rule(self, message_id: str, rule_type: Optional[str] = None) -> Dict[str, Any]:
        """Accept a suggested rule and persist it."""
        item = next((ri for ri in self.review_items if ri.message_id == message_id), None)
        if item is None:
            return {"ok": False, "error": "Message not found in current review batch"}

        suggestion = item.suggested_rule
        if rule_type:
            # Allow caller to override which rule type to accept.
            pass

        if suggestion["type"] == "sender_domain":
            from plugins.dynamic_classifier import DynamicClassifier

            classifier = DynamicClassifier()
            classifier.confirm_label(suggestion["value"], suggestion["category"])
            return {
                "ok": True,
                "rule": suggestion,
                "applied_to": "data/dynamic_labels.json",
            }

        # Subject/keyword rules go to local intelligence.
        intel = LocalIntelligence()
        intel.learn(
            EmailMessage(
                id=item.message_id,
                thread_id="",
                sender=item.sender,
                subject=item.subject,
                body_text="",
                body_html=None,
                received_at=datetime.now(timezone.utc),
            ),
            item.processed,
        )
        return {
            "ok": True,
            "rule": suggestion,
            "applied_to": "data/local_rules.json",
        }

    def reject_rule(self, message_id: str) -> Dict[str, Any]:
        """Mark a suggested rule as rejected so it is not re-suggested."""
        item = next((ri for ri in self.review_items if ri.message_id == message_id), None)
        if item is None:
            return {"ok": False, "error": "Message not found"}

        if item.suggested_rule["type"] == "sender_domain":
            from plugins.dynamic_classifier import DynamicClassifier

            classifier = DynamicClassifier()
            classifier.reject_pattern(item.suggested_rule["value"])
        return {"ok": True, "message": "Rule rejected"}

    def get_status(self) -> Dict[str, Any]:
        """Return current runner status for the UI."""
        remaining = len(self.message_ids)
        processed = self.total_fetched - remaining
        return {
            "authenticated": self._authenticated,
            "total_fetched": self.total_fetched,
            "processed": processed,
            "remaining": remaining,
            "batch": self.current_batch.status if self.current_batch else "idle",
            "llm_calls": getattr(
                self.agent.processors[0], "llm_calls", 0
            )
            if self.agent.processors
            else 0,
            "local_hits": getattr(
                self.agent.processors[0], "local_hits", 0
            )
            if self.agent.processors
            else 0,
        }
