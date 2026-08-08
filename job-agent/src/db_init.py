import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "job_agent.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    jd_text TEXT,
    posted_at TEXT,
    first_seen_at TEXT NOT NULL,
    relevance_score REAL,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'scored', 'tailored', 'digested', 'rejected'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    name TEXT NOT NULL,
    title TEXT,
    profile_url TEXT,
    rank INTEGER,
    message_draft TEXT,
    send_status TEXT NOT NULL DEFAULT 'draft'
        CHECK (send_status IN ('draft', 'approved', 'sent'))
);

CREATE TABLE IF NOT EXISTS run_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    calls_made INTEGER NOT NULL DEFAULT 0,
    errors TEXT,
    backoff_state TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_contacts_job_id ON contacts(job_id);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"DB initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
