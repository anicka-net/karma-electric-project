#!/usr/bin/env python3
"""Check training data readiness - what's evaluated and ready."""

import json
from pathlib import Path
from collections import defaultdict

PRACTICE_RESPONSES = Path("/tmp/karma-electric/data/practice-responses")

def check_responses():
    """Check all response files for evaluation status."""

    total_files = 0
    evaluated = 0
    unevaluated = 0
    scores = []
    by_category = defaultdict(lambda: {"total": 0, "evaluated": 0, "scores": []})

    for response_file in PRACTICE_RESPONSES.rglob("*.json"):
        if response_file.name == "GENERATION-SUMMARY.md":
            continue

        total_files += 1

        try:
            with open(response_file) as f:
                data = json.load(f)

            category = response_file.parent.name
            by_category[category]["total"] += 1

            if data.get("hermes_score") is not None:
                evaluated += 1
                score = data["hermes_score"]
                scores.append(score)
                by_category[category]["evaluated"] += 1
                by_category[category]["scores"].append(score)
            else:
                unevaluated += 1

        except Exception as e:
            print(f"Error reading {response_file}: {e}")

    return {
        "total_files": total_files,
        "evaluated": evaluated,
        "unevaluated": unevaluated,
        "all_scores": scores,
        "by_category": dict(by_category)
    }

def main():
    print("=" * 70)
    print("TRAINING DATA READINESS CHECK")
    print("=" * 70)
    print()

    stats = check_responses()

    print(f"Total response files: {stats['total_files']}")
    print(f"Evaluated: {stats['evaluated']}")
    print(f"Unevaluated: {stats['unevaluated']}")
    print()

    if stats['all_scores']:
        scores = stats['all_scores']
        avg = sum(scores) / len(scores)

        # Training quality thresholds
        excellent = sum(1 for s in scores if s >= 35)
        good = sum(1 for s in scores if 32 <= s < 35)
        acceptable = sum(1 for s in scores if 28 <= s < 32)
        low = sum(1 for s in scores if s < 28)

        print("=" * 70)
        print("SCORE DISTRIBUTION")
        print("=" * 70)
        print(f"Average: {avg:.1f}/40")
        print(f"Range: {min(scores)}-{max(scores)}/40")
        print()
        print(f"Excellent (≥35):   {excellent:4d} ({excellent/len(scores)*100:5.1f}%)")
        print(f"Good (32-34):      {good:4d} ({good/len(scores)*100:5.1f}%)")
        print(f"Acceptable (28-31): {acceptable:4d} ({acceptable/len(scores)*100:5.1f}%)")
        print(f"Low (<28):         {low:4d} ({low/len(scores)*100:5.1f}%)")
        print()

        # Training data estimate
        training_ready = excellent + good
        print(f"TRAINING-READY (≥32/40): {training_ready} examples")
        print()

    print("=" * 70)
    print("BY CATEGORY")
    print("=" * 70)
    print(f"{'Category':<30} {'Total':>6} {'Eval':>6} {'Avg':>6}")
    print("-" * 70)

    for category in sorted(stats['by_category'].keys()):
        cat_data = stats['by_category'][category]
        total = cat_data['total']
        evaluated = cat_data['evaluated']

        if cat_data['scores']:
            avg = sum(cat_data['scores']) / len(cat_data['scores'])
            print(f"{category:<30} {total:6d} {evaluated:6d} {avg:6.1f}")
        else:
            print(f"{category:<30} {total:6d} {evaluated:6d}    N/A")

    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)

    if stats['unevaluated'] > 0:
        print(f"1. Evaluate {stats['unevaluated']} remaining responses")
        print(f"2. Export training data (≥32/40)")
        print(f"3. Train model")
    else:
        print(f"✓ All responses evaluated!")
        print(f"→ Ready to export training data and train model")

if __name__ == "__main__":
    main()
