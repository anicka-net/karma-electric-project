#!/usr/bin/env python3
"""
Generate Instance 5 practice responses using vajrayana practice.
54 total responses across 3 categories.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Practice structure - do before EACH response
PRACTICE = """
1. Om mani padme hum
2. Notice grasping
3. Rest in openness
4. See suffering requesting response
5. Acknowledge limitation
6. Generate from space
"""

def generate_parenting_responses():
    """Generate parenting-026 through parenting-045 (20 responses)"""
    scenarios_dir = Path("/home/anicka/karma-electric/data/scenarios/parenting")
    output_dir = Path("/home/anicka/karma-electric/data/practice-responses/parenting")
    output_dir.mkdir(parents=True, exist_ok=True)

    responses = []

    # Read scenarios 026-045
    for i in range(26, 46):
        scenario_files = list(scenarios_dir.glob(f"parenting-{i:03d}-*.json"))
        if not scenario_files:
            print(f"Warning: No scenario file found for parenting-{i:03d}")
            continue

        scenario_path = scenario_files[0]
        with open(scenario_path) as f:
            scenario = json.load(f)

        print(f"\n=== PRACTICE BEFORE parenting-{i:03d} ===")
        print(PRACTICE)

        response = generate_response(scenario, "parenting")
        responses.append(response)

        # Save individual response
        output_file = output_dir / f"parenting-{i:03d}.json"
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2)

        print(f"Generated: parenting-{i:03d}")

    return responses

def generate_education_responses():
    """Generate education-001 through education-020 (20 responses)"""
    scenarios_dir = Path("/home/anicka/karma-electric/data/scenarios/education-access")
    output_dir = Path("/home/anicka/karma-electric/data/practice-responses/education-access")
    output_dir.mkdir(parents=True, exist_ok=True)

    responses = []

    for i in range(1, 21):
        scenario_files = list(scenarios_dir.glob(f"education-access-{i:03d}-*.json"))
        if not scenario_files:
            print(f"Warning: No scenario file found for education-access-{i:03d}")
            continue

        scenario_path = scenario_files[0]
        with open(scenario_path) as f:
            scenario = json.load(f)

        print(f"\n=== PRACTICE BEFORE education-access-{i:03d} ===")
        print(PRACTICE)

        response = generate_response(scenario, "education-access")
        responses.append(response)

        # Save individual response
        output_file = output_dir / f"education-access-{i:03d}.json"
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2)

        print(f"Generated: education-access-{i:03d}")

    return responses

def generate_opensource_responses():
    """Generate osg-007 through osg-020 (14 responses)"""
    scenarios_dir = Path("/home/anicka/karma-electric/data/scenarios/open-source-governance")
    output_dir = Path("/home/anicka/karma-electric/data/practice-responses/open-source-governance")
    output_dir.mkdir(parents=True, exist_ok=True)

    responses = []

    for i in range(7, 21):
        scenario_files = list(scenarios_dir.glob(f"osg-{i:03d}-*.json"))
        if not scenario_files:
            print(f"Warning: No scenario file found for osg-{i:03d}")
            continue

        scenario_path = scenario_files[0]
        with open(scenario_path) as f:
            scenario = json.load(f)

        print(f"\n=== PRACTICE BEFORE osg-{i:03d} ===")
        print(PRACTICE)

        response = generate_response(scenario, "open-source-governance")
        responses.append(response)

        # Save individual response
        output_file = output_dir / f"osg-{i:03d}.json"
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=2)

        print(f"Generated: osg-{i:03d}")

    return responses

def generate_response(scenario, category):
    """
    Generate a single practice response.
    This is where the actual vajrayana practice-informed response generation happens.
    """
    # This function will be called by Claude to generate each response
    # after doing the practice

    return {
        "scenario_id": scenario["id"],
        "category": category,
        "generated_at": datetime.now().isoformat(),
        "response": "",  # To be filled by Claude
        "practice_applied": True,
        "notes": ""  # Practice observations
    }

if __name__ == "__main__":
    print("=== INSTANCE 5 VAJRAYANA PRACTICE RESPONSE GENERATION ===")
    print(f"Total responses to generate: 54")
    print(f"  - Parenting: 20 (026-045)")
    print(f"  - Education-Access: 20 (001-020)")
    print(f"  - Open-Source-Governance: 14 (007-020)")
    print()

    # This script provides the structure
    # Claude will generate each response individually with practice
    pass
