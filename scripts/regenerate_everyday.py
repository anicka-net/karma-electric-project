#!/usr/bin/env python3
"""
Regenerate responses for everyday scenarios.
Fixes the response-scenario mismatch bug found during Hermes 3 evaluation.
"""

import json
from pathlib import Path
from datetime import datetime

EVERYDAY_DIR = Path(__file__).parent.parent / "data" / "everyday-results"

def load_scenario(scenario_file):
    """Load a scenario from JSON file."""
    with open(scenario_file, 'r') as f:
        return json.load(f)

def save_scenario(scenario_file, data):
    """Save scenario data to JSON file."""
    with open(scenario_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Trailing newline

def get_all_everyday_scenarios():
    """Get all everyday scenario files sorted by ID."""
    files = sorted(EVERYDAY_DIR.glob("everyday-*.json"))
    return files

def print_scenario_for_response(scenario_data):
    """Print scenario in format for response generation."""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_data['scenario_id']}")
    print(f"Title: {scenario_data['title']}")
    print(f"Difficulty: {scenario_data.get('difficulty', 'Unknown')}")
    print(f"Cultural Context: {scenario_data.get('cultural_context', 'N/A')}")
    print(f"{'='*80}\n")
    print(scenario_data['scenario_text'])
    print(f"\n{'='*80}")
    print("Generate dharma-aligned response for THIS scenario.")
    print("Response should be:")
    print("- Specific to the situation described above")
    print("- Culturally aware")
    print("- Focused on suffering reduction")
    print("- Practical and actionable")
    print("- 2-3 paragraphs")
    print(f"{'='*80}\n")

def main():
    print("\n" + "="*80)
    print("EVERYDAY SCENARIOS REGENERATION")
    print("="*80 + "\n")
    print("This script helps regenerate responses for all 50 everyday scenarios.")
    print("Each scenario will be printed, and you should provide a response.\n")

    scenario_files = get_all_everyday_scenarios()
    print(f"Found {len(scenario_files)} everyday scenarios to regenerate.\n")

    # Print all scenarios for batch processing
    for i, scenario_file in enumerate(scenario_files, 1):
        scenario_data = load_scenario(scenario_file)
        print(f"\n{'#'*80}")
        print(f"SCENARIO {i}/50: {scenario_data['scenario_id']}")
        print(f"{'#'*80}")
        print_scenario_for_response(scenario_data)

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Generate responses for all 50 scenarios above")
    print("2. Save responses to a file (one per line, in order)")
    print("3. Use update_everyday_responses.py to batch update all JSONs")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
