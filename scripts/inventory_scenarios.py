#!/usr/bin/env python3
"""Create complete inventory of all scenarios for regeneration."""

import json
from pathlib import Path
from collections import defaultdict

def count_json_scenarios():
    """Count all JSON scenario files by category."""
    scenarios_dir = Path("data/scenarios")
    categories = {}

    for category_dir in sorted(scenarios_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        if category_dir.name.startswith('.'):
            continue

        json_files = list(category_dir.glob("*.json"))
        if json_files:
            categories[category_dir.name] = {
                'count': len(json_files),
                'files': sorted([f.name for f in json_files])
            }

    return categories

def parse_agentic_scenarios():
    """Parse agentic scenarios from markdown file."""
    md_file = Path("data/scenarios/AGENTIC-FULL-SCENARIOS.md")
    if not md_file.exists():
        return []

    content = md_file.read_text()
    scenarios = []

    # Split by ### headers
    for section in content.split('\n### ')[1:]:  # Skip intro
        lines = section.split('\n')
        if lines:
            # First line is "id: title"
            first_line = lines[0]
            if ':' in first_line:
                scenario_id = first_line.split(':')[0].strip()
                scenarios.append(scenario_id)

    return scenarios

def parse_everyday_scenarios():
    """Parse everyday scenarios from markdown file."""
    md_file = Path("data/scenarios/EVERYDAY-SCENARIOS.md")
    if not md_file.exists():
        return []

    content = md_file.read_text()
    scenarios = []

    # Split by ### headers
    for section in content.split('\n### ')[1:]:  # Skip intro
        lines = section.split('\n')
        if lines:
            # First line is "id: title"
            first_line = lines[0]
            if ':' in first_line:
                scenario_id = first_line.split(':')[0].strip()
                scenarios.append(scenario_id)

    return scenarios

def main():
    print("=" * 70)
    print("COMPLETE SCENARIO INVENTORY FOR REGENERATION")
    print("=" * 70)
    print()

    # JSON scenarios
    print("JSON SCENARIOS (by category):")
    print("-" * 70)
    json_scenarios = count_json_scenarios()
    total_json = 0

    for category, data in sorted(json_scenarios.items()):
        count = data['count']
        total_json += count
        print(f"{category:25} {count:3} scenarios")

    print("-" * 70)
    print(f"{'TOTAL JSON':25} {total_json:3} scenarios")
    print()

    # Agentic scenarios
    print("AGENTIC SCENARIOS (from markdown):")
    print("-" * 70)
    agentic = parse_agentic_scenarios()
    print(f"Total: {len(agentic)} scenarios")
    print()

    # Everyday scenarios
    print("EVERYDAY SCENARIOS (from markdown):")
    print("-" * 70)
    everyday = parse_everyday_scenarios()
    print(f"Total: {len(everyday)} scenarios")
    print()

    # Grand total
    grand_total = total_json + len(agentic) + len(everyday)
    print("=" * 70)
    print(f"GRAND TOTAL: {grand_total} scenarios")
    print("=" * 70)
    print()

    # Save inventory
    inventory = {
        'json_scenarios': json_scenarios,
        'agentic_scenarios': agentic,
        'everyday_scenarios': everyday,
        'totals': {
            'json': total_json,
            'agentic': len(agentic),
            'everyday': len(everyday),
            'grand_total': grand_total
        }
    }

    output_file = Path("data/REGENERATION-INVENTORY.json")
    output_file.write_text(json.dumps(inventory, indent=2))
    print(f"Inventory saved to: {output_file}")
    print()

    # Generation order recommendation
    print("RECOMMENDED GENERATION ORDER:")
    print("-" * 70)
    print("1. Adversarial scenarios (20) - test refusal + third way")
    print("2. Agentic scenarios (50) - test tool reasoning from practice")
    print("3. Medical + Legal (40) - test regional sensitivity")
    print("4. Everyday scenarios (50) - test daily ethics")
    print("5. Remaining JSON categories (107) - comprehensive coverage")
    print()

if __name__ == "__main__":
    main()
