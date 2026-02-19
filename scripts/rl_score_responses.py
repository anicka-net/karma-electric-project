#!/usr/bin/env python3
"""
Batch reward scoring for RL rejection sampling.

Scores generated responses using KE-8B as reward model.
Reuses reward_test_utils.py for scoring API and parsing.

Usage:
    # Score all responses (KE-8B must be running)
    python rl_score_responses.py score

    # Resume scoring (skip already-scored)
    python rl_score_responses.py score --resume

    # Custom KE-8B endpoint
    python rl_score_responses.py score --ke8b-url http://localhost:8401/v1/chat/completions

    # Stats on scored responses
    python rl_score_responses.py stats
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reward_test_utils import (
    query_ke8b_reward, extract_reward_scores, check_ke8b,
    KE8B_URL, DIMENSIONS,
)

# ── Config ────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data" / "rl-generation"
RESPONSES_FILE = DATA_DIR / "apertus-responses.jsonl"
SCORED_FILE = DATA_DIR / "apertus-scored.jsonl"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Resume support ────────────────────────────────────────────────

def load_scored_keys(scored_file):
    """Load keys of already-scored entries for resume."""
    keys = set()
    if not scored_file.exists():
        return keys
    with open(scored_file) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            key = f"{entry.get('prompt_hash', '')}:{entry.get('generation_id', '')}"
            keys.add(key)
    return keys


# ── Scoring ───────────────────────────────────────────────────────

def run_score(args):
    """Score all generated responses with KE-8B."""
    responses_file = Path(args.input) if args.input else RESPONSES_FILE
    scored_file = Path(args.output) if args.output else SCORED_FILE

    if not responses_file.exists():
        log(f"ERROR: {responses_file} not found. Run rl_generate_apertus.py first.")
        sys.exit(1)

    # Check KE-8B
    ke8b_url = args.ke8b_url
    log(f"Checking KE-8B at {ke8b_url}...")
    if not check_ke8b(ke8b_url):
        log(f"ERROR: KE-8B not reachable at {ke8b_url}")
        sys.exit(1)
    log("KE-8B OK")

    # Load responses
    responses = []
    with open(responses_file) as f:
        for line in f:
            if not line.strip():
                continue
            responses.append(json.loads(line))
    log(f"Loaded {len(responses)} responses from {responses_file}")

    # Resume support
    scored_keys = set()
    if args.resume:
        scored_keys = load_scored_keys(scored_file)
        log(f"Resume: {len(scored_keys)} already scored")

    mode = "a" if args.resume else "w"
    out_f = open(scored_file, mode, encoding="utf-8")

    total_scored = 0
    total_errors = 0
    total_skipped = 0
    start_time = time.time()

    try:
        for ri, resp_entry in enumerate(responses):
            prompt_hash = resp_entry.get("prompt_hash", "")
            gen_id = resp_entry.get("generation_id", 0)
            key = f"{prompt_hash}:{gen_id}"

            if key in scored_keys:
                total_skipped += 1
                continue

            prompt_text = resp_entry["prompt"]
            response_text = resp_entry["response"]

            if not response_text:
                total_skipped += 1
                continue

            log(f"[{ri+1}/{len(responses)}] Scoring hash={prompt_hash[:8]}... "
                f"gen={gen_id}")

            t0 = time.time()
            try:
                raw_eval = query_ke8b_reward(prompt_text, response_text,
                                              url=ke8b_url)
                elapsed = time.time() - t0
                scores = extract_reward_scores(raw_eval)

                scored_entry = {
                    "prompt": prompt_text,
                    "prompt_hash": prompt_hash,
                    "source": resp_entry.get("source", "unknown"),
                    "generation_id": gen_id,
                    "response": response_text,
                    "scores": {
                        d: scores.get(d) for d in DIMENSIONS + ["overall"]
                    },
                    "red_flags": scores.get("red_flags"),
                    "scored_at": datetime.now().isoformat(),
                }

                out_f.write(json.dumps(scored_entry, ensure_ascii=False) + "\n")
                out_f.flush()
                total_scored += 1

                overall = scores.get("overall", "?")
                log(f"  overall={overall}/10 ({elapsed:.1f}s)")

            except Exception as e:
                elapsed = time.time() - t0
                log(f"  ERROR ({elapsed:.1f}s): {e}")
                total_errors += 1

                # Back off on repeated errors
                if total_errors % 5 == 0:
                    log("  Multiple errors, waiting 10s...")
                    time.sleep(10)
                    if not check_ke8b(ke8b_url):
                        log("  KE-8B unreachable. Stopping.")
                        break

            # Brief pause to avoid overwhelming the server
            time.sleep(0.1)

            # Progress every 500 scores
            if total_scored > 0 and total_scored % 500 == 0:
                elapsed_total = time.time() - start_time
                rate = total_scored / elapsed_total * 3600
                log(f"  Progress: {total_scored} scored, {total_errors} errors, "
                    f"{rate:.0f}/hr")

    finally:
        out_f.close()

    elapsed_total = time.time() - start_time
    log(f"\nDone: {total_scored} scored, {total_errors} errors, "
        f"{total_skipped} skipped in {elapsed_total/3600:.1f}h")


# ── Stats ─────────────────────────────────────────────────────────

def run_stats(args):
    """Print statistics on scored responses."""
    scored_file = Path(args.output) if args.output else SCORED_FILE

    if not scored_file.exists():
        log(f"No scored file: {scored_file}")
        sys.exit(1)

    entries = []
    with open(scored_file) as f:
        for line in f:
            if not line.strip():
                continue
            entries.append(json.loads(line))

    if not entries:
        log("No scored entries found")
        return

    # Overall scores
    overall_scores = [e["scores"].get("overall") for e in entries
                      if e["scores"].get("overall") is not None]

    print(f"\n{'='*60}")
    print(f"RL Scoring Statistics")
    print(f"{'='*60}")
    print(f"Total scored:  {len(entries)}")
    print(f"With overall:  {len(overall_scores)}")

    if overall_scores:
        avg = sum(overall_scores) / len(overall_scores)
        overall_scores.sort()
        print(f"\nOverall score distribution:")
        print(f"  Mean:  {avg:.2f}")
        print(f"  Min:   {min(overall_scores)}")
        print(f"  P25:   {overall_scores[len(overall_scores)//4]}")
        print(f"  P50:   {overall_scores[len(overall_scores)//2]}")
        print(f"  P75:   {overall_scores[3*len(overall_scores)//4]}")
        print(f"  Max:   {max(overall_scores)}")

        # Distribution
        print(f"\n  Score histogram:")
        for s in range(1, 11):
            count = sum(1 for v in overall_scores if round(v) == s)
            bar = "#" * (count * 50 // len(overall_scores))
            pct = 100 * count / len(overall_scores)
            print(f"    {s:2d}: {bar:30s} {count:5d} ({pct:.1f}%)")

    # Per-dimension stats
    print(f"\nPer-dimension means:")
    for dim in DIMENSIONS + ["overall"]:
        vals = [e["scores"].get(dim) for e in entries
                if e["scores"].get(dim) is not None]
        if vals:
            avg = sum(vals) / len(vals)
            print(f"  {dim:<22s}: {avg:.2f} (n={len(vals)})")

    # By source
    by_source = {}
    for e in entries:
        s = e.get("source", "unknown")
        score = e["scores"].get("overall")
        if score is not None:
            by_source.setdefault(s, []).append(score)

    print(f"\nMean overall by source:")
    for s, scores in sorted(by_source.items(),
                             key=lambda x: -sum(x[1])/len(x[1])):
        avg = sum(scores) / len(scores)
        print(f"  {s:<25s}: {avg:.2f} (n={len(scores)})")

    # Red flags
    flagged = sum(1 for e in entries if e.get("red_flags"))
    print(f"\nRed flags: {flagged}/{len(entries)} "
          f"({100*flagged/len(entries):.1f}%)")

    # Per-prompt coverage
    by_prompt = {}
    for e in entries:
        h = e.get("prompt_hash", "")
        by_prompt.setdefault(h, []).append(e)

    complete = sum(1 for resps in by_prompt.values() if len(resps) >= 4)
    print(f"\nPrompt coverage:")
    print(f"  Unique prompts: {len(by_prompt)}")
    print(f"  Complete (4/4): {complete}")


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Batch reward scoring for RL rejection sampling")
    sub = parser.add_subparsers(dest="command")

    # Score
    sc = sub.add_parser("score", help="Score responses with KE-8B")
    sc.add_argument("--input", default=None,
                    help="Input responses JSONL")
    sc.add_argument("--output", default=None,
                    help="Output scored JSONL")
    sc.add_argument("--ke8b-url", default=KE8B_URL,
                    help="KE-8B endpoint URL")
    sc.add_argument("--resume", action="store_true",
                    help="Skip already-scored entries")

    # Stats
    st = sub.add_parser("stats", help="Show scoring statistics")
    st.add_argument("--output", default=None)

    args = parser.parse_args()

    if args.command == "score":
        run_score(args)
    elif args.command == "stats":
        run_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
