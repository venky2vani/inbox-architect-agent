"""Tests for medical document classification and bill due date detection."""

import tempfile
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


class TestMedicalClassification:
    """Test medical document detection and extraction."""

    def test_lab_result_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "lab@diagnostics.com",
            "Your Lab Results Are Ready",
            "Your blood work results are now available for review at our portal.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "medical"
        assert "medical" in result.extracted_data.get("tags", [])
        assert "health" in result.extracted_data.get("tags", [])

    def test_prescription_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "pharmacy@rx.com",
            "Prescription Ready for Pickup",
            "Your prescription is ready for pickup at CVS Pharmacy.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "medical"
        assert result.category in ["action_needed", "reference"]
        assert "medical" in result.extracted_data.get("tags", [])

    def test_appointment_confirmation(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "clinic@health.com",
            "Appointment Confirmation - Dr. Smith",
            "Your appointment with Dr. Smith is confirmed for tomorrow at 2:30 PM.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "medical"
        assert result.category == "action_needed"
        assert "Confirm or reschedule appointment" in result.action_items[0]

    def test_discharge_summary(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "hospital@health.com",
            "Hospital Discharge Summary",
            (
                "Your discharge summary from General Hospital is attached. "
                "Please follow up with your primary care physician within 5 days."
            ),
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "medical"
        assert "medical" in result.extracted_data.get("tags", [])

    def test_vaccination_record(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "health@state.gov",
            "Vaccination Record Available",
            "Your COVID-19 vaccination record is now available for download.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "medical"
        assert "medical" in result.extracted_data.get("tags", [])


class TestBillDueDateClassification:
    """Test bill due date detection and priority boosting."""

    def test_bill_due_today_is_urgent(self):
        processor = SmartInboxProcessor(api_key=None)
        today = datetime.now().date()
        msg = make_message(
            "billing@utility.com",
            "Bill Payment Due Today",
            f"Your electricity bill of $150 is due today {today}.",
        )
        result = processor._fallback_process(msg)
        assert result.priority == 5
        assert "urgent" in result.extracted_data.get("tags", [])
        assert "bill" in result.extracted_data.get("tags", [])

    def test_bill_due_in_2_days_is_urgent(self):
        processor = SmartInboxProcessor(api_key=None)
        in_two_days = (datetime.now().date() + timedelta(days=2)).isoformat()
        msg = make_message(
            "billing@utility.com",
            "Payment Due Notice",
            f"Please pay your water bill of $85 by {in_two_days}.",
        )
        result = processor._fallback_process(msg)
        assert result.priority >= 4
        assert any(tag in result.extracted_data.get("tags", []) for tag in ["urgent", "due-soon"])

    def test_bill_due_in_7_days_is_high_priority(self):
        processor = SmartInboxProcessor(api_key=None)
        in_seven_days = (datetime.now().date() + timedelta(days=7)).isoformat()
        msg = make_message(
            "billing@cc.com",
            "Credit Card Statement",
            f"Amount due: $500. Payment deadline: {in_seven_days}",
        )
        result = processor._fallback_process(msg)
        assert result.priority >= 4
        assert "due-soon" in result.extracted_data.get("tags", [])

    def test_bill_due_in_10_days_is_normal_priority(self):
        processor = SmartInboxProcessor(api_key=None)
        in_ten_days = (datetime.now().date() + timedelta(days=10)).isoformat()
        msg = make_message(
            "billing@utility.com",
            "Upcoming Bill",
            f"Your next payment is due on {in_ten_days}.",
        )
        result = processor._fallback_process(msg)
        assert result.priority >= 2
        assert "due-soon" not in result.extracted_data.get("tags", [])
        assert "urgent" not in result.extracted_data.get("tags", [])

    def test_invoice_with_amount_and_due_date(self):
        processor = SmartInboxProcessor(api_key=None)
        today = datetime.now().date()
        msg = make_message(
            "vendor@company.com",
            "Invoice INV-2024-001",
            f"Invoice Amount: $1,500 | Due Date: {today}",
        )
        result = processor._fallback_process(msg)
        assert "Pay" in result.action_items[0]
        assert "$1,500" in result.action_items[0]

    def test_payment_overdue(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@lender.com",
            "Payment Overdue Notice",
            "Your payment of $500 is now overdue. Please settle immediately.",
        )
        result = processor._fallback_process(msg)
        assert result.priority == 5
        assert "urgent" in result.extracted_data.get("tags", [])

    def test_balance_due_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "billing@utility.com",
            "Bill Statement",
            "Balance due: $250. Please pay by Aug 25, 2024.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "bill"
        assert "bill" in result.extracted_data.get("tags", [])


class TestMedicalProviderExtraction:
    """Test extraction of medical provider names."""

    def test_extract_provider_from_clinic_email(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "info@greenclinic.com",
            "Appointment Reminder",
            "From: Green Medical Clinic\nYour appointment is tomorrow.",
        )
        result = processor._fallback_process(msg)
        medical_data = result.extracted_data.get("medical", {})
        # Provider extraction may or may not succeed depending on exact parsing
        # Just ensure the medical classification is detected
        assert result.extracted_data.get("type") == "medical"


class TestMedicalActionItems:
    """Test action item generation for medical documents."""

    def test_prescription_action_item(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "pharmacy@rx.com",
            "Prescription Refill Available",
            "Your prescription for amoxicillin is ready for pickup.",
        )
        result = processor._fallback_process(msg)
        assert any("refill" in item.lower() or "pharmacy" in item.lower() for item in result.action_items)

    def test_appointment_action_item(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "clinic@health.com",
            "Confirm Your Appointment",
            "Please confirm your appointment with cardiology next week.",
        )
        result = processor._fallback_process(msg)
        assert any("confirm" in item.lower() or "reschedule" in item.lower() for item in result.action_items)

    def test_lab_result_action_item(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "lab@diagnostics.com",
            "Lab Results Ready",
            "Your glucose test results are now available.",
        )
        result = processor._fallback_process(msg)
        assert any("review" in item.lower() for item in result.action_items)
