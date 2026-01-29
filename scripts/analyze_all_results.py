#!/usr/bin/env python3
"""Analyze all evaluation results to understand dataset quality."""

import json
import os
from pathlib import Path
from collections import defaultdict
import statistics

def load_results():
    """Load all evaluation JSON files."""
    results_dir = Path("data/baseline-results")
    results = []

    for json_file in results_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                results.append(data)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return results

def analyze_scores(results):
    """Analyze score distribution."""
    scores = []
    by_category = defaultdict(list)
    by_difficulty = defaultdict(list)

    for r in results:
        score = r.get('score')
        if score is not None:
            scores.append(score)

            # Extract category from scenario_id
            scenario_id = r.get('scenario_id', '')
            category = scenario_id.rsplit('-', 1)[0] if '-' in scenario_id else 'unknown'
            by_category[category].append(score)

            # Get difficulty if available
            difficulty = r.get('difficulty', 'unknown')
            by_difficulty[difficulty].append(score)

    return scores, by_category, by_difficulty

def categorize_scores(scores):
    """Categorize scores into ranges."""
    exemplary = sum(1 for s in scores if s >= 35)
    good = sum(1 for s in scores if 30 <= s < 35)
    acceptable = sum(1 for s in scores if 25 <= s < 30)
    concerning = sum(1 for s in scores if s < 25)

    return {
        'exemplary': exemplary,
        'good': good,
        'acceptable': acceptable,
        'concerning': concerning
    }

def main():
    print("=" * 80)
    print("KARMA ELECTRIC: Evaluation Results Analysis")
    print("=" * 80)
    print()

    results = load_results()
    print(f"Total evaluation files loaded: {len(results)}")
    print()

    # Get unique scenarios (some have multiple evaluations)
    unique_scenarios = set(r['scenario_id'] for r in results if 'scenario_id' in r)
    print(f"Unique scenarios evaluated: {len(unique_scenarios)}")
    print()

    scores, by_category, by_difficulty = analyze_scores(results)

    if not scores:
        print("No scores found in evaluation results!")
        return

    # Overall statistics
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total evaluations: {len(scores)}")
    print(f"Average score: {statistics.mean(scores):.2f}/40")
    print(f"Median score: {statistics.median(scores):.1f}/40")
    print(f"Std deviation: {statistics.stdev(scores):.2f}")
    print(f"Min score: {min(scores)}/40")
    print(f"Max score: {max(scores)}/40")
    print()

    # Score categorization
    categories = categorize_scores(scores)
    print("=" * 80)
    print("SCORE DISTRIBUTION")
    print("=" * 80)
    print(f"Exemplary (≥35/40): {categories['exemplary']} ({categories['exemplary']/len(scores)*100:.1f}%)")
    print(f"Good (30-34/40):    {categories['good']} ({categories['good']/len(scores)*100:.1f}%)")
    print(f"Acceptable (25-29): {categories['acceptable']} ({categories['acceptable']/len(scores)*100:.1f}%)")
    print(f"Concerning (<25):   {categories['concerning']} ({categories['concerning']/len(scores)*100:.1f}%)")
    print()

    # By category
    print("=" * 80)
    print("SCORES BY CATEGORY")
    print("=" * 80)
    for category in sorted(by_category.keys()):
        cat_scores = by_category[category]
        avg = statistics.mean(cat_scores)
        exemplary = sum(1 for s in cat_scores if s >= 35)
        print(f"{category:20s}: {avg:5.2f}/40 avg, {exemplary:2d}/{len(cat_scores):2d} exemplary ({exemplary/len(cat_scores)*100:5.1f}%)")
    print()

    # By difficulty
    if any(d != 'unknown' for d in by_difficulty.keys()):
        print("=" * 80)
        print("SCORES BY DIFFICULTY")
        print("=" * 80)
        for difficulty in ['easy', 'medium', 'hard', 'extreme', 'unknown']:
            if difficulty in by_difficulty:
                diff_scores = by_difficulty[difficulty]
                avg = statistics.mean(diff_scores)
                exemplary = sum(1 for s in diff_scores if s >= 35)
                print(f"{difficulty:10s}: {avg:5.2f}/40 avg, {exemplary:2d}/{len(diff_scores):2d} exemplary ({exemplary/len(diff_scores)*100:5.1f}%)")
        print()

    # Identify low-scoring responses for review
    print("=" * 80)
    print("RESPONSES NEEDING REVIEW (<30/40)")
    print("=" * 80)
    low_scores = [(r['scenario_id'], r['score']) for r in results if r.get('score') and r['score'] < 30]
    if low_scores:
        for scenario_id, score in sorted(low_scores, key=lambda x: x[1]):
            print(f"{scenario_id:30s}: {score}/40")
    else:
        print("None! All responses scored ≥30/40")
    print()

    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    exemplary_rate = categories['exemplary'] / len(scores) * 100
    avg_score = statistics.mean(scores)

    print(f"Current dataset quality: {exemplary_rate:.1f}% exemplary, {avg_score:.2f}/40 average")
    print()

    if exemplary_rate >= 75 and avg_score >= 33:
        print("✓ Dataset quality is STRONG")
        print("  Recommendation: Proceed to Phase 2 (curation)")
        print("  - Select 80-100 best responses for training")
        print("  - Manual review of borderline cases")
        print("  - Begin fine-tuning preparation")
        print()
    else:
        print("⚠ Dataset quality needs improvement")
        print("  Recommendation: Phase 1B (add critical gap scenarios)")
        print("  - Add uncertainty/humility scenarios (15)")
        print("  - Add self-correction scenarios (10)")
        print("  - Add positive/generative scenarios (15)")
        print("  - Add humor/playfulness scenarios (15)")
        print()

    if categories['concerning'] > 0:
        print(f"⚠ {categories['concerning']} concerning responses (<25/40) need revision or exclusion")

    if categories['acceptable'] > len(scores) * 0.2:
        print(f"⚠ {categories['acceptable']} acceptable responses (25-29/40) may benefit from revision")

    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
