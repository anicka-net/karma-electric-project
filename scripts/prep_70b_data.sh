#!/bin/bash
# Prepare all data for 70B weekend run
#
# Run this BEFORE training. Creates all data files
# needed for the 70B training run.
#
# Output files:
#   data/thinking-stage1-mot.jsonl    — 15K MoT examples (~60MB)
#   train-70b-v10.1-thinking.jsonl    — 4,248 KE examples with <think> (~40MB)
#   data/training.db                  — already exists (source of truth)

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Preparing 70B training data ==="
echo "Working directory: $(pwd)"
echo ""

# Stage 1: Mixture-of-Thoughts (downloads from HuggingFace)
if [ -f "data/thinking-stage1-mot.jsonl" ]; then
    COUNT=$(wc -l < data/thinking-stage1-mot.jsonl)
    echo "Stage 1 data exists: $COUNT examples"
    if [ "$COUNT" -lt 10000 ]; then
        echo "  Only $COUNT examples — regenerating with 5000/domain..."
        python3 scripts/prepare_thinking_stage1.py --n-per-domain 5000
    fi
else
    echo "Preparing stage 1 data (5000 per domain = 15K total)..."
    python3 scripts/prepare_thinking_stage1.py --n-per-domain 5000
fi

# Stage 2: KE data with reasoning traces
echo ""
echo "Exporting stage 2 data (KE with reasoning traces)..."
python3 scripts/training_db.py export \
    -o train-70b-v10.1-thinking.jsonl --reasoning \
    --system-prompt v4 \
    --category-prompt reward-evaluation:reward-evaluator-v1 \
    --category-prompt reward-evaluation-v5:reward-evaluator-v1 \
    --category-prompt reward-evaluation-style-variant:reward-evaluator-v1

S2_COUNT=$(wc -l < train-70b-v10.1-thinking.jsonl)
echo "Stage 2: $S2_COUNT examples"

# Summary
echo ""
echo "============================================"
echo "Data ready. Files needed for training:"
echo "  data/thinking-stage1-mot.jsonl   ($(du -sh data/thinking-stage1-mot.jsonl | cut -f1))"
echo "  train-70b-v10.1-thinking.jsonl   ($(du -sh train-70b-v10.1-thinking.jsonl | cut -f1))"
echo "  scripts/train_apertus_70b_thinking.py"
echo "  scripts/launch_70b_weekend.sh"
echo ""
echo "Also need:"
echo "  pip install torch transformers>=4.56.0 datasets accelerate trl peft bitsandbytes"
echo "  python3 scripts/download_70b_model.py  (downloads ~142GB)"
echo "============================================"
