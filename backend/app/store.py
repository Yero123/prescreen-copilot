"""Storage: one case per candidate, with its full history.

candidates   one row per person, unique by email (never duplicated)
submissions  each reply a candidate sends (a new reply is a new submission, same candidate)
evaluations  each harness run on a submission, stored whole as JSON
events       what the recruiter did: overrides, decisions, email edits and approvals

Plain sqlite3 from the standard library: no ORM, one file, no server.
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "app.db"
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    role_id TEXT NOT NULL,
    reply TEXT NOT NULL,
    cv TEXT NOT NULL,
    status TEXT NOT NULL,            -- processing | done | error
    received_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES submissions(id),
    result_json TEXT NOT NULL,
    bucket TEXT,
    provider TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES submissions(id),
    kind TEXT NOT NULL,              -- override | decision | email_edited | email_approved
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_submissions_candidate ON submissions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_submission ON evaluations(submission_id);
CREATE INDEX IF NOT EXISTS idx_events_submission ON events(submission_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_path() -> Path:
    return Path(os.getenv("DB_PATH", str(DEFAULT_DB)))


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.executescript(SCHEMA)
            yield conn
            conn.commit()
        finally:
            conn.close()


def upsert_candidate(conn, email: str, name: str) -> int:
    email = email.strip().lower()
    row = conn.execute("SELECT id FROM candidates WHERE email = ?", (email,)).fetchone()
    if row:
        conn.execute("UPDATE candidates SET name = ? WHERE id = ?", (name.strip(), row["id"]))
        return row["id"]
    cur = conn.execute("INSERT INTO candidates (email, name, created_at) VALUES (?, ?, ?)",
                       (email, name.strip(), now()))
    return cur.lastrowid


def create_submission(email: str, name: str, role_id: str, reply: str, cv: str,
                      status: str = "processing", received_at: str | None = None) -> int:
    with connect() as conn:
        candidate_id = upsert_candidate(conn, email, name)
        cur = conn.execute(
            "INSERT INTO submissions (candidate_id, role_id, reply, cv, status, received_at) VALUES (?, ?, ?, ?, ?, ?)",
            (candidate_id, role_id, reply, cv, status, received_at or now()))
        return cur.lastrowid


def save_evaluation(submission_id: int, result: dict, bucket: str | None, provider: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO evaluations (submission_id, result_json, bucket, provider, created_at) VALUES (?, ?, ?, ?, ?)",
            (submission_id, json.dumps(result, ensure_ascii=False), bucket, provider, now()))
        conn.execute("UPDATE submissions SET status = 'done' WHERE id = ?", (submission_id,))


def mark_error(submission_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE submissions SET status = 'error' WHERE id = ?", (submission_id,))


def add_event(submission_id: int, kind: str, payload: dict) -> None:
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM submissions WHERE id = ?", (submission_id,)).fetchone():
            raise KeyError(submission_id)
        conn.execute("INSERT INTO events (submission_id, kind, payload_json, created_at) VALUES (?, ?, ?, ?)",
                     (submission_id, kind, json.dumps(payload, ensure_ascii=False), now()))


def get_submission(submission_id: int) -> dict | None:
    with connect() as conn:
        s = conn.execute(
            "SELECT s.*, c.email, c.name, c.id AS cid FROM submissions s JOIN candidates c ON c.id = s.candidate_id "
            "WHERE s.id = ?", (submission_id,)).fetchone()
        if not s:
            return None
        ev = conn.execute("SELECT * FROM evaluations WHERE submission_id = ? ORDER BY id DESC LIMIT 1",
                          (submission_id,)).fetchone()
        events = conn.execute("SELECT kind, payload_json, created_at FROM events WHERE submission_id = ? ORDER BY id",
                              (submission_id,)).fetchall()
        history = conn.execute("SELECT id, received_at, status FROM submissions WHERE candidate_id = ? ORDER BY id",
                               (s["cid"],)).fetchall()
    return {
        "id": s["id"], "role_id": s["role_id"], "status": s["status"], "received_at": s["received_at"],
        "candidate": {"id": s["cid"], "name": s["name"], "email": s["email"]},
        "reply": s["reply"], "cv": s["cv"],
        "result": json.loads(ev["result_json"]) if ev else None,
        "events": [{"kind": e["kind"], "payload": json.loads(e["payload_json"]), "at": e["created_at"]} for e in events],
        "history": [dict(h) for h in history],
    }


def list_latest_submissions() -> list[dict]:
    """The latest submission of every candidate, newest first."""
    with connect() as conn:
        rows = conn.execute("""
            SELECT s.id FROM submissions s
            WHERE s.id = (SELECT MAX(id) FROM submissions WHERE candidate_id = s.candidate_id)
            ORDER BY s.received_at DESC, s.id DESC
        """).fetchall()
    return [get_submission(r["id"]) for r in rows]
