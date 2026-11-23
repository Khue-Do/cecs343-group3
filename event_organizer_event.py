"""Event publishing and public event-list operations (Issues #7 and #10)."""

from decimal import Decimal, InvalidOperation
import secrets
import sqlite3

from database import initialize_database


class EventOrganizerEvent:
    def __init__(self, connection):
        self._db = connection
        initialize_database(self._db)

    def publish_event(
        self,
        name,
        date,
        ticket_price,
        *,
        venue="",
        time="",
        ticket_count=0,
        status="published",
        event_id=None,
    ):
        name = (name or "").strip()
        date = (date or "").strip()
        raw_price = ("" if ticket_price is None else str(ticket_price)).strip()
        if not name:
            return {"message": " go to the polls"}
        if not date:
            return {"message": "Enter an event date"}
        if not raw_price:
            return {"message": "Enter a ticket price"}
        try:
            price = Decimal(raw_price)
            if not price.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            return {"message": "Enter a number for the ticket price"}

        try:
            count = int(ticket_count)
            if count < 0:
                raise ValueError
        except (TypeError, ValueError):
            return {"message": "Enter a valid ticket count"}

        event_id = event_id or f"EVT-{secrets.token_hex(4).upper()}"
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO events "
                    "(event_id, title, event_date, event_time, venue, "
                    "price_cents, ticket_count, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event_id,
                        name,
                        date,
                        str(time or "").strip(),
                        str(venue or "").strip(),
                        int((price * 100).quantize(Decimal("1"))),
                        count,
                        status,
                    ),
                )
        except sqlite3.Error:
            return {"message": "Event not stored"}
        return {"message": "Event stored", "event": self.get_event(event_id)}

    def get_event(self, event_id):
        row = self._db.execute(
            "SELECT event_id, title, event_date, event_time, venue, price_cents, "
            "ticket_count, status FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        return self._as_event(row) if row else None

    def list_events(self, *, date=None, include_unpublished=False):
        query = "SELECT event_id, title, event_date, event_time, venue, price_cents, " \
            "ticket_count, status FROM events"
        clauses = []
        values = []
        if not include_unpublished:
            clauses.append("status = 'published'")
        if date:
            clauses.append("event_date = ?")
            values.append(date)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY event_date, title"
        return [self._as_event(row) for row in self._db.execute(query, values)]

    def set_status(self, event_id, status):
        if status not in {"published", "unpublished"}:
            raise ValueError("status must be published or unpublished")
        with self._db:
            cursor = self._db.execute(
                "UPDATE events SET status = ? WHERE event_id = ?", (status, event_id)
            )
        return cursor.rowcount == 1

    def set_seats(self, event_id, seats):
        """Seed named inventory; purchases without a seat request auto-assign it."""
        seats = [str(seat).strip() for seat in seats]
        if any(not seat for seat in seats) or len(set(seats)) != len(seats):
            raise ValueError("seat names must be nonempty and unique")
        with self._db:
            for seat in seats:
                self._db.execute(
                    "INSERT OR IGNORE INTO event_seats (event_id, seat) VALUES (?, ?)",
                    (event_id, seat),
                )
        return seats

    @staticmethod
    def _as_event(row):
        price = None if row[5] is None else Decimal(row[5]) / 100
        return {
            "event_id": row[0],
            "name": row[1],
            "title": row[1],
            "date": row[2],
            "time": row[3],
            "venue": row[4],
            "ticket_price": price,
            "price": price,
            "ticket_count": row[6],
            "status": row[7],
        }
