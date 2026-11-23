
"""Unit tests for Issue #20 payment integrity."""

import sqlite3
import pytest
from payment_integrity import PaymentIntegrity


@pytest.fixture
def setup_payment():
    db = sqlite3.connect(":memory:")

    db.execute("""
        CREATE TABLE inventory (
            ticket_id INTEGER PRIMARY KEY,
            available INTEGER NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            payment_id TEXT UNIQUE NOT NULL,
            ticket_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)

    db.execute(
        "INSERT INTO inventory VALUES (1, 10)"
    )
    db.commit()

    yield PaymentIntegrity(db), db
    db.close()


def test_successful_payment_issues_order(setup_payment):
    payment, db = setup_payment

    order_id = payment.process_payment("TX-1", 1, 1, True)

    assert order_id is not None
    assert db.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0] == 1


def test_successful_payment_updates_inventory(setup_payment):
    payment, db = setup_payment

    payment.process_payment("TX-1", 1, 1, True)

    available = db.execute(
        "SELECT available FROM inventory"
    ).fetchone()[0]

    assert available == 9


def test_failed_payment_no_order(setup_payment):
    payment, db = setup_payment

    result = payment.process_payment("TX-1", 1, 1, False)

    assert result is None
    assert db.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0] == 0


def test_failed_payment_keeps_inventory(setup_payment):
    payment, db = setup_payment

    payment.process_payment("TX-1", 1, 1, False)

    available = db.execute(
        "SELECT available FROM inventory"
    ).fetchone()[0]

    assert available == 10


def test_successful_retry_no_duplicate(setup_payment):
    payment, db = setup_payment

    payment.process_payment("TX-1", 1, 1, False)

    first_order = payment.process_payment(
        "TX-2", 1, 1, True
    )

    second_order = payment.process_payment(
        "TX-2", 1, 1, True
    )

    assert first_order == second_order

    assert db.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0] == 1

    assert db.execute(
        "SELECT available FROM inventory"
    ).fetchone()[0] == 9
