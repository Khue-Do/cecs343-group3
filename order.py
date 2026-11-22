"""Order records, payment outcomes, and transactional ticket inventory.

Statuses: pending means payment has not completed; confirmed means payment
succeeded and tickets were issued; canceled means payment was declined or the
customer canceled; refunded records a completed refund; expired means the
payment deadline passed without payment.
"""

from datetime import datetime, timezone
from decimal import Decimal
import secrets
import sqlite3
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from database import initialize_database


class OrderService:
    STATUSES = {"pending", "confirmed", "canceled", "refunded", "expired"}

    def __init__(self, connection, payment_processor, code_generator=None):
        self._db = connection
        self._payment_processor = payment_processor
        self._code_generator = code_generator or self._new_ticket_code
        initialize_database(self._db)

    def purchase(
        self,
        owner_email,
        event_id,
        quantity,
        payment_method,
        *,
        order_ref=None,
        transaction_ref=None,
        seats=None,
        idempotency_key=None,
    ):
        """Charge once, then atomically record the order and issue its tickets."""
        if not owner_email:
            return {"message": "Account required", "tickets": []}
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return {"message": "Ticket details unavailable", "tickets": []}
        if quantity < 1 or quantity > 4:
            return {"message": "Ticket details unavailable", "tickets": []}

        order_ref = order_ref or self._new_order_ref()
        idempotency_key = idempotency_key or order_ref
        transaction_ref = transaction_ref or f"TX-{secrets.token_hex(4).upper()}"
        try:
            self._db.execute("BEGIN IMMEDIATE")
            existing_ref = self._db.execute(
                "SELECT order_ref FROM orders WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing_ref:
                self._db.commit()
                existing_order = self.get_order(existing_ref[0])
                if (
                    existing_order is None
                    or existing_order["owner_email"] != owner_email
                    or existing_order["event_id"] != event_id
                ):
                    return {"message": "Order not created", "tickets": []}
                existing_tickets = [
                    self.get_ticket(owner_email, row[0])
                    for row in self._db.execute(
                        "SELECT code FROM tickets WHERE order_ref = ? AND status = 'valid' ORDER BY code",
                        (existing_ref[0],),
                    )
                ]
                return {
                    "message": "Order confirmed" if existing_order["status"] == "confirmed" else f"Order {existing_order['status']}",
                    "order": existing_order,
                    "tickets": existing_tickets,
                }
            event = self._db.execute(
                "SELECT title, event_date, event_time, venue, price_cents, ticket_count "
                "FROM events WHERE event_id = ? AND status = 'published'",
                (event_id,),
            ).fetchone()
            if event is None or not all((event[0], event[1], event[2], event[3])) or event[4] is None:
                self._db.rollback()
                return {"message": "Ticket details unavailable", "tickets": []}

            title, event_date, event_time, venue, price_cents, ticket_count = event
            seat_list = None
            if seats is not None:
                seat_list = self._select_seats(event_id, quantity, seats)
                if seat_list is None:
                    self._db.rollback()
                    return {"message": f"Seat {list(seats)[0]} is not available", "tickets": []}

            sold = self._db.execute(
                "SELECT COUNT(*) FROM tickets WHERE event_id = ? AND status = 'valid'",
                (event_id,),
            ).fetchone()[0]
            if sold + quantity > ticket_count:
                self._db.rollback()
                return {
                    "message": "Order not created",
                    "detail": f"Ticket count: {ticket_count}",
                    "tickets": [],
                }

            if seat_list is None:
                seat_list = self._select_seats(event_id, quantity, None)
                if seat_list is None:
                    self._db.rollback()
                    return {"message": "Seat is not available", "tickets": []}

            total = Decimal(price_cents) * quantity / 100
            try:
                payment_result = self._payment_processor(payment_method, total)
            except Exception:
                payment_result = False
            if isinstance(payment_result, dict):
                payment_status = str(payment_result.get("status", "")).lower()
                transaction_ref = payment_result.get("transaction_ref") or transaction_ref
            elif isinstance(payment_result, str):
                payment_status = payment_result.lower()
            else:
                payment_status = "confirmed" if payment_result else "declined"
            if payment_status in {"success", "succeeded", "paid", "confirmed"}:
                status = "confirmed"
                paid = True
            elif payment_status == "pending":
                status = "pending"
                paid = False
            else:
                status = "canceled"
                paid = False
            attempt_number = self._db.execute(
                "SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM payment_attempts "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()[0]
            self._db.execute(
                "INSERT INTO payment_attempts "
                "(idempotency_key, attempt_number, owner_email, event_id, quantity, "
                "total_cents, transaction_ref, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (idempotency_key, attempt_number, owner_email, event_id, quantity,
                 price_cents * quantity, transaction_ref, payment_status,
                 datetime.now(timezone.utc).isoformat()),
            )
            if not paid:
                self._db.commit()
                return {
                    "message": "Payment pending" if status == "pending" else "Payment declined",
                    "order": None,
                    "tickets": [],
                }

            self._db.execute(
                "INSERT INTO orders "
                "(order_ref, owner_email, event_id, total_cents, transaction_ref, status, idempotency_key) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (order_ref, owner_email, event_id, price_cents * quantity,
                 transaction_ref, status, idempotency_key),
            )

            tickets = []
            codes = set()
            for seat in seat_list:
                code = self._unique_code(codes)
                codes.add(code)
                tickets.append(code)
                self._db.execute(
                    "INSERT INTO tickets "
                    "(code, owner_email, event_title, venue, event_date, event_time, "
                    "event_id, order_ref, seat, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'valid')",
                    (code, owner_email, title, venue, event_date, event_time,
                     event_id, order_ref, seat),
                )
                if seat is not None:
                    self._db.execute(
                        "UPDATE event_seats SET order_ref = ? WHERE event_id = ? AND seat = ?",
                        (order_ref, event_id, seat),
                    )
                self._db.execute(
                    "INSERT INTO order_items (order_ref, ticket_title, quantity, seat) "
                    "VALUES (?, ?, 1, ?)",
                    (order_ref, title, seat),
                )
            self._db.commit()
            return {
                "message": "Order confirmed",
                "order": self.get_order(order_ref),
                "tickets": [self.get_ticket(owner_email, code) for code in tickets],
            }
        except sqlite3.IntegrityError:
            self._db.rollback()
            if seats:
                return {"message": f"Seat {list(seats)[0]} is not available", "tickets": []}
            return {"message": "Seat is not available", "tickets": []}
        except sqlite3.Error:
            self._db.rollback()
            return {"message": "Order not created", "tickets": []}
        except Exception:
            self._db.rollback()
            return {"message": "Ticket could not be issued", "tickets": []}

    def record_order(
        self,
        order_ref,
        owner_email,
        event_id,
        total,
        transaction_ref,
        status,
        ticket_selections,
        *,
        deadline=None,
    ):
        """Save/view the payment status and ticket selections (Issue #8)."""
        if status not in self.STATUSES:
            raise ValueError("unsupported order status")
        total_cents = int((Decimal(str(total)) * 100).quantize(Decimal("1")))
        with self._db:
            self._db.execute(
                "INSERT INTO orders "
                "(order_ref, owner_email, event_id, total_cents, transaction_ref, status, deadline) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (order_ref, owner_email, event_id, total_cents, transaction_ref, status, deadline),
            )
            for selection in ticket_selections:
                self._db.execute(
                    "INSERT INTO order_items (order_ref, ticket_title, quantity, seat) "
                    "VALUES (?, ?, ?, ?)",
                    (order_ref, selection["title"], int(selection.get("quantity", 1)), selection.get("seat")),
                )
        return self.get_order(order_ref)

    def get_order(self, order_ref):
        row = self._db.execute(
            "SELECT order_ref, owner_email, event_id, total_cents, transaction_ref, status, deadline "
            "FROM orders WHERE order_ref = ?",
            (order_ref,),
        ).fetchone()
        if row is None:
            return None
        items = [
            {"title": item[0], "quantity": item[1], "seat": item[2]}
            for item in self._db.execute(
                "SELECT ticket_title, quantity, seat FROM order_items WHERE order_ref = ?",
                (order_ref,),
            )
        ]
        return {
            "order_ref": row[0],
            "owner_email": row[1],
            "event_id": row[2],
            "total": Decimal(row[3]) / 100,
            "transaction_ref": row[4],
            "status": row[5],
            "deadline": row[6],
            "ticket_selections": items,
        }

    def cancel(self, owner_email, order_ref):
        order = self.get_order(order_ref)
        if order is None or order["owner_email"] != owner_email:
            return {"message": f"Order {order_ref} not found"}
        if order["status"] == "canceled":
            return {"message": f"Order {order_ref} already canceled"}
        if order["status"] in {"refunded", "expired"}:
            return {"message": f"Order {order_ref} cannot be canceled"}
        try:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute("UPDATE orders SET status = 'canceled' WHERE order_ref = ?", (order_ref,))
            self._db.execute("UPDATE tickets SET status = 'canceled' WHERE order_ref = ?", (order_ref,))
            self._db.execute("UPDATE event_seats SET order_ref = NULL WHERE order_ref = ?", (order_ref,))
            self._db.commit()
        except sqlite3.Error:
            self._db.rollback()
            return {"message": "Order could not be canceled"}
        return {"message": f"Order {order_ref} canceled", "order": self.get_order(order_ref)}

    def update_status(self, order_ref, status):
        if status not in self.STATUSES:
            raise ValueError("unsupported order status")
        with self._db:
            cursor = self._db.execute(
                "UPDATE orders SET status = ? WHERE order_ref = ?", (status, order_ref)
            )
            if cursor.rowcount and status in {"refunded", "canceled", "expired"}:
                self._db.execute("UPDATE tickets SET status = ? WHERE order_ref = ?", (status, order_ref))
                self._db.execute("UPDATE event_seats SET order_ref = NULL WHERE order_ref = ?", (order_ref,))
        return self.get_order(order_ref)

    def expire_past_deadlines(self, now=None):
        now = now or datetime.now(timezone.utc)
        if isinstance(now, str):
            now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        pending = list(self._db.execute(
            "SELECT order_ref, deadline FROM orders WHERE status = 'pending' AND deadline IS NOT NULL"
        ))
        refs = []
        for ref, deadline in pending:
            parsed = self._parse_deadline(deadline)
            if parsed is not None and parsed < now:
                refs.append(ref)
        with self._db:
            self._db.executemany(
                "UPDATE orders SET status = 'expired' WHERE order_ref = ?",
                [(ref,) for ref in refs],
            )
        return [self.get_order(ref) for ref in refs]

    def get_ticket(self, owner_email, code):
        row = self._db.execute(
            "SELECT code, event_title, venue, event_date, event_time, seat "
            "FROM tickets WHERE code = ? AND owner_email = ? AND status = 'valid'",
            (code, owner_email),
        ).fetchone()
        if row is None:
            return None
        return {"code": row[0], "title": row[1], "venue": row[2],
                "date": row[3], "time": row[4], "seat": row[5]}

    def tickets_for(self, owner_email, as_of=None):
        rows = self._db.execute(
            "SELECT code, event_title, venue, event_date, event_time, seat "
            "FROM tickets WHERE owner_email = ? AND status = 'valid' ORDER BY event_date",
            (owner_email,),
        )
        tickets = [
            {"code": r[0], "title": r[1], "venue": r[2], "date": r[3], "time": r[4], "seat": r[5]}
            for r in rows
        ]
        if as_of is None:
            as_of = datetime.now().date()
        elif isinstance(as_of, str):
            as_of = self._parse_event_date(as_of)
        current = [ticket for ticket in tickets if self._parse_event_date(ticket["date"]) >= as_of]
        past = [ticket for ticket in tickets if self._parse_event_date(ticket["date"]) < as_of]
        return {"current": current, "past": past}

    @staticmethod
    def _parse_event_date(value):
        for pattern in ("%Y-%m-%d", "%B %d, %Y", "%B %d %Y"):
            try:
                return datetime.strptime(value, pattern).date()
            except (TypeError, ValueError):
                pass
        raise ValueError(f"Unsupported event date: {value}")

    @staticmethod
    def _parse_deadline(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        pieces = value.rsplit(" ", 1)
        if len(pieces) == 2:
            try:
                zone = ZoneInfo(pieces[1])
                parsed = datetime.strptime(pieces[0], "%Y-%m-%d %H:%M")
                return parsed.replace(tzinfo=zone).astimezone(timezone.utc)
            except (ValueError, ZoneInfoNotFoundError):
                return None
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _select_seats(self, event_id, quantity, requested):
        if requested is not None:
            requested = list(requested)
            if len(requested) != quantity or len(set(requested)) != quantity:
                return None
            for seat in requested:
                row = self._db.execute(
                    "SELECT order_ref FROM event_seats WHERE event_id = ? AND seat = ?",
                    (event_id, seat),
                ).fetchone()
                if row is None or row[0] is not None:
                    return None
            return requested

        available = [row[0] for row in self._db.execute(
            "SELECT seat FROM event_seats WHERE event_id = ? AND order_ref IS NULL ORDER BY seat LIMIT ?",
            (event_id, quantity),
        )]
        all_seats = self._db.execute(
            "SELECT COUNT(*) FROM event_seats WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
        if all_seats and len(available) != quantity:
            return None
        return available if all_seats else [None] * quantity

    def _unique_code(self, codes):
        for _ in range(100):
            try:
                code = self._code_generator()
            except Exception as error:
                raise RuntimeError("ticket code service unavailable") from error
            if not code or code in codes:
                continue
            if self._db.execute("SELECT 1 FROM tickets WHERE code = ?", (code,)).fetchone() is None:
                return code
        raise RuntimeError("ticket code service unavailable")

    @staticmethod
    def _new_ticket_code():
        return f"TKT-{secrets.token_hex(6).upper()}"

    @staticmethod
    def _new_order_ref():
        return f"ORD-{secrets.token_hex(4).upper()}"
