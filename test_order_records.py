
"""Unit tests for Issue #8 payment order records."""

from datetime import datetime
from zoneinfo import ZoneInfo
from order_records import OrderRecords


def test_pending_payment():
    records = OrderRecords()

    records.save_order(
        "ORD-300", "General Admission",
        50.00, "TX-8822", "pending"
    )

    result = records.view_order("ORD-300")

    assert result["ticket"] == "General Admission"
    assert result["total"] == 50.00
    assert result["transaction"] == "TX-8822"
    assert result["status"] == "Pending"


def test_declined_payment():
    records = OrderRecords()

    records.save_order(
        "ORD-300", "General Admission",
        50.00, "TX-8823", "declined"
    )

    result = records.view_order("ORD-300")

    assert result["ticket"] == "General Admission"
    assert result["total"] == 50.00
    assert result["transaction"] == "TX-8823"
    assert result["status"] == "Canceled"


def test_refunded_payment():
    records = OrderRecords()

    records.save_order(
        "ORD-301", "General Admission",
        50.00, "TX-8824", "refunded"
    )

    result = records.view_order("ORD-301")

    assert result["ticket"] == "General Admission"
    assert result["total"] == 50.00
    assert result["transaction"] == "TX-8824"
    assert result["status"] == "Refunded"


def test_expired_payment():
    records = OrderRecords()

    deadline = datetime(
        2026, 10, 12, 14, 0,
        tzinfo=ZoneInfo("America/Los_Angeles")
    )

    records.save_order(
        "ORD-302", "General Admission",
        50.00, "TX-8825", "pending", deadline
    )

    result = records.view_order("ORD-302")

    assert result["ticket"] == "General Admission"
    assert result["total"] == 50.00
    assert result["transaction"] == "TX-8825"
    assert result["status"] == "Expired"
