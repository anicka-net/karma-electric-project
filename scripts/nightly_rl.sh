#!/bin/bash
#
# Nightly rejection sampling runner for ai01.
#
# Manages server lifecycle and runs generation/scoring in overnight windows.
# Designed to not disrupt daytime GPU usage.
#
# Usage:
#   ./scripts/nightly_rl.sh generate [START] [END]   # Apertus 70B generation
#   ./scripts/nightly_rl.sh score                     # 8B evaluator scoring
#   ./scripts/nightly_rl.sh status                    # check progress
#   ./scripts/nightly_rl.sh stop                      # kill servers
#
# Schedule (14h overnight windows, 18:00-08:00):
#
#   Pass 1 — 1 response per 11,500 prompts:
#     Generation: ~1,800/night → 7 nights
#     Scoring:    ~11,500 in 10h → 1 night
#
#   Filter: select interesting prompts (< 1 min)
#
#   Pass 2 — 3 more responses per filtered prompt (~40% = 4,600):
#     Generation: ~13,800 responses → 4-5 nights
#     Scoring:    ~13,800 in ~12h → 1 night
#
#   Total: ~2 weeks of overnight runs
#
# Nightly commands (run from karma-electric repo root):
#
#   Pass 1, night 1:  ./scripts/nightly_rl.sh generate 0 1800
#   Pass 1, night 2:  ./scripts/nightly_rl.sh generate 1800 3600
#   Pass 1, night 3:  ./scripts/nightly_rl.sh generate 3600 5400
#   Pass 1, night 4:  ./scripts/nightly_rl.sh generate 5400 7200
#   Pass 1, night 5:  ./scripts/nightly_rl.sh generate 7200 9000
#   Pass 1, night 6:  ./scripts/nightly_rl.sh generate 9000 10800
#   Pass 1, night 7:  ./scripts/nightly_rl.sh generate 10800 11500
#   Pass 1, night 8:  ./scripts/nightly_rl.sh score
#   Then:             python3 scripts/rejection_sampling.py filter
#   Pass 2, night 9+: ./scripts/nightly_rl.sh generate-pass2 [START] [END]
#   Final night:      ./scripts/nightly_rl.sh score
#   Then:             python3 scripts/rejection_sampling.py extract-pairs
#                     python3 scripts/rejection_sampling.py stats

set -euo pipefail

AI01="ai01"
LLAMA_SERVER="/space/anicka/llama-cpp-acap/build/bin/llama-server"
APERTUS_MODEL="/space/anicka/models/gguf/swiss-ai_Apertus-70B-Instruct-2509-Q4_K_M.gguf"
KE8B_MODEL="/space/anicka/karma-electric-8b/karma-electric-8b-v10.1-Q8_0.gguf"
WORKDIR="/space/anicka/karma-electric-8b"
LOGDIR="data/rejection-sampling"

start_apertus() {
    echo "Starting Apertus 70B on ai01:8385..."
    ssh "$AI01" "cd $WORKDIR && nohup $LLAMA_SERVER -m $APERTUS_MODEL --port 8385 -ngl 99 -c 4096 > llama-server-apertus-nightly.log 2>&1 & echo \$!"
    echo "Waiting for model to load..."
    for i in $(seq 1 40); do
        sleep 15
        if ssh "$AI01" "curl -sf http://localhost:8385/health" >/dev/null 2>&1; then
            echo "Apertus ready."
            return 0
        fi
        echo "  loading... ($((i*15))s)"
    done
    echo "ERROR: Apertus failed to start in 10 minutes"
    return 1
}

start_evaluator() {
    echo "Starting KE 8B evaluator on ai01:8384..."
    ssh "$AI01" "cd $WORKDIR && nohup $LLAMA_SERVER -m $KE8B_MODEL --port 8384 -ngl 99 -c 4096 > llama-server-ke8b-nightly.log 2>&1 & echo \$!"
    sleep 10
    if ssh "$AI01" "curl -sf http://localhost:8384/health" >/dev/null 2>&1; then
        echo "Evaluator ready."
        return 0
    fi
    echo "ERROR: Evaluator failed to start"
    return 1
}

stop_servers() {
    echo "Stopping all llama-server processes on ai01..."
    ssh "$AI01" "pkill -f llama-server 2>/dev/null || true"
    sleep 2
    if ssh "$AI01" "pgrep -a llama-server" 2>/dev/null; then
        echo "WARNING: some processes still running"
    else
        echo "All servers stopped."
    fi
}

ensure_tunnel() {
    local port=$1
    if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
        return 0
    fi
    echo "Setting up SSH tunnel for port $port..."
    ssh -fN -L "$port:localhost:$port" "$AI01"
    sleep 2
}

case "${1:-}" in
    generate)
        START="${2:-0}"
        END="${3:-1800}"
        stop_servers
        start_apertus
        ensure_tunnel 8385
        echo "Generating responses [$START:$END], n=1 per prompt..."
        python3 scripts/rejection_sampling.py generate \
            --start "$START" --end "$END" --n-per-prompt 1 \
            > "$LOGDIR/nightly-generate-${START}-${END}.log" 2>&1
        echo "Generation complete. Stopping server."
        stop_servers
        echo "Done. Check: python3 scripts/rejection_sampling.py stats"
        ;;

    generate-pass2)
        START="${2:-0}"
        END="${3:-}"
        stop_servers
        start_apertus
        ensure_tunnel 8385
        echo "Generating pass-2 responses..."
        ARGS="--n-extra 3"
        [ -n "$START" ] && ARGS="$ARGS --start $START"
        [ -n "$END" ] && ARGS="$ARGS --end $END"
        python3 scripts/rejection_sampling.py generate-pass2 $ARGS \
            > "$LOGDIR/nightly-pass2-${START}-${END:-end}.log" 2>&1
        echo "Pass-2 generation complete. Stopping server."
        stop_servers
        ;;

    score)
        stop_servers
        start_evaluator
        ensure_tunnel 8384
        echo "Scoring all unscored responses..."
        python3 scripts/rejection_sampling.py score \
            > "$LOGDIR/nightly-score.log" 2>&1
        echo "Scoring complete. Stopping server."
        stop_servers
        echo "Done. Run: python3 scripts/rejection_sampling.py stats"
        ;;

    status)
        echo "=== ai01 GPU ==="
        ssh "$AI01" "nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader" 2>/dev/null || echo "unreachable"
        echo ""
        echo "=== Servers ==="
        ssh "$AI01" "pgrep -a llama-server" 2>/dev/null || echo "none running"
        echo ""
        echo "=== Data ==="
        python3 scripts/rejection_sampling.py stats
        ;;

    stop)
        stop_servers
        ;;

    *)
        echo "Usage: $0 {generate|generate-pass2|score|status|stop} [args]"
        echo ""
        echo "  generate [START] [END]  — Run Apertus 70B, 1 response per prompt"
        echo "  generate-pass2 [START] [END] — Run Apertus 70B for filtered prompts"
        echo "  score                   — Run KE 8B evaluator on all unscored"
        echo "  status                  — Check GPU, servers, and data progress"
        echo "  stop                    — Kill all servers on ai01"
        ;;
esac
