"""Local residual intelligence for the Smart Inbox processor.

Learns from LLM outputs over time and short-circuits future LLM calls when a
locally cached rule is confident enough.
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from plugins.base import EmailMessage, ProcessedItem

# Simple English stop words used when tokenizing subjects/bodies.
_STOP_WORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "shall",
    "can",
    "need",
    "dare",
    "ought",
    "used",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "under",
    "and",
    "but",
    "or",
    "yet",
    "so",
    "if",
    "because",
    "although",
    "though",
    "while",
    "where",
    "when",
    "that",
    "which",
    "who",
    "whom",
    "whose",
    "what",
    "this",
    "these",
    "those",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "its",
    "our",
    "their",
}

# Weight given to each rule type when combining evidence.
_RULE_TYPE_WEIGHTS = {
    "sender_email": 1.0,
    "sender_domain": 0.7,
    "subject_keyword": 0.4,
    "body_keyword": 0.25,
}

# Minimum individual confidence a rule must have before it can vote in
# classification. Body keywords are noisier, so they need higher individual
# reliability than sender-based rules.
_RULE_TYPE_MIN_CONFIDENCE = {
    "sender_email": 0.80,
    "sender_domain": 0.75,
    "subject_keyword": 0.70,
    "body_keyword": 0.80,
}

# Tokens that are too generic or boilerplate to be useful predictors.
_NOISY_TOKENS = {
    "com",
    "www",
    "dear",
    "please",
    "click",
    "regards",
    "thanks",
    "hello",
    "unsubscribe",
    "view",
    "browser",
    "online",
    "web",
    "version",
    "footer",
    "privacy",
    "policy",
    "terms",
    "conditions",
    "mailto",
    "http",
    "https",
    "html",
    "body",
    "message",
    "email",
}

# Rules with enough samples but persistently low confidence are unlikely to
# become useful and pollute aggregate confidence.
_LOW_CONFIDENCE_PRUNE_SAMPLES = 10
_LOW_CONFIDENCE_PRUNE_THRESHOLD = 0.5


class LocalIntelligence:
    """Self-updating local rule cache learned from LLM outputs."""

    def __init__(
        self,
        rules_path: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        min_hits: Optional[int] = None,
        prune_after_days: Optional[int] = None,
    ):
        self.rules_path = Path(
            rules_path or os.getenv("LOCAL_INTELLIGENCE_PATH", "data/local_rules.json")
        )
        self.confidence_threshold = float(
            confidence_threshold
            or os.getenv("LOCAL_INTELLIGENCE_THRESHOLD", "0.85")
        )
        self.min_hits = int(min_hits or os.getenv("LOCAL_INTELLIGENCE_MIN_HITS", "3"))
        self.prune_after_days = int(
            prune_after_days or os.getenv("LOCAL_INTELLIGENCE_PRUNE_DAYS", "30")
        )
        self.rules: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        """Load rules from disk."""
        if not self.rules_path.exists():
            self.rules = []
            return
        try:
            data = json.loads(self.rules_path.read_text(encoding="utf-8"))
            self.rules = data.get("rules", [])
        except (json.JSONDecodeError, OSError):
            self.rules = []

    def _save(self) -> None:
        """Persist rules to disk.

        Callers must hold ``self._lock`` when modifying rules. This method is
        also safe to call independently because it acquires the lock itself.
        """
        with self._lock:
            self.rules_path.parent.mkdir(parents=True, exist_ok=True)
            self.rules_path.write_text(
                json.dumps({"rules": self.rules}, indent=2), encoding="utf-8"
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _confidence(rule: Dict[str, Any]) -> float:
        hits = rule.get("hits", 0)
        misses = rule.get("misses", 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return hits / total

    @staticmethod
    def _extract_domain(sender: str) -> str:
        """Extract the email domain from a sender string like 'Name <a@b.com>'."""
        match = re.search(r"[\w\.\-]+@([\w\.\-]+)", sender)
        return match.group(1).lower() if match else ""

    @staticmethod
    def _extract_keywords(text: str, top_n: int = 8) -> List[str]:
        """Extract meaningful keywords from text."""
        if not text:
            return []
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        counts: Dict[str, int] = {}
        for token in tokens:
            if token in _STOP_WORDS or token in _NOISY_TOKENS:
                continue
            counts[token] = counts.get(token, 0) + 1
        # Return the most frequent keywords, deduplicated and sorted.
        sorted_tokens = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [token for token, _ in sorted_tokens[:top_n]]

    def _features(self, message: EmailMessage) -> List[Tuple[str, str]]:
        """Return feature tuples (type, value) for an email."""
        sender_email = ""
        sender_domain = ""
        match = re.search(r"[\w\.\-]+@[\w\.\-]+", message.sender)
        if match:
            sender_email = match.group(0).lower()
            sender_domain = self._extract_domain(message.sender)

        features: List[Tuple[str, str]] = []
        if sender_email:
            features.append(("sender_email", sender_email))
        if sender_domain:
            features.append(("sender_domain", sender_domain))

        for keyword in self._extract_keywords(message.subject, top_n=6):
            features.append(("subject_keyword", keyword))

        body_text = message.body_text or ""
        for keyword in self._extract_keywords(body_text, top_n=12):
            features.append(("body_keyword", keyword))

        return features

    def _find_rule(self, rule_type: str, value: str) -> Optional[Dict[str, Any]]:
        for rule in self.rules:
            if rule.get("type") == rule_type and rule.get("value") == value:
                return rule
        return None

    def _create_rule(
        self,
        rule_type: str,
        value: str,
        category: str,
        priority: int,
        should_archive: bool,
    ) -> Dict[str, Any]:
        now = self._now()
        return {
            "id": str(uuid.uuid4()),
            "type": rule_type,
            "value": value,
            "category": category,
            "priority": priority,
            "should_archive": should_archive,
            "hits": 1,
            "misses": 0,
            "created_at": now,
            "last_used": now,
        }

    def _update_rule(
        self,
        rule: Dict[str, Any],
        category: str,
        priority: int,
        should_archive: bool,
    ) -> None:
        """Increment hits/misses and update rule attributes."""
        same_outcome = (
            rule.get("category") == category
            and rule.get("priority") == priority
            and rule.get("should_archive") == should_archive
        )
        if same_outcome:
            rule["hits"] = rule.get("hits", 0) + 1
        else:
            rule["misses"] = rule.get("misses", 0) + 1
            # Weighted average toward the most recent outcome.
            total = rule["hits"] + rule["misses"]
            if total > 0:
                rule["category"] = category
                rule["priority"] = priority
                rule["should_archive"] = should_archive
        rule["last_used"] = self._now()

    def learn(self, message: EmailMessage, item: ProcessedItem) -> None:
        """Update local rules based on an LLM-derived result."""
        with self._lock:
            should_archive = item.status == "archived" or item.category == "noise"
            for rule_type, value in self._features(message):
                rule = self._find_rule(rule_type, value)
                if rule is None:
                    self.rules.append(
                        self._create_rule(
                            rule_type,
                            value,
                            item.category,
                            item.priority,
                            should_archive,
                        )
                    )
                else:
                    self._update_rule(
                        rule, item.category, item.priority, should_archive
                    )
            self.prune()
            self._save()

    def classify(self, message: EmailMessage) -> Optional[ProcessedItem]:
        """Return a ProcessedItem if local rules are confident enough."""
        with self._lock:
            features = self._features(message)
            matched_rules: List[Dict[str, Any]] = []
            for rule_type, value in features:
                rule = self._find_rule(rule_type, value)
                if rule is None:
                    continue
                total = rule.get("hits", 0) + rule.get("misses", 0)
                if total < self.min_hits:
                    continue
                individual_conf = self._confidence(rule)
                min_conf = _RULE_TYPE_MIN_CONFIDENCE.get(rule_type, 0.0)
                if individual_conf < min_conf:
                    continue
                matched_rules.append(rule)

            if not matched_rules:
                return None

            # Combine evidence weighted by rule type and confidence.
            weighted_score = 0.0
            total_weight = 0.0
            categories: Dict[str, float] = {}
            priorities: List[int] = []
            should_archive_votes = 0.0

            for rule in matched_rules:
                weight = _RULE_TYPE_WEIGHTS.get(rule.get("type", ""), 0.1)
                conf = self._confidence(rule)
                w = weight * conf
                total_weight += w
                weighted_score += conf * w
                cat = rule.get("category", "reference")
                categories[cat] = categories.get(cat, 0.0) + w
                priorities.append(rule.get("priority", 3))
                if rule.get("should_archive", False):
                    should_archive_votes += w

            if total_weight == 0:
                return None

            avg_confidence = weighted_score / total_weight
            if avg_confidence < self.confidence_threshold:
                return None

            best_category = max(categories, key=categories.get)
            # Use the median priority among matching rules.
            priorities.sort()
            priority = priorities[len(priorities) // 2]
            should_archive = should_archive_votes > (total_weight / 2)

            for rule in matched_rules:
                rule["last_used"] = self._now()
            self._save()

            summary = (
                f"Local intelligence: matched {len(matched_rules)} rule(s) "
                f"for category '{best_category}' (confidence: {avg_confidence:.2f})."
            )
            return ProcessedItem(
                original_id=message.id,
                sender=message.sender,
                subject=message.subject,
                category=best_category,
                priority=priority,
                summary=summary,
                action_items=[],
                extracted_data={"_local_intelligence": True},
                destination="sheets_index",
                status="archived" if should_archive else "pending",
            )

    def prune(self) -> None:
        """Remove stale, low-confidence rules."""
        now = datetime.now(timezone.utc)
        kept: List[Dict[str, Any]] = []
        for rule in self.rules:
            last_used_str = rule.get("last_used") or rule.get("created_at")
            if last_used_str:
                try:
                    last_used = datetime.fromisoformat(last_used_str)
                    age_days = (now - last_used).days
                except ValueError:
                    age_days = 0
            else:
                age_days = 0

            conf = self._confidence(rule)
            total = rule.get("hits", 0) + rule.get("misses", 0)

            # Drop rules that have enough samples but are still wrong most of the time.
            if (
                total >= _LOW_CONFIDENCE_PRUNE_SAMPLES
                and conf < _LOW_CONFIDENCE_PRUNE_THRESHOLD
            ):
                continue

            # Keep rules that are either young or proven (high confidence and enough hits).
            proven = total >= self.min_hits and conf >= self.confidence_threshold
            if age_days < self.prune_after_days or proven:
                kept.append(rule)

        self.rules = kept
