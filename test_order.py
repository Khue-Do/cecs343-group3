"""Unit tests for Issues #8, #19, and payment/inventory integrity in #20."""

import sqlite3

from event_organizer_event import EventOrganizerEvent
from order import OrderService


def setup_services(ticket_count=1, payment=lambda _method, _total: True):
    db = sqlite3.connect(":memory:")
    EventOrganizerEvent(db).publish_event(
        "Jazz Night", "2026-11-14", "25.00", venue="The Blue Room",
        time="7:00 PM", ticket_count=ticket_count, event_id="EVT-104"
    )
    EventOrganizerEvent(db).set_seats("EVT-104", ["A1"])
    return db, OrderService(db, payment, code_generator=iter(["JZ-1042", "JZ-1043"]).__next__)


def test_canceling_order_releases_seat_for_another_purchase():
    _db, orders = setup_services()
    first = orders.purchase(
        "ana@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"]
    )
    canceled = orders.cancel("ana@example.com", "ORD-1001")
    second = orders.purchase(
        "ben@example.com", "EVT-104", 1, {}, order_ref="ORD-1002", seats=["A1"]
    )

    assert first["order"]["status"] == "confirmed"
    assert canceled["message"] == "Order ORD-1001 canceled"
    assert second["order"]["status"] == "confirmed"


def test_sold_seat_cannot_be_purchased_by_another_customer():
    _db, orders = setup_services(ticket_count=2)
    orders.purchase("ana@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"])

    result = orders.purchase("ben@example.com", "EVT-104", 1, {}, order_ref="ORD-1002", seats=["A1"])

    assert result["message"] == "Seat A1 is not available"


def test_quantity_above_inventory_is_rejected_with_available_count():
    _db, orders = setup_services(ticket_count=1)

    result = orders.purchase("ana@example.com", "EVT-104", 2, {}, order_ref="ORD-1003")

    assert result["message"] == "Order not created"
    assert result["detail"] == "Ticket count: 1"
    assert orders.get_order("ORD-1003") is None


def test_declined_payment_creates_no_ticket_and_does_not_reserve_seat():
    db, orders = setup_services(payment=lambda _method, _total: False)

    result = orders.purchase(
        "ana@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"]
    )

    seat_owner = db.execute(
        "SELECT order_ref FROM event_seats WHERE event_id = 'EVT-104' AND seat = 'A1'"
    ).fetchone()[0]
    assert result["message"] == "Payment declined"
    assert result["order"] is None
    assert result["tickets"] == []
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert db.execute("SELECT status FROM payment_attempts").fetchone()[0] == "declined"
    assert seat_owner is None


def test_pending_payment_is_saved_without_issuing_or_reserving_tickets():
    db, orders = setup_services(payment=lambda _method, _total: {"status": "pending", "transaction_ref": "TX-8822"})

    result = orders.purchase(
        "ana@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"]
    )

    assert result["message"] == "Payment pending"
    assert result["order"] is None
    assert result["tickets"] == []
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert db.execute(
        "SELECT transaction_ref, status FROM payment_attempts"
    ).fetchone() == ("TX-8822", "pending")
    assert db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 0
    assert db.execute(
        "SELECT order_ref FROM event_seats WHERE event_id = 'EVT-104' AND seat = 'A1'"
    ).fetchone()[0] is None


def test_successful_retry_issues_one_order_and_updates_inventory_once():
    db, _orders = setup_services()
    outcomes = iter([False, True])
    charges = []

    def processor(_method, total):
        charges.append(total)
        return next(outcomes)

    orders = OrderService(
        db, processor, code_generator=iter(["JZ-1042"]).__next__
    )
    first = orders.purchase(
        "maya@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"]
    )
    second = orders.purchase(
        "maya@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"]
    )
    repeated_success = orders.purchase(
        "maya@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"]
    )

    assert first["order"] is None
    assert second["message"] == "Order confirmed"
    assert repeated_success["order"]["order_ref"] == "ORD-1001"
    assert len(repeated_success["tickets"]) == 1
    assert len(charges) == 2
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'valid'").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM payment_attempts").fetchone()[0] == 2


def test_second_cancellation_and_missing_order_messages():
    _db, orders = setup_services()
    orders.purchase("ana@example.com", "EVT-104", 1, {}, order_ref="ORD-1001", seats=["A1"])
    orders.cancel("ana@example.com", "ORD-1001")

    assert orders.cancel("ana@example.com", "ORD-1001")["message"] == "Order ORD-1001 already canceled"
    assert orders.cancel("ana@example.com", "ORD-9999")["message"] == "Order ORD-9999 not found"


def test_saved_order_displays_transaction_and_status_and_expires():
    db, orders = setup_services()
    orders.record_order(
        "ORD-302", "ana@example.com", "EVT-104", "50.00", "TX-8825", "pending",
        [{"title": "General Admission", "quantity": 1}],
        deadline="2026-10-12 14:00 America/Los_Angeles",
    )

    expired = orders.expire_past_deadlines(now="2026-11-21T00:00:00+00:00")
    saved = orders.get_order("ORD-302")

    assert expired[0]["status"] == "expired"
    assert saved["transaction_ref"] == "TX-8825"
    assert saved["ticket_selections"][0]["title"] == "General Admission"

def test_issue20_successful_payment_creates_order():
    db, orders = setup_services()

    result = orders.purchase(
        "maya@example.com", "EVT-104", 1, {},
        order_ref="ORD-2001", seats=["A1"]
    )

    assert result["message"] == "Order confirmed"
    assert result["order"]["status"] == "confirmed"
    assert len(result["tickets"]) == 1
    assert db.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0] == 1


def test_issue20_successful_payment_reserves_seat():
    db, orders = setup_services()

    orders.purchase(
        "maya@example.com", "EVT-104", 1, {},
        order_ref="ORD-2001", seats=["A1"]
    )

    seat = db.execute(
        "SELECT order_ref FROM event_seats "
        "WHERE event_id = 'EVT-104' AND seat = 'A1'"
    ).fetchone()

    assert seat[0] == "ORD-2001"
    assert db.execute(
        "SELECT COUNT(*) FROM tickets "
        "WHERE status = 'valid'"
    ).fetchone()[0] == 1


def test_issue20_failed_payment_keeps_inventory():
    db, orders = setup_services(
        payment=lambda _method, _total: False
    )

    result = orders.purchase(
        "maya@example.com", "EVT-104", 1, {},
        order_ref="ORD-2001", seats=["A1"]
    )

    assert result["order"] is None
    assert result["tickets"] == []

    assert db.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0] == 0

    assert db.execute(
        "SELECT COUNT(*) FROM tickets"
    ).fetchone()[0] == 0

    seat = db.execute(
        "SELECT order_ref FROM event_seats "
        "WHERE event_id = 'EVT-104' AND seat = 'A1'"
    ).fetchone()

    assert seat[0] is None
