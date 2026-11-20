"""Issue and persist tickets after a successful payment (Issue #17)."""

from dataclasses import asdict, dataclass
from decimal import Decimal
import secrets


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
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS tickets ("
            " code TEXT PRIMARY KEY,"
            " owner_email TEXT NOT NULL,"
            " event_title TEXT NOT NULL,"
            " venue TEXT NOT NULL,"
            " event_date TEXT NOT NULL,"
            " event_time TEXT NOT NULL)"
        )
        self._db.commit()

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
            or price <= 0
            or not all((title, venue, event_date, event_time))
        ):
            return {"message": "Ticket details unavailable", "tickets": []}

        total = price * quantity
        if not self._payment_processor(payment_method, total):
            return {"message": "Payment declined", "tickets": []}

        tickets = []
        codes = set()
        for _ in range(quantity):
            code = self._next_unique_code(codes)
            codes.add(code)
            tickets.append(Ticket(code, title, venue, event_date, event_time))

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

        return {
            "message": "Tickets issued",
            "tickets": [ticket.as_dict() for ticket in tickets],
        }

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
