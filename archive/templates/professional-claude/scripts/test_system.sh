#!/bin/bash
# Test professional-claude system

echo "=========================================="
echo "Professional Claude: System Test"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."

# Test 1: Database initialized
echo "Test 1: Database initialization"
if [ -f "context/sessions.db" ]; then
    echo "  ✓ Database exists"
    count=$(sqlite3 context/sessions.db "SELECT COUNT(*) FROM sessions;")
    echo "  ✓ Sessions table accessible ($count sessions)"
else
    echo "  ✗ Database missing - run ./scripts/init_session.sh"
    exit 1
fi

# Test 2: Can log session
echo ""
echo "Test 2: Session logging"
python3 scripts/log_session.py \
  --topic "System test" \
  --decisions "Test decision" \
  --next "Test next step" 2>&1 | grep "Session logged"
if [ $? -eq 0 ]; then
    echo "  ✓ Logging works"
else
    echo "  ✗ Logging failed"
    exit 1
fi

# Test 3: Can query sessions
echo ""
echo "Test 3: Session query"
python3 scripts/query_session.py --last 1 > /tmp/pc-test-output.txt
if grep -q "System test" /tmp/pc-test-output.txt; then
    echo "  ✓ Query works"
else
    echo "  ✗ Query failed"
    exit 1
fi

# Test 4: Karma-electric principles accessible
echo ""
echo "Test 4: Karma-electric principles access"
if [ -f "../storage/karma-electric.db" ]; then
    principle_count=$(sqlite3 ../storage/karma-electric.db "SELECT COUNT(*) FROM immutable_principles;" 2>/dev/null)
    if [ "$principle_count" -gt 0 ]; then
        echo "  ✓ Can access $principle_count karma-electric principles"
    else
        echo "  ⚠ Karma-electric DB exists but no principles"
    fi
else
    echo "  ⚠ Karma-electric DB not found (principles unavailable)"
    echo "    Claude will work but without ethical foundation"
fi

# Test 5: Required files exist
echo ""
echo "Test 5: Required files"
files=(
    "README.md"
    ".claude-init/principles.md"
    ".claude-init/session-template.md"
    "QUICK-START.md"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file missing"
        all_exist=false
    fi
done

# Cleanup test data
sqlite3 context/sessions.db "DELETE FROM sessions WHERE topic = 'System test';" 2>/dev/null

echo ""
echo "=========================================="
if $all_exist; then
    echo "✓ ALL TESTS PASSED"
    echo "=========================================="
    echo ""
    echo "Professional Claude system ready for use."
    echo ""
    echo "To use:"
    echo "  1. Point fresh Claude to ~/karma-electric/professional-claude/README.md"
    echo "  2. Claude self-initializes"
    echo "  3. Start working with critical thinking + context continuity"
    echo ""
else
    echo "✗ SOME TESTS FAILED"
    echo "=========================================="
    exit 1
fi
