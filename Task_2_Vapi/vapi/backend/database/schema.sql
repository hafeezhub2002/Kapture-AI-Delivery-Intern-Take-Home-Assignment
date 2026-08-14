-- Logical schema for the collections voicebot prototype.
-- The implementation uses an in-memory datastore, but this mirrors the intended structure.

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    loan_type TEXT NOT NULL,
    overdue_amount REAL NOT NULL,
    days_past_due INTEGER NOT NULL,
    due_date TEXT,
    phone_number TEXT,
    is_dnc INTEGER NOT NULL DEFAULT 0,
    is_paid INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE call_sessions (
    call_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    state TEXT NOT NULL,
    authentication_status TEXT NOT NULL,
    intent TEXT NOT NULL,
    disposition TEXT,
    verification_attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_user_message TEXT,
    last_bot_message TEXT,
    ptp_amount REAL,
    ptp_date TEXT,
    callback_date TEXT,
    escalation_reason TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE call_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details_json TEXT NOT NULL,
    FOREIGN KEY (call_id) REFERENCES call_sessions(call_id)
);

CREATE TABLE ptp_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    ptp_date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE dispositions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    disposition TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    details_json TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
