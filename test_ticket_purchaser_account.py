import sqlite3
from datetime import datetime, timedelta, timezone

from ticket_purchaser_account import AccountSignup

def test_ac1_signup_with_new_email_sends_verification_link():
    db = sqlite3.connect(":memory:")
    sent = []
    signup = AccountSignup(
        db,
        send_email=lambda to, subject, body: sent.append((to, body)),
        base_url="https://tickets.example.com",
    )

    result = signup.sign_up("sam.park@example.com")

    assert result == {"message": "Check sam.park@example.com for a verification link."}
    assert len(sent) == 1
    to, body = sent[0]
    assert to == "sam.park@example.com"
    token = db.execute(
        "SELECT token FROM pending_verifications WHERE email = ?",
        ("sam.park@example.com",),
    ).fetchone()[0]
    assert f"https://tickets.example.com/verify/{token}" in body


def test_signup_validates_email_and_rejects_duplicate_account():
    db = sqlite3.connect(":memory:")
    sent = []
    signup = AccountSignup(db, lambda *message: sent.append(message), "https://tickets.example.com")

    assert signup.sign_up("")["message"] == "Enter an email address."
    assert signup.sign_up("not-an-email")["message"] == "Enter an email address in the form name@domain."
    signup.sign_up("sam.park@example.com")
    row = db.execute(
        "SELECT email, created_at FROM pending_verifications WHERE email = ?",
        ("sam.park@example.com",),
    ).fetchone()
    with db:
        db.execute(
            "INSERT INTO accounts (email, verified, created_at) VALUES (?, 1, ?)",
            (row[0], row[1]),
        )

    result = signup.sign_up("sam.park@example.com")

    assert result["message"] == "An account exists for this email. Log in instead."
    assert result["link"]["label"] == "Log in"


def test_verification_expires_after_15_minutes_and_cannot_be_reused():
    db = sqlite3.connect(":memory:")
    sent = []
    signup = AccountSignup(db, lambda *message: sent.append(message), "https://tickets.example.com")
    signup.sign_up("sam.park@example.com")
    token = db.execute("SELECT token FROM pending_verifications").fetchone()[0]
    created = datetime.fromisoformat(
        db.execute("SELECT created_at FROM pending_verifications WHERE token = ?", (token,)).fetchone()[0]
    )

    expired = signup.verify_email(token, now=created + timedelta(minutes=16))
    fresh = signup.verify_email(token, now=created + timedelta(minutes=14))
    reused = signup.verify_email(token, now=created + timedelta(minutes=15))

    assert expired["message"] == "This link has expired."
    assert fresh["message"] == "Email verified"
    assert reused["message"] == "This link was already used."


def test_login_link_handles_unknown_and_unverified_accounts():
    db = sqlite3.connect(":memory:")
    sent = []
    signup = AccountSignup(db, lambda *message: sent.append(message), "https://tickets.example.com")

    unknown = signup.login_link("nobody@example.com")
    signup.sign_up("sam.park@example.com")
    unverified = signup.login_link("sam.park@example.com")

    assert unknown["message"] == "No account exists for this email."
    assert unknown["link"]["label"] == "Create account"
    assert unverified["message"] == "Verify your email first. Check sam.park@example.com for the link."
    assert unverified["button"]["label"] == "Resend verification email"
