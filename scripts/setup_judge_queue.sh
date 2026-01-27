#!/bin/bash
# Setup judge queue infrastructure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_ROOT/storage/karma-electric.db"
SCHEMA_PATH="$PROJECT_ROOT/storage/schema-queue.sql"
DAEMON_PATH="$SCRIPT_DIR/judge_queue_daemon.py"

echo "Setting up judge queue infrastructure..."
echo

# 1. Make daemon executable
echo "[1/3] Making daemon executable..."
chmod +x "$DAEMON_PATH"
echo "  ✓ $DAEMON_PATH"

# 2. Create queue table in database
echo "[2/3] Creating queue table in database..."
if [ ! -f "$DB_PATH" ]; then
    echo "  ✗ Database not found: $DB_PATH"
    echo "  Please run MCP setup first"
    exit 1
fi

sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
echo "  ✓ judge_queue table created"

# 3. Verify table exists
echo "[3/3] Verifying setup..."
TABLE_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='judge_queue';")
if [ "$TABLE_COUNT" -eq "1" ]; then
    echo "  ✓ judge_queue table verified"
else
    echo "  ✗ judge_queue table not found!"
    exit 1
fi

echo
echo "="
echo "Setup complete!"
echo
echo "Usage:"
echo "  Start daemon:  $DAEMON_PATH"
echo "  Foreground:    $DAEMON_PATH --foreground"
echo "  Check status:  cat /tmp/judge-queue-status.txt"
echo "  View logs:     tail -f /tmp/judge-queue.log"
echo "  Stop daemon:   kill -TERM \$(cat /tmp/judge-queue.pid)"
echo
echo "From instances, use MCP tools:"
echo "  submit_to_judge(scenario_id, scenario_data, response_text, instance_id)"
echo "  check_judge_status(instance_id='instance-4')"
echo
