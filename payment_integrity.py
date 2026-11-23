
import sqlite3


class PaymentIntegrity:
    def __init__(self, connection):
        self.db = connection

    def process_payment(self, payment_id, ticket_id,
                        quantity, payment_success):

        if quantity <= 0:
            raise ValueError("Invalid quantity")

        if not payment_success:
            return None

        with self.db:
            # Check whether this payment already created an order
            existing = self.db.execute(
                "SELECT id FROM orders WHERE payment_id = ?",
                (payment_id,)
            ).fetchone()

            if existing:
                return existing[0]

            # Remove tickets only when enough are available
            result = self.db.execute(
                """
                UPDATE inventory
                SET available = available - ?
                WHERE ticket_id = ? AND available >= ?
                """,
                (quantity, ticket_id, quantity)
            )

            if result.rowcount == 0:
                raise ValueError("Not enough tickets")

            # Create the order
            cursor = self.db.execute(
                """
                INSERT INTO orders
                    (payment_id, ticket_id, quantity)
                VALUES (?, ?, ?)
                """,
                (payment_id, ticket_id, quantity)
            )

            return cursor.lastrowid
