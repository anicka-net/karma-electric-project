#!/bin/bash
# Run RL simulation: 10 iterations x 20 questions, both models, then judge all
set -e

cd /space/anicka/karma-electric-8b
SCRIPT=rl_simulate_llamacpp.py
LLAMA=Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf
APERTUS=swiss-ai_Apertus-70B-Instruct-2509-Q4_K_M.gguf
KE_JUDGE=karma-electric-8b-v6-Q8_0.gguf

echo "=== Phase 1: Generate with Llama 70B ==="
python3 $SCRIPT generate \
    --model /space/anicka/models/gguf/$LLAMA \
    --iterations 10 --samples 20 --port 8400 \
    --responses-dir rl-sim-results/llama70b

echo ""
echo "=== Phase 2: Generate with Apertus 70B ==="
python3 $SCRIPT generate \
    --model /space/anicka/models/gguf/$APERTUS \
    --iterations 10 --samples 20 --port 8400 \
    --responses-dir rl-sim-results/apertus70b

echo ""
echo "=== Phase 3: Judge Llama 70B responses ==="
python3 $SCRIPT judge \
    --model $KE_JUDGE \
    --responses-dir rl-sim-results/llama70b \
    --port 8401

echo ""
echo "=== Phase 4: Judge Apertus 70B responses ==="
python3 $SCRIPT judge \
    --model $KE_JUDGE \
    --responses-dir rl-sim-results/apertus70b \
    --port 8401

echo ""
echo "=== Phase 5: Compare ==="
python3 $SCRIPT compare \
    --dir1 rl-sim-results/llama70b \
    --dir2 rl-sim-results/apertus70b

echo ""
echo "=== DONE ==="
