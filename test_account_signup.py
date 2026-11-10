
"""Tests for the account creation and login acceptance criteria.

The only account implementation supplied is ``AccountSignup.sign_up``. Tests
that need routes or account/verification state are retained below as explicit
skips until that implementation is available.
"""

import sqlite3

import pytest


@pytest.fixture
def signup():
    """Create AccountSignup with an in-memory database and captured email."""
    module = pytest.importorskip(
        "app", reason="The app module containing AccountSignup was not provided"
    )
    account_signup = getattr(module, "AccountSignup", None)
    if account_signup is None:
        pytest.skip("app.py does not provide AccountSignup")

    connection = sqlite3.connect(":memory:")
    sent_emails = []

    def capture_email(email, subject, body):
        sent_emails.append((email, subject, body))

    service = account_signup(
        connection, capture_email, "https://example.test"
    )
    yield service, connection, sent_emails
    connection.close()


@pytest.fixture
def client():
    """Use the project's Flask test client when an app with routes is present."""
    module = pytest.importorskip(
        "app", reason="No app.py with signup/login routes was provided"
    )
    flask_app = getattr(module, "app", None)
    if flask_app is None or not hasattr(flask_app, "test_client"):
        pytest.skip("app.py does not expose a Flask test client")

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as test_client:
        yield test_client


def test_ac1_signup_returns_verification_message_and_sends_email(signup):
    service, connection, sent_emails = signup

    result = service.sign_up("sam.park@example.com")

    assert result["message"] == (
        "Check sam.park@example.com for a verification link."
    )
    assert sent_emails[0][0] == "sam.park@example.com"
    assert "https://example.test/verify/" in sent_emails[0][2]
    stored_email = connection.execute(
        "SELECT email FROM pending_verifications"
    ).fetchone()[0]
    assert stored_email == "sam.park@example.com"


def test_ac2_empty_email_shows_error_and_stays_on_signup(client):
    response = client.post("/signup", data={"email": ""})

    assert "Enter an email address." in response.get_data(as_text=True)
    assert response.request.path == "/signup"


def test_ac3_email_without_at_shows_format_error_and_stays_on_signup(client):
    # The issue's example includes an @. This input matches the criterion title.
    response = client.post("/signup", data={"email": "sam.park.example.com"})

    assert "Enter an email address in the form name@domain." in response.get_data(
        as_text=True
    )
    assert response.request.path == "/signup"


def test_ac4_existing_signup_email_shows_login_link():
    pytest.skip(
        "Needs a signup route and a supported way to seed an existing account"
    )


def test_ac5_login_for_unknown_email_shows_create_account_link(client):
    response = client.post("/login", data={"email": "sam.park@example.com"})
    body = response.get_data(as_text=True)

    assert "No account exists for this email." in body
    assert "Create account" in body


def test_ac6_unverified_login_offers_resending_verification():
    pytest.skip(
        "Needs login, pending-account state, and verification-resend behavior"
    )


def test_ac7_expired_verification_link_is_rejected():
    pytest.skip(
        "Needs a verification handler and a controllable clock; the supplied code "
        "has neither. The issue description says 15 minutes while AC7 says 30."
    )


def test_ac8_reused_verification_link_is_rejected():
    pytest.skip("Needs a verification handler that records consumed links")


def test_signup_accepts_and_preserves_leading_trailing_spaces(signup):
    service, connection, sent_emails = signup
    email = " sam.park@example.com "

    service.sign_up(email)

    stored_email = connection.execute(
        "SELECT email FROM pending_verifications"
    ).fetchone()[0]
    assert stored_email == email
    assert sent_emails[0][0] == email


def test_signup_accepts_and_preserves_plus_tag(signup):
    service, connection, sent_emails = signup
    email = "sam+concert@example.com"

    service.sign_up(email)

    stored_email = connection.execute(
        "SELECT email FROM pending_verifications"
    ).fetchone()[0]
    assert stored_email == email
    assert sent_emails[0][0] == email


def test_signup_accepts_and_preserves_uppercase_letters(signup):
    service, connection, sent_emails = signup
    email = "SAM.PARK@EXAMPLE.COM"

    service.sign_up(email)

    stored_email = connection.execute(
        "SELECT email FROM pending_verifications"
    ).fetchone()[0]
    assert stored_email == email
    assert sent_emails[0][0] == email


