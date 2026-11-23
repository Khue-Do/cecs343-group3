"""Route/API-level tests for Issues #7, #9, #10, #17, #19, and accessibility basics."""

import re

from web_app import create_app
from ticket import TicketPurchaseService


def make_app(tmp_path):
    sent = []
    codes = iter(["JZ-1042", "JZ-1043", "JZ-1044"])
    app = create_app(
        str(tmp_path / "tickets.sqlite"),
        send_email=lambda *message: sent.append(message),
        payment_processor=lambda _method, _amount: True,
        ticket_code_generator=lambda: next(codes),
    )
    app.config.update(TESTING=True)
    return app, sent


def test_signup_route_shows_field_error_associated_with_email(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/signup", data={"email": ""})

    assert b"Enter an email address." in response.data
    assert b'aria-describedby="email-error"' in response.data
    assert b'role="alert"' in response.data


def test_signup_verification_expires_and_cannot_show_home_on_reuse(tmp_path):
    from datetime import datetime, timedelta, timezone

    app, sent = make_app(tmp_path)
    client = app.test_client()
    client.post("/signup", data={"email": "sam.park@example.com"})
    token = app.extensions["ticketing_db"].execute(
        "SELECT token FROM pending_verifications WHERE email = ?",
        ("sam.park@example.com",),
    ).fetchone()[0]
    created = datetime.now(timezone.utc)
    app.extensions["ticketing_db"].execute(
        "UPDATE pending_verifications SET created_at = ? WHERE token = ?",
        ((created - timedelta(minutes=16)).isoformat(), token),
    )
    app.extensions["ticketing_db"].commit()

    expired = client.get(f"/verify/{token}")

    assert b"This link has expired." in expired.data
    assert b"Send a new link" in expired.data
    assert len(sent) == 1


def test_verification_creates_account_then_reuse_shows_already_used(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()
    client.post("/signup", data={"email": "sam.park@example.com"})
    token = app.extensions["ticketing_db"].execute(
        "SELECT token FROM pending_verifications WHERE email = ?",
        ("sam.park@example.com",),
    ).fetchone()[0]

    verified = client.get(f"/verify/{token}")
    reused = client.get(f"/verify/{token}")

    assert verified.status_code == 302
    assert app.extensions["ticketing_db"].execute(
        "SELECT verified FROM accounts WHERE email = ?",
        ("sam.park@example.com",),
    ).fetchone() == (1,)
    assert b"This link was already used." in reused.data
    assert b"Log in" in reused.data
    assert b"<h1>Events</h1>" not in reused.data


def test_published_event_is_visible_and_date_search_returns_no_events(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()
    result = app.extensions["events"].publish_event(
        "Harbor Lights", "2026-11-14", "40", venue="Harbor", time="7:00 PM",
        ticket_count=2, event_id="EVT-104",
    )
    assert result["message"] == "Event stored"

    found = client.get("/events?date=2026-11-14")
    missing = client.get("/events?date=2026-11-15")

    assert b"Harbor Lights" in found.data
    assert b"$40.00" in found.data
    assert b"2026-11-14" in found.data
    assert b"No events found" in missing.data


def test_profile_shows_no_tickets(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()

    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"No tickets" in response.data


def test_profile_hides_unpublished_events(tmp_path):
    app, _sent = make_app(tmp_path)

    app.extensions["events"].publish_event(
        "Harbor Lights",
        "2026-11-14",
        "40",
        event_id="EVT-104",
        status="unpublished",
    )

    app.extensions["events"].publish_event(
	"Cedar Room",
	"2026-11-15",
	"25",
	event_id="EVT-105",
    )

    client = app.test_client()

    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    response = client.get("/profile")

    assert response.status_code == 200

    html = response.data.decode("utf-8")
    event_list = html.split("<h2>Event list</h2>", 1)[1].split("<form", 1)[0]

    assert "Harbor Lights" not in event_list
    assert "Cedar Room" in event_list

def test_issue_7_publisher_submission_displays_saved_event_in_list(tmp_path):
    app, _sent = make_app(tmp_path)
    response = app.test_client().post(
        "/events/publish",
        data={
            "name": "Jazz Night", "date": "2026-11-14", "ticket_price": "25.00",
            "venue": "The Blue Room", "time": "7:00 PM", "ticket_count": "1",
        },
        follow_redirects=True,
    )

    assert b"Jazz Night" in response.data
    assert b"2026-11-14" in response.data
    assert b"$25.00" in response.data


def test_unpublished_and_missing_price_events_render_without_a_price(tmp_path):
    app, _sent = make_app(tmp_path)
    db = app.extensions["ticketing_db"]
    app.extensions["events"].publish_event(
        "Harbor Lights", "2026-11-14", "40", event_id="EVT-104", status="unpublished"
    )
    with db:
        db.execute(
            "INSERT INTO events (event_id, title, event_date, price_cents, status) "
            "VALUES (?, ?, ?, NULL, 'published')",
            ("EVT-105", "Cedar Room", "2026-11-15"),
        )

    response = app.test_client().get("/events")

    assert b"Cedar Room" in response.data
    assert b"missing a ticket price" in response.data
    assert b"Harbor Lights" not in response.data


def test_profile_shows_missing_ticket_price(tmp_path):
    app, _sent = make_app(tmp_path)
    db = app.extensions["ticketing_db"]

    with db:
        db.execute(
            "INSERT INTO events (event_id, title, event_date, price_cents, status) "
            "VALUES (?, ?, ?, NULL, 'published')",
            ("EVT-104", "Harbor Lights", "2026-11-14"),
        )

    client = app.test_client()

    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    response = client.get("/profile")

    assert response.status_code == 200

    html = response.data.decode("utf-8")
    event_list = html.split("<h2>Event list</h2>", 1)[1].split("<form", 1)[0]

    assert "Harbor Lights — 2026-11-14 — missing a ticket price" in event_list
    assert "$" not in event_list


def test_event_service_timeout_is_shown_as_a_message(tmp_path):
    app, _sent = make_app(tmp_path)

    def timeout(**_kwargs):
        raise TimeoutError

    app.extensions["events"].list_events = timeout

    response = app.test_client().get("/events")

    assert response.status_code == 503
    assert b"Events could not be loaded" in response.data


def test_profile_event_service_timeout(tmp_path):
    app, _sent = make_app(tmp_path)

    def timeout(**_kwargs):
        raise TimeoutError

    app.extensions["events"].list_events = timeout

    client = app.test_client()

    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    response = client.get("/profile")

    assert response.status_code == 503
    assert b"Events could not be loaded" in response.data


def test_purchase_persists_ticket_and_prevents_other_account_from_viewing_it(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()
    app.extensions["events"].publish_event(
        "Jazz Night", "2026-11-14", "25", venue="The Blue Room", time="7:00 PM",
        ticket_count=1, event_id="EVT-104",
    )
    app.extensions["events"].set_seats("EVT-104", ["A1"])
    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    bought = client.post(
        "/purchase",
        data={"event_id": "EVT-104", "quantity": "1", "last_four": "4242", "balance": "25", "order_ref": "ORD-1001"},
    )
    assert b"JZ-1042" in bought.data

    refreshed = client.get("/tickets/JZ-1042")
    with client.session_transaction() as state:
        state["email"] = "lee@example.com"
    other_owner = client.get("/tickets/JZ-1042")

    assert b"The Blue Room" in refreshed.data
    assert b"7:00 PM" in refreshed.data
    assert b"Ticket not found" in other_owner.data
    assert b"JZ-1042" not in other_owner.data


def test_seat_inventory_and_cancellation_are_enforced_at_the_purchase_route(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()
    app.extensions["events"].publish_event(
        "Jazz Night", "2026-11-14", "25", venue="The Blue Room", time="7:00 PM",
        ticket_count=1, event_id="EVT-104",
    )
    app.extensions["events"].set_seats("EVT-104", ["A1"])
    with client.session_transaction() as state:
        state["email"] = "ana@example.com"
    first = client.post(
        "/purchase", data={"event_id": "EVT-104", "quantity": "1", "seat": "A1", "order_ref": "ORD-1001"}
    )
    canceled = client.post("/orders/ORD-1001/cancel")
    with client.session_transaction() as state:
        state["email"] = "ben@example.com"
    second = client.post(
        "/purchase", data={"event_id": "EVT-104", "quantity": "1", "seat": "A1", "order_ref": "ORD-1002"}
    )

    assert b"Order confirmed" in first.data
    assert b"Order ORD-1001 canceled" in canceled.data
    assert b"Order confirmed" in second.data


def test_second_customer_cannot_buy_an_occupied_seat_through_the_route(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()
    app.extensions["events"].publish_event(
        "Jazz Night", "2026-11-14", "25", venue="The Blue Room", time="7:00 PM",
        ticket_count=2, event_id="EVT-104",
    )
    app.extensions["events"].set_seats("EVT-104", ["A1"])
    with client.session_transaction() as state:
        state["email"] = "ana@example.com"
    client.post("/purchase", data={"event_id": "EVT-104", "quantity": "1", "seat": "A1", "order_ref": "ORD-1001"})
    with client.session_transaction() as state:
        state["email"] = "ben@example.com"

    response = client.post(
        "/purchase", data={"event_id": "EVT-104", "quantity": "1", "seat": "A1", "order_ref": "ORD-1002"}
    )

    assert b"Seat A1 is not available" in response.data


def test_failed_payment_retry_creates_only_one_order_through_the_route(tmp_path):
    outcomes = iter([False, True])
    charges = []
    app = create_app(
        str(tmp_path / "retry.sqlite"),
        payment_processor=lambda _method, amount: (charges.append(amount), next(outcomes))[1],
        ticket_code_generator=lambda: "JZ-1042",
    )
    app.config.update(TESTING=True)
    client = app.test_client()
    app.extensions["events"].publish_event(
        "Jazz Night", "2026-11-14", "25", venue="The Blue Room", time="7:00 PM",
        ticket_count=1, event_id="EVT-104",
    )
    app.extensions["events"].set_seats("EVT-104", ["A1"])
    with client.session_transaction() as state:
        state["email"] = "maya@example.com"
    checkout = {
        "event_id": "EVT-104", "quantity": "1", "seat": "A1", "order_ref": "ORD-1001"
    }

    failed = client.post("/purchase", data=checkout)
    succeeded = client.post("/purchase", data=checkout)
    duplicate = client.post("/purchase", data=checkout)
    db = app.extensions["ticketing_db"]

    assert b"Payment declined" in failed.data
    assert b"Order confirmed" in succeeded.data
    assert b"Order confirmed" in duplicate.data
    assert len(charges) == 2
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'valid'").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM payment_attempts").fetchone()[0] == 2


def test_profile_separates_current_and_past_tickets_and_searches_events(tmp_path):
    app, _sent = make_app(tmp_path)
    db = app.extensions["ticketing_db"]
    app.extensions["events"].publish_event(
        "Harbor Lights", "2026-11-14", "40", venue="Harbor", time="7:00 PM",
        ticket_count=1, event_id="EVT-104",
    )
    app.extensions["events"].publish_event(
        "Cedar Room", "2026-05-02", "25", venue="Cedar", time="8:00 PM",
        ticket_count=1, event_id="EVT-052",
    )
    issuer = TicketPurchaseService(
        db, lambda _method, _amount: True,
        code_generator=iter(["T-104", "T-052"]).__next__,
    )
    issuer.purchase("maya@example.com", {
        "title": "Harbor Lights", "venue": "Harbor", "date": "2026-11-14",
        "time": "7:00 PM", "price": "40",
    }, 1, {})
    issuer.purchase("maya@example.com", {
        "title": "Cedar Room", "venue": "Cedar", "date": "2026-05-02",
        "time": "8:00 PM", "price": "25",
    }, 1, {})
    client = app.test_client()
    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    response = client.get("/profile?date=2026-11-14")

    assert b"T-104" in response.data
    assert b"T-052" in response.data
    assert b"Harbor Lights" in response.data
    assert b"$40.00" in response.data
    
    html = response.data.decode("utf-8")

    current_start = html.index("<h2>Current tickets</h2>")
    past_start = html.index("<h2>Past tickets</h2>")
    event_start = html.index("<h2>Event list</h2>")

    assert current_start < html.index("T-104") < past_start
    assert past_start < html.index("T-052") < event_start
    
    event_list = html[event_start:]

    assert "Harbor Lights — 2026-11-14 — $40.00" in event_list


def test_profile_search_no_matching_date(tmp_path):
    
    app, _sent = make_app(tmp_path)

    app.extensions["events"].publish_event(
        "Harbor Lights",
        "2026-11-14",
        "40",
        venue="Harbor",
        time="7:00 PM",
        ticket_count=2,
        event_id="EVT-104",
    )

    client = app.test_client()

    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    response = client.get("/profile?date=2026-11-15")

    assert response.status_code == 200
    assert b"No events found" in response.data


def test_order_screen_shows_saved_payment_details(tmp_path):
    app, _sent = make_app(tmp_path)
    client = app.test_client()
    app.extensions["events"].publish_event(
        "EVT-104", "2026-11-14", "50", venue="Room", time="7:00 PM",
        ticket_count=1, event_id="EVT-104",
    )
    app.extensions["orders"].record_order(
        "ORD-301", "maya@example.com", "EVT-104", "50.00", "TX-8824", "refunded",
        [{"title": "General Admission", "quantity": 1}],
    )
    with client.session_transaction() as state:
        state["email"] = "maya@example.com"

    response = client.get("/orders/ORD-301")

    assert b"General Admission" in response.data
    assert b"$50.00" in response.data
    assert b"TX-8824" in response.data
    assert b"Refunded" in response.data


def test_event_pages_have_semantic_landmarks_labels_and_keyboard_focus_style(tmp_path):
    app, _sent = make_app(tmp_path)
    response = app.test_client().get("/events/publish")

    assert b"<main id=\"main\">" in response.data
    assert b"<nav aria-label=\"Main navigation\">" in response.data
    assert b"Skip to main content" in response.data
    assert b'<label for="name">Event name</label>' in response.data
    assert b"outline:3px solid" in response.data
    html = response.get_data(as_text=True)
    input_ids = set(re.findall(r'<input id="([^"]+)"', html))
    label_targets = set(re.findall(r'<label for="([^"]+)"', html))
    assert input_ids <= label_targets
    assert b"<button type=\"submit\">Publish event</button>" in response.data


def test_accessible_text_and_focus_colors_meet_contrast_thresholds(tmp_path):
    app, _sent = make_app(tmp_path)
    html = app.test_client().get("/events/publish").get_data(as_text=True)

    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def contrast(foreground, background="#ffffff"):
        light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
        return (light + 0.05) / (dark + 0.05)

    # WCAG AA normal text requires 4.5:1; the focus outline exceeds 3:1.
    assert all(contrast(color) >= 4.5 for color in ("#111111", "#0645ad", "#8b0000", "#075c24"))
    assert contrast("#b54708") >= 3.0
    assert "a:focus,button:focus,input:focus{outline:3px solid #b54708" in html
