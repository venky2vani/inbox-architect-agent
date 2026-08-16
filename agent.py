"""Inbox Architect Agent orchestrator.

Loads connectors, processors, and persistence plugins dynamically and runs the
daily digest workflow.
"""

import argparse
import importlib
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

from plugins.base import (
    EmailConnector,
    PersistencePlugin,
    ProcessedItem,
    ProcessorPlugin,
)
from plugins.checkpoint import Checkpoint

logger = logging.getLogger(__name__)


class InboxArchitectAgent:
    """Coordinates plugins to fetch, process, and store emails."""

    def __init__(self, plugins_dir: str = "plugins"):
        self.connectors: List[EmailConnector] = []
        self.persistence: PersistencePlugin | None = None
        self.processors: List[ProcessorPlugin] = []
        self.plugins_dir = plugins_dir
        self.checkpoint: Optional[Checkpoint] = None
        self.failed_ids: List[str] = []
        # Parallel processing configuration. All plugins implement copy_for_thread()
        # safely, so parallel processing is enabled by default for performance.
        # Disable with PARALLEL_PROCESSING=false if needed for debugging.
        self.max_workers = int(os.getenv("PARALLEL_MAX_WORKERS", "0"))
        if self.max_workers <= 0:
            # Auto-detect: CPU count * 2, capped at 8
            self.max_workers = min(8, (os.cpu_count() or 4) * 2)
        self.use_parallel = os.getenv("PARALLEL_PROCESSING", "true").lower() == "true"

    def load_plugins(self) -> None:
        """Discover and instantiate plugins from the plugins directory."""
        logger.info("Loading plugins from %s", self.plugins_dir)
        for filename in sorted(os.listdir(self.plugins_dir)):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue

            module_name = f"{self.plugins_dir}.{filename[:-3]}"
            logger.debug("Importing module %s", module_name)
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to import %s: %s", module_name, exc)
                continue

            self._register_connector(module, filename)
            self._register_persistence(module, filename)
            self._register_processor(module, filename)

        if not self.connectors:
            logger.warning("No email connectors loaded.")
        if not self.persistence:
            logger.warning("No persistence plugin loaded.")
        if not self.processors:
            logger.warning("No processor plugin loaded.")

    def _register_connector(self, module, filename: str) -> None:
        """Instantiate a connector class from a module if present."""
        if not filename.endswith("_connector.py"):
            return
        cls = self._find_plugin_class(module, filename, EmailConnector)
        if cls:
            try:
                instance = cls()
                self.connectors.append(instance)
                logger.info("Loaded connector: %s", instance.name)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to instantiate %s: %s", cls.__name__, exc)

    def _register_persistence(self, module, filename: str) -> None:
        """Instantiate a persistence class from a module if present."""
        if not filename.endswith("_persistence.py"):
            return
        cls = self._find_plugin_class(module, filename, PersistencePlugin)
        if cls:
            try:
                instance = cls()
                self.persistence = instance
                logger.info("Loaded persistence: %s", instance.name)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to instantiate %s: %s", cls.__name__, exc)

    def _register_processor(self, module, filename: str) -> None:
        """Instantiate a processor class from a module if present."""
        if not filename.endswith("_processor.py"):
            return
        cls = self._find_plugin_class(module, filename, ProcessorPlugin)
        if cls:
            try:
                instance = cls()
                self.processors.append(instance)
                logger.info("Loaded processor: %s", instance.name)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to instantiate %s: %s", cls.__name__, exc)

    def _find_plugin_class(self, module, filename: str, base_class: type) -> type | None:
        """Find a plugin class in a module by convention or inheritance.

        First try the PascalCase name derived from the filename. If that does
        not exist or is not the expected base class, fall back to the first
        class in the module that inherits from the base class.
        """
        class_name = self._to_class_name(filename[:-3])
        cls = getattr(module, class_name, None)
        if cls and isinstance(cls, type) and issubclass(cls, base_class):
            return cls

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, base_class)
                and attr is not base_class
            ):
                return attr
        return None

    @staticmethod
    def _to_class_name(filename: str) -> str:
        """Convert snake_case filename to PascalCase class name."""
        return "".join(part.title() for part in filename.split("_"))

    def authenticate_connectors(self) -> None:
        """Run authentication for every loaded connector."""
        for connector in self.connectors:
            logger.info("Authenticating connector: %s", connector.name)
            start = time.perf_counter()
            connector.authenticate()
            elapsed = time.perf_counter() - start
            logger.info("Authenticated %s in %.2fs", connector.name, elapsed)

    def analyze_patterns(self, limit: int = 200) -> None:
        """Analyze emails for emerging patterns and suggest new dynamic labels."""
        from plugins.dynamic_classifier import DynamicClassifier

        classifier = DynamicClassifier()

        if not self.connectors:
            raise RuntimeError("No connectors available.")

        all_messages: List[Any] = []
        for connector in self.connectors:
            logger.info("Fetching %d emails for pattern analysis...", limit)
            message_ids = connector._list_unread_ids(limit)
            logger.info("Fetched %d message IDs", len(message_ids))

            for msg_meta in message_ids:
                try:
                    msg = connector.fetch_message_by_id(msg_meta["id"])
                    all_messages.append(msg)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Failed to fetch message %s: %s", msg_meta["id"], exc)

        if not all_messages:
            logger.warning("No messages found for analysis")
            return

        logger.info("Analyzing %d emails for patterns...", len(all_messages))
        suggestions = classifier.analyze_emails(all_messages)

        if not suggestions:
            print("\n✓ No new patterns found. Your current categories are comprehensive!")
            return

        print(f"\n🎯 Found {len(suggestions)} potential new categories:\n")
        approved_count = 0
        rejected_count = 0

        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion['suggested_label'].upper()}")
            print(f"   Domain: {suggestion['domain']}")
            print(f"   Emails: {suggestion['email_count']}")
            print(f"   Confidence: {suggestion['confidence']:.1%}")
            print(f"   Description: {suggestion['suggested_description']}")

            while True:
                response = input("   Approve? (y/n/skip): ").strip().lower()
                if response in ("y", "yes"):
                    classifier.confirm_label(
                        suggestion['domain'],
                        suggestion['suggested_label']
                    )
                    print(f"   ✓ Approved!\n")
                    approved_count += 1
                    break
                elif response in ("n", "no"):
                    classifier.reject_pattern(suggestion['domain'])
                    print(f"   ✗ Rejected\n")
                    rejected_count += 1
                    break
                elif response in ("s", "skip"):
                    print(f"   ⊘ Skipped\n")
                    break
                else:
                    print("   Invalid input. Please enter: y (approve), n (reject), or skip")

        output_path = "data/pattern_review.md"
        classifier.export_suggestions_to_file(suggestions, output_path)
        print(f"\n📊 Results: {approved_count} approved, {rejected_count} rejected")
        print(f"✓ Full suggestions saved to: {output_path}")

    def confirm_label(self, domain: str, label: str) -> None:
        """Confirm a dynamic label for a domain."""
        from plugins.dynamic_classifier import DynamicClassifier
        classifier = DynamicClassifier()
        classifier.confirm_label(domain, label)
        print(f"✓ Confirmed label '{label}' for domain: {domain}")
        print(f"✓ New label saved to: data/dynamic_labels.json")

    def reject_pattern(self, domain: str) -> None:
        """Reject a suggested pattern for a domain."""
        from plugins.dynamic_classifier import DynamicClassifier
        classifier = DynamicClassifier()
        classifier.reject_pattern(domain)
        print(f"✓ Rejected pattern for domain: {domain}")
        print(f"✓ Pattern will be skipped in future analyses")

    def run_daily_digest(
        self,
        limit: int = 50,
        archive_noise: bool = True,
        dry_run: bool = False,
        batch_size: int = 50,
        resume: bool = False,
        checkpoint_path: Optional[str] = None,
    ) -> None:
        """Main execution loop: fetch, process, store, and optionally archive."""
        if not self.connectors:
            raise RuntimeError("No connectors available.")
        if not dry_run and not self.persistence:
            raise RuntimeError("No persistence plugin available.")
        if not self.processors:
            raise RuntimeError("No processor plugin available.")

        if dry_run:
            logger.info("DRY RUN: no emails will be archived or stored")

        self.checkpoint = Checkpoint(checkpoint_path) if resume else None
        if resume:
            logger.info(
                "Resume enabled; %d message(s) already processed",
                self.checkpoint.processed_count if self.checkpoint else 0,
            )

        all_processed: List[ProcessedItem] = []
        total_attempted = 0
        total_failed = 0
        run_start = time.perf_counter()

        for connector in self.connectors:
            logger.info("Listing unread messages from %s (limit=%d)", connector.name, limit)
            start_list = time.perf_counter()
            message_ids = connector._list_unread_ids(limit)
            logger.info(
                "Listed %d unread message ID(s) from %s in %.2fs",
                len(message_ids),
                connector.name,
                time.perf_counter() - start_list,
            )

            if resume and self.checkpoint:
                original_count = len(message_ids)
                message_ids = [
                    m for m in message_ids if not self.checkpoint.is_processed(m["id"])
                ]
                logger.info(
                    "Skipping %d already-processed message(s); %d remaining",
                    original_count - len(message_ids),
                    len(message_ids),
                )

            total = len(message_ids)
            for batch_start in range(0, total, batch_size):
                batch_ids = message_ids[batch_start : batch_start + batch_size]
                logger.info(
                    "Processing batch %d-%d of %d",
                    batch_start + 1,
                    min(batch_start + batch_size, total),
                    total,
                )
                batch_processed = self._process_batch(
                    connector,
                    batch_ids,
                    archive_noise,
                    dry_run,
                )
                all_processed.extend(batch_processed)
                total_attempted += len(batch_ids)
                total_failed += len(batch_ids) - len(batch_processed)

                # Persist intermediate results so data is not lost on crash.
                if not dry_run and batch_processed and self.persistence:
                    try:
                        self.persistence.store_index(batch_processed)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error("Failed to store batch index: %s", exc)

        elapsed = time.perf_counter() - run_start
        logger.info("Run completed in %.2fs", elapsed)
        self._print_summary(
            all_processed,
            total_attempted,
            total_failed,
            elapsed,
        )

    def _process_batch(
        self,
        connector: EmailConnector,
        batch_ids: List[Dict[str, str]],
        archive_noise: bool,
        dry_run: bool,
    ) -> List[ProcessedItem]:
        """Fetch and process a batch of message IDs.

        Uses parallel processing if enabled (default), otherwise sequential.
        """
        if self.use_parallel and len(batch_ids) > 1:
            return self._process_batch_parallel(connector, batch_ids, archive_noise, dry_run)
        return self._process_batch_sequential(connector, batch_ids, archive_noise, dry_run)

    def _process_batch_parallel(
        self,
        connector: EmailConnector,
        batch_ids: List[Dict[str, str]],
        archive_noise: bool,
        dry_run: bool,
    ) -> List[ProcessedItem]:
        """Process batch in parallel using ThreadPoolExecutor.

        Each worker thread receives its own copies of the connector and
        persistence plugins. The underlying Google API clients use httplib2,
        which is not thread-safe, so sharing a single service across threads
        leads to crashes such as segmentation faults.
        """
        if dry_run:
            logger.warning(
                "DRY RUN: no emails will be archived or labeled in Gmail for this batch"
            )

        batch_processed: List[ProcessedItem] = []
        total = len(batch_ids)

        logger.info("Processing %d emails with %d parallel workers", total, self.max_workers)

        processor = self.processors[0]
        base_persistence = self.persistence
        thread_local = threading.local()

        def get_thread_connector() -> EmailConnector:
            """Return a thread-local copy of the connector."""
            if not hasattr(thread_local, "connector"):
                thread_local.connector = connector.copy_for_thread()
            return thread_local.connector

        def get_thread_persistence() -> Optional[PersistencePlugin]:
            """Return a thread-local copy of the persistence plugin (if any)."""
            if base_persistence is None:
                return None
            if not hasattr(thread_local, "persistence"):
                thread_local.persistence = base_persistence.copy_for_thread()
            return thread_local.persistence

        def worker_task(
            msg_meta: Dict[str, str], idx: int, total: int
        ) -> Optional[ProcessedItem]:
            """Callable executed in each worker thread."""
            return self._process_single_email(
                get_thread_connector(),
                processor,
                msg_meta,
                archive_noise,
                dry_run,
                idx,
                total,
                get_thread_persistence(),
            )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(worker_task, msg_meta, idx, total): (idx, msg_meta)
                for idx, msg_meta in enumerate(batch_ids, 1)
            }

            # Process completed tasks as they finish
            for future in as_completed(futures):
                idx, msg_meta = futures[future]
                try:
                    result = future.result(timeout=120)  # 120 second timeout per email
                    if result is not None:
                        batch_processed.append(result)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error(
                        "[%d/%d] Failed to process message %s: %s",
                        idx,
                        total,
                        msg_meta["id"],
                        exc,
                    )
                    self.failed_ids.append(msg_meta["id"])

        return batch_processed

    def _process_single_email(
        self,
        connector: EmailConnector,
        processor: ProcessorPlugin,
        msg_meta: Dict[str, str],
        archive_noise: bool,
        dry_run: bool,
        idx: int,
        total: int,
        persistence: Optional[PersistencePlugin] = None,
    ) -> Optional[ProcessedItem]:
        """Process a single email (can be called in parallel).

        When ``persistence`` is provided it is used for attachment storage instead
        of ``self.persistence``. This lets worker threads use thread-local
        persistence instances that wrap non-thread-safe network clients.
        """
        msg_id = msg_meta["id"]
        try:
            logger.debug("[%d/%d] Fetching message %s", idx, total, msg_id)
            msg = connector.fetch_message_by_id(msg_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[%d/%d] Failed to fetch message %s: %s", idx, total, msg_id, exc)
            self.failed_ids.append(msg_id)
            return None

        logger.info("[%d/%d] Processing: %s", idx, total, msg.subject[:60])
        try:
            start_process = time.perf_counter()
            processed = processor.process(msg)
            elapsed_process = time.perf_counter() - start_process
            logger.info(
                "[%d/%d] Categorized as %s (priority=%d) in %.2fs",
                idx,
                total,
                processed.category,
                processed.priority,
                elapsed_process,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("[%d/%d] Failed to process message %s: %s", idx, total, msg_id, exc)
            self.failed_ids.append(msg_id)
            return None

        # Store attachments
        if not dry_run and msg.attachments and persistence:
            drive_links: List[str] = []
            for att in msg.attachments:
                try:
                    link = persistence.store_attachment(msg.id, att, att["content_bytes"])
                    logger.info("Stored attachment %s", att["name"])
                    drive_links.append(link)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Failed to store attachment %s: %s", att["name"], exc)
            processed.drive_link = "\n".join(drive_links)

        # Archive noise
        if archive_noise and processed.category == "noise":
            if dry_run:
                logger.info("[dry-run] Would archive: %s", msg.subject[:60])
            else:
                try:
                    connector.archive(msg.id)
                    logger.info("Archived noise: %s", msg.subject[:60])
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Failed to archive message %s: %s", msg.id, exc)

        # Apply Gmail labels
        labels_to_apply: List[str] = []
        category = processed.category
        if category:
            labels_to_apply.append(category.replace("_", " ").title().replace(" ", "_"))

        email_type = (processed.extracted_data or {}).get("type", "other")
        if email_type and email_type != "other":
            type_label = email_type.title()
            if type_label not in labels_to_apply:
                labels_to_apply.append(type_label)

        if labels_to_apply:
            if dry_run:
                logger.info("[dry-run] Would apply labels %s to: %s", labels_to_apply, msg.subject[:60])
            else:
                try:
                    connector.mark_processed(msg.id, labels_to_apply)
                    logger.info("Applied labels %s to: %s", labels_to_apply, msg.subject[:60])
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Failed to apply labels to %s: %s", msg.id, exc)

        # Update checkpoint
        if self.checkpoint:
            self.checkpoint.mark_processed(msg.id)

        return processed

    def _process_batch_sequential(
        self,
        connector: EmailConnector,
        batch_ids: List[Dict[str, str]],
        archive_noise: bool,
        dry_run: bool,
    ) -> List[ProcessedItem]:
        """Process batch sequentially (original implementation)."""
        if dry_run:
            logger.warning(
                "DRY RUN: no emails will be archived or labeled in Gmail for this batch"
            )

        processor = self.processors[0]
        batch_processed: List[ProcessedItem] = []

        for idx, msg_meta in enumerate(batch_ids, 1):
            msg_id = msg_meta["id"]
            try:
                logger.debug("Fetching message %s", msg_id)
                msg = connector.fetch_message_by_id(msg_id)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[%d/%d] Failed to fetch message %s: %s", idx, len(batch_ids), msg_id, exc)
                self.failed_ids.append(msg_id)
                continue

            logger.info(
                "[%d/%d] Processing: %s",
                idx,
                len(batch_ids),
                msg.subject[:60],
            )
            try:
                start_process = time.perf_counter()
                processed = processor.process(msg)
                elapsed_process = time.perf_counter() - start_process
                logger.info(
                    "[%d/%d] Categorized as %s (priority=%d) in %.2fs",
                    idx,
                    len(batch_ids),
                    processed.category,
                    processed.priority,
                    elapsed_process,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "[%d/%d] Failed to process message %s: %s",
                    idx,
                    len(batch_ids),
                    msg_id,
                    exc,
                )
                self.failed_ids.append(msg_id)
                continue

            # Store attachments and update drive link.
            if not dry_run and msg.attachments and self.persistence:
                drive_links: List[str] = []
                for att in msg.attachments:
                    try:
                        start_att = time.perf_counter()
                        link = self.persistence.store_attachment(
                            msg.id, att, att["content_bytes"]
                        )
                        elapsed_att = time.perf_counter() - start_att
                        logger.info(
                            "Stored attachment %s in %.2fs",
                            att["name"],
                            elapsed_att,
                        )
                        drive_links.append(link)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error(
                            "Failed to store attachment %s: %s", att["name"], exc
                        )
                processed.drive_link = "\n".join(drive_links)

            batch_processed.append(processed)

            # Archive noise automatically if configured.
            if archive_noise and processed.category == "noise":
                if dry_run:
                    logger.info("[dry-run] Would archive: %s", msg.subject[:60])
                else:
                    logger.info("Archiving noise: %s", msg.subject[:60])
                    try:
                        connector.archive(msg.id)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error("Failed to archive message %s: %s", msg.id, exc)

            # Compute Gmail labels based on the category and extracted type.
            labels_to_apply: List[str] = []

            # Category label (e.g. Banking_Investment, Action_Needed, Noise).
            category = processed.category
            if category:
                labels_to_apply.append(
                    category.replace("_", " ").title().replace(" ", "_")
                )

            # Type label from extracted data (e.g. Invoice, Payment, Bill).
            email_type = (processed.extracted_data or {}).get("type", "other")
            if email_type and email_type != "other":
                type_label = email_type.title()
                if type_label not in labels_to_apply:
                    labels_to_apply.append(type_label)

            if labels_to_apply:
                if dry_run:
                    logger.info(
                        "[dry-run] Would apply labels %s to: %s",
                        labels_to_apply,
                        msg.subject[:60],
                    )
                else:
                    logger.info(
                        "Applying labels %s to: %s", labels_to_apply, msg.subject[:60]
                    )
                    try:
                        connector.mark_processed(msg.id, labels_to_apply)
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error("Failed to apply labels to %s: %s", msg.id, exc)

            # Update checkpoint after each successful email.
            if self.checkpoint:
                self.checkpoint.mark_processed(msg.id)

        return batch_processed

    def _print_summary(
        self,
        items: List[ProcessedItem],
        attempted: int,
        failed: int,
        elapsed: float,
    ) -> None:
        """Print a concise console summary of processed items."""
        processor = self.processors[0] if self.processors else None
        print("\n--- Daily Digest Summary ---")
        print(f"Generated at: {datetime.now().isoformat()}")
        print(f"Total attempted: {attempted}")
        print(f"Successfully processed: {len(items)}")
        print(f"Failed: {failed}")
        if self.failed_ids:
            print(f"Failed message IDs: {', '.join(self.failed_ids[:10])}{'...' if len(self.failed_ids) > 10 else ''}")
        for category in ["action_needed", "waiting_for", "reference", "noise"]:
            count = sum(1 for i in items if i.category == category)
            print(f"  {category}: {count}")
        if (
            processor
            and hasattr(processor, "local_hits")
            and hasattr(processor, "llm_calls")
            and isinstance(getattr(processor, "local_hits", None), int)
            and isinstance(getattr(processor, "llm_calls", None), int)
        ):
            print(f"Local intelligence hits: {processor.local_hits}")
            print(f"LLM calls: {processor.llm_calls}")
        print(f"Total elapsed: {elapsed:.2f}s")
        print("----------------------------")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML configuration if it exists."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def apply_config(config: Dict[str, Any]) -> None:
    """Map config values to environment variables so plugins can read them."""
    mappings = {
        ("gmail", "credentials_path"): "GMAIL_CREDENTIALS_PATH",
        ("gmail", "token_path"): "GMAIL_TOKEN_PATH",
        ("gmail", "archive_label"): "GMAIL_ARCHIVE_LABEL",
        ("persistence", "credentials_path"): "GOOGLE_CREDENTIALS_PATH",
        ("persistence", "token_path"): "GOOGLE_TOKEN_PATH",
        ("persistence", "sheet_name"): "PERSISTENCE_SHEET_NAME",
        ("persistence", "drive_root_name"): "PERSISTENCE_DRIVE_ROOT_NAME",
        ("processor", "model"): "PROCESSOR_MODEL",
        ("processor", "base_url"): "OPENAI_BASE_URL",
        ("processor", "provider"): "LLM_PROVIDER",
        ("processor", "prompt_path"): "LLM_SYSTEM_PROMPT_PATH",
        ("processor", "local_intelligence", "enabled"): "LOCAL_INTELLIGENCE_ENABLED",
        ("processor", "local_intelligence", "rules_path"): "LOCAL_INTELLIGENCE_PATH",
        ("processor", "local_intelligence", "confidence_threshold"): "LOCAL_INTELLIGENCE_THRESHOLD",
        ("processor", "local_intelligence", "min_hits"): "LOCAL_INTELLIGENCE_MIN_HITS",
        ("processor", "local_intelligence", "prune_after_days"): "LOCAL_INTELLIGENCE_PRUNE_DAYS",
        ("processor", "rate_limit_delay"): "LLM_RATE_LIMIT_DELAY",
        ("agent", "daily_digest", "batch_size"): "DAILY_DIGEST_BATCH_SIZE",
        ("agent", "daily_digest", "checkpoint_path"): "CHECKPOINT_PATH",
    }

    processor_rules = config.get("processor", {}).get("rules", {})
    rule_mappings = {
        "high_priority_senders": "HIGH_PRIORITY_SENDERS",
        "low_priority_senders": "LOW_PRIORITY_SENDERS",
        "always_noise_senders": "ALWAYS_NOISE_SENDERS",
        "custom": "CUSTOM_RULES",
    }
    for key, env_var in rule_mappings.items():
        value = processor_rules.get(key)
        if value and not os.getenv(env_var):
            os.environ[env_var] = str(value).strip()

    for keys, env_var in mappings.items():
        value = config
        for key in keys:
            value = value.get(key, {}) if isinstance(value, dict) else None
            if value is None:
                break
        if value and not os.getenv(env_var):
            os.environ[env_var] = str(value)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Inbox Architect Agent — daily email triage and summarization."
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Process emails without archiving or writing to Sheets/Drive.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum unread emails to fetch (default: config.agent.daily_digest.limit or 50).",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        default=None,
        help="Do not archive emails categorized as noise.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml).",
    )
    parser.add_argument(
        "--credentials-dir",
        type=str,
        default="credentials",
        help="Directory containing OAuth credentials.json and token.json.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO).",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Optional log file path (default: log to console only).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Resume from the last checkpoint and skip already-processed emails.",
    )
    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        default=False,
        help="Reset the checkpoint before running.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Number of emails to process before persisting intermediate results.",
    )
    parser.add_argument(
        "--analyze-patterns",
        action="store_true",
        help="Analyze emails for new emerging patterns and suggest dynamic labels.",
    )
    parser.add_argument(
        "--confirm-label",
        nargs=2,
        metavar=("DOMAIN", "LABEL"),
        help="Confirm a suggested dynamic label (requires DOMAIN and LABEL name).",
    )
    parser.add_argument(
        "--reject-pattern",
        metavar="DOMAIN",
        help="Reject a suggested pattern from analysis.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the interactive review UI server (http://127.0.0.1:8000).",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Configure logging before anything else so startup messages are captured.
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: List[Any] = [logging.StreamHandler()]
    if args.log_file:
        os.makedirs(os.path.dirname(args.log_file) or ".", exist_ok=True)
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format=log_format,
        handlers=handlers,
        force=True,
    )

    # Load .env first so config.yaml can reference env vars if needed.
    load_dotenv()

    # Load and apply config.yaml settings.
    config = load_config(args.config)
    apply_config(config)

    # Resolve CLI overrides against config defaults.
    digest_config = config.get("agent", {}).get("daily_digest", {})
    limit = args.limit if args.limit is not None else digest_config.get("limit", 50)
    archive_noise = (
        not args.no_archive
        if args.no_archive is not None
        else digest_config.get("archive_noise", True)
    )
    batch_size = (
        args.batch_size
        if args.batch_size is not None
        else digest_config.get("batch_size", 50)
    )

    # Derive credential paths from config/env/CLI.
    credentials_dir = args.credentials_dir
    os.environ.setdefault("GMAIL_CREDENTIALS_PATH", f"{credentials_dir}/credentials.json")
    os.environ.setdefault("GMAIL_TOKEN_PATH", f"{credentials_dir}/token.json")
    os.environ.setdefault("GOOGLE_CREDENTIALS_PATH", f"{credentials_dir}/credentials.json")
    os.environ.setdefault("GOOGLE_TOKEN_PATH", f"{credentials_dir}/token.json")

    agent = InboxArchitectAgent()
    agent.load_plugins()

    if args.reset_checkpoint:
        checkpoint_path = os.getenv("CHECKPOINT_PATH", "data/checkpoint.json")
        logger.info("Resetting checkpoint: %s", checkpoint_path)
        Checkpoint(checkpoint_path).reset()

    agent.authenticate_connectors()

    if args.analyze_patterns:
        agent.analyze_patterns(limit=limit)
        return

    if args.confirm_label:
        domain, label = args.confirm_label
        agent.confirm_label(domain, label)
        return

    if args.reject_pattern:
        agent.reject_pattern(args.reject_pattern)
        return

    if args.ui:
        # Launch the interactive review UI server
        import subprocess
        import sys
        logger.info("Launching review UI server at http://127.0.0.1:8000")
        logger.info("Press Ctrl+C to stop the server")
        try:
            subprocess.run(
                [sys.executable, "-m", "uvicorn", "ui.review_server:app",
                 "--host", "127.0.0.1", "--port", "8000"],
                check=False
            )
        except KeyboardInterrupt:
            logger.info("UI server stopped")
        return

    agent.run_daily_digest(
        limit=limit,
        archive_noise=archive_noise,
        dry_run=args.dry_run,
        batch_size=batch_size,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
