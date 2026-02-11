#!/usr/bin/env python3
"""
Filter unified candidates by Judge Hermes score threshold.

Reads all judge-results files, matches scores to unified-candidates.jsonl by ID,
outputs only examples meeting the score threshold.

Usage:
    python3 scripts/filter_by_judge_score.py                # default threshold 32
    python3 scripts/filter_by_judge_score.py --threshold 35  # higher bar
    python3 scripts/filter_by_judge_score.py --stats         # show stats only
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

CANDIDATES_FILE = Path("data/training-candidates/unified-candidates.jsonl")
JUDGE_RESULTS_DIR = Path("data/judge-results")
OUTPUT_FILE = Path("data/training-candidates/judged-approved.jsonl")


def load_all_scores():
    """Load highest score per ID across all judge-results files."""
    scores = {}
    if not JUDGE_RESULTS_DIR.exists():
        return scores

    for result_file in sorted(JUDGE_RESULTS_DIR.glob("hermes-run-*.jsonl")):
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    eid = entry.get("id")
                    score = entry.get("hermes_score")
                    if eid and score is not None:
                        # Keep highest score if evaluated multiple times
                        if eid not in scores or score > scores[eid]:
                            scores[eid] = score
                except json.JSONDecodeError:
                    continue
    return scores


def main():
    parser = argparse.ArgumentParser(description="Filter candidates by judge score")
    parser.add_argument("--threshold", type=int, default=32, help="Minimum score (default: 32)")
    parser.add_argument("--stats", action="store_true", help="Show stats only, don't write output")
    args = parser.parse_args()

    if not CANDIDATES_FILE.exists():
        print(f"ERROR: {CANDIDATES_FILE} not found")
        sys.exit(1)

    scores = load_all_scores()
    if not scores:
        print("ERROR: No judge scores found in data/judge-results/")
        print("Run: python3 scripts/run_hermes_judge.py")
        sys.exit(1)

    # Load candidates
    candidates = []
    with open(CANDIDATES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Match and filter
    scored = 0
    unscored = 0
    approved = []
    rejected = []
    score_dist = defaultdict(int)

    for ex in candidates:
        eid = ex.get("id", "")
        if eid in scores:
            scored += 1
            s = scores[eid]
            score_dist[s] += 1
            if s >= args.threshold:
                approved.append(ex)
            else:
                rejected.append(ex)
        else:
            unscored += 1

    print(f"{'='*60}")
    print(f"JUDGE SCORE FILTER (threshold: {args.threshold}/40)")
    print(f"{'='*60}")
    print(f"Total candidates: {len(candidates)}")
    print(f"Scored: {scored}")
    print(f"Unscored: {unscored}")
    print(f"Approved (>={args.threshold}): {len(approved)}")
    print(f"Rejected (<{args.threshold}): {len(rejected)}")

    if scored > 0:
        all_scores = [scores[ex.get("id")] for ex in candidates if ex.get("id") in scores]
        avg = sum(all_scores) / len(all_scores)
        print(f"\nScore stats: min={min(all_scores)}, max={max(all_scores)}, avg={avg:.1f}/40")

        print(f"\nDistribution:")
        for s in sorted(score_dist.keys()):
            bar = '#' * score_dist[s]
            print(f"  {s:2d}/40: {score_dist[s]:4d} {bar}")

    if not args.stats:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for ex in approved:
                f.write(json.dumps(ex, ensure_ascii=False) + '\n')
        print(f"\nOutput: {OUTPUT_FILE} ({len(approved)} examples)")


if __name__ == "__main__":
    main()
