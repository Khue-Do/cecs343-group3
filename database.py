"""Shared SQLite schema for the ticket purchasing features."""


def initialize_database(connection):
    """Create the feature tables if they do not already exist."""
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL DEFAULT '',
            venue TEXT NOT NULL DEFAULT '',
            price_cents INTEGER,
            ticket_count INTEGER NOT NULL DEFAULT 0 CHECK(ticket_count >= 0),
            status TEXT NOT NULL DEFAULT 'published'
                CHECK(status IN ('published', 'unpublished'))
        );

        CREATE TABLE IF NOT EXISTS accounts (
            email TEXT PRIMARY KEY,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pending_verifications (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS login_tokens (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_ref TEXT PRIMARY KEY,
            owner_email TEXT NOT NULL,
            event_id TEXT NOT NULL,
            total_cents INTEGER NOT NULL,
            transaction_ref TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN
                ('pending', 'confirmed', 'canceled', 'refunded', 'expired')),
            deadline TEXT,
            idempotency_key TEXT UNIQUE,
            FOREIGN KEY(event_id) REFERENCES events(event_id)
        );

        CREATE TABLE IF NOT EXISTS payment_attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            idempotency_key TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            owner_email TEXT NOT NULL,
            event_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_cents INTEGER NOT NULL,
            transaction_ref TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(idempotency_key, attempt_number),
            FOREIGN KEY(event_id) REFERENCES events(event_id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_ref TEXT NOT NULL,
            ticket_title TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            seat TEXT,
            FOREIGN KEY(order_ref) REFERENCES orders(order_ref)
        );

        CREATE TABLE IF NOT EXISTS tickets (
            code TEXT PRIMARY KEY,
            owner_email TEXT NOT NULL,
            event_title TEXT NOT NULL,
            venue TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            event_id TEXT,
            order_ref TEXT,
            seat TEXT,
            status TEXT NOT NULL DEFAULT 'valid'
        );

        CREATE TABLE IF NOT EXISTS event_seats (
            event_id TEXT NOT NULL,
            seat TEXT NOT NULL,
            order_ref TEXT,
            PRIMARY KEY(event_id, seat),
            FOREIGN KEY(event_id) REFERENCES events(event_id),
            FOREIGN KEY(order_ref) REFERENCES orders(order_ref)
        );
        """
    )
    ticket_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(tickets)")
    }
    for name, declaration in (
        ("event_id", "TEXT"),
        ("order_ref", "TEXT"),
        ("seat", "TEXT"),
        ("status", "TEXT NOT NULL DEFAULT 'valid'"),
    ):
        if name not in ticket_columns:
            connection.execute(f"ALTER TABLE tickets ADD COLUMN {name} {declaration}")
    verification_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(pending_verifications)")
    }
    if "used" not in verification_columns:
        connection.execute(
            "ALTER TABLE pending_verifications ADD COLUMN used INTEGER NOT NULL DEFAULT 0"
        )
    order_columns = {row[1] for row in connection.execute("PRAGMA table_info(orders)")}
    if "idempotency_key" not in order_columns:
        connection.execute("ALTER TABLE orders ADD COLUMN idempotency_key TEXT")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency_key "
        "ON orders(idempotency_key) WHERE idempotency_key IS NOT NULL"
    )
    connection.commit()
    connection.commit()
