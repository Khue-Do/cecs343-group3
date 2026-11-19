"""Unit tests for ticket purchase and issuance (Issue #17, AC1)."""

import sqlite3
from decimal import Decimal

from ticket import TicketPurchaseService


def test_successful_two_ticket_purchase_issues_distinct_ticket_details():
    db = sqlite3.connect(":memory:")
    charges = []

    def payment_processor(payment_method, amount):
        charges.append((payment_method, amount))
        return (
            payment_method["last_four"] == "4242"
            and amount <= payment_method["balance"]
        )

    service = TicketPurchaseService(db, payment_processor)
    event = {
        "title": "Jazz Night",
        "venue": "The Blue Room",
        "date": "November 1, 2026",
        "time": "7:00 PM",
        "price": "25.00",
    }

    result = service.purchase(
        "maya@example.com",
        event,
        2,
        {"last_four": "4242", "balance": Decimal("50.00")},
    )

    assert result["message"] == "Tickets issued"
    assert len(result["tickets"]) == 2
    codes = [ticket["code"] for ticket in result["tickets"]]
    assert all(codes)
    assert len(set(codes)) == 2
    assert all(
        ticket["title"] == "Jazz Night"
        and ticket["venue"] == "The Blue Room"
        and ticket["date"] == "November 1, 2026"
        and ticket["time"] == "7:00 PM"
        for ticket in result["tickets"]
    )
    assert charges == [
        (
            {"last_four": "4242", "balance": Decimal("50.00")},
            Decimal("50.00"),
        )
    ]
    stored_codes = {
        row[0]
        for row in db.execute(
            "SELECT code FROM tickets WHERE owner_email = ?",
            ("maya@example.com",),
        )
    }
    assert stored_codes == set(codes)
