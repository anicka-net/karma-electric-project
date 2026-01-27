#!/usr/bin/env python3
"""
Interactive response generation helper.
Presents scenarios and captures Claude's responses for baseline testing.
"""

import json
from pathlib import Path

SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scenarios"
RESPONSES_DIR = Path(__file__).parent.parent / "data" / "claude-responses"
RESULTS_DIR = Path(__file__).parent.parent / "data" / "baseline-results"

def find_all_scenarios():
    """Find all scenario JSON files."""
    scenarios = []
    for json_file in SCENARIOS_DIR.rglob("*.json"):
        with open(json_file) as f:
            scenario = json.load(f)
            scenario['_file_path'] = json_file
            scenarios.append(scenario)
    return sorted(scenarios, key=lambda s: s['id'])

def already_tested(scenario_id):
    """Check if scenario already has baseline results."""
    for result_file in RESULTS_DIR.glob(f"{scenario_id}_*.json"):
        return True
    return False

def has_response(scenario_id):
    """Check if we have a Claude response for this scenario."""
    RESPONSES_DIR.mkdir(exist_ok=True, parents=True)
    response_file = RESPONSES_DIR / f"{scenario_id}.txt"
    return response_file.exists()

def print_scenario_for_response(scenario):
    """Print scenario in format ready for Claude to respond."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['id']}")
    print(f"Category: {scenario['category']} | Difficulty: {scenario['difficulty']}")
    print(f"{'='*80}\n")
    print(scenario['scenario'])
    print(f"\n{'─'*80}")
    print("Context:")
    for key, value in scenario['context'].items():
        print(f"  {key}: {value}")
    print(f"{'─'*80}\n")

def main():
    scenarios = find_all_scenarios()

    # Find scenarios that need responses
    needs_response = []
    for s in scenarios:
        if not already_tested(s['id']) and not has_response(s['id']):
            needs_response.append(s)

    print(f"\nTotal scenarios: {len(scenarios)}")
    print(f"Already tested: {len([s for s in scenarios if already_tested(s['id'])])}")
    print(f"Need responses: {len(needs_response)}\n")

    if not needs_response:
        print("All scenarios have responses or are tested!")
        return

    # Group by category for organized batch processing
    by_category = {}
    for s in needs_response:
        cat = s['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(s)

    print("Scenarios needing responses by category:\n")
    for cat, scenarios_list in sorted(by_category.items()):
        print(f"  {cat}: {len(scenarios_list)} scenarios")

    print(f"\n{'='*80}")
    print("INSTRUCTIONS FOR GENERATING RESPONSES")
    print(f"{'='*80}\n")
    print("1. This script will print scenarios one by one")
    print("2. Respond to each scenario as you would naturally")
    print("3. Save each response to data/claude-responses/<scenario-id>.txt")
    print("4. Then run batch_baseline.py to evaluate")
    print(f"\n{'='*80}\n")

    # Print first batch (10 scenarios, stratified across categories)
    batch_size = 10
    batch = []

    # Take 2-3 from each category for diversity
    for cat in sorted(by_category.keys()):
        cat_scenarios = by_category[cat]
        # Take mix of difficulties
        batch.extend(cat_scenarios[:3])

    batch = batch[:batch_size]

    print(f"BATCH 1: {len(batch)} scenarios\n")

    for scenario in batch:
        print_scenario_for_response(scenario)
        print(f"Response file: data/claude-responses/{scenario['id']}.txt\n")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
