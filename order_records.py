
from datetime import datetime
from zoneinfo import ZoneInfo


class OrderRecords:
    def __init__(self):
        self.orders = {}

    def save_order(self, order_id, ticket, total,
                   transaction, payment, deadline=None):
        status = self.get_status(payment, deadline)

        order = {
            "order_id": order_id,
            "ticket": ticket,
            "total": total,
            "transaction": transaction,
            "status": status,
            "payment": payment,
            "deadline": deadline
        }

        self.orders[order_id] = order
        return order

    def get_status(self, payment, deadline=None):
        if payment == "refunded":
            return "Refunded"

        if payment == "declined":
            return "Canceled"

        if payment == "confirmed":
            return "Confirmed"

        if payment == "pending":
            if deadline is not None:
                now = datetime.now(
                    ZoneInfo("America/Los_Angeles")
                )

                if now >= deadline:
                    return "Expired"

            return "Pending"

        raise ValueError("Invalid payment status")

    def view_order(self, order_id):
        order = self.orders[order_id].copy()

        order["status"] = self.get_status(
            order["payment"],
            order["deadline"]
        )

        return {
            "ticket": order["ticket"],
            "total": order["total"],
            "transaction": order["transaction"],
            "status": order["status"]
        }
