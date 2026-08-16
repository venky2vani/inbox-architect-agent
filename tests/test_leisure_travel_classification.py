"""Tests for leisure, travel, shopping, work, and personal classifications."""

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


class TestTravelClassification:
    """Test travel document detection and extraction."""

    def test_flight_booking_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "bookings@airline.com",
            "Flight Confirmation - New York to London",
            "Your flight booking confirmation #AA123456. Departure: Aug 25, 2026 at 10:00 AM from JFK to LHR.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "travel"
        assert "travel" in result.extracted_data.get("tags", [])

    def test_hotel_reservation_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "reservations@hotel.com",
            "Hotel Booking Confirmation",
            "Your hotel reservation is confirmed. Check-in: Aug 25, 2026. Booking reference: HT789012.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "travel"
        assert "travel" in result.extracted_data.get("tags", [])

    def test_car_rental_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "reservations@rental.com",
            "Car Rental Confirmation",
            "Your car rental booking confirmation. Vehicle pickup: Aug 25, 2026 at JFK. Reservation #CR345678.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "travel"
        assert "travel" in result.extracted_data.get("tags", [])


class TestLeisureEventClassification:
    """Test leisure and event document detection."""

    def test_concert_ticket_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "tickets@ticketmaster.com",
            "Concert Tickets - Taylor Swift Live",
            "Your concert tickets have been confirmed. Artist: Taylor Swift. Date: September 15, 2026.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "event"
        assert "leisure" in result.extracted_data.get("tags", [])

    def test_movie_screening_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "tickets@cinema.com",
            "Movie Ticket Confirmation",
            "Your movie screening ticket. Film: Inception. Time: 7:30 PM, September 10, 2026.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "event"
        assert "leisure" in result.extracted_data.get("tags", [])

    def test_sports_event_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "tickets@sports.com",
            "Game Ticket - Yankees vs Red Sox",
            "Your baseball game ticket confirmed. Team: Yankees. Match: vs Red Sox. Date: September 5, 2026.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "event"
        assert "leisure" in result.extracted_data.get("tags", [])

    def test_restaurant_reservation_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "reservations@restaurant.com",
            "Reservation Confirmed",
            "Your dining reservation confirmed. Restaurant: The Italian Place. Reservation for 4 people at 7:00 PM.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "event"
        assert "leisure" in result.extracted_data.get("tags", [])


class TestShoppingOrderClassification:
    """Test shopping and order detection."""

    def test_order_confirmation_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "orders@amazon.com",
            "Order Confirmation - Your Purchase",
            "Thank you for your order. Order number #12345678. Items: Laptop, Mouse. Total: $1,299.99.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "order"
        assert "shopping" in result.extracted_data.get("tags", [])

    def test_shipment_tracking_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "shipments@delivery.com",
            "Your Package Has Shipped",
            "Your package has shipped. Tracking number: TRK987654. Expected delivery: Aug 20, 2026.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "order"
        assert "shopping" in result.extracted_data.get("tags", [])
        assert result.category in ["action_needed", "reference"]

    def test_delivery_notification_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "notifications@fedex.com",
            "Delivery Notification",
            "Your package will arrive on Aug 18, 2026. Out for delivery today.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "order"
        assert "shopping" in result.extracted_data.get("tags", [])

    def test_return_request_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "support@amazon.com",
            "Return Confirmation",
            "Your return request has been processed. Refund amount: $99.99. Order #12345678.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "order"
        assert "shopping" in result.extracted_data.get("tags", [])


class TestWorkClassification:
    """Test work-related document detection."""

    def test_project_update_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "project.lead@company.com",
            "Project Update - Q4 Roadmap",
            "Project deadline is August 30, 2026. Next sprint deliverables: API redesign, database optimization.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "work"
        assert "work" in result.extracted_data.get("tags", [])
        assert result.category == "action_needed"

    def test_collaboration_request_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "dev.lead@company.com",
            "Code Review Requested",
            "Please review the pull request for the auth module. Changes include OAuth2 implementation.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "work"
        assert "work" in result.extracted_data.get("tags", [])
        assert result.category == "action_needed"

    def test_assignment_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "manager@company.com",
            "Task Assignment",
            "You have been assigned to the task: Implement user dashboard. Please start by next Monday.",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "work"
        assert "work" in result.extracted_data.get("tags", [])
        assert result.category == "action_needed"


class TestPersonalClassification:
    """Test personal communication detection."""

    def test_family_email_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "mom@personal.com",
            "Family Gathering This Weekend",
            "Hi, I wanted to let you know about the family dinner this Sunday. Can you make it?",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "personal"
        assert "personal" in result.extracted_data.get("tags", [])

    def test_friend_email_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "john@gmail.com",
            "Let's Catch Up",
            "Hey buddy! I'm in town next week. Should we grab coffee?",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "personal"
        assert "personal" in result.extracted_data.get("tags", [])

    def test_social_invitation_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "sarah@gmail.com",
            "You're Invited to a Party!",
            "I'm throwing a party on Saturday night. Hope you can make it!",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "personal"
        assert "personal" in result.extracted_data.get("tags", [])

    def test_hobby_group_email_detection(self):
        processor = SmartInboxProcessor(api_key=None)
        msg = make_message(
            "runners@meetup.com",
            "Running Club Meetup",
            "This week's group run is at Central Park. Join our community of runners!",
        )
        result = processor._fallback_process(msg)
        assert result.extracted_data.get("type") == "personal"
        assert "personal" in result.extracted_data.get("tags", [])


class TestExtractionHelpers:
    """Test helper methods for data extraction."""

    def test_travel_destination_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        text = "Destination: Paris, France. Check-in date: August 25, 2026."
        destination = processor._extract_travel_destination(text)
        assert destination is not None
        assert "Paris" in destination or "France" in destination

    def test_event_name_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        text = "Event: Summer Music Festival. Date: August 20, 2026."
        event_name = processor._extract_event_name(text)
        assert event_name is not None

    def test_order_number_extraction(self):
        processor = SmartInboxProcessor(api_key=None)
        text = "Order number: #AMZ12345678. Confirmation ID: AMZ12345678."
        order_num = processor._extract_order_number(text)
        assert order_num is not None
        assert "AMZ12345678" in order_num
