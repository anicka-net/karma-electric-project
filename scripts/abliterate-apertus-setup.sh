#!/bin/bash
# Quick setup: install deps, launch abliteration in tmux
# The actual work runs in tmux so it survives SSH drops
set -e

echo "=== Installing dependencies ==="
pip install --quiet --upgrade pip
pip install --quiet --no-cache-dir \
    torch transformers accelerate bitsandbytes \
    datasets huggingface-hub pandas tqdm safetensors

pip cache purge 2>/dev/null || true
rm -rf /root/.cache/pip /tmp/pip-*

apt-get update -qq && apt-get install -y -qq aria2 rsync tmux >/dev/null 2>&1 || true
rm -rf /var/lib/apt/lists/*

echo "=== Cloning llm-abliteration ==="
cd /workspace
if [ ! -d llm-abliteration ]; then
    git clone --depth 1 https://github.com/jim-plus/llm-abliteration.git
fi

echo "=== Setting up SSH key for twilight ==="
chmod 600 /tmp/vast-transfer-key

echo "=== Launching abliteration job in tmux ==="
cp /tmp/abliterate-apertus-job.sh /workspace/abliterate-job.sh
chmod +x /workspace/abliterate-job.sh
tmux new-session -d -s abliterate "bash /workspace/abliterate-job.sh 2>&1 | tee /workspace/abliterate.log"

echo ""
echo "Job launched in tmux session 'abliterate'"
echo "Monitor: ssh -p 2222 root@localhost 'tail -f /workspace/abliterate.log'"
echo "Attach:  ssh -p 2222 root@localhost 'tmux attach -t abliterate'"
echo ""
echo "Setup complete."
