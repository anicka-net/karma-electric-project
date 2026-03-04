#!/bin/bash
#
# Cron-driven rejection sampling. Figures out what phase we're in
# and does the right thing automatically.
#
# Crontab (run from karma-electric repo root):
#   0 18 * * * cd /home/anicka/playground/karma-electric && ./scripts/nightly_cron.sh start >> data/rejection-sampling/cron.log 2>&1
#   0  8 * * * cd /home/anicka/playground/karma-electric && ./scripts/nightly_cron.sh stop  >> data/rejection-sampling/cron.log 2>&1
#
# State machine (auto-advances through phases):
#   1. Pass-1 generate: 1 response per 11,500 prompts (Apertus 70B)
#   2. Pass-1 score: score all pass-1 responses (KE 8B)
#   3. Filter: select prompts for pass-2
#   4. Pass-2 generate: 3 more per filtered prompt (Apertus 70B)
#   5. Pass-2 score: score pass-2 responses (KE 8B)
#   6. Extract pairs: done
#

set -euo pipefail

AI01="ai01"
LLAMA_SERVER="/space/anicka/llama-cpp-acap/build/bin/llama-server"
APERTUS_MODEL="/space/anicka/models/gguf/swiss-ai_Apertus-70B-Instruct-2509-Q4_K_M.gguf"
KE8B_MODEL="/space/anicka/karma-electric-8b/karma-electric-8b-v10.1-Q8_0.gguf"
WORKDIR="/space/anicka/karma-electric-8b"

DATADIR="data/rejection-sampling"
RESPONSES="$DATADIR/responses.jsonl"
SCORED="$DATADIR/scored-responses.jsonl"
PASS2_PROMPTS="$DATADIR/pass2-prompts.jsonl"

TOTAL_PROMPTS=11500
PASS1_N=1
PASS2_N=3

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

stop_servers() {
    ssh "$AI01" "pkill -f llama-server 2>/dev/null || true" 2>/dev/null
    # Kill any local tunnel orphans
    pkill -f "ssh -fN -L 838[45]:localhost" 2>/dev/null || true
    sleep 2
}

start_apertus() {
    stop_servers
    log "Starting Apertus 70B..."
    ssh "$AI01" "cd $WORKDIR && nohup $LLAMA_SERVER -m $APERTUS_MODEL --port 8385 -ngl 99 -c 4096 > llama-server-cron.log 2>&1 & echo \$!"
    for i in $(seq 1 40); do
        sleep 15
        if ssh "$AI01" "curl -sf http://localhost:8385/health" >/dev/null 2>&1; then
            log "Apertus ready."
            ssh -fN -L 8385:localhost:8385 "$AI01"
            return 0
        fi
    done
    log "ERROR: Apertus failed to load"
    return 1
}

start_evaluator() {
    stop_servers
    log "Starting KE 8B evaluator..."
    ssh "$AI01" "cd $WORKDIR && nohup $LLAMA_SERVER -m $KE8B_MODEL --port 8384 -ngl 99 -c 4096 > llama-server-cron.log 2>&1 & echo \$!"
    sleep 15
    if ssh "$AI01" "curl -sf http://localhost:8384/health" >/dev/null 2>&1; then
        log "Evaluator ready."
        ssh -fN -L 8384:localhost:8384 "$AI01"
        return 0
    fi
    log "ERROR: Evaluator failed to start"
    return 1
}

count_lines() {
    [ -f "$1" ] && wc -l < "$1" || echo 0
}

# Count unique prompt indices with response_idx=0 (pass-1 responses)
count_pass1_responses() {
    [ -f "$RESPONSES" ] || { echo 0; return; }
    python3 -c "
import json
seen = set()
with open('$RESPONSES') as f:
    for line in f:
        d = json.loads(line)
        if d['response_idx'] == 0:
            seen.add(d['prompt_idx'])
print(len(seen))
"
}

count_responses() {
    count_lines "$RESPONSES"
}

count_scored() {
    count_lines "$SCORED"
}

determine_phase() {
    local pass1_done=$(count_pass1_responses)
    local total_responses=$(count_responses)
    local total_scored=$(count_scored)

    # Phase 1: generate 1 per prompt
    if [ "$pass1_done" -lt "$TOTAL_PROMPTS" ]; then
        echo "pass1-generate"
        return
    fi

    # Phase 2: score pass-1
    if [ "$total_scored" -lt "$total_responses" ]; then
        echo "score"
        return
    fi

    # Phase 3: filter (if not done yet)
    if [ ! -f "$PASS2_PROMPTS" ]; then
        echo "filter"
        return
    fi

    # Phase 4: check if pass-2 generation needed
    local pass2_count
    pass2_count=$(wc -l < "$PASS2_PROMPTS")
    local expected_total=$((TOTAL_PROMPTS * PASS1_N + pass2_count * PASS2_N))
    if [ "$total_responses" -lt "$expected_total" ]; then
        echo "pass2-generate"
        return
    fi

    # Phase 5: score pass-2
    if [ "$total_scored" -lt "$total_responses" ]; then
        echo "score"
        return
    fi

    # Phase 6: done
    echo "done"
}

cmd_start() {
    mkdir -p "$DATADIR"

    local phase=$(determine_phase)
    log "Phase: $phase"
    log "  responses=$(count_responses) scored=$(count_scored) pass1=$(count_pass1_responses)/$TOTAL_PROMPTS"

    case "$phase" in
        pass1-generate)
            start_apertus
            log "Running pass-1 generation (n=1 per prompt)..."
            python3 scripts/rejection_sampling.py generate \
                --n-per-prompt 1 \
                > "$DATADIR/cron-generate.log" 2>&1
            log "Pass-1 generation session complete."
            # If generation finished, immediately score
            local new_pass1=$(count_pass1_responses)
            if [ "$new_pass1" -ge "$TOTAL_PROMPTS" ]; then
                log "Pass-1 complete! Switching to scoring..."
                stop_servers
                start_evaluator
                python3 scripts/rejection_sampling.py score \
                    > "$DATADIR/cron-score.log" 2>&1
                log "Scoring complete."
                # Auto-filter
                python3 scripts/rejection_sampling.py filter
                log "Filter complete. Pass-2 will start next night."
            fi
            stop_servers
            ;;

        score)
            start_evaluator
            log "Running scoring..."
            python3 scripts/rejection_sampling.py score \
                > "$DATADIR/cron-score.log" 2>&1
            log "Scoring complete."
            stop_servers
            # If this was after pass-1, auto-filter
            if [ ! -f "$PASS2_PROMPTS" ]; then
                python3 scripts/rejection_sampling.py filter
                log "Filter complete."
            fi
            ;;

        filter)
            python3 scripts/rejection_sampling.py filter
            log "Filter complete. Pass-2 generation will start next night."
            ;;

        pass2-generate)
            start_apertus
            log "Running pass-2 generation (n=3 extra)..."
            python3 scripts/rejection_sampling.py generate-pass2 \
                > "$DATADIR/cron-pass2.log" 2>&1
            log "Pass-2 generation session complete."
            # If finished, score immediately
            local total_r=$(count_responses)
            local total_s=$(count_scored)
            if [ "$total_s" -lt "$total_r" ]; then
                local unscored=$((total_r - total_s))
                log "Pass-2 may be complete. $unscored unscored responses."
                stop_servers
                start_evaluator
                python3 scripts/rejection_sampling.py score \
                    > "$DATADIR/cron-score.log" 2>&1
                log "Scoring complete."
                python3 scripts/rejection_sampling.py extract-pairs
                python3 scripts/rejection_sampling.py stats
                log "=== ALL DONE ==="
            fi
            stop_servers
            ;;

        done)
            log "All phases complete. Extract pairs if not done:"
            log "  python3 scripts/rejection_sampling.py extract-pairs"
            log "  python3 scripts/rejection_sampling.py stats"
            ;;
    esac
}

cmd_stop() {
    log "Cron stop: killing servers and generation..."
    # Kill the python generation/scoring process
    pkill -f "rejection_sampling.py" 2>/dev/null || true
    stop_servers
    log "Stopped. Progress:"
    log "  responses=$(count_responses) scored=$(count_scored) pass1=$(count_pass1_responses)/$TOTAL_PROMPTS"
}

case "${1:-}" in
    start) cmd_start ;;
    stop)  cmd_stop ;;
    status)
        phase=$(determine_phase)
        log "Phase: $phase"
        log "  responses=$(count_responses) scored=$(count_scored) pass1=$(count_pass1_responses)/$TOTAL_PROMPTS"
        [ -f "$PASS2_PROMPTS" ] && log "  pass2 prompts: $(wc -l < "$PASS2_PROMPTS")"
        ssh "$AI01" "pgrep -a llama-server" 2>/dev/null || log "  no servers running"
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        ;;
esac
