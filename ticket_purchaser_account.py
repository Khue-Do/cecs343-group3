import secrets
from datetime import datetime, timedelta, timezone
import re

from database import initialize_database


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
        initialize_database(self._db)

    def sign_up(self, email):
        email = (email or "").strip()
        if not email:
            return {"message": "Enter an email address.", "field": "email"}
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return {
                "message": "Enter an email address in the form name@domain.",
                "field": "email",
            }
        if self._db.execute("SELECT 1 FROM accounts WHERE email = ?", (email,)).fetchone():
            return {
                "message": "An account exists for this email. Log in instead.",
                "link": {"label": "Log in", "href": "/login"},
                "field": "email",
            }
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

    def verify_email(self, token, *, now=None):
        row = self._db.execute(
            "SELECT email, created_at, used FROM pending_verifications WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return {"message": "This link is invalid."}
        email, created_at, used = row
        if used:
            return {
                "message": "This link was already used.",
                "link": {"label": "Log in", "href": "/login"},
            }
        sent_at = datetime.fromisoformat(created_at)
        now = now or datetime.now(timezone.utc)
        if now - sent_at > timedelta(minutes=15):
            return {
                "message": "This link has expired.",
                "button": {"label": "Send a new link", "action": "/signup/resend"},
                "email": email,
            }
        with self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO accounts (email, verified, created_at) VALUES (?, 1, ?)",
                (email, now.isoformat()),
            )
            self._db.execute(
                "UPDATE pending_verifications SET used = 1 WHERE token = ?", (token,)
            )
        return {"message": "Email verified", "email": email}

    def login_link(self, email):
        email = (email or "").strip()
        account = self._db.execute(
            "SELECT verified FROM accounts WHERE email = ?", (email,)
        ).fetchone()
        if account is None:
            pending = self._db.execute(
                "SELECT 1 FROM pending_verifications WHERE email = ? AND used = 0 LIMIT 1",
                (email,),
            ).fetchone()
            if pending:
                return {
                    "message": f"Verify your email first. Check {email} for the link.",
                    "button": {
                        "label": "Resend verification email",
                        "action": "/signup/resend",
                    },
                    "stay_on": "/login",
                }
            return {
                "message": "No account exists for this email.",
                "link": {"label": "Create account", "href": "/signup"},
                "field": "email",
            }
        if not account[0]:
            return {
                "message": f"Verify your email first. Check {email} for the link.",
                "button": {"label": "Resend verification email", "action": "/signup/resend"},
                "stay_on": "/login",
            }
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc).isoformat()
        with self._db:
            self._db.execute(
                "INSERT INTO login_tokens (token, email, created_at) VALUES (?, ?, ?)",
                (token, email, now),
            )
        self._send_email(
            email,
            "Log in to your account",
            f"Log in: {self._base_url}/login/{token}",
        )
        return {"message": f"Check {email} for a log in link."}

    def resend_verification(self, email):
        pending = self._db.execute(
            "SELECT 1 FROM pending_verifications WHERE email = ? AND used = 0 LIMIT 1",
            (email,),
        ).fetchone()
        if pending:
            token = secrets.token_urlsafe(32)
            now = datetime.now(timezone.utc).isoformat()
            with self._db:
                self._db.execute(
                    "INSERT INTO pending_verifications (token, email, created_at) VALUES (?, ?, ?)",
                    (token, email, now),
                )
            self._send_email(
                email,
                "Verify your email",
                f"Confirm your account: {self._base_url}/verify/{token}",
            )
            return {"message": f"Check {email} for a verification link."}
        return {"message": "No pending verification found."}

    def use_login_link(self, token, *, now=None):
        row = self._db.execute(
            "SELECT email, created_at, used FROM login_tokens WHERE token = ?", (token,)
        ).fetchone()
        if row is None or row[2]:
            return {"message": "This link is invalid or was already used."}
        email, created_at, _ = row
        now = now or datetime.now(timezone.utc)
        if now - datetime.fromisoformat(created_at) > timedelta(minutes=15):
            return {"message": "This link has expired."}
        with self._db:
            self._db.execute("UPDATE login_tokens SET used = 1 WHERE token = ?", (token,))
        return {"message": "Logged in", "email": email}
