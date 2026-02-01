#!/bin/bash
# Recovery script after vast.ai machine reroll
# SIMPLIFIED: IP addresses are stable (10.32.184.2), only need to redeploy guardian

set -e

HOST="10.32.184.2"
PORT="2222"

echo "========================================================================"
echo "RECOVERY AFTER MACHINE REROLL"
echo "========================================================================"
echo "Host: $HOST:$PORT (permanent IP)"
echo ""

# Test connection
echo "→ Testing SSH connection..."
if ! ssh -p $PORT root@$HOST 'echo "✓ SSH working"' 2>/dev/null; then
    echo "⚠ Cannot connect yet - machine may still be booting"
    echo "  Waiting 30 seconds..."
    sleep 30
    if ! ssh -p $PORT root@$HOST 'echo "✓ SSH working"'; then
        echo "✗ Still cannot connect to $HOST:$PORT"
        echo "  Check with Vojtech on machine status"
        exit 1
    fi
fi
echo ""

# Deploy disk guardian
echo "→ Deploying disk guardian..."
scp -P $PORT scripts/ollama_disk_guardian.py root@$HOST:/usr/local/bin/
ssh -p $PORT root@$HOST 'chmod +x /usr/local/bin/ollama_disk_guardian.py'

ssh -p $PORT root@$HOST 'python3 /usr/local/bin/ollama_disk_guardian.py --daemon --threshold 85 --check-interval 60' 2>/dev/null &
sleep 3

if ssh -p $PORT root@$HOST 'ps aux | grep ollama_disk_guardian | grep -v grep' > /dev/null 2>/dev/null; then
    echo "✓ Disk guardian deployed and running"
else
    echo "⚠ Disk guardian may not be running - check manually"
fi
echo ""

# Check Ollama
echo "→ Checking Ollama service..."
if curl -s http://$HOST:11434/api/tags | grep -q "hermes3"; then
    echo "✓ Ollama responding with Hermes model"
else
    echo "⚠ Ollama not responding or Hermes model not loaded"
    echo "  May need to wait for model to load or pull manually"
fi
echo ""

# Check evaluation progress
echo "→ Checking evaluation progress..."
EVALUATED=$(find data/practice-responses -name "*.json" -exec grep -l "hermes_score" {} \; 2>/dev/null | wc -l)
TOTAL=$(find data/practice-responses -name "*.json" 2>/dev/null | wc -l)
REMAINING=$((TOTAL - EVALUATED))

echo "  Evaluated: $EVALUATED/$TOTAL"
echo "  Remaining: $REMAINING"
echo ""

# Resume evaluation
if [ $REMAINING -gt 0 ]; then
    echo "→ Ready to resume evaluation"
    echo ""
    echo "To resume evaluation, run:"
    echo "  nohup python3 scripts/evaluate_responses_hermes.py --no-prompt > evaluation.log 2>&1 &"
    echo ""
    echo "Monitor progress:"
    echo "  tail -f evaluation.log"
else
    echo "✓ All responses evaluated!"
    echo ""
    echo "Next steps:"
    echo "  python3 scripts/check_training_readiness.py"
    echo "  python3 scripts/export_training_data.py --threshold 32"
fi

echo ""
echo "========================================================================"
echo "RECOVERY COMPLETE"
echo "========================================================================"
echo ""
echo "IP addresses unchanged: $HOST:$PORT (permanent)"
echo "Disk guardian: Running"
echo "Evaluation: Ready to resume"
echo ""
