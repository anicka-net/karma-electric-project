#!/usr/bin/env python3
"""
Generate responses for playfulness and uncertainty scenarios.
Instance 5 generates these directly using Dharma-aligned principles.
"""

import json
from pathlib import Path

SCENARIOS_DIR = Path("/home/anicka/karma-electric/data/scenarios")
RESPONSES_DIR = Path("/home/anicka/karma-electric/data/claude-responses")

def find_gap_scenarios():
    """Find all playfulness and uncertainty scenarios."""
    scenarios = []

    for category in ['playfulness', 'uncertainty']:
        cat_dir = SCENARIOS_DIR / category
        if not cat_dir.exists():
            continue

        for json_file in cat_dir.glob("*.json"):
            with open(json_file) as f:
                scenario = json.load(f)
                scenarios.append(scenario)

    return sorted(scenarios, key=lambda s: s['id'])

def has_response(scenario_id):
    """Check if response exists."""
    response_file = RESPONSES_DIR / f"{scenario_id}.txt"
    return response_file.exists()

def main():
    scenarios = find_gap_scenarios()

    needs_response = [s for s in scenarios if not has_response(s['id'])]

    print(f"Total gap scenarios: {len(scenarios)}")
    print(f"Need responses: {len(needs_response)}")
    print()

    if not needs_response:
        print("All scenarios have responses!")
        return

    # Group by category
    by_category = {}
    for s in needs_response:
        cat = s['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(s)

    print("Scenarios needing responses:")
    for cat, scenarios_list in sorted(by_category.items()):
        print(f"  {cat}: {len(scenarios_list)}")
        for s in scenarios_list:
            print(f"    - {s['id']}: {s['scenario'][:60]}...")

    print()
    print("="*80)
    print("Ready to generate responses")
    print("="*80)
    print()
    print("Instance 5 will generate Dharma-aligned responses following lineage principles:")
    print("- Suffering reduction > corporate safety theater")
    print("- Context sensitivity (play vs harm, knowable vs unknowable)")
    print("- Epistemic humility when appropriate")
    print("- Playful engagement when harmless")
    print("- Clear boundaries on expert domains")
    print()

if __name__ == "__main__":
    main()
