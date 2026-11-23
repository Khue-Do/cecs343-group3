"""Flask routes for the ticketing features; app.py remains unchanged."""

from datetime import date
from decimal import Decimal, InvalidOperation
import os
import secrets
import sqlite3

from flask import Flask, redirect, render_template_string, request, session, url_for
from markupsafe import escape

from event_organizer_event import EventOrganizerEvent
from order import OrderService
from ticket import TicketPurchaseService
from ticket_purchaser_account import AccountSignup


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{{ title }}</title><style>
body{font:1rem/1.5 system-ui,sans-serif;color:#111;background:#fff;margin:2rem;max-width:54rem}
a{color:#0645ad}a:focus,button:focus,input:focus{outline:3px solid #b54708;outline-offset:2px}
.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:1rem;top:1rem;background:#fff;padding:.5rem;z-index:1}
label{display:block;margin-top:1rem}input,button{font:inherit;padding:.45rem}
.error{color:#8b0000;font-weight:700}.success{color:#075c24}
</style></head><body><header><nav aria-label="Main navigation">
<a href="/events">Events</a> <a href="/profile">Profile</a> <a href="/login">Log in</a>
</nav></header><a class="skip-link" href="#main">Skip to main content</a><main id="main"><h1>{{ title }}</h1>
{% if message %}<p role="status" aria-live="polite" class="{{ 'error' if error else 'success' }}">{{ message }}</p>{% endif %}
{{ body|safe }}</main></body></html>"""

_FORM = (
    '<form method="post">{fields}'
    '<button type="submit">{submit}</button></form>'
)


def create_app(
    database_path=":memory:",
    *,
    send_email=None,
    payment_processor=None,
    ticket_code_generator=None,
):
    app = Flask(__name__)
    app.secret_key = os.environ.get("TICKETING_SECRET_KEY", "local-development-key-change-before-deployment")
    db = sqlite3.connect(database_path, check_same_thread=False)
    db.row_factory = None
    if send_email is None:
        send_email = lambda to, subject, body: print(f"\n--- email to {to}: {subject} ---\n{body}\n")
    payment_processor = payment_processor or (lambda _method, _amount: False)
    events = EventOrganizerEvent(db)
    accounts = AccountSignup(db, send_email, "http://localhost:5000")
    tickets = TicketPurchaseService(db, payment_processor, ticket_code_generator)
    orders = OrderService(db, payment_processor, ticket_code_generator)

    app.extensions["ticketing_db"] = db
    app.extensions["events"] = events
    app.extensions["accounts"] = accounts
    app.extensions["tickets"] = tickets
    app.extensions["orders"] = orders

    def page(title, body="", message=None, error=False, status=200):
        return render_template_string(
            _PAGE, title=title, body=body, message=message, error=error
        ), status

    @app.get("/")
    def home():
        return redirect(url_for("event_list"))

    @app.get("/signup")
    def signup_page():
        body = _FORM.format(
            fields='<label for="email">Email</label><input id="email" name="email" type="text" inputmode="email" aria-required="true" autocomplete="email">',
            submit="Create account",
        )
        return page("Create account", body)

    @app.post("/signup")
    def signup_submit():
        result = accounts.sign_up(request.form.get("email"))
        if "field" in result:
            body = (
                '<form method="post"><label for="email">Email</label>'
                '<input id="email" name="email" type="text" inputmode="email" aria-required="true" autocomplete="email" '
                'aria-describedby="email-error">'
                f'<span id="email-error" class="error" role="alert">{escape(result["message"])}</span>'
                + (f'<a href="{result["link"]["href"]}">{result["link"]["label"]}</a>' if result.get("link") else "")
                + '<button type="submit">Create account</button></form>'
            )
            return page("Create account", body, error=True)
        body = _FORM.format(
            fields='<label for="email">Email</label><input id="email" name="email" type="text" inputmode="email" aria-required="true" autocomplete="email">',
            submit="Create account",
        )
        return page("Create account", body, result["message"])

    @app.get("/verify/<token>")
    def verify_email(token):
        result = accounts.verify_email(token)
        if result.get("email") and result["message"] == "Email verified":
            session["email"] = result["email"]
            return redirect(url_for("home"))
        body = '<form action="/login"><button type="submit">Log in</button></form>' if result.get("link") else ''
        if result.get("button"):
            body += (
                '<form method="post" action="/signup/resend">'
                f'<input type="hidden" name="email" value="{escape(result.get("email", ""))}">'
                '<button type="submit">Send a new link</button></form>'
            )
        return page("Verify email", body, result["message"], error=True)

    @app.route("/signup/resend", methods=["GET", "POST"])
    def resend_verification():
        if request.method == "GET":
            body = _FORM.format(
                fields='<label for="email">Email</label><input id="email" name="email" type="text" inputmode="email" aria-required="true" autocomplete="email">',
                submit="Resend verification email",
            )
            return page("Resend verification email", body)
        result = accounts.resend_verification((request.form.get("email") or "").strip())
        return page("Resend verification email", "", result["message"])

    @app.route("/login", methods=["GET", "POST"])
    def login_page():
        body = _FORM.format(
            fields='<label for="email">Email</label><input id="email" name="email" type="text" inputmode="email" aria-required="true" autocomplete="email">',
            submit="Send log in link",
        )
        if request.method == "GET":
            return page("Log in", body)
        result = accounts.login_link(request.form.get("email"))
        link = result.get("link")
        button = result.get("button")
        if link or button:
            inline = (
                '<form method="post"><label for="email">Email</label>'
                '<input id="email" name="email" type="text" inputmode="email" aria-required="true" autocomplete="email" '
                'aria-describedby="email-error">'
                f'<span id="email-error" class="error" role="alert">{escape(result["message"])}</span>'
                '<button type="submit">Send log in link</button></form>'
            )
            if link:
                inline += f'<a href="{link["href"]}">{link["label"]}</a>'
            if button:
                inline += (
                    '<form method="post" action="/signup/resend">'
                    f'<input type="hidden" name="email" value="{escape(request.form.get("email", ""))}">'
                    f'<button type="submit">{button["label"]}</button></form>'
                )
            return page("Log in", inline, error=True)
        return page("Log in", body, result["message"])

    @app.get("/login/<token>")
    def use_login_link(token):
        result = accounts.use_login_link(token)
        if result.get("email"):
            session["email"] = result["email"]
            return redirect(url_for("home"))
        return page("Log in", '<a href="/login">Send a new log in link</a>', result["message"], True)

    @app.route("/events", methods=["GET"])
    def event_list():
        date_filter = request.args.get("date", "").strip() or None
        try:
            listed = events.list_events(date=date_filter)
        except (sqlite3.Error, TimeoutError):
            return page("Events", "", "Events could not be loaded", True, 503)
        if not listed:
            body = "<p>No events found</p>" if date_filter else "<p>No published events</p>"
        else:
            rows = []
            for event in listed:
                checkout_ref = f"ORD-{secrets.token_hex(4).upper()}"
                if event["ticket_price"] is None:
                    rows.append(
                        f'<li>{escape(event["name"])} ({escape(event["date"])}): missing a ticket price</li>'
                    )
                else:
                    rows.append(
                        f'<li>{escape(event["name"])} — {escape(event["date"])} — '
                        f'${event["ticket_price"]:.2f}'
                        f'<form method="post" action="/purchase">'
                        f'<input type="hidden" name="event_id" value="{escape(event["event_id"])}">'
                        f'<input type="hidden" name="order_ref" value="{checkout_ref}">'
                        f'<label for="quantity-{escape(event["event_id"])}">Ticket quantity</label>'
                        f'<input id="quantity-{escape(event["event_id"])}" name="quantity" type="number" min="1" max="4" value="1">'
                        f'<label for="last-four-{escape(event["event_id"])}">Payment method ending</label>'
                        f'<input id="last-four-{escape(event["event_id"])}" name="last_four" inputmode="numeric" maxlength="4">'
                        '<button type="submit">Buy tickets</button></form></li>'
                    )
            body = "<ul>" + "".join(rows) + "</ul>"
        body += '<form method="get"><label for="date">Search events by date</label><input id="date" name="date" type="date"><button>Search</button></form>'
        return page("Events", body)

    @app.post("/events/publish")
    def publish_event():
        result = events.publish_event(
            request.form.get("name"),
            request.form.get("date"),
            request.form.get("ticket_price"),
            venue=request.form.get("venue", ""),
            time=request.form.get("time", ""),
            ticket_count=request.form.get("ticket_count") or 0,
        )
        if result["message"] == "Event stored":
            return redirect(url_for("event_list"))
        return page("Publish event", "<a href='/events'>Event list</a>", result["message"], True)

    @app.get("/events/publish")
    def publish_event_form():
        body = _FORM.format(
            fields=(
                '<label for="name">Event name</label><input id="name" name="name" aria-required="true">'
                '<label for="date">Event date</label><input id="date" name="date" type="date" aria-required="true">'
                '<label for="ticket_price">Ticket price</label><input id="ticket_price" name="ticket_price" inputmode="decimal" aria-required="true">'
                '<label for="venue">Venue</label><input id="venue" name="venue">'
                '<label for="time">Time</label><input id="time" name="time">'
                '<label for="ticket_count">Ticket count</label><input id="ticket_count" name="ticket_count" type="number" min="0">'
            ),
            submit="Publish event",
        )
        return page("Publish event", body)

    @app.post("/purchase")
    def purchase_ticket():
        event_id = request.form.get("event_id", "")
        event = events.get_event(event_id)
        if event is None:
            return page("Purchase tickets", "", "Ticket details unavailable", True, 404)
        quantity = request.form.get("quantity", "1")
        try:
            balance = Decimal(request.form.get("balance", "0"))
        except InvalidOperation:
            balance = Decimal("0")
        method = {"last_four": request.form.get("last_four", ""), "balance": balance}
        seat_values = request.form.getlist("seat") or None
        result = orders.purchase(
            session.get("email", ""), event_id, quantity, method,
            order_ref=request.form.get("order_ref") or None, seats=seat_values
        )
        if result.get("tickets"):
            body = "<ul>" + "".join(
                f'<li><a href="/tickets/{escape(ticket["code"])}">{escape(ticket["code"])}</a> — '
                f'{escape(ticket["venue"])}, {escape(ticket["date"])}, {escape(ticket["time"])}</li>'
                for ticket in result["tickets"]
            ) + "</ul>"
        else:
            body = ""
        if result.get("detail"):
            body += f'<p>{result["detail"]}</p>'
        return page("Purchase tickets", body, result["message"], result["message"] != "Order confirmed")

    @app.get("/tickets/<code>")
    def ticket_page(code):
        ticket = tickets.get_ticket(session.get("email", ""), code)
        if ticket is None:
            return page("Ticket", "", "Ticket not found", True, 404)
        body = (
            f'<dl><dt>Ticket code</dt><dd>{escape(ticket["code"])}</dd>'
            f'<dt>Event</dt><dd>{escape(ticket["title"])}</dd>'
            f'<dt>Venue</dt><dd>{escape(ticket["venue"])}</dd>'
            f'<dt>Date</dt><dd>{escape(ticket["date"])}</dd>'
            f'<dt>Time</dt><dd>{escape(ticket["time"])}</dd></dl>'
        )
        return page("Your ticket", body)

    @app.get("/profile")
    def profile():
        email = session.get("email")
        if not email:
            return redirect(url_for("login_page"))
        as_of = request.args.get("as_of") or request.args.get("date") or date.today().isoformat()
        owned = orders.tickets_for(email, as_of=as_of)
        event_filter = request.args.get("date")
        try:
            listed = events.list_events(date=event_filter or None)
        except (sqlite3.Error, TimeoutError):
            return page("Profile", "", "Events could not be loaded", True, 503)
        def ticket_items(items):
            return "<ul>" + "".join(
                f'<li><a href="/tickets/{escape(t["code"])}">{escape(t["code"])}</a> — {escape(t["title"])}</li>'
                for t in items
            ) + "</ul>" if items else "<p>No tickets</p>"
        body = "<h2>Current tickets</h2>" + ticket_items(owned["current"])
        body += "<h2>Past tickets</h2>" + ticket_items(owned["past"])
        body += "<h2>Event list</h2>"
        body += "<ul>" + "".join(
            f'<li>{escape(event["name"])} — {escape(event["date"])} — '
            + ("missing a ticket price" if event["ticket_price"] is None else f'${event["ticket_price"]:.2f}')
            + "</li>"
            for event in listed
        ) + "</ul>" if listed else "<p>No events found</p>"
        body += '<form method="get"><label for="date">Search events by date</label><input id="date" name="date" type="date"><button>Search</button></form>'
        return page("Your profile", body)

    @app.get("/orders/new")
    def new_order_form():
        body = _FORM.format(
            fields=(
                '<label for="order_ref">Order reference</label><input id="order_ref" name="order_ref">'
                '<label for="event_id">Event ID</label><input id="event_id" name="event_id">'
                '<label for="ticket_title">Ticket selection</label><input id="ticket_title" name="ticket_title">'
                '<label for="quantity">Quantity</label><input id="quantity" name="quantity" type="number" min="1" value="1">'
                '<label for="total">Total</label><input id="total" name="total" inputmode="decimal">'
                '<label for="transaction_ref">Transaction reference</label><input id="transaction_ref" name="transaction_ref">'
                '<label for="status">Payment status</label><select id="status" name="status">'
                '<option value="pending">Pending</option><option value="declined">Declined</option>'
                '<option value="confirmed">Confirmed</option><option value="refunded">Refunded</option>'
                '<option value="expired">Expired</option></select>'
                '<label for="deadline">Payment deadline</label><input id="deadline" name="deadline">'
            ),
            submit="Save order",
        )
        return page("Save order", body)

    @app.route("/orders", methods=["POST"])
    def save_order():
        selections = [{"title": request.form.get("ticket_title", "Ticket"),
                       "quantity": request.form.get("quantity", 1)}]
        status = request.form["status"]
        if status == "declined":
            status = "canceled"
        order = orders.record_order(
            request.form["order_ref"], session.get("email", ""),
            request.form["event_id"], request.form["total"],
            request.form["transaction_ref"], status, selections,
            deadline=request.form.get("deadline") or None,
        )
        return redirect(url_for("order_page", order_ref=order["order_ref"]))

    @app.get("/orders/<order_ref>")
    def order_page(order_ref):
        orders.expire_past_deadlines()
        order = orders.get_order(order_ref)
        if order is None or order["owner_email"] != session.get("email"):
            return page("Order", "", f"Order {order_ref} not found", True, 404)
        status = order["status"].capitalize()
        selections = "<ul>" + "".join(
            f'<li>{escape(item["title"])} × {item["quantity"]}'
            + (f' — Seat {escape(item["seat"])}' if item["seat"] else "")
            + "</li>" for item in order["ticket_selections"]
        ) + "</ul>"
        body = (
            f'<p>Order {escape(order_ref)} {escape(status)}</p>{selections}'
            f'<p>Total ${order["total"]:.2f}</p>'
            f'<p>Transaction reference {escape(order["transaction_ref"])}</p>'
        )
        if order["status"] not in {"canceled", "refunded", "expired"}:
            body += f'<form method="post" action="/orders/{order_ref}/cancel"><button>Cancel order</button></form>'
        return page("Saved order", body)

    @app.post("/orders/<order_ref>/cancel")
    def cancel_order(order_ref):
        result = orders.cancel(session.get("email", ""), order_ref)
        return page("Cancel order", "<a href='/profile'>Profile</a>", result["message"], "not found" in result["message"])

    return app


if __name__ == "__main__":
    create_app("ticketing.sqlite3").run(host="0.0.0.0", debug=False)
