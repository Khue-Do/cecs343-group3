import sqlite3
from datetime import datetime, timedelta, timezone

from ticket_purchaser_account import AccountSignup

BASE_URL = "https://tickets.example.com"
EMAIL = "sam.park@example.com"


def make_signup():
    db = sqlite3.connect(":memory:")
    sent = []
    signup = AccountSignup(
        db,
        send_email=lambda to, subject, body: sent.append((to, subject, body)),
        base_url=BASE_URL,
    )
    return signup, db, sent


def set_sent_time(db, token, sent_at):
    with db:
        db.execute(
            "UPDATE pending_verifications SET created_at = ? WHERE token = ?",
            (sent_at.isoformat(), token),
        )


def pending_token(db, email=EMAIL):
    return db.execute(
        "SELECT token FROM pending_verifications WHERE email = ?", (email,)
    ).fetchone()[0]


def account_count(db, email=EMAIL):
    return db.execute(
        "SELECT COUNT(*) FROM accounts WHERE email = ?", (email,)
    ).fetchone()[0]

# AC: new email on /signup
def test_signup_with_new_email_shows_check_email_message():
    signup, db, sent = make_signup()

    result = signup.sign_up(EMAIL)

    assert result == {"message": f"Check {EMAIL} for a verification link."}
    assert account_count(db) == 0              # account is created only after verification
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == EMAIL
    assert f"{BASE_URL}/verify/{pending_token(db)}" in body

# AC: empty email on /signup
def test_signup_with_empty_email_shows_error_under_email_field():
    signup, db, sent = make_signup()

    result = signup.sign_up("")

    assert result["message"] == "Enter an email address."
    assert result["field"] == "email"          # message renders under the Email field
    assert "stay_on" not in result and "redirect" not in result
    assert sent == []                          # nothing sent
    assert db.execute("SELECT COUNT(*) FROM pending_verifications").fetchone()[0] == 0


# AC: malformed email on /signup
def test_signup_with_malformed_email_shows_format_error_under_email_field():
    signup, db, sent = make_signup()

    for bad in ["sam.park", "sam.park@example", "sam park@example.com", "@example.com"]:
        result = signup.sign_up(bad)

        assert result["message"] == "Enter an email address in the form name@domain."
        assert result["field"] == "email"
        assert "redirect" not in result

    assert sent == []
    assert db.execute("SELECT COUNT(*) FROM pending_verifications").fetchone()[0] == 0


# AC: existing account on /signup
def test_signup_with_existing_account_shows_log_in_link_next_to_message():
    signup, db, sent = make_signup()
    with db:
        db.execute(
            "INSERT INTO accounts (email, verified, created_at) VALUES (?, 1, ?)",
            (EMAIL, datetime.now(timezone.utc).isoformat()),
        )

    result = signup.sign_up(EMAIL)

    assert result["message"] == "An account exists for this email. Log in instead."
    assert result["field"] == "email"
    assert result["link"] == {"label": "Log in", "href": "/login"}
    assert sent == []


# AC: no account on /login
def test_login_with_no_account_shows_create_account_link():
    signup, db, sent = make_signup()

    result = signup.login_link(EMAIL)

    assert result["message"] == "No account exists for this email."
    assert result["field"] == "email"
    assert result["link"] == {"label": "Create account", "href": "/signup"}
    assert sent == []


# AC: account not yet verified, on /login
def test_login_before_verification_link_clicked_offers_resend_and_stays_on_login():
    signup, db, sent = make_signup()
    signup.sign_up(EMAIL)
    sent.clear()

    result = signup.login_link(EMAIL)

    assert result["message"] == f"Verify your email first. Check {EMAIL} for the link."
    assert result["button"] == {
        "label": "Resend verification email",
        "action": "/signup/resend",
    }
    assert result["stay_on"] == "/login"
    assert sent == []                          # no log in link is sent


def test_login_with_unverified_account_row_offers_resend_and_stays_on_login():
    signup, db, sent = make_signup()
    with db:
        db.execute(
            "INSERT INTO accounts (email, verified, created_at) VALUES (?, 0, ?)",
            (EMAIL, datetime.now(timezone.utc).isoformat()),
        )

    result = signup.login_link(EMAIL)

    assert result["message"] == f"Verify your email first. Check {EMAIL} for the link."
    assert result["button"]["label"] == "Resend verification email"
    assert result["stay_on"] == "/login"
    assert sent == []


# AC: link sent at 10:00, clicked at 10:16
def test_verification_link_clicked_after_16_minutes_is_expired_and_creates_no_account():
    signup, db, sent = make_signup()
    signup.sign_up(EMAIL)
    token = pending_token(db)
    sent_at = datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc)
    set_sent_time(db, token, sent_at)

    result = signup.verify_email(token, now=sent_at + timedelta(minutes=16))

    assert result["message"] == "This link has expired."
    assert result["button"] == {"label": "Send a new link", "action": "/signup/resend"}
    assert result["email"] == EMAIL
    assert result["message"] != "Email verified"   # home page is not shown
    assert account_count(db) == 0


# AC: link already used at 09:00, clicked again at 09:10
def test_verification_link_clicked_again_is_already_used_and_offers_log_in():
    signup, db, sent = make_signup()
    signup.sign_up(EMAIL)
    token = pending_token(db)
    first_click = datetime(2026, 11, 22, 9, 0, tzinfo=timezone.utc)
    set_sent_time(db, token, first_click - timedelta(minutes=1))

    first = signup.verify_email(token, now=first_click)
    second = signup.verify_email(token, now=first_click + timedelta(minutes=10))

    assert first["message"] == "Email verified"   # reached the home page
    assert second["message"] == "This link was already used."
    assert second["link"] == {"label": "Log in", "href": "/login"}
    assert second["message"] != "Email verified"  # home page is not shown again
    assert account_count(db) == 1                 # no duplicate account
