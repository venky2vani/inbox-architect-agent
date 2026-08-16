"""LLM-powered processor for the Inbox Architect Agent."""

import json
import logging
import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from plugins.base import EmailMessage, ProcessedItem, ProcessorPlugin
from plugins.local_intelligence import LocalIntelligence
from plugins.retry import retry_with_backoff, is_transient_llm_error
from plugins.dynamic_classifier import DynamicClassifier

logger = logging.getLogger(__name__)

llm_retry = retry_with_backoff(
    max_retries=3,
    base_delay=2.0,
    exceptions=(Exception,),
    predicate=is_transient_llm_error,
)


class SmartInboxProcessor(ProcessorPlugin):
    """Categorize and summarize emails using an LLM."""

    name = "smart_inbox"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = None,
        prompt_path: Optional[str] = None,
        local_intelligence: Optional[LocalIntelligence] = None,
        rate_limit_delay: Optional[float] = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
        self.model = model or os.getenv("PROCESSOR_MODEL", "gpt-4o-mini")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.prompt_path = prompt_path or os.getenv(
            "LLM_SYSTEM_PROMPT_PATH", "prompts/system.txt"
        )
        self.rate_limit_delay = float(
            rate_limit_delay or os.getenv("LLM_RATE_LIMIT_DELAY", "0")
        )
        self.api_key = api_key
        self.client: Optional[Any] = None
        self.local_hits = 0
        self.llm_calls = 0
        self._last_llm_call_time: Optional[float] = None

        local_enabled = (
            local_intelligence is not None
            or os.getenv("LOCAL_INTELLIGENCE_ENABLED", "true").lower() != "false"
        )
        if local_enabled and local_intelligence is None:
            self.local_intel = LocalIntelligence()
        elif local_intelligence is not None:
            self.local_intel = local_intelligence
        else:
            self.local_intel = None

        if self.provider == "anthropic":
            anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                from anthropic import Anthropic

                self.api_key = anthropic_key
                self.client = Anthropic(api_key=anthropic_key)
        elif self.api_key or os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI

            openai_key = api_key or os.getenv("OPENAI_API_KEY")
            self.api_key = openai_key
            client_kwargs: Dict[str, Any] = {"api_key": openai_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self.client = OpenAI(**client_kwargs)

        self.high_priority_senders = self._parse_sender_list(
            os.getenv("HIGH_PRIORITY_SENDERS", "")
        )
        self.low_priority_senders = self._parse_sender_list(
            os.getenv("LOW_PRIORITY_SENDERS", "")
        )
        self.always_noise_senders = self._parse_sender_list(
            os.getenv("ALWAYS_NOISE_SENDERS", "")
        )
        self.custom_rules = os.getenv("CUSTOM_RULES", "")

    @staticmethod
    def _parse_sender_list(value: str) -> List[str]:
        """Parse a comma-separated list of email addresses/domains."""
        return [s.strip().lower() for s in value.split(",") if s.strip()]

    def _check_dynamic_label(self, message: EmailMessage) -> Optional[ProcessedItem]:
        """Check if email matches a confirmed dynamic label."""
        try:
            classifier = DynamicClassifier()
            confirmed_labels = classifier.get_confirmed_labels()
            if not confirmed_labels:
                return None

            # Extract sender domain
            sender_lower = message.sender.lower()
            sender_domain = sender_lower.split("@")[-1].strip(">")

            # Check if domain matches any confirmed label
            for label_entry in confirmed_labels:
                if label_entry["domain"].lower() in sender_domain:
                    logger.info(
                        "Dynamic label match: %s → %s",
                        label_entry["domain"],
                        label_entry["label"],
                    )
                    return ProcessedItem(
                        original_id=message.id,
                        sender=message.sender,
                        subject=message.subject,
                        category=label_entry["label"],
                        priority=3,
                        summary=f"Categorized by dynamic label: {label_entry['label']}",
                        action_items=[],
                        extracted_data={},
                        destination="sheets_index",
                        status="pending",
                    )
        except Exception as e:
            logger.debug("Error checking dynamic labels: %s", e)
        return None

    def _build_system_prompt(self) -> str:
        """Build the system prompt from a file, appending optional custom rules."""
        prompt_path = Path(self.prompt_path)
        if prompt_path.exists():
            prompt = prompt_path.read_text(encoding="utf-8")
        else:
            # Minimal fallback if the prompt file is missing.
            prompt = (
                "You are an Inbox Architect. Analyze the email and output strict JSON."
            )
        if self.custom_rules:
            prompt += f"\nAdditional user rules:\n{self.custom_rules}\n"
        return prompt

    def process(self, message: EmailMessage) -> ProcessedItem:
        """Process a single email into a structured item."""
        # Apply hard sender overrides before calling the LLM.
        override = self._sender_override(message)
        if override:
            logger.info("Hard rule override for sender: %s", message.sender)
            return override

        # Check for confirmed dynamic labels.
        dynamic_result = self._check_dynamic_label(message)
        if dynamic_result:
            return dynamic_result

        # Try local intelligence first.
        if self.local_intel is not None:
            logger.debug("Checking local intelligence for: %s", message.subject[:60])
            local_result = self.local_intel.classify(message)
            if local_result is not None:
                self.local_hits += 1
                logger.info("Local intelligence hit for: %s", message.subject[:60])
                return local_result

        if self.client is None:
            # Fallback when no API key is configured (useful for local testing).
            logger.debug("No LLM client; using rule-based fallback")
            return self._fallback_process(message)

        processed = self._process_with_llm(message)
        self.llm_calls += 1
        if self.local_intel is not None:
            self.local_intel.learn(message, processed)
        return processed

    def _apply_rate_limit(self) -> None:
        """Sleep if needed to respect the configured rate limit delay."""
        if self.rate_limit_delay <= 0 or self._last_llm_call_time is None:
            return
        elapsed = time.perf_counter() - self._last_llm_call_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
            time.sleep(sleep_time)

    @llm_retry
    def _call_llm(self, content: str) -> Any:
        """Call the configured LLM provider with retry/backoff."""
        self._apply_rate_limit()
        try:
            if self.provider == "anthropic":
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=self._build_system_prompt(),
                    messages=[{"role": "user", "content": content}],
                    temperature=0.2,
                )
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": content},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        finally:
            self._last_llm_call_time = time.perf_counter()

    def _process_with_llm(self, message: EmailMessage) -> ProcessedItem:
        """Send the email to the LLM and map the result."""
        body_text = message.body_text or ""
        content = (
            f"From: {message.sender}\n"
            f"Subject: {message.subject}\n\n"
            f"{body_text[:6000]}"
        )

        logger.info("Calling %s LLM for: %s", self.provider, message.subject[:60])
        start = time.perf_counter()
        response = self._call_llm(content)
        elapsed = time.perf_counter() - start
        logger.info("LLM responded in %.2fs for: %s", elapsed, message.subject[:60])

        if self.provider == "anthropic":
            raw = response.content[0].text or "{}"
        else:
            raw = response.choices[0].message.content or "{}"

        result, is_garbage = self._extract_json(raw)
        processed = self._result_to_item(message, result)
        if is_garbage:
            logger.warning("LLM returned non-JSON for: %s", message.subject[:60])
            processed.summary = f"LLM returned non-JSON response: {raw[:500]}"
            processed.extracted_data = {"_llm_raw_response": raw}
        return processed

    @staticmethod
    def _extract_json(text: str) -> Tuple[Dict[str, Any], bool]:
        """Parse JSON from an LLM response, handling markdown fences.

        Returns the parsed dict and a boolean indicating whether the raw
        response was invalid JSON ("garbage").
        """
        text = text.strip()
        if not text:
            return {}, True

        # Try the raw text first.
        try:
            return json.loads(text), False
        except json.JSONDecodeError:
            pass

        # Look for JSON inside markdown code fences.
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fenced:
            try:
                return json.loads(fenced.group(1)), False
            except json.JSONDecodeError:
                pass

        return {}, True

    def _sender_override(self, message: EmailMessage) -> Optional[ProcessedItem]:
        """Apply sender-based overrides independent of the LLM."""
        sender_lower = message.sender.lower()

        for pattern in self.always_noise_senders:
            if pattern in sender_lower:
                return ProcessedItem(
                    original_id=message.id,
                    sender=message.sender,
                    subject=message.subject,
                    category="noise",
                    priority=1,
                    summary=f"Auto-archived: sender matched noise list ({pattern}).",
                    action_items=[],
                    extracted_data={},
                    destination="sheets_index",
                    status="archived",
                )

        for pattern in self.high_priority_senders:
            if pattern in sender_lower:
                # Still run through LLM, but force minimum priority 4.
                if self.client is None:
                    return self._fallback_process(message, min_priority=4)
                item = self._process_with_llm(message)
                item.priority = max(item.priority, 4)
                return item

        return None

    def _result_to_item(
        self, message: EmailMessage, result: Dict[str, Any]
    ) -> ProcessedItem:
        """Map the LLM JSON result into a ProcessedItem."""
        category = result.get("category", "reference")
        priority = self._clamp_priority(result.get("priority", 3))
        summary = result.get("summary", "")
        action_items = result.get("action_items", [])
        extracted_data = result.get("extracted_data", {})
        tags = result.get("tags", [])
        if tags:
            extracted_data["tags"] = tags
        should_archive = result.get("should_archive", category == "noise")

        return ProcessedItem(
            original_id=message.id,
            sender=message.sender,
            subject=message.subject,
            category=category,
            priority=priority,
            summary=summary,
            action_items=action_items,
            extracted_data=extracted_data,
            destination="sheets_index",
            status="archived" if should_archive else "pending",
        )

    @staticmethod
    def _clamp_priority(value: Any) -> int:
        """Ensure priority is an integer between 1 and 5."""
        try:
            priority = int(value)
        except (TypeError, ValueError):
            priority = 3
        return max(1, min(5, priority))

    def _fallback_process(
        self, message: EmailMessage, min_priority: int = 1
    ) -> ProcessedItem:
        """Rule-based fallback when no LLM is available."""
        logger.info("Rule-based fallback for: %s", message.subject[:60])
        subject_lower = message.subject.lower()
        body_text = message.body_text or ""
        body_lower = body_text.lower()
        combined = f"{subject_lower} {body_lower}"

        noise_keywords = [
            "unsubscribe",
            "newsletter",
            "promotion",
            "sale",
            "no reply",
            "noreply",
            "do not reply",
        ]
        urgent_keywords = ["urgent", "asap", "deadline", "action required", "overdue"]
        financial_keywords = {
            "invoice": ["invoice"],
            "payment": ["payment made", "payment received", "payment confirmation", "paid"],
            "bill": ["bill", "billing", "amount due", "balance due"],
            "refund": ["refund"],
            "salary": ["salary", "payroll", "payslip"],
            "investment": ["investment", "dividend", "stock", "mutual fund"],
            "tax": ["tax", "tds", "gst", "income tax"],
        }
        subscription_keywords = {
            "streaming": ["netflix", "hulu", "disney+", "prime video", "spotify", "apple music", "youtube premium", "aha", "sonyliv", "hotstar", "jiocinema", "zee5", "voot", "mxplayer", "twitch", "paramount+", "peacock", "apple tv+"],
            "software": ["adobe", "microsoft 365", "office 365", "slack", "figma", "notion", "canva", "photoshop"],
            "cloud": ["dropbox", "google one", "icloud", "onedrive", "backblaze", "crashplan"],
            "news": ["medium", "newsletter", "news subscription", "wall street journal", "new york times"],
            "membership": ["membership", "annual subscription", "monthly subscription", "recurring billing"],
            "fitness": ["gym", "peloton", "headspace", "calm", "fitbit", "audible", "masterclass"],
            "other": ["subscription", "renewal", "billing cycle", "auto-renew", "recurring charge"],
        }
        medical_keywords = {
            "lab_result": ["lab result", "laboratory result", "test result", "blood work", "pathology report"],
            "prescription": ["prescription", "rx", "refill", "medication"],
            "appointment": ["appointment", "doctor's visit", "consultation", "checkup"],
            "discharge": ["discharge summary", "discharge note", "hospital discharge"],
            "vaccination": ["vaccination", "vaccine", "immunization"],
            "health_insurance": ["insurance", "claim", "policy", "coverage", "deductible"],
            "doctor_note": ["doctor's note", "medical note", "physician note", "clinical note"],
        }
        travel_keywords = {
            "flight": ["flight", "airline", "booking confirmation", "itinerary", "boarding pass", "departure time"],
            "hotel": ["hotel", "resort", "accommodation check-in", "hotel booking", "hotel reservation"],
            "car": ["car rental", "rental confirmation", "vehicle pickup", "drive rental"],
            "trip": ["trip", "vacation", "travel itinerary", "travel advisor", "tour"],
        }
        leisure_keywords = {
            "event": ["event", "ticket", "registration", "rsvp", "attending"],
            "concert": ["concert", "show", "live performance", "artist"],
            "movie": ["movie", "cinema", "screening", "film ticket"],
            "sports": ["sports", "game", "match", "tournament", "team"],
            "restaurant": ["restaurant", "dining reservation", "reservation confirmed", "table"],
        }
        shopping_keywords = {
            "order": ["order confirmation", "order number", "purchased", "placed order", "thank you for your order"],
            "shipment": ["shipped", "tracking number", "delivery date", "on the way", "package"],
            "delivery": ["delivered", "out for delivery", "will arrive", "delivery confirmation"],
            "return": ["return request", "return processed", "exchange", "replacement order"],
        }
        work_keywords = {
            "project": ["project", "sprint", "task", "deadline", "deliverable"],
            "collaboration": ["collaborate", "share", "review", "feedback", "pull request", "code review"],
            "meeting": ["meeting", "sync", "standup", "all-hands"],
            "assignment": ["assigned to you", "assigned to me", "task", "action item"],
        }
        personal_keywords = {
            "family": ["family", "mom", "dad", "brother", "sister", "parent", "child"],
            "friend": ["friend", "buddy", "pal", "catch up", "let's hang"],
            "social": ["party", "hangout", "gathering", "meetup"],
            "hobby": ["hobby", "interest", "club", "group", "community"],
        }
        meeting_keywords = ["meeting", "calendar invite", "zoom", "teams call"]

        is_noise = any(k in combined for k in noise_keywords)
        is_urgent = any(k in combined for k in urgent_keywords)
        is_meeting = any(k in combined for k in meeting_keywords)

        detected_subscription = [
            sub_type
            for sub_type, keywords in subscription_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_subscription = bool(detected_subscription)

        detected_types = [
            doc_type
            for doc_type, keywords in financial_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_financial = bool(detected_types)

        detected_medical = [
            doc_type
            for doc_type, keywords in medical_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_medical = bool(detected_medical)

        detected_travel = [
            doc_type
            for doc_type, keywords in travel_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_travel = bool(detected_travel)

        detected_leisure = [
            doc_type
            for doc_type, keywords in leisure_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_leisure = bool(detected_leisure)

        detected_shopping = [
            doc_type
            for doc_type, keywords in shopping_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_shopping = bool(detected_shopping)

        detected_work = [
            doc_type
            for doc_type, keywords in work_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_work = bool(detected_work)

        detected_personal = [
            doc_type
            for doc_type, keywords in personal_keywords.items()
            if any(k in combined for k in keywords)
        ]
        is_personal = bool(detected_personal)

        if is_noise:
            category = "noise"
            priority = 1
        elif is_urgent:
            category = "action_needed"
            priority = 5
        elif is_subscription:
            category = "action_needed" if "charge" in combined or "charged" in combined else "reference"
            priority = 3
        elif is_medical:
            category = "action_needed" if detected_medical[0] in ["prescription", "appointment"] else "reference"
            priority = 3
        elif is_travel:
            category = "action_needed" if detected_travel[0] in ["flight", "hotel", "car"] else "reference"
            priority = 3
        elif is_leisure:
            category = "action_needed" if "rsvp" in combined or "confirm" in combined else "reference"
            priority = 2
        elif is_shopping:
            category = "action_needed" if detected_shopping[0] in ["delivery", "return"] else "reference"
            priority = 2
        elif is_work:
            category = "action_needed"
            priority = 4
        elif is_personal:
            category = "action_needed" if "?" in body_text or "please" in body_lower else "reference"
            priority = 2
        elif "?" in body_text or "please" in body_lower:
            category = "action_needed"
            priority = 3
        else:
            category = "reference"
            priority = 2

        priority = max(priority, min_priority)

        extracted: Dict[str, Any] = {"type": "other"}
        tags: List[str] = []
        due_date: Optional[str] = None
        amount: Optional[str] = None

        if is_subscription:
            sub_type = detected_subscription[0]
            extracted["type"] = "subscription"
            extracted["subscription"] = {"category": sub_type}
            tags.append("subscription")
            tags.append(sub_type)
            service_name = self._extract_service_name(message.sender, body_text)
            if service_name:
                extracted["subscription"]["service"] = service_name
            amount = self._extract_amount(body_text)
            if amount:
                extracted["subscription"]["amount"] = amount
            renewal_date = self._extract_renewal_date(body_text, message.received_at.date())
            if renewal_date:
                extracted["subscription"]["renewal_date"] = renewal_date
        elif is_shopping:
            shopping_type = detected_shopping[0]
            extracted["type"] = "order"
            extracted["order"] = {}
            tags.append("shopping")
            order_number = self._extract_order_number(body_text)
            if order_number:
                extracted["order"]["order_number"] = order_number
            amount = self._extract_amount(body_text)
            if amount:
                extracted["order"]["amount"] = amount
        elif detected_types:
            doc_type = detected_types[0]
            extracted["type"] = doc_type
            tags.append("finance")
            tags.append(doc_type)
            amount = self._extract_amount(body_text)
            due_date = self._extract_due_date(body_text, message.received_at.date())
            if amount or due_date:
                extracted[doc_type] = {}
                if amount:
                    extracted[doc_type]["amount"] = amount
                if due_date:
                    extracted[doc_type]["due_date"] = due_date
        elif is_medical:
            doc_type = detected_medical[0]
            extracted["type"] = "medical"
            extracted["medical"] = {"report_type": doc_type}
            tags.append("medical")
            tags.append("health")
            provider = self._extract_medical_provider(body_text)
            if provider:
                extracted["medical"]["provider"] = provider
        elif is_travel:
            travel_type = detected_travel[0]
            extracted["type"] = "travel"
            extracted["travel"] = {"type": travel_type}
            tags.append("travel")
            destination = self._extract_travel_destination(body_text)
            if destination:
                extracted["travel"]["destination"] = destination
        elif is_leisure:
            event_type = detected_leisure[0]
            extracted["type"] = "event"
            extracted["event"] = {"category": event_type}
            tags.append("leisure")
            event_name = self._extract_event_name(body_text)
            if event_name:
                extracted["event"]["name"] = event_name
        elif is_work:
            work_type = detected_work[0]
            extracted["type"] = "work"
            extracted["work"] = {"type": work_type}
            tags.append("work")
        elif is_personal:
            personal_type = detected_personal[0]
            extracted["type"] = "personal"
            extracted["personal"] = {"type": personal_type}
            tags.append("personal")
        elif is_meeting:
            extracted["type"] = "meeting"

        # Boost priority for high-cost subscriptions
        if is_subscription and amount:
            try:
                amount_str = amount.replace("$", "").replace(",", "")
                amount_num = float(amount_str)
                if amount_num > 15:  # Flag subscriptions costing >$15/month
                    priority = max(priority, 4)
                    tags.append("expensive")
            except (ValueError, AttributeError):
                pass

        # Boost priority for upcoming renewals
        if is_subscription and renewal_date:
            days_left = self._days_until(renewal_date, message.received_at.date())
            if days_left is not None:
                if days_left <= 3:
                    priority = max(priority, 4)
                    tags.append("renews-soon")
                elif days_left <= 7:
                    tags.append("renews-week")

        # Boost priority for upcoming due dates (bills, invoices, etc).
        if due_date:
            days_left = self._days_until(due_date, message.received_at.date())
            if days_left is not None:
                if days_left <= 3:
                    priority = max(priority, 5)
                    tags.append("urgent")
                elif days_left <= 7:
                    priority = max(priority, 4)
                    tags.append("due-soon")

        if is_financial:
            tags.append("finance")
        if is_urgent:
            tags.append("urgent")
        if tags:
            extracted["tags"] = list(dict.fromkeys(tags))  # preserve order, remove dupes

        summary = (
            f"Fallback processing: email from {message.sender} "
            f"regarding '{message.subject}'."
        )

        # Build concrete action items based on document type.
        action_items = ["Review manually (LLM not configured)"]
        if is_subscription:
            sub_type = detected_subscription[0]
            if amount:
                action_items = [f"Review {sub_type} subscription charge of {amount}"]
                if renewal_date:
                    action_items.append(f"Renews on {renewal_date}")
                action_items.append("Consider cancelling if unused")
            else:
                action_items = [f"Review {sub_type} subscription renewal"]
                action_items.append("Check if still needed and cancel if unused")
        elif is_medical:
            medical_type = detected_medical[0]
            if medical_type == "prescription":
                action_items = ["Refill prescription or contact pharmacy"]
            elif medical_type == "appointment":
                action_items = ["Confirm or reschedule appointment"]
            else:
                action_items = [f"Review {medical_type.replace('_', ' ')} from medical provider"]
        elif is_travel:
            action_items = [f"Review travel booking and confirm {detected_travel[0]}"]
        elif is_leisure:
            action_items = [f"Confirm attendance for {detected_leisure[0]} event"]
        elif is_shopping:
            if detected_shopping[0] in ["delivery", "return"]:
                action_items = [f"Review {detected_shopping[0]} status and track package"]
            else:
                action_items = ["Review order details and confirm"]
        elif is_work:
            action_items = ["Review work task and respond as needed"]
        elif is_personal:
            action_items = ["Review personal message and respond"]
        elif detected_types and due_date and amount:
            doc_type = detected_types[0]
            action_items = [f"Pay {doc_type} of {amount} by {due_date}"]
        elif detected_types and due_date:
            doc_type = detected_types[0]
            action_items = [f"Settle {doc_type} by {due_date}"]
        elif detected_types and amount:
            doc_type = detected_types[0]
            action_items = [f"Review {doc_type} of {amount}"]

        return ProcessedItem(
            original_id=message.id,
            sender=message.sender,
            subject=message.subject,
            category=category,
            priority=priority,
            summary=summary,
            action_items=action_items,
            extracted_data=extracted,
            destination="sheets_index",
            status="archived" if category == "noise" else "pending",
        )

    @staticmethod
    def _extract_amount(text: str) -> Optional[str]:
        """Extract a currency amount from text (fallback heuristic)."""
        # Look for common currency patterns like $123.45, £99, €1,234.00.
        match = re.search(r"[\$\£\€]\s*[\d,]+\.?\d{0,2}", text)
        return match.group(0).strip() if match else None

    @staticmethod
    def _extract_due_date(text: str, reference_date: Optional[date] = None) -> Optional[str]:
        """Extract a due/payment date from text using common formats.

        Supports ISO/numeric dates, named months, and relative phrases such as
        "due today", "due tomorrow", and "due in N days".
        """
        if not text:
            return None
        text_lower = text.lower()
        today = reference_date or datetime.now().date()

        # Relative dates with expanded keywords for bills
        bill_keywords = r"\b(due|pay|payment|settle|balance due|amount due|overdue|deadline)\b"

        if re.search(bill_keywords + r".*?\btoday\b", text_lower):
            return today.isoformat()
        if re.search(bill_keywords + r".*?\btomorrow\b", text_lower):
            return (today + timedelta(days=1)).isoformat()

        days_match = re.search(bill_keywords + r".*?in\s+(\d+)\s+days?\b", text_lower)
        if days_match:
            return (today + timedelta(days=int(days_match.group(2)))).isoformat()

        # Handle "due on" format with flexible spacing
        due_on_match = re.search(bill_keywords + r".*?(?:on|by)\s+(\d{1,2})?-?(\w+)?-?(\d{4})?", text_lower)
        if due_on_match:
            pass  # Let the more specific patterns below handle this

        month_map = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }

        # ISO / numeric formats
        for pattern in [
            r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",  # YYYY-MM-DD
            r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b",  # DD/MM/YYYY or MM/DD/YYYY
        ]:
            for match in re.finditer(pattern, text):
                groups = match.groups()
                candidates = []
                if len(groups[0]) == 4:
                    candidates.append((int(groups[0]), int(groups[1]), int(groups[2])))
                else:
                    day_or_month_1, day_or_month_2, year = int(groups[0]), int(groups[1]), int(groups[2])
                    candidates.append((year, day_or_month_2, day_or_month_1))
                    candidates.append((year, day_or_month_1, day_or_month_2))
                for year, month, day in candidates:
                    try:
                        return date(year, month, day).isoformat()
                    except ValueError:
                        continue

        # Named months: "20 Aug 2024" or "Aug 20, 2024"
        for pattern in [
            (r"\b(\d{1,2})\s+([a-z]{3,})\s+(\d{4})\b", 0, 1, 2),  # day month year
            (r"\b([a-z]{3,})\s+(\d{1,2})(?:,)?\s+(\d{4})\b", 1, 0, 2),  # month day year
        ]:
            regex, day_idx, month_idx, year_idx = pattern
            for match in re.finditer(regex, text_lower):
                groups = match.groups()
                try:
                    day = int(groups[day_idx])
                    month = month_map.get(groups[month_idx])
                    year = int(groups[year_idx])
                    if month is None:
                        continue
                    return date(year, month, day).isoformat()
                except (ValueError, IndexError):
                    continue

        return None

    @staticmethod
    def _days_until(due_date_str: str, reference_date: Optional[date] = None) -> Optional[int]:
        """Return the number of days between a due date and the reference date."""
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            today = reference_date or datetime.now().date()
            return (due_date - today).days
        except ValueError:
            return None

    @staticmethod
    def _extract_medical_provider(text: str) -> Optional[str]:
        """Extract medical provider name (hospital, clinic, lab, pharmacy) from text."""
        if not text:
            return None
        text_lower = text.lower()

        # Common patterns for medical provider names.
        patterns = [
            r"(?:from|at|provider|clinic|hospital|lab|pharmacy):\s*([A-Za-z\s&\.,]+?)(?:\n|$)",
            r"(?:Dr\.|Doctor|Clinic|Hospital|Lab|Pharmacy)\s+([A-Za-z\s&\.,]+?)(?:\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                provider = match.group(1).strip()
                if provider and len(provider) < 100:
                    return provider

        return None

    @staticmethod
    def _extract_travel_destination(text: str) -> Optional[str]:
        """Extract travel destination from email text."""
        if not text:
            return None
        text_lower = text.lower()
        patterns = [
            r"(?:to|destination|traveling to):\s*([A-Za-z\s,]+?)(?:\n|,|$)",
            r"(?:destination|arriving in|flying to|traveling to)\s+([A-Za-z\s,]+?)(?:\n|,|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                destination = match.group(1).strip()
                if destination and len(destination) < 100:
                    return destination
        return None

    @staticmethod
    def _extract_event_name(text: str) -> Optional[str]:
        """Extract event name from email text."""
        if not text:
            return None
        patterns = [
            r"(?:event|concert|show|game|match):\s*([A-Za-z0-9\s&\-\.]+?)(?:\.|,|\n|$)",
            r"(?:title|event name):\s*([A-Za-z0-9\s&\-\.]+?)(?:,|\n|$)",
            r"event:\s*([A-Za-z0-9\s&\-\.]+?)(?:,|\n|Date|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name and len(name) < 150:
                    return name
        return None

    @staticmethod
    def _extract_order_number(text: str) -> Optional[str]:
        """Extract order number from email text."""
        if not text:
            return None
        patterns = [
            r"order\s*(?:number|#|id):\s*#?([A-Z0-9\-]+)",
            r"(?:order|ref|reference|confirmation)\s*#\s*([A-Z0-9\-]+)",
            r"#([A-Z0-9]{8,})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                order_num = match.group(1).strip().lstrip("#")
                if order_num and len(order_num) < 50:
                    return order_num
        return None

    @staticmethod
    def _extract_service_name(sender: str, text: str) -> Optional[str]:
        """Extract subscription service name from sender or text."""
        if not sender and not text:
            return None

        combined = f"{sender} {text}".lower()

        # Common subscription services
        services = {
            "netflix": ["netflix"],
            "spotify": ["spotify"],
            "apple music": ["apple music", "itunes"],
            "adobe": ["adobe", "creative cloud"],
            "microsoft 365": ["microsoft 365", "office 365"],
            "slack": ["slack"],
            "dropbox": ["dropbox"],
            "google one": ["google one", "google drive"],
            "medium": ["medium"],
            "hulu": ["hulu"],
            "disney+": ["disney+"],
            "amazon prime": ["amazon prime", "prime video"],
            "youtube premium": ["youtube premium", "youtube tv"],
            "headspace": ["headspace"],
            "calm": ["calm"],
            "peloton": ["peloton"],
        }

        for service, keywords in services.items():
            if any(k in combined for k in keywords):
                return service

        # Fallback: try to extract from sender domain
        if sender and "@" in sender:
            domain = sender.split("@")[1].split(".")[0]
            return domain.capitalize() if domain else None

        return None

    @staticmethod
    def _extract_renewal_date(text: str, reference_date: Optional[date] = None) -> Optional[str]:
        """Extract subscription renewal/next billing date from text."""
        if not text:
            return None

        text_lower = text.lower()
        today = reference_date or datetime.now().date()

        # Relative dates for renewals
        if re.search(r"\b(?:renews?|billing|charged|next)\s+(?:today|next day)\b", text_lower):
            return today.isoformat()

        if re.search(r"\b(?:renews?|billing|charged|next)\s+tomorrow\b", text_lower):
            return (today + timedelta(days=1)).isoformat()

        # "renews in X days"
        renewal_match = re.search(
            r"(?:renews?|next billing|charged).*?in\s+(\d+)\s+days?",
            text_lower
        )
        if renewal_match:
            days = int(renewal_match.group(1))
            return (today + timedelta(days=days)).isoformat()

        # Use the same date extraction as due dates for "renews on" format
        month_map = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }

        # ISO/numeric formats (YYYY-MM-DD or DD/MM/YYYY)
        for pattern in [
            r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",
            r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b",
        ]:
            for match in re.finditer(pattern, text):
                groups = match.groups()
                candidates = []
                if len(groups[0]) == 4:
                    candidates.append((int(groups[0]), int(groups[1]), int(groups[2])))
                else:
                    day_or_month_1, day_or_month_2, year = int(groups[0]), int(groups[1]), int(groups[2])
                    candidates.append((year, day_or_month_2, day_or_month_1))
                    candidates.append((year, day_or_month_1, day_or_month_2))
                for year, month, day in candidates:
                    try:
                        return date(year, month, day).isoformat()
                    except ValueError:
                        continue

        # Named months
        for pattern in [
            (r"\b(\d{1,2})\s+([a-z]{3,})\s+(\d{4})\b", 0, 1, 2),
            (r"\b([a-z]{3,})\s+(\d{1,2})(?:,)?\s+(\d{4})\b", 1, 0, 2),
        ]:
            regex, day_idx, month_idx, year_idx = pattern
            for match in re.finditer(regex, text_lower):
                groups = match.groups()
                try:
                    day = int(groups[day_idx])
                    month = month_map.get(groups[month_idx])
                    year = int(groups[year_idx])
                    if month is None:
                        continue
                    return date(year, month, day).isoformat()
                except (ValueError, IndexError):
                    continue

        return None
