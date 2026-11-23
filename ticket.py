"""Issue and persist tickets after a successful payment (Issue #17)."""

from dataclasses import asdict, dataclass
from decimal import Decimal
import secrets

from database import initialize_database


@dataclass(frozen=True)
class Ticket:
    code: str
    title: str
    venue: str
    date: str
    time: str

    def as_dict(self):
        return asdict(self)


class TicketPurchaseService:
    """Create tickets for a purchaser when the injected payment succeeds.

    ``payment_processor`` is a callable receiving ``(payment_method, total)``
    and returning a truthy value only when the charge succeeds. The database
    stores the purchaser email with each ticket so later account-page work can
    retrieve tickets by owner.
    """

    def __init__(self, connection, payment_processor, code_generator=None):
        self._db = connection
        self._payment_processor = payment_processor
        self._code_generator = code_generator or self._new_code
        initialize_database(self._db)

    def purchase(self, account_email, event, quantity, payment_method):
        """Return ticket details for a successful purchase."""
        if not account_email:
            return {"message": "Account required", "tickets": []}

        try:
            quantity = int(quantity)
            price = Decimal(str(event["price"]))
            title = event["title"]
            venue = event["venue"]
            event_date = event["date"]
            event_time = event["time"]
        except (KeyError, TypeError, ValueError, ArithmeticError):
            return {"message": "Ticket details unavailable", "tickets": []}

        if (
            quantity < 1
            or quantity > 4
            or not price.is_finite()
            or price <= 0
            or not all((title, venue, event_date, event_time))
        ):
            return {"message": "Ticket details unavailable", "tickets": []}

        total = price * quantity
        try:
            payment_succeeded = self._payment_processor(payment_method, total)
        except Exception:
            payment_succeeded = False
        if not payment_succeeded:
            return {"message": "Payment declined", "tickets": []}

        tickets = []
        codes = set()
        try:
            for _ in range(quantity):
                code = self._next_unique_code(codes)
                codes.add(code)
                tickets.append(Ticket(code, title, venue, event_date, event_time))
        except Exception:
            return {"message": "Ticket could not be issued", "tickets": []}

        try:
            with self._db:
                self._db.executemany(
                    "INSERT INTO tickets "
                    "(code, owner_email, event_title, venue, event_date, event_time) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        (
                            ticket.code,
                            account_email,
                            ticket.title,
                            ticket.venue,
                            ticket.date,
                            ticket.time,
                        )
                        for ticket in tickets
                    ],
                )
        except Exception:
            return {"message": "Ticket could not be issued", "tickets": []}

        return {
            "message": "Tickets issued",
            "tickets": [ticket.as_dict() for ticket in tickets],
        }

    def get_ticket(self, account_email, code):
        """Return a ticket only to its owner; otherwise return None."""
        row = self._db.execute(
            "SELECT code, event_title, venue, event_date, event_time "
            "FROM tickets WHERE code = ? AND owner_email = ? AND status = 'valid'",
            (code, account_email),
        ).fetchone()
        if row is None:
            return None
        return Ticket(*row).as_dict()

    def tickets_for(self, account_email):
        """Return all valid tickets owned by an account, including after reload."""
        rows = self._db.execute(
            "SELECT code, event_title, venue, event_date, event_time "
            "FROM tickets WHERE owner_email = ? AND status = 'valid' ORDER BY event_date",
            (account_email,),
        )
        return [Ticket(*row).as_dict() for row in rows]

    @staticmethod
    def _new_code():
        return f"TKT-{secrets.token_hex(6).upper()}"

    def _next_unique_code(self, codes_in_purchase):
        for _ in range(100):
            code = self._code_generator()
            if not code or code in codes_in_purchase:
                continue
            exists = self._db.execute(
                "SELECT 1 FROM tickets WHERE code = ?", (code,)
            ).fetchone()
            if exists is None:
                return code
        raise RuntimeError("Could not generate a unique ticket code")
