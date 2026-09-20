import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class BackupNotFoundError(Exception):
    pass


def backup_database(db_path: Path, backup_dir: Path) -> Path:
    """Milestone 57: a real, verifiable SQLite backup using sqlite3's own
    backup API (consistent even if the source db is being written to
    concurrently — safer than a plain file copy of a live SQLite file).
    Named with a timestamp so multiple backups don't overwrite each other."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Microsecond precision so two backups taken in quick succession (e.g. in
    # a test, or a fast-firing scheduled job) never collide on the same filename.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"backup_{timestamp}.db"

    source_conn = sqlite3.connect(db_path)
    dest_conn = sqlite3.connect(backup_path)
    try:
        source_conn.backup(dest_conn)
    finally:
        source_conn.close()
        dest_conn.close()

    return backup_path


def restore_database(backup_path: Path, target_db_path: Path) -> None:
    """Milestone 57: restore is the other half of a real DR drill — a backup
    nobody has ever restored from is unverified. Copies the backup file over
    the target path; the target's parent directory is created if needed."""
    if not backup_path.exists():
        raise BackupNotFoundError(f"Backup file not found: {backup_path}")

    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_db_path)


def verify_backup_integrity(backup_path: Path) -> bool:
    """Runs SQLite's own integrity check against a backup file — catches a
    truncated/corrupted backup before it's trusted for a real restore."""
    if not backup_path.exists():
        raise BackupNotFoundError(f"Backup file not found: {backup_path}")

    conn = sqlite3.connect(backup_path)
    try:
        result = conn.execute("PRAGMA integrity_check;").fetchone()
        return result[0] == "ok"
    finally:
        conn.close()
