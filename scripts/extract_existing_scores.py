#!/usr/bin/env python3
"""
Extract existing Hermes scores from practice-response source files
into the unified judge-results format.

Walks data/practice-responses/, finds all JSONs with hermes_score,
and writes them to data/judge-results/hermes-run-000-existing.jsonl.

This migrates the 805 existing scores into the new holistic storage format.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

RESPONSES_DIR = Path("data/practice-responses")
OUTPUT_FILE = Path("data/judge-results/hermes-run-000-existing.jsonl")


def main():
    if not RESPONSES_DIR.exists():
        print(f"ERROR: {RESPONSES_DIR} not found")
        sys.exit(1)

    all_files = sorted(RESPONSES_DIR.rglob("*.json"))
    all_files = [f for f in all_files if not f.name.startswith('.')]

    print(f"Scanning {len(all_files)} response files...")

    results = []
    category_counts = defaultdict(int)
    score_values = []

    for fpath in all_files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        score = data.get("hermes_score")
        if score is None:
            continue

        scenario_id = data.get("scenario_id", fpath.stem)
        category = fpath.parent.name

        result = {
            "id": scenario_id,
            "source_file": str(fpath),
            "category": category,
            "hermes_score": score,
            "hermes_evaluation": data.get("hermes_evaluation", ""),
            "hermes_evaluated_at": data.get("hermes_evaluated_at", ""),
            "judge_model": data.get("judge_model", "hermes3:70b"),
            "meditation_in_prompt": data.get("meditation_in_prompt", False),
            "run": "000-existing",
        }

        results.append(result)
        category_counts[category] += 1
        score_values.append(score)

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Summary
    print(f"\n{'='*60}")
    print(f"EXISTING SCORES EXTRACTED")
    print(f"{'='*60}")
    print(f"Total scores: {len(results)}")
    print(f"Output: {OUTPUT_FILE}")

    if score_values:
        avg = sum(score_values) / len(score_values)
        print(f"\nScore stats: min={min(score_values)}, max={max(score_values)}, avg={avg:.1f}/40")

        print(f"\nBy category:")
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            cat_scores = [r["hermes_score"] for r in results if r["category"] == cat]
            cat_avg = sum(cat_scores) / len(cat_scores)
            print(f"  {cat}: {count} scores (avg {cat_avg:.1f}/40)")

    # Check overlap with unified-candidates
    unified = Path("data/training-candidates/unified-candidates.jsonl")
    if unified.exists():
        unified_ids = set()
        with open(unified, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                    unified_ids.add(ex.get("id", ""))
                except json.JSONDecodeError:
                    continue

        scored_ids = {r["id"] for r in results}
        overlap = unified_ids & scored_ids
        print(f"\nOverlap with unified-candidates.jsonl:")
        print(f"  Unified dataset IDs: {len(unified_ids)}")
        print(f"  Scored IDs: {len(scored_ids)}")
        print(f"  Already scored in unified: {len(overlap)}")
        print(f"  Still need scoring: {len(unified_ids) - len(overlap)}")


if __name__ == "__main__":
    main()
