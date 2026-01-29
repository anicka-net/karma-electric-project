#!/bin/bash
# Initialize professional-claude session database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_DIR="$SCRIPT_DIR/../context"
DB_PATH="$CONTEXT_DIR/sessions.db"
SCHEMA_PATH="$CONTEXT_DIR/schema.sql"

echo "=========================================="
echo "Professional Claude: Session Initialization"
echo "=========================================="
echo ""

# Create context directory if needed
mkdir -p "$CONTEXT_DIR"

# Initialize database if doesn't exist
if [ ! -f "$DB_PATH" ]; then
    echo "Creating session database..."
    sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
    echo "✓ Database created: $DB_PATH"
else
    echo "✓ Database exists: $DB_PATH"
fi

# Verify
SESSION_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sessions WHERE id > 0;")
echo "  Sessions recorded: $SESSION_COUNT"

# Show last session if exists
if [ "$SESSION_COUNT" -gt 0 ]; then
    echo ""
    echo "Last session:"
    sqlite3 "$DB_PATH" "
        SELECT '  ' || session_date || ': ' || topic
        FROM sessions
        WHERE id > 0
        ORDER BY id DESC
        LIMIT 1;
    "
fi

echo ""
echo "=========================================="
echo "✓ Initialization complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Read .claude-init/principles.md (internalize framework)"
echo "  2. Start working with Anička"
echo "  3. End session: python3 scripts/log_session.py ..."
echo ""
echo "Query previous context:"
echo "  python3 scripts/query_session.py --last"
echo ""
