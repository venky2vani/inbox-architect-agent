"""Inbox Architect Agent orchestrator.

Loads connectors, processors, and persistence plugins dynamically and runs the
daily digest workflow.
"""

import argparse
import importlib
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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
        """Fetch and process a batch of message IDs, isolating per-email failures."""
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

            # Apply a Gmail label based on the extracted type (e.g. Invoice, Payment, Bill).
            if not dry_run:
                email_type = (processed.extracted_data or {}).get("type", "other")
                if email_type and email_type != "other":
                    type_label = email_type.title()
                    logger.info("Applying label '%s' to: %s", type_label, msg.subject[:60])
                    try:
                        connector.mark_processed(msg.id, [type_label])
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error("Failed to apply label to %s: %s", msg.id, exc)

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

    agent.run_daily_digest(
        limit=limit,
        archive_noise=archive_noise,
        dry_run=args.dry_run,
        batch_size=batch_size,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
