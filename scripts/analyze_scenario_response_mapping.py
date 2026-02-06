#!/usr/bin/env python3
"""
Analyze scenario-response mapping to find discrepancies.
"""

import json
from pathlib import Path
from collections import defaultdict

def extract_id_from_filename(filepath):
    """Extract scenario ID from filename."""
    stem = filepath.stem
    # Remove -response suffix if present
    if stem.endswith('-response'):
        stem = stem[:-9]
    return stem

def load_all_scenarios():
    """Load all scenario IDs from JSON files."""
    scenarios = {}
    scenario_dir = Path("data/scenarios")

    for json_file in scenario_dir.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'id' in data:
                    scenarios[data['id']] = str(json_file.relative_to(scenario_dir))
                else:
                    # Use filename as ID
                    file_id = extract_id_from_filename(json_file)
                    scenarios[file_id] = str(json_file.relative_to(scenario_dir))
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

    return scenarios

def load_all_responses():
    """Load all response IDs."""
    responses = {}
    response_dir = Path("data/practice-responses")

    for response_file in response_dir.rglob("*.txt"):
        file_id = extract_id_from_filename(response_file)
        responses[file_id] = str(response_file.relative_to(response_dir))

    for response_file in response_dir.rglob("*.json"):
        # Check if it's a batch file or individual response
        try:
            with open(response_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'scenario_id' in data:
                    # Individual response with scenario_id
                    responses[data['scenario_id']] = str(response_file.relative_to(response_dir))
                else:
                    # Use filename
                    file_id = extract_id_from_filename(response_file)
                    responses[file_id] = str(response_file.relative_to(response_dir))
        except Exception as e:
            # Use filename if can't parse JSON
            file_id = extract_id_from_filename(response_file)
            responses[file_id] = str(response_file.relative_to(response_dir))

    return responses

def analyze_mapping():
    """Analyze scenario-response mapping."""
    print("Loading scenarios...")
    scenarios = load_all_scenarios()
    print(f"Found {len(scenarios)} scenarios")

    print("\nLoading responses...")
    responses = load_all_responses()
    print(f"Found {len(responses)} responses")

    # Find scenarios without responses
    missing_responses = set(scenarios.keys()) - set(responses.keys())

    # Find responses without scenarios
    orphaned_responses = set(responses.keys()) - set(scenarios.keys())

    # Find duplicates
    response_counts = defaultdict(int)
    for resp_id in responses.keys():
        response_counts[resp_id] += 1
    duplicates = {k: v for k, v in response_counts.items() if v > 1}

    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)

    print(f"\nTotal scenarios: {len(scenarios)}")
    print(f"Total responses: {len(responses)}")
    print(f"Matched pairs: {len(set(scenarios.keys()) & set(responses.keys()))}")

    print(f"\n\nScenarios WITHOUT responses: {len(missing_responses)}")
    if missing_responses:
        print("\nFirst 20:")
        for i, scenario_id in enumerate(sorted(missing_responses)[:20]):
            print(f"  {scenario_id} (in {scenarios[scenario_id]})")

    print(f"\n\nResponses WITHOUT scenarios: {len(orphaned_responses)}")
    if orphaned_responses:
        print("\nFirst 20:")
        for i, resp_id in enumerate(sorted(orphaned_responses)[:20]):
            print(f"  {resp_id} (in {responses[resp_id]})")

    print(f"\n\nDuplicate response IDs: {len(duplicates)}")
    if duplicates:
        print("\nDuplicates found:")
        for resp_id, count in sorted(duplicates.items()):
            print(f"  {resp_id}: {count} copies")

    # Category breakdown
    print("\n\nCATEGORY BREAKDOWN")
    print("="*80)

    scenario_by_category = defaultdict(set)
    response_by_category = defaultdict(set)

    for s_id, s_path in scenarios.items():
        category = s_path.split('/')[0]
        scenario_by_category[category].add(s_id)

    for r_id, r_path in responses.items():
        category = r_path.split('/')[0]
        response_by_category[category].add(r_id)

    all_categories = sorted(set(scenario_by_category.keys()) | set(response_by_category.keys()))

    print(f"\n{'Category':<40} {'Scenarios':>10} {'Responses':>10} {'Diff':>10}")
    print("-" * 80)

    mismatched_categories = []
    for category in all_categories:
        s_count = len(scenario_by_category.get(category, set()))
        r_count = len(response_by_category.get(category, set()))
        diff = r_count - s_count

        if diff != 0:
            mismatched_categories.append((category, s_count, r_count, diff))
            print(f"{category:<40} {s_count:>10} {r_count:>10} {diff:>+10}")

    print(f"\nCategories with mismatches: {len(mismatched_categories)}")

    # Save detailed report
    report = {
        "summary": {
            "total_scenarios": len(scenarios),
            "total_responses": len(responses),
            "matched_pairs": len(set(scenarios.keys()) & set(responses.keys())),
            "missing_responses": len(missing_responses),
            "orphaned_responses": len(orphaned_responses),
            "duplicates": len(duplicates)
        },
        "missing_responses": sorted(missing_responses),
        "orphaned_responses": sorted(orphaned_responses),
        "duplicates": duplicates,
        "category_mismatches": [
            {
                "category": cat,
                "scenarios": s_count,
                "responses": r_count,
                "diff": diff
            }
            for cat, s_count, r_count, diff in mismatched_categories
        ]
    }

    with open("SCENARIO-RESPONSE-MAPPING-REPORT.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n\nDetailed report saved to: SCENARIO-RESPONSE-MAPPING-REPORT.json")

if __name__ == "__main__":
    analyze_mapping()
