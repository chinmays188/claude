#!/bin/bash
# Runs the job-agent pipeline once per calendar day (IST). Invoked by launchd
# both at the scheduled 7 PM IST time and on every wake/login, so a run
# started late (Mac was asleep at 7 PM) still happens the same day instead
# of being silently skipped.
set -euo pipefail

PROJECT_DIR="/Users/chinmay/claude.md/Project/job-agent"
PYTHON="$PROJECT_DIR/venv/bin/python3"
DB="$PROJECT_DIR/data/job_agent.db"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

export PATH="/Users/chinmay/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

TODAY_IST=$(TZ=Asia/Kolkata date +%Y%m%d)
LOG_FILE="$LOG_DIR/run_${TODAY_IST}.log"

ALREADY_RAN=$("$PYTHON" - <<PYEOF
import sqlite3
conn = sqlite3.connect("$DB")
row = conn.execute(
    "SELECT 1 FROM stage_runs WHERE run_id LIKE ? LIMIT 1", ("$TODAY_IST%",)
).fetchone()
print("yes" if row else "no")
PYEOF
)

if [ "$ALREADY_RAN" = "yes" ]; then
    echo "$(date): today's run ($TODAY_IST IST) already started — skipping." >> "$LOG_FILE"
    exit 0
fi

echo "$(date): starting daily run ($TODAY_IST IST)." >> "$LOG_FILE"
cd "$PROJECT_DIR/src"
"$PYTHON" orchestrator.py >> "$LOG_FILE" 2>&1
echo "$(date): run finished with exit code $?." >> "$LOG_FILE"
