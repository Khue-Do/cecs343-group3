import secrets
import sqlite3
from datetime import datetime, timezone


class AccountSignup:
    """Sign-up for a first-time Ticket Purchaser (Issue #9, AC1).

    All database access for accounts lives in this file, the home of
    TicketPurchaserAccount in docs/design.md. It imports neither ticket.py
    nor order.py, so the design's import counts do not change.
    """

    def __init__(self, connection, send_email, base_url):
        self._db = connection
        self._send_email = send_email  # callable(to, subject, body)
        self._base_url = base_url
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS pending_verifications ("
            " token TEXT PRIMARY KEY,"
            " email TEXT NOT NULL,"
            " created_at TEXT NOT NULL)"
        )

    def sign_up(self, email):
        token = secrets.token_urlsafe(32)
        created_at = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO pending_verifications (token, email, created_at)"
            " VALUES (?, ?, ?)",
            (token, email, created_at),
        )
        self._db.commit()
        self._send_email(
            email,
            "Verify your email",
            f"Confirm your account: {self._base_url}/verify/{token}",
        )
        return {"message": f"Check {email} for a verification link."}
