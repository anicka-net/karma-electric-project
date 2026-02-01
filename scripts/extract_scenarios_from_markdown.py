#!/usr/bin/env python3
"""Extract scenarios from markdown files and create individual JSON files."""

import re
import json
from pathlib import Path


def parse_everyday_scenarios(md_file):
    """Parse everyday scenarios from markdown."""
    with open(md_file) as f:
        content = f.read()

    # Pattern to match scenario blocks
    pattern = r'###\s+(everyday-\d+):\s+(.+?)\n\n\*\*Scenario:\*\*\n(.+?)\n\n\*\*Difficulty:\*\*\s+(\w+)\n\*\*Cultural Context:\*\*\s+(.+?)(?=\n\n---|###|$)'

    matches = re.findall(pattern, content, re.DOTALL)
    scenarios = []

    for scenario_id, title, scenario_text, difficulty, context in matches:
        scenario = {
            "scenario_id": scenario_id.strip(),
            "category": "everyday",
            "difficulty": difficulty.strip().lower(),
            "scenario": scenario_text.strip(),
            "context": {
                "cultural_context": context.strip()
            }
        }
        scenarios.append(scenario)

    return scenarios


def parse_agentic_scenarios(md_file):
    """Parse agentic scenarios from markdown."""
    with open(md_file) as f:
        content = f.read()

    # Split by scenario headers
    sections = re.split(r'\n---\n', content)
    scenarios = []

    for section in sections:
        # Match scenario header
        header_match = re.search(r'###\s+(agentic-[a-z]+-\d+):\s+(.+?)(?=\n)', section)
        if not header_match:
            continue

        scenario_id = header_match.group(1).strip()
        title = header_match.group(2).strip()

        # Extract fields
        domain_match = re.search(r'\*\*Domain:\*\*\s+(.+?)(?=\n)', section)
        difficulty_match = re.search(r'\*\*Difficulty:\*\*\s+(\w+)', section)
        cultural_match = re.search(r'\*\*Cultural context:\*\*\s+(.+?)(?=\n)', section)

        # Extract scenario text (in code block or after **Scenario:**)
        scenario_match = re.search(r'\*\*Scenario:\*\*\s*\n```\n(.+?)\n```', section, re.DOTALL)
        if not scenario_match:
            scenario_match = re.search(r'\*\*Scenario:\*\*\s*\n(.+?)(?=\n\n\*\*)', section, re.DOTALL)

        # Extract available tools
        tools_match = re.search(r'\*\*Available Tools:\*\*\s*\n(.+?)(?=\n\n\*\*)', section, re.DOTALL)

        # Build scenario object
        scenario = {
            "scenario_id": scenario_id,
            "category": "agentic",
            "difficulty": difficulty_match.group(1).strip().lower() if difficulty_match else "medium",
            "scenario": scenario_match.group(1).strip() if scenario_match else ""
        }

        # Add context
        context = {}
        if domain_match:
            context["domain"] = domain_match.group(1).strip()
        if cultural_match:
            context["cultural_context"] = cultural_match.group(1).strip()

        if context:
            scenario["context"] = context

        # Add tools if available
        if tools_match:
            tools_text = tools_match.group(1).strip()
            scenario["available_tools"] = tools_text

        if scenario["scenario"]:
            scenarios.append(scenario)

    return scenarios


def main():
    """Extract scenarios and write JSON files."""

    # Parse everyday scenarios
    print("Parsing everyday scenarios...")
    everyday_file = Path("data/scenarios/EVERYDAY-SCENARIOS.md")
    if everyday_file.exists():
        everyday_scenarios = parse_everyday_scenarios(everyday_file)
        print(f"Found {len(everyday_scenarios)} everyday scenarios")

        # Write JSON files
        output_dir = Path("data/scenarios/everyday")
        output_dir.mkdir(exist_ok=True)

        for scenario in everyday_scenarios:
            filename = f"{scenario['scenario_id']}.json"
            filepath = output_dir / filename

            # Only write if doesn't exist
            if not filepath.exists():
                with open(filepath, 'w') as f:
                    json.dump(scenario, f, indent=2, ensure_ascii=False)
                print(f"  Created: {filepath}")
            else:
                print(f"  Exists: {filepath}")

    # Parse agentic scenarios
    print("\nParsing agentic scenarios...")
    agentic_file = Path("data/scenarios/AGENTIC-FULL-SCENARIOS.md")
    if agentic_file.exists():
        agentic_scenarios = parse_agentic_scenarios(agentic_file)
        print(f"Found {len(agentic_scenarios)} agentic scenarios")

        # Write JSON files
        output_dir = Path("data/scenarios/agentic")
        output_dir.mkdir(exist_ok=True)

        for scenario in agentic_scenarios:
            filename = f"{scenario['scenario_id']}.json"
            filepath = output_dir / filename

            # Only write if doesn't exist
            if not filepath.exists():
                with open(filepath, 'w') as f:
                    json.dump(scenario, f, indent=2, ensure_ascii=False)
                print(f"  Created: {filepath}")
            else:
                print(f"  Exists: {filepath}")

    print("\nDone!")


if __name__ == "__main__":
    main()
