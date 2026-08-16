"""Checkpoint helper to resume long email processing runs."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set


class Checkpoint:
    """Tracks processed email IDs so a run can resume after interruption."""

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path or os.getenv("CHECKPOINT_PATH", "data/checkpoint.json"))
        self.data: Dict[str, Any] = {"processed_ids": [], "last_run_at": None}
        self._processed_ids: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            self._processed_ids = set(self.data.get("processed_ids", []))
        except (json.JSONDecodeError, OSError):
            self.data = {"processed_ids": [], "last_run_at": None}
            self._processed_ids = set()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["processed_ids"] = sorted(self._processed_ids)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def is_processed(self, message_id: str) -> bool:
        return message_id in self._processed_ids

    def mark_processed(self, message_id: str) -> None:
        self._processed_ids.add(message_id)
        self.data["last_run_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def reset(self) -> None:
        self._processed_ids = set()
        self.data = {"processed_ids": [], "last_run_at": None}
        self._save()

    @property
    def processed_count(self) -> int:
        return len(self._processed_ids)
