#!/bin/bash
# Recovery script after vast.ai machine reroll
# Redeploys disk guardian and resumes evaluation

set -e

NEW_HOST="$1"
NEW_PORT="${2:-2222}"

if [ -z "$NEW_HOST" ]; then
    echo "Usage: $0 <new_host_ip> [ssh_port]"
    echo "Example: $0 10.32.184.5 2222"
    exit 1
fi

echo "========================================================================"
echo "RECOVERY AFTER MACHINE REROLL"
echo "========================================================================"
echo "New host: $NEW_HOST:$NEW_PORT"
echo ""

# Update connection info
echo "→ Updating connection configuration..."
sed -i "s/OLLAMA_URL = \"http:\/\/[0-9.]*:11434/OLLAMA_URL = \"http:\/\/$NEW_HOST:11434/g" scripts/evaluate_responses_hermes.py
sed -i "s/OLLAMA_URL = \"http:\/\/[0-9.]*:11434/OLLAMA_URL = \"http:\/\/$NEW_HOST:11434/g" scripts/ensure_hermes_connection.py
echo "✓ Configuration updated"
echo ""

# Test connection
echo "→ Testing SSH connection..."
if ! ssh -p $NEW_PORT root@$NEW_HOST 'echo "✓ SSH working"'; then
    echo "✗ Cannot connect to $NEW_HOST:$NEW_PORT"
    echo "  Check if machine is ready and SSH key is configured"
    exit 1
fi
echo ""

# Accept host key
echo "→ Adding host key..."
ssh-keyscan -p $NEW_PORT $NEW_HOST >> ~/.ssh/known_hosts 2>/dev/null || true
echo "✓ Host key added"
echo ""

# Deploy disk guardian
echo "→ Deploying disk guardian..."
scp -P $NEW_PORT scripts/ollama_disk_guardian.py root@$NEW_HOST:/usr/local/bin/
ssh -p $NEW_PORT root@$NEW_HOST 'chmod +x /usr/local/bin/ollama_disk_guardian.py'

ssh -p $NEW_PORT root@$NEW_HOST 'python3 /usr/local/bin/ollama_disk_guardian.py --daemon --threshold 85 --check-interval 60' &
sleep 3

if ssh -p $NEW_PORT root@$NEW_HOST 'ps aux | grep ollama_disk_guardian | grep -v grep' > /dev/null; then
    echo "✓ Disk guardian deployed and running"
else
    echo "⚠ Disk guardian may not be running - check manually"
fi
echo ""

# Check Ollama
echo "→ Checking Ollama service..."
if curl -s http://$NEW_HOST:11434/api/tags | grep -q "hermes3"; then
    echo "✓ Ollama responding with Hermes model"
else
    echo "⚠ Ollama not responding or Hermes model not loaded"
    echo "  You may need to load the model manually"
fi
echo ""

# Check evaluation progress
echo "→ Checking evaluation progress..."
EVALUATED=$(find data/practice-responses -name "*.json" -exec grep -l "hermes_score" {} \; | wc -l)
TOTAL=$(find data/practice-responses -name "*.json" | wc -l)
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
fi

echo "========================================================================"
echo "RECOVERY COMPLETE"
echo "========================================================================"
echo ""
echo "Updated configuration for: $NEW_HOST:$NEW_PORT"
echo "Disk guardian: Running"
echo "Next step: Resume evaluation (if needed)"
echo ""
