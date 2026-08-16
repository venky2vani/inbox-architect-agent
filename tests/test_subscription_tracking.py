"""Tests for subscription tracking and management."""

from datetime import datetime, timedelta

from plugins.base import EmailMessage
from plugins.llm_processor import SmartInboxProcessor


def make_message(sender: str, subject: str, body: str = "") -> EmailMessage:
    return EmailMessage(
        id="m1",
        thread_id="t1",
        sender=sender,
        subject=subject,
        body_text=body,
        body_html=None,
        received_at=datetime.now(),
    )


class TestSubscriptionDetection:
    """Test subscription email detection and categorization."""

    def test_netflix_subscription_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@netflix.com",
            "Netflix Subscription Charged",
            "Your Netflix subscription has been charged $15.99. Next billing date: September 16, 2026.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "subscription"
        assert "subscription" in result.extracted_data.get("tags", [])
        assert result.category == "action_needed"

    def test_spotify_subscription_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@spotify.com",
            "Spotify Premium Renews Tomorrow",
            "Your Spotify Premium subscription will renew tomorrow for $12.99.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "subscription"
        assert "subscription" in result.extracted_data.get("tags", [])

    def test_adobe_subscription_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@adobe.com",
            "Adobe Creative Cloud Renewal",
            "Your Adobe Creative Cloud subscription has been charged $54.99. Active until October 16, 2026.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "subscription"
        assert "subscription" in result.extracted_data.get("tags", [])
        assert result.priority >= 4  # High cost subscription


class TestSubscriptionExtraction:
    """Test subscription details extraction."""

    def test_service_name_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@dropbox.com",
            "Dropbox Plus Subscription",
            "Dropbox Plus subscription renewed for $11.99.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        assert sub_data.get("service") in ["dropbox", "Dropbox"]

    def test_amount_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Subscription Charged",
            "Your subscription has been charged $29.99 for this month.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        assert "$29.99" in sub_data.get("amount", "")

    def test_renewal_date_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Subscription Renewal",
            "Your subscription will renew on September 20, 2026.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        renewal = sub_data.get("renewal_date")
        assert renewal == "2026-09-20"

    def test_renewal_in_days_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Upcoming Renewal",
            "Your subscription renews in 5 days for $19.99.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        renewal = sub_data.get("renewal_date")
        assert renewal is not None


class TestHighCostSubscriptionFlagging:
    """Test that high-cost subscriptions are flagged."""

    def test_expensive_subscription_priority_boost(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@microsoft.com",
            "Microsoft 365 Subscription",
            "Your Microsoft 365 subscription charged $99.99 annually.",
        )
        result = processor._fallback_process(msg)
        assert result.priority >= 4
        assert "expensive" in result.extracted_data.get("tags", [])

    def test_moderate_cost_subscription_normal_priority(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Service Subscription",
            "Your subscription charged $9.99.",
        )
        result = processor._fallback_process(msg)
        assert "expensive" not in result.extracted_data.get("tags", [])

    def test_high_cost_flagging_threshold(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Premium Subscription",
            "Your premium subscription charged $15.01.",
        )
        result = processor._fallback_process(msg)
        assert "expensive" in result.extracted_data.get("tags", [])


class TestSubscriptionActionItems:
    """Test action item generation for subscriptions."""

    def test_subscription_charge_action_item(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Subscription Charged",
            "Your subscription charged $25.00.",
        )
        result = processor._fallback_process(msg)
        assert any("charge" in item.lower() for item in result.action_items)
        assert any("cancel" in item.lower() or "unused" in item.lower() for item in result.action_items)

    def test_subscription_renewal_action_item(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Subscription Renewal",
            "Your subscription will renew soon.",
        )
        result = processor._fallback_process(msg)
        assert any("renewal" in item.lower() or "renew" in item.lower() for item in result.action_items)


class TestSubscriptionCategories:
    """Test subscription category detection."""

    def test_streaming_subscription_categorization(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@hulu.com",
            "Hulu Subscription",
            "Hulu subscription renewed.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        assert sub_data.get("category") == "streaming"

    def test_software_subscription_categorization(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@figma.com",
            "Figma Subscription",
            "Figma professional subscription renewed.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        assert sub_data.get("category") == "software"

    def test_cloud_subscription_categorization(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@googleone.com",
            "Google One Storage",
            "Google One subscription renewed for cloud storage.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        assert sub_data.get("category") == "cloud"

    def test_fitness_subscription_categorization(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@peloton.com",
            "Peloton Subscription",
            "Peloton app subscription renewed.",
        )
        result = processor._fallback_process(msg)
        sub_data = result.extracted_data.get("subscription", {})
        assert sub_data.get("category") == "fitness"


class TestSubscriptionTagging:
    """Test subscription-related tags."""

    def test_renews_soon_tag(self):
        today = datetime.now().date()
        renewal_in_2_days = (today + timedelta(days=2)).isoformat()
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Renewal Soon",
            f"Your subscription renews on {renewal_in_2_days}.",
        )
        result = processor._fallback_process(msg)
        assert "renews-soon" in result.extracted_data.get("tags", [])

    def test_renews_week_tag(self):
        today = datetime.now().date()
        renewal_in_5_days = (today + timedelta(days=5)).isoformat()
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Renewal Next Week",
            f"Your subscription renews on {renewal_in_5_days}.",
        )
        result = processor._fallback_process(msg)
        assert "renews-week" in result.extracted_data.get("tags", [])

    def test_subscription_tag(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Subscription",
            "Your subscription has been processed.",
        )
        result = processor._fallback_process(msg)
        assert "subscription" in result.extracted_data.get("tags", [])


class TestSubscriptionVsFinancial:
    """Test that subscriptions are properly distinguished from financial."""

    def test_subscription_not_invoice(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@service.com",
            "Subscription Renewal",
            "Your subscription has been charged $19.99.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "subscription"
        assert result.extracted_data.get("type") != "invoice"

    def test_subscription_priority_vs_bill_priority(self):
        processor = SmartInboxProcessor(api_key=None)
        sub_msg = make_message(
            "billing@service.com",
            "Subscription",
            "Your subscription charged $20 and renews in 5 days.",
        )
        bill_msg = make_message(
            "billing@utility.com",
            "Bill",
            "Your utility bill is due in 5 days. Amount: $150.",
        )
        sub_result = processor._fallback_process(sub_msg)
        bill_result = processor._fallback_process(bill_msg)
        # Bill should have higher priority due to larger amount
        assert bill_result.priority >= sub_result.priority
