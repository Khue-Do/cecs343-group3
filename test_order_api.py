
"""Route/API tests for Issue #8."""

import pytest
from order_api import app, records


@pytest.fixture
def client():
    app.config["TESTING"] = True
    records.orders.clear()

    with app.test_client() as client:
        yield client


@pytest.mark.parametrize(
    "payment,transaction,status",
    [
        ("pending", "TX-8822", "Pending"),
        ("declined", "TX-8823", "Canceled"),
        ("refunded", "TX-8824", "Refunded"),
    ]
)
def test_save_and_view_order(
    client, payment, transaction, status
):
    response = client.post("/orders", json={
        "order_id": "ORD-300",
        "ticket": "General Admission",
        "total": 50.00,
        "transaction": transaction,
        "payment": payment
    })

    assert response.status_code == 201

    response = client.get("/orders/ORD-300")

    assert response.status_code == 200
    assert response.json["ticket"] == "General Admission"
    assert response.json["total"] == 50.00
    assert response.json["transaction"] == transaction
    assert response.json["status"] == status
