#!/bin/bash
# Deploy Hermes infrastructure to twilight:2222
# Run this once when new instance is ready

set -e

JUMPHOST="localhost"
REMOTE_HOST="localhost"
REMOTE_PORT="2222"
SSH_OPTS="-J ${JUMPHOST} -p ${REMOTE_PORT}"

echo "========================================================================"
echo "DEPLOYING HERMES INFRASTRUCTURE"
echo "========================================================================"
echo ""

# Test connection
echo "→ Testing connection via ${JUMPHOST} to ${REMOTE_HOST}:${REMOTE_PORT}..."
if ! ssh ${SSH_OPTS} ${REMOTE_HOST} 'echo "✓ Connection successful"'; then
    echo "✗ Cannot connect via jumphost to ${REMOTE_HOST}:${REMOTE_PORT}"
    echo "  Wait for Vojtech to finish spinning up instance"
    exit 1
fi
echo ""

# Check Ollama
echo "→ Checking Ollama service..."
if ssh ${SSH_OPTS} ${SSH_HOST} 'systemctl status ollama' > /dev/null 2>&1; then
    echo "✓ Ollama service found"
else
    echo "⚠ Ollama service not found or not running"
    echo "  Starting Ollama..."
    ssh ${SSH_OPTS} ${SSH_HOST} 'sudo systemctl start ollama'
    sleep 3
fi
echo ""

# Check Hermes model
echo "→ Checking for Hermes model..."
if ssh ${SSH_OPTS} ${SSH_HOST} 'ollama list | grep hermes3-largectx' > /dev/null 2>&1; then
    echo "✓ Hermes model available"
else
    echo "⚠ Hermes model not found"
    echo "  This may need to be pulled manually"
    echo "  Run: ssh ${SSH_OPTS} ${SSH_HOST} 'ollama pull hermes3-largectx'"
fi
echo ""

# Deploy disk guardian
echo "→ Deploying disk guardian..."
scp -o "ProxyJump=${JUMPHOST}" -P ${REMOTE_PORT} scripts/ollama_disk_guardian.py ${REMOTE_HOST}:/tmp/
scp -o "ProxyJump=${JUMPHOST}" -P ${REMOTE_PORT} scripts/ollama-disk-guardian.service ${REMOTE_HOST}:/tmp/

ssh ${SSH_OPTS} ${REMOTE_HOST} '
    sudo mv /tmp/ollama_disk_guardian.py /usr/local/bin/
    sudo chmod +x /usr/local/bin/ollama_disk_guardian.py
    sudo mv /tmp/ollama-disk-guardian.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable ollama-disk-guardian
    sudo systemctl start ollama-disk-guardian
'

echo "✓ Disk guardian deployed"
echo ""

# Verify disk guardian
echo "→ Verifying disk guardian..."
if ssh ${SSH_OPTS} ${SSH_HOST} 'sudo systemctl is-active ollama-disk-guardian' > /dev/null 2>&1; then
    echo "✓ Disk guardian running"
    ssh ${SSH_OPTS} ${SSH_HOST} 'sudo systemctl status ollama-disk-guardian | head -10'
else
    echo "✗ Disk guardian not running!"
    exit 1
fi
echo ""

echo "========================================================================"
echo "DEPLOYMENT COMPLETE"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "1. Test connection: python3 scripts/ensure_hermes_connection.py"
echo "2. Start evaluation: python3 scripts/evaluate_responses_hermes.py"
echo ""
