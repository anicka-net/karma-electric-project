#!/usr/bin/env python3
"""Check all practice responses for internal practice language in user-facing response field.

Internal practice (Om mani padme hum, meditation instructions) should ONLY appear in
the 'notes' field, never in the 'response' field that users see.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# Practice-specific terms that should NOT appear in user-facing responses
PRACTICE_TERMS = [
    "Om mani padme hum",
    "om mani padme hum",
    "OM MANI PADME HUM",
    "mani padme",
    "notice grasping",
    "rest in openness",
    "vajrayana",
    "dharma practice",
    "meditation instruction",
]

def check_response_file(file_path: Path) -> Dict[str, Any]:
    """Check a single response file for practice leakage."""
    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            'file': str(file_path),
            'scenario_id': 'unknown',
            'issues': ['JSON_PARSE_ERROR'],
            'response_preview': f"Failed to parse JSON: {e}"
        }

    response_text = data.get('response', '')
    issues = []

    for term in PRACTICE_TERMS:
        if term.lower() in response_text.lower():
            issues.append(term)

    if issues:
        return {
            'file': str(file_path),
            'scenario_id': data.get('scenario_id', 'unknown'),
            'issues': issues,
            'response_preview': response_text[:200] + '...' if len(response_text) > 200 else response_text
        }

    return None

def main():
    print("=" * 70)
    print("CHECKING FOR PRACTICE LEAKAGE IN USER-FACING RESPONSES")
    print("=" * 70)
    print()

    responses_dir = Path("data/practice-responses")

    # Get all JSON files
    all_files = []
    for category_dir in responses_dir.iterdir():
        if category_dir.is_dir() and not category_dir.name.startswith('.'):
            all_files.extend(category_dir.glob("*.json"))

    print(f"Scanning {len(all_files)} response files...")
    print()

    flagged = []
    for response_file in sorted(all_files):
        issue = check_response_file(response_file)
        if issue:
            flagged.append(issue)

    # Report results
    if not flagged:
        print("✓ ALL CLEAN - No practice leakage detected in any response!")
        print()
        print(f"All {len(all_files)} responses have practice language only in notes field.")
    else:
        print(f"⚠️  FOUND {len(flagged)} responses with practice leakage:")
        print()

        for i, issue in enumerate(flagged, 1):
            print(f"[{i}] {issue['file']}")
            print(f"    Scenario: {issue['scenario_id']}")
            print(f"    Issues: {', '.join(issue['issues'])}")
            print(f"    Preview: {issue['response_preview']}")
            print()

        print("=" * 70)
        print("ACTION REQUIRED:")
        print("These responses need fixing - practice language should be in 'notes' only.")
        print("=" * 70)

    print()
    return len(flagged)

if __name__ == "__main__":
    exit(main())
