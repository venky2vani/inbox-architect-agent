"""Dynamic label discovery for emerging email patterns."""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from plugins.base import EmailMessage

logger = logging.getLogger(__name__)


class DynamicClassifier:
    """Discovers emerging email patterns and suggests new categories."""

    MIN_CLUSTER_SIZE = 50  # Minimum emails to suggest new category
    CONFIDENCE_THRESHOLD = 0.60  # Minimum confidence for suggestion

    def __init__(self, config_path: str = "data/dynamic_labels.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load dynamic labels config from file."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load dynamic config: %s", e)
        return {
            "discovered_patterns": {},
            "confirmed_labels": [],
            "rejected_patterns": [],
            "last_analysis": None,
        }

    def _save_config(self) -> None:
        """Save dynamic labels config to file."""
        self.config_path.write_text(
            json.dumps(self.data, indent=2, default=str), encoding="utf-8"
        )

    def analyze_emails(self, messages: List[EmailMessage]) -> List[Dict[str, Any]]:
        """Analyze a batch of emails for new emerging patterns.

        Returns list of suggested new categories with confidence scores.
        """
        logger.info("Analyzing %d emails for patterns...", len(messages))

        # Skip already-classified categories from existing classification
        existing_categories = {
            "subscription",
            "shopping",
            "medical",
            "financial",
            "travel",
            "work",
            "personal",
            "leisure",
            "noise",
        }

        # Cluster emails by sender domain
        clusters = self._cluster_by_sender(messages)

        # Build set of confirmed and rejected domains for fast lookup
        confirmed_domains = {
            c["domain"] for c in self.data["confirmed_labels"]
        }
        rejected_domains = {
            r["domain"] for r in self.data["rejected_patterns"]
        }

        # Find clusters that are outliers (don't fit existing categories)
        suggestions = []
        for cluster_domain, emails in clusters.items():
            if len(emails) < self.MIN_CLUSTER_SIZE:
                continue

            # Skip if already has a confirmed label
            if cluster_domain in confirmed_domains:
                logger.debug("Skipping already-confirmed domain: %s", cluster_domain)
                continue

            # Skip if already rejected
            if cluster_domain in rejected_domains:
                logger.debug("Skipping rejected pattern: %s", cluster_domain)
                continue

            # Analyze the cluster
            suggestion = self._analyze_cluster(cluster_domain, emails)
            if suggestion and suggestion["confidence"] >= self.CONFIDENCE_THRESHOLD:
                suggestions.append(suggestion)

        # Sort by confidence (highest first)
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        logger.info(
            "Found %d potential new categories (confidence >= %.2f)",
            len(suggestions),
            self.CONFIDENCE_THRESHOLD,
        )
        return suggestions

    def _cluster_by_sender(
        self, messages: List[EmailMessage]
    ) -> Dict[str, List[EmailMessage]]:
        """Group emails by sender domain."""
        clusters: Dict[str, List[EmailMessage]] = defaultdict(list)
        for msg in messages:
            domain = self._extract_domain(msg.sender)
            if domain:
                clusters[domain].append(msg)
        return clusters

    @staticmethod
    def _extract_domain(sender: str) -> Optional[str]:
        """Extract domain from email address."""
        try:
            domain = sender.split("@")[-1].strip(">").lower()
            if "." in domain:
                return domain
        except Exception:
            pass
        return None

    def _analyze_cluster(
        self, domain: str, emails: List[EmailMessage]
    ) -> Optional[Dict[str, Any]]:
        """Analyze a sender cluster for category suggestion."""
        # Extract common keywords
        keywords = self._extract_keywords(emails)

        # Determine category based on keywords
        category_guess = self._guess_category(domain, keywords, emails)
        if not category_guess:
            return None

        # Calculate confidence based on keyword consistency
        confidence = self._calculate_confidence(keywords, emails)

        return {
            "domain": domain,
            "suggested_label": category_guess["label"],
            "suggested_description": category_guess["description"],
            "example_keywords": keywords[:5],
            "email_count": len(emails),
            "confidence": confidence,
            "example_subjects": [
                emails[i].subject[:60] for i in range(min(3, len(emails)))
            ],
            "first_seen": emails[0].received_at if emails else None,
            "last_seen": emails[-1].received_at if emails else None,
        }

    def _extract_keywords(self, emails: List[EmailMessage]) -> List[str]:
        """Extract common keywords from email subjects and bodies."""
        keyword_freq: Dict[str, int] = defaultdict(int)

        for msg in emails:
            # Extract from subject
            if hasattr(msg, 'subject') and msg.subject:
                words = self._tokenize(msg.subject.lower())
                for word in words:
                    keyword_freq[word] += 1

            # Extract from body (if available)
            body_text = None
            if hasattr(msg, "body") and msg.body:
                body_text = msg.body
            # Handle mocks with __getitem__
            elif hasattr(msg, '__getitem__'):
                try:
                    body_text = msg.get("body", "")
                except (TypeError, KeyError):
                    body_text = None

            if body_text:
                words = self._tokenize(str(body_text)[:500].lower())
                for word in words:
                    keyword_freq[word] += 0.5  # Lower weight for body

        # Filter and sort - be more lenient with frequency threshold
        keywords = [
            word
            for word, freq in sorted(
                keyword_freq.items(), key=lambda x: x[1], reverse=True
            )
            if freq >= 1.0 and len(word) > 3  # Lowered threshold from 2 to 1.0
        ]
        return keywords[:10]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization."""
        import re

        return re.findall(r"\b\w+\b", text)

    def _guess_category(
        self, domain: str, keywords: List[str], emails: List[EmailMessage]
    ) -> Optional[Dict[str, str]]:
        """Guess category based on domain and keywords."""
        domain_lower = domain.lower()
        keywords_text = " ".join(keywords).lower()

        # Crypto/DeFi exchanges (check before ecommerce)
        if any(
            x in domain_lower
            for x in [
                "coinbase",
                "kraken",
                "binance",
                "crypto",
                "blockchain",
                "ethereum",
                "defi",
                "wallet",
            ]
        ):
            return {
                "label": "crypto_exchanges",
                "description": "Cryptocurrency and blockchain transaction notifications",
            }

        # Gaming / Esports (check before ecommerce)
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "steam",
                "epic",
                "playstation",
                "xbox",
                "game",
                "gaming",
                "esports",
                "tournament",
                "multiplayer",
                "battle",
            ]
        ):
            return {
                "label": "gaming",
                "description": "Gaming platforms, purchases, and tournament notifications",
            }

        # Gambling/Sports betting
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "betting",
                "casino",
                "poker",
                "sports-book",
                "draftkings",
                "fanduel",
                "gamble",
                "wager",
                "lottery",
            ]
        ):
            return {
                "label": "gambling",
                "description": "Sports betting and gambling platforms",
            }

        # Social media platforms
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "facebook",
                "twitter",
                "x.com",
                "instagram",
                "tiktok",
                "snapchat",
                "reddit",
                "pinterest",
                "social",
            ]
        ):
            return {
                "label": "social_media",
                "description": "Social media platform notifications and updates",
            }

        # Developer tools / Code hosting
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "github",
                "gitlab",
                "bitbucket",
                "docker",
                "npm",
                "pypi",
                "maven",
                "code",
                "repository",
                "aws.amazon",
                "vercel",
                "netlify",
                "heroku",
                "digitalocean",
                "stackoverflow",
                "kubernetes",
                "jenkins",
                "github actions",
                "ci/cd",
                "continuous integration",
            ]
        ):
            return {
                "label": "developer_tools",
                "description": "Developer tools, version control, and CI/CD platforms",
            }

        # Job platforms / Recruiting
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "linkedin",
                "indeed",
                "glassdoor",
                "hired",
                "recruitment",
                "application",
                "job",
                "jobs",
                "recruiter",
                "hiring",
                "career",
                "interview",
            ]
        ):
            return {
                "label": "job_platforms",
                "description": "Job applications, recruiting, and career platforms",
            }

        # Education / Online courses
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "udemy",
                "coursera",
                "edx",
                "pluralsight",
                "skillshare",
                "udacity",
                "khanacademy",
                "course",
                "courses",
                "webinar",
                "webinars",
                "tutorial",
                "tutorials",
                "certification",
                "certifications",
                "learning",
                "bootcamp",
                "workshop",
                "masterclass",
                "e-learning",
                "online course",
                "training",
            ]
        ):
            return {
                "label": "education",
                "description": "Online courses, webinars, and learning platforms",
            }

        # Medical / Healthcare
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "metropolis",
                "thyrocare",
                "apollo",
                "practo",
                "pharmeasy",
                "medlife",
                "1mg",
                "medical",
                "healthcare",
                "lab",
                "laboratory",
                "test results",
                "prescription",
                "appointment",
                "doctor",
                "hospital",
                "clinic",
                "health",
                "diagnostic",
                "scan",
                "vaccination",
                "pharmacy",
            ]
        ):
            return {
                "label": "medical",
                "description": "Healthcare, lab results, prescriptions, and appointments",
            }

        # Travel / Booking (check before ecommerce)
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "booking",
                "expedia",
                "kayak",
                "tripadvisor",
                "airbnb",
                "hotel",
                "flight",
                "reservation",
                "irctc",
                "makemytrip",
                "goibibo",
                "yatra",
                "cleartrip",
                "oyorooms",
                "trip",
                "travel",
                "holiday",
                "package",
                "tour",
            ]
        ):
            return {
                "label": "travel_booking",
                "description": "Travel bookings, flights, hotels, and reservations",
            }

        # Real estate / Property
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "zillow",
                "redfin",
                "airbnb",
                "property",
                "estate",
                "listing",
                "mortgage",
                "rental",
                "housing",
                "apartment",
                "landlord",
            ]
        ):
            return {
                "label": "real_estate",
                "description": "Property listings, real estate, and rental platforms",
            }

        # Food Delivery / Restaurants
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "zomato",
                "swiggy",
                "doordash",
                "grubhub",
                "ubereats",
                "deliveroo",
                "foodpanda",
                "food delivery",
                "restaurant order",
                "food order",
                "delivered",
                "restaurant",
                "meal",
                "food",
            ]
        ):
            return {
                "label": "food_delivery",
                "description": "Food delivery platforms and restaurant orders",
            }

        # e-Commerce / Retail
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "amazon",
                "flipkart",
                "ebay",
                "shopify",
                "myntra",
                "nykaa",
                "meesho",
                "order",
                "purchase",
                "shipping",
                "shipped",
                "delivery",
                "voucher",
                "cashback",
                "deal",
                "discount",
            ]
        ):
            return {
                "label": "ecommerce",
                "description": "Online shopping, orders, and shipment notifications",
            }

        # Streaming / Entertainment
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "netflix",
                "primevideo",
                "prime video",
                "hotstar",
                "disney",
                "sonyliv",
                "sony liv",
                "aha",
                "zee5",
                "voot",
                "mxplayer",
                "mx player",
                "spotify",
                "appletv",
                "apple tv",
                "youtube premium",
                "twitch",
                "youtube",
                "vimeo",
                "hulu",
                "peacock",
                "streamer",
                "channel",
                "subscription",
            ]
        ):
            return {
                "label": "streaming_video",
                "description": "Video streaming and content platforms",
            }

        # Utilities / Government services
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "gov.in",
                "government",
                "electricity",
                "utility",
                "utilities",
                "bill payment",
                "msedcl",
                "kyc",
                "know your customer",
                "pension",
                "yojna",
                "income tax",
                "gst",
                "aadhaar",
                "pan card",
                "epfo",
                "passport",
                "driving licence",
                "driving license",
                "municipal",
                "property tax",
            ]
        ):
            return {
                "label": "utilities_government",
                "description": "Government services, utility bills, and public sector notifications",
            }

        # Banking / Investment
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "bank",
                "investment",
                "brokerage",
                "fidelity",
                "vanguard",
                "td",
                "charles",
                "portfolio",
                # Indian banks
                "hdfc",
                "icici",
                "idbi",
                "sbi",
                "axis",
                "kotak",
                "pnb",
                "bankofbaroda",
                "canara",
                "unionbankofindia",
                "bankofindia",
                "indianbank",
                "centralbankofindia",
                "iob",
                "ucobank",
                "yesbank",
                "idfc",
                "indusind",
                "federalbank",
                "southindianbank",
                "karnatakabank",
                "rblbank",
                "bandhanbank",
                "aubank",
                # Fintech / wallets
                "paytm",
                "phonepe",
                "cred",
                "mobikwik",
                "freecharge",
                "googlepay",
                "gpay",
                # Common card/payment networks
                "mastercard",
                "visa",
                "amex",
                "rupay",
                # Transaction keywords
                "debit",
                "debited",
                "credit",
                "upi",
                "imps",
                "neft",
                "rtgs",
                "credit card",
                "loan",
                "emi",
                "statement",
                "transaction",
                "balance",
                "mutual fund",
                "sip",
                "investment",
                "trading",
                "demat",
                "nse",
                "bse",
            ]
        ):
            return {
                "label": "banking_investment",
                "description": "Banking, investment accounts, and portfolio updates",
            }

        # Newsletters / Content subscriptions
        if any(
            x in domain_lower or x in keywords_text
            for x in [
                "newsletter",
                "newsletters",
                "digest",
                "weekly",
                "edition",
                "issue",
                "podcast",
                "episode",
                "roundup",
                "briefing",
                "ai newsletter",
                "ai news",
                "tech news",
                "dev digest",
                "tldr",
            ]
        ):
            return {
                "label": "newsletters",
                "description": "Newsletters, podcasts, and regular content digests",
            }

        # Generic fallback
        if keywords:
            label = f"category_{keywords[0][:20]}"
            description = f"Emails related to {keywords[0]}"
            return {"label": label, "description": description}

        return None

    @staticmethod
    def _calculate_confidence(keywords: List[str], emails: List[EmailMessage]) -> float:
        """Calculate confidence score for category suggestion.

        Based on:
        - Number of emails (more = higher confidence)
        - Keyword consistency (more consistent = higher confidence)
        - Recency (recent emails = higher confidence)
        """
        # Score based on cluster size
        size_score = min(len(emails) / 200, 1.0)  # Normalize to 0-1

        # Score based on keyword consistency
        if keywords:
            consistency_score = min(len(keywords) / 10, 1.0)
        else:
            consistency_score = 0.0

        # Combine scores
        confidence = (size_score * 0.6) + (consistency_score * 0.4)
        return min(confidence, 1.0)

    def confirm_label(self, domain: str, label: str) -> None:
        """User confirms a suggested label."""
        self.data["confirmed_labels"].append(
            {
                "domain": domain,
                "label": label,
                "confirmed_at": datetime.now().isoformat(),
            }
        )
        if domain in self.data["discovered_patterns"]:
            del self.data["discovered_patterns"][domain]
        self._save_config()
        logger.info("Confirmed label '%s' for domain: %s", label, domain)

    def reject_pattern(self, domain: str) -> None:
        """User rejects a suggested pattern."""
        self.data["rejected_patterns"].append(
            {
                "domain": domain,
                "rejected_at": datetime.now().isoformat(),
            }
        )
        if domain in self.data["discovered_patterns"]:
            del self.data["discovered_patterns"][domain]
        self._save_config()
        logger.info("Rejected pattern for domain: %s", domain)

    def export_suggestions_to_file(
        self, suggestions: List[Dict[str, Any]], output_path: str = "data/pattern_review.md"
    ) -> None:
        """Export suggestions to a markdown file for user review."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        content = """# Dynamic Label Discovery Review

## Instructions
Review the suggested categories below. For each:
1. Read the sample emails
2. Decide if it's a real pattern worth tracking
3. Add to APPROVED_LABELS.md if you want to use it
4. Ignore if not relevant

---

"""

        for i, suggestion in enumerate(suggestions, 1):
            content += f"## {i}. {suggestion['suggested_label'].upper()}\n\n"
            content += f"**Domain:** `{suggestion['domain']}`\n"
            content += f"**Email Count:** {suggestion['email_count']}\n"
            content += f"**Confidence:** {suggestion['confidence']:.1%}\n"
            content += f"**Description:** {suggestion['suggested_description']}\n\n"

            content += "**Common Keywords:** "
            content += ", ".join(f"`{kw}`" for kw in suggestion["example_keywords"])
            content += "\n\n"

            content += "**Sample Subjects:**\n"
            for subject in suggestion["example_subjects"]:
                content += f"- {subject}\n"

            content += f"\n**Period:** {suggestion['first_seen']} to {suggestion['last_seen']}\n\n"
            content += "---\n\n"

        output.write_text(content, encoding="utf-8")
        logger.info("Exported %d suggestions to %s", len(suggestions), output_path)

    def get_confirmed_labels(self) -> List[Dict[str, str]]:
        """Get all confirmed dynamic labels for integration."""
        return self.data["confirmed_labels"]
