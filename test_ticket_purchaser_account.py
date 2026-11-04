import sqlite3

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
