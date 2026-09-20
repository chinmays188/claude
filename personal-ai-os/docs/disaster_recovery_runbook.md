# Disaster Recovery Runbook (Phase 5, Milestone 57)

## Scope

This runbook covers the SQLite-backed data this project actually persists
(`data/personal_ai.db` — memory, tasks, goals, decision graph, commitments,
outcomes, job queue, releases). It does not cover a real multi-region/
multi-datacenter disaster scenario, since no such deployment exists.

## Backup procedure

```python
from pathlib import Path
from app.platform.disaster_recovery import backup_database, verify_backup_integrity

backup_path = backup_database(Path("data/personal_ai.db"), Path("data/backups"))
assert verify_backup_integrity(backup_path)
```

Run on a schedule (a real deployment: a cron job or Milestone 39's Scheduler
with an `INTERVAL` job calling this). Verifying integrity immediately after
backup catches a corrupted backup before it's relied on later.

## Restore procedure (a real drill, not just a written plan)

```python
from pathlib import Path
from app.platform.disaster_recovery import restore_database

restore_database(Path("data/backups/backup_20260101T000000Z.db"), Path("data/personal_ai.db"))
```

**This runbook's restore path is tested** (`tests/test_disaster_recovery.py`)
— backup, corrupt/delete the "live" file, restore, verify data is back. This
is the actual point of a DR drill: an untested restore procedure is not a
real recovery capability, it's an assumption.

## What was verified vs. what remains a gap

**Verified in this sandbox:**
- Backup produces a valid, integrity-checked SQLite file
- Restore correctly recovers from a backup after simulated data loss
  (file deleted/corrupted)
- Multiple backups can coexist without overwriting each other

**Honest gaps — not verified, and cannot be verified without real infrastructure:**
- **Off-site/off-host backup storage.** `backup_database()` writes to a local
  directory; a real DR plan requires backups stored somewhere that survives
  the loss of the host machine itself (S3, another region, etc.) — no such
  storage is integrated here.
- **Recovery time objective (RTO) / recovery point objective (RPO) under
  real failure conditions.** This runbook has not been tested against an
  actual infrastructure failure (disk failure, host loss) — only against a
  simulated local file loss.
- **A real incident.** No disaster has actually occurred and been recovered
  from; this is a rehearsed procedure, not a battle-tested one.

These gaps are named explicitly rather than left implicit, consistent with
this project's practice throughout every phase.
