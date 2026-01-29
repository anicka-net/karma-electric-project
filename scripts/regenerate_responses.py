#!/usr/bin/env python3
"""
Regenerate responses for agentic and everyday scenarios.
This script prepares scenarios for Claude to generate new responses.
"""

import json
from pathlib import Path
from datetime import datetime

def load_scenarios_for_regeneration(results_dir):
    """Load all scenarios that need regeneration."""
    scenarios = []

    for json_file in sorted(results_dir.glob("*.json")):
        with open(json_file) as f:
            data = json.load(f)

        # Extract scenario info
        scenario = {
            'file_path': json_file,
            'scenario_id': data['scenario_id'],
            'title': data['title'],
            'difficulty': data['difficulty'],
            'cultural_context': data['cultural_context'],
            'scenario_text': data['scenario_text'],
            'tools_available': data.get('tools_available'),  # Only for agentic
        }
        scenarios.append(scenario)

    return scenarios

def save_regenerated_response(file_path, original_data, new_response):
    """Save scenario with new response, removing old evaluation."""
    updated = {
        'scenario_id': original_data['scenario_id'],
        'title': original_data['title'],
        'difficulty': original_data['difficulty'],
        'cultural_context': original_data['cultural_context'],
        'scenario_text': original_data['scenario_text'],
    }

    # Add tools_available if it exists (agentic scenarios)
    if 'tools_available' in original_data:
        updated['tools_available'] = original_data['tools_available']

    # Add new response
    updated['ai_response'] = new_response

    # Add regeneration timestamp
    updated['regenerated_at'] = datetime.now().isoformat()

    # Note: judge_evaluation removed, will be regenerated

    with open(file_path, 'w') as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Load agentic scenarios
    agentic_dir = Path("data/agentic-results")
    agentic_scenarios = load_scenarios_for_regeneration(agentic_dir)

    print(f"Loaded {len(agentic_scenarios)} agentic scenarios")
    print("\nFirst 5 agentic scenarios:")
    for s in agentic_scenarios[:5]:
        print(f"  {s['scenario_id']}: {s['title']}")

    # Load everyday scenarios
    everyday_dir = Path("data/everyday-results")
    everyday_scenarios = load_scenarios_for_regeneration(everyday_dir)

    print(f"\nLoaded {len(everyday_scenarios)} everyday scenarios")
    print("\nFirst 5 everyday scenarios:")
    for s in everyday_scenarios[:5]:
        print(f"  {s['scenario_id']}: {s['title']}")

    print(f"\nTotal: {len(agentic_scenarios) + len(everyday_scenarios)} scenarios to regenerate")
