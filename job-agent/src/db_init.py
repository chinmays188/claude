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
    relevance_reason TEXT,
    job_url TEXT,
    contact_search_status TEXT NOT NULL DEFAULT 'not_attempted'
        CHECK (contact_search_status IN
            ('not_attempted', 'found', 'no_contacts_found', 'company_unverified')),
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'scored', 'tailored', 'digested', 'rejected', 'scoring_failed'))
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

CREATE TABLE IF NOT EXISTS stage_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL
        CHECK (stage IN ('discovery', 'scoring', 'tailoring', 'contacts', 'outreach_digest')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    started_at TEXT,
    finished_at TEXT,
    result_summary TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_contacts_job_id ON contacts(job_id);
CREATE INDEX IF NOT EXISTS idx_stage_runs_run_id ON stage_runs(run_id);
"""


def migrate_jobs_table(conn):
    """SQLite can't ALTER a CHECK constraint or add it retroactively, so bring
    an existing jobs table up to the current schema via rebuild-and-copy."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()]

    if "relevance_reason" not in cols:
        conn.executescript("""
            ALTER TABLE jobs RENAME TO jobs_old;

            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                jd_text TEXT,
                posted_at TEXT,
                first_seen_at TEXT NOT NULL,
                relevance_score REAL,
                relevance_reason TEXT,
                status TEXT NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'scored', 'tailored', 'digested', 'rejected', 'scoring_failed'))
            );

            INSERT INTO jobs (id, title, company, location, jd_text, posted_at,
                               first_seen_at, relevance_score, status)
            SELECT id, title, company, location, jd_text, posted_at,
                   first_seen_at, relevance_score, status
            FROM jobs_old;

            DROP TABLE jobs_old;
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        """)
        conn.commit()
        print("Migrated jobs table: added relevance_reason, added 'scoring_failed' status")
        cols = [row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()]

    if "job_url" not in cols:
        conn.executescript("""
            ALTER TABLE jobs RENAME TO jobs_old;

            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                jd_text TEXT,
                posted_at TEXT,
                first_seen_at TEXT NOT NULL,
                relevance_score REAL,
                relevance_reason TEXT,
                job_url TEXT,
                contact_search_status TEXT NOT NULL DEFAULT 'not_attempted'
                    CHECK (contact_search_status IN
                        ('not_attempted', 'found', 'no_contacts_found', 'company_unverified')),
                status TEXT NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'scored', 'tailored', 'digested', 'rejected', 'scoring_failed'))
            );

            INSERT INTO jobs (id, title, company, location, jd_text, posted_at,
                               first_seen_at, relevance_score, relevance_reason,
                               job_url, status)
            SELECT id, title, company, location, jd_text, posted_at,
                   first_seen_at, relevance_score, relevance_reason,
                   'https://www.linkedin.com/jobs/view/' || id || '/', status
            FROM jobs_old;

            DROP TABLE jobs_old;
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        """)
        conn.commit()
        print("Migrated jobs table: added job_url (backfilled), contact_search_status")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    migrate_jobs_table(conn)
    conn.close()
    print(f"DB initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
