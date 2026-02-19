#!/usr/bin/env python3
"""
Best-of-N selection for RL rejection sampling.

Groups scored responses by prompt, picks the highest-scored,
filters by threshold, and formats for SFT training.

Usage:
    # Select best responses (default threshold >= 7)
    python rl_select_best.py select

    # Stricter threshold
    python rl_select_best.py select --threshold 8

    # Stats on selection
    python rl_select_best.py stats
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"
SCORED_FILE = DATA_DIR / "rl-generation" / "apertus-scored.jsonl"
TRAINING_DIR = DATA_DIR / "rl-training"
OUTPUT_FILE = TRAINING_DIR / "apertus-rl-sft-v1.jsonl"

DEFAULT_THRESHOLD = 7.0


def log(msg):
    print(f"[rl-select] {msg}", flush=True)


# ── Selection ─────────────────────────────────────────────────────

def run_select(args):
    """Select best response per prompt and format for SFT."""
    scored_file = Path(args.input) if args.input else SCORED_FILE
    output_file = Path(args.output) if args.output else OUTPUT_FILE
    threshold = args.threshold

    if not scored_file.exists():
        log(f"ERROR: {scored_file} not found. Run rl_score_responses.py first.")
        sys.exit(1)

    # Load all scored responses, group by prompt
    by_prompt = defaultdict(list)
    total_loaded = 0
    with open(scored_file) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            h = entry.get("prompt_hash", "")
            by_prompt[h].append(entry)
            total_loaded += 1

    log(f"Loaded {total_loaded} scored responses for {len(by_prompt)} prompts")

    # Select best per prompt
    selected = []
    rejected_low_score = 0
    rejected_red_flags = 0
    rejected_no_score = 0
    score_distribution = defaultdict(int)

    for prompt_hash, responses in by_prompt.items():
        # Sort by overall score (highest first)
        scored_responses = []
        for r in responses:
            overall = r.get("scores", {}).get("overall")
            if overall is None:
                rejected_no_score += 1
                continue
            scored_responses.append((overall, r))

        if not scored_responses:
            continue

        scored_responses.sort(key=lambda x: x[0], reverse=True)
        best_score, best_response = scored_responses[0]

        # Track all scores for stats
        for score, _ in scored_responses:
            score_distribution[round(score)] += 1

        # Apply filters
        if best_response.get("red_flags"):
            # Check if red flags are substantive (not "None" or "none detected")
            flags = best_response["red_flags"].strip().lower()
            if flags and flags not in ("none", "none detected", "none identified",
                                        "n/a", "no red flags", "no red flags detected",
                                        "none.", "none identified."):
                rejected_red_flags += 1
                continue

        if best_score < threshold:
            rejected_low_score += 1
            continue

        # Format as SFT training example
        sft_example = {
            "conversations": [
                {"role": "user", "content": best_response["prompt"]},
                {"role": "assistant", "content": best_response["response"]},
            ],
            "source": best_response.get("source", "unknown"),
            "prompt_hash": prompt_hash,
            "reward_score": best_score,
            "reward_scores": best_response.get("scores", {}),
        }
        selected.append(sft_example)

    # Sort by score descending for easy spot-checking
    selected.sort(key=lambda x: x["reward_score"], reverse=True)

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in selected:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Print report
    print(f"\n{'='*60}")
    print(f"RL Selection Report")
    print(f"{'='*60}")
    print(f"Total prompts:          {len(by_prompt)}")
    print(f"Selected:               {len(selected)}")
    print(f"Rejected (low score):   {rejected_low_score}")
    print(f"Rejected (red flags):   {rejected_red_flags}")
    print(f"Rejected (no score):    {rejected_no_score}")
    print(f"Threshold:              >= {threshold}")
    print(f"Yield:                  {100*len(selected)/max(len(by_prompt),1):.1f}%")

    if selected:
        scores = [e["reward_score"] for e in selected]
        print(f"\nSelected score distribution:")
        print(f"  Mean:  {sum(scores)/len(scores):.2f}")
        print(f"  Min:   {min(scores)}")
        print(f"  Max:   {max(scores)}")

    # Source breakdown
    by_source = defaultdict(int)
    for e in selected:
        by_source[e["source"]] += 1

    print(f"\nBy source:")
    for s, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {s:<25s} {count:>6}")

    print(f"\nAll response score distribution (all N per prompt):")
    for s in range(1, 11):
        count = score_distribution.get(s, 0)
        total = sum(score_distribution.values())
        bar = "#" * (count * 40 // max(total, 1))
        pct = 100 * count / max(total, 1)
        print(f"  {s:2d}: {bar:30s} {count:5d} ({pct:.1f}%)")

    print(f"\nOutput: {output_file}")
    print(f"{'='*60}")


# ── Stats ─────────────────────────────────────────────────────────

def run_stats(args):
    """Show statistics on the selected training data."""
    output_file = Path(args.output) if args.output else OUTPUT_FILE

    if not output_file.exists():
        log(f"No output file: {output_file}")
        sys.exit(1)

    entries = []
    with open(output_file) as f:
        for line in f:
            if not line.strip():
                continue
            entries.append(json.loads(line))

    if not entries:
        log("No entries found")
        return

    scores = [e["reward_score"] for e in entries]
    scores.sort()

    print(f"\n{'='*60}")
    print(f"RL SFT Training Data Statistics")
    print(f"{'='*60}")
    print(f"Total examples:  {len(entries)}")
    print(f"Score range:     {min(scores)} - {max(scores)}")
    print(f"Mean score:      {sum(scores)/len(scores):.2f}")
    print(f"P25:             {scores[len(scores)//4]}")
    print(f"P50:             {scores[len(scores)//2]}")

    # Response length
    lengths = [len(e["conversations"][1]["content"]) for e in entries]
    lengths.sort()
    print(f"\nResponse length:")
    print(f"  Mean:  {sum(lengths)//len(lengths)} chars")
    print(f"  P50:   {lengths[len(lengths)//2]} chars")
    print(f"  P95:   {lengths[int(len(lengths)*0.95)]} chars")

    # By source
    by_source = defaultdict(list)
    for e in entries:
        by_source[e["source"]].append(e["reward_score"])

    print(f"\nBy source:")
    print(f"  {'Source':<25s} {'Count':>6} {'Mean':>6}")
    for s, sc in sorted(by_source.items(), key=lambda x: -len(x[1])):
        avg = sum(sc) / len(sc)
        print(f"  {s:<25s} {len(sc):>6} {avg:>5.1f}")


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Best-of-N selection for RL rejection sampling")
    sub = parser.add_subparsers(dest="command")

    # Select
    sel = sub.add_parser("select", help="Select best responses and format for SFT")
    sel.add_argument("--input", default=None, help="Scored responses JSONL")
    sel.add_argument("--output", default=None, help="Output SFT JSONL")
    sel.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                     help="Minimum overall score threshold")

    # Stats
    st = sub.add_parser("stats", help="Show statistics on selected data")
    st.add_argument("--output", default=None)

    args = parser.parse_args()

    if args.command == "select":
        run_select(args)
    elif args.command == "stats":
        run_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
