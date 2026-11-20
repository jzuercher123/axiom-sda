-- SQLite (WAL mode) schema for event index & system state
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS system_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    timestamp_utc TEXT NOT NULL,
    summary TEXT,
    fits_path TEXT,
    signature_sha256 TEXT,
    attestation_valid INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);