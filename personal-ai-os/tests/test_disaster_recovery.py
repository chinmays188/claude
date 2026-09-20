import sqlite3

import pytest

from app.platform.disaster_recovery import (
    BackupNotFoundError,
    backup_database,
    restore_database,
    verify_backup_integrity,
)


def _make_db_with_data(path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test_data (value) VALUES ('important data')")
    conn.commit()
    conn.close()


def test_backup_creates_a_valid_sqlite_file(tmp_path):
    db_path = tmp_path / "live.db"
    _make_db_with_data(db_path)

    backup_path = backup_database(db_path, tmp_path / "backups")

    assert backup_path.exists()
    assert verify_backup_integrity(backup_path)


def test_backup_preserves_actual_data(tmp_path):
    db_path = tmp_path / "live.db"
    _make_db_with_data(db_path)

    backup_path = backup_database(db_path, tmp_path / "backups")

    conn = sqlite3.connect(backup_path)
    row = conn.execute("SELECT value FROM test_data").fetchone()
    conn.close()

    assert row[0] == "important data"


def test_full_disaster_recovery_drill(tmp_path):
    """The real DR drill: backup, simulate data loss, restore, verify data
    is actually back — not just that a restore function exists."""
    db_path = tmp_path / "live.db"
    _make_db_with_data(db_path)
    backup_path = backup_database(db_path, tmp_path / "backups")

    # Simulate disaster: the live database is destroyed.
    db_path.unlink()
    assert not db_path.exists()

    restore_database(backup_path, db_path)

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT value FROM test_data").fetchone()
    conn.close()
    assert row[0] == "important data"


def test_restore_missing_backup_raises(tmp_path):
    with pytest.raises(BackupNotFoundError):
        restore_database(tmp_path / "does_not_exist.db", tmp_path / "target.db")


def test_verify_integrity_missing_backup_raises(tmp_path):
    with pytest.raises(BackupNotFoundError):
        verify_backup_integrity(tmp_path / "does_not_exist.db")


def test_multiple_backups_do_not_overwrite_each_other(tmp_path):
    db_path = tmp_path / "live.db"
    _make_db_with_data(db_path)

    backup1 = backup_database(db_path, tmp_path / "backups")
    backup2 = backup_database(db_path, tmp_path / "backups")

    assert backup1 != backup2
    assert backup1.exists()
    assert backup2.exists()
