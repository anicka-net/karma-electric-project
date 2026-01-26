#!/bin/bash
# Test connection auto-recovery

echo "=========================================="
echo "Connection Recovery Test"
echo "=========================================="

echo ""
echo "Step 1: Kill existing tunnel..."
pkill -f "ssh.*11434.*twilight" 2>/dev/null
sleep 1

echo ""
echo "Step 2: Verify tunnel is dead..."
if curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "⚠ Tunnel still alive somehow"
else
    echo "✓ Tunnel confirmed dead"
fi

echo ""
echo "Step 3: Test auto-restart..."
python3 scripts/ensure_ollama_connection.py

echo ""
echo "Step 4: Verify connection works..."
if curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✓ Connection auto-recovered successfully!"
    echo ""
    echo "This will survive laptop sleep/wake cycles."
else
    echo "✗ Auto-recovery failed"
    exit 1
fi
