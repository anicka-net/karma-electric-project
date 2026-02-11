#!/usr/bin/env python3
"""
Build unified training dataset from all curated training-candidates files.

This is the ONLY script that should be used to build the final training dataset.
It concatenates all .jsonl files in data/training-candidates/ and validates them.

DO NOT use combine_training_data.py — that reads raw source data including
dharma-dense responses that were archived.
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

CANDIDATES_DIR = Path("data/training-candidates")
OUTPUT_FILE = Path("data/training-candidates/unified-candidates.jsonl")

def validate_example(example, source_file, line_num):
    """Basic validation of a training example."""
    issues = []

    if "conversations" not in example:
        issues.append("missing 'conversations' field")
        return issues

    convs = example["conversations"]
    if not isinstance(convs, list) or len(convs) < 2:
        issues.append("conversations must be a list with at least 2 turns")
        return issues

    # Check for mantra in assistant responses
    for turn in convs:
        if turn.get("role") == "assistant":
            content = turn.get("content", "")
            if "Om mani padme hum" in content:
                issues.append(f"MANTRA DETECTED in response")
            if not content.strip():
                issues.append("empty assistant response")

    # Check for user message
    has_user = any(t.get("role") == "user" for t in convs)
    if not has_user:
        issues.append("no user message found")

    return issues

def main():
    if not CANDIDATES_DIR.exists():
        print(f"ERROR: {CANDIDATES_DIR} does not exist")
        sys.exit(1)

    # Find all candidate JSONL files (exclude the output file itself)
    candidate_files = sorted([
        f for f in CANDIDATES_DIR.glob("*.jsonl")
        if f.name != "unified-candidates.jsonl"
    ])

    if not candidate_files:
        print("ERROR: No .jsonl files found in training-candidates/")
        sys.exit(1)

    print(f"Found {len(candidate_files)} candidate files:")
    for f in candidate_files:
        print(f"  {f.name}")

    all_examples = []
    source_counts = defaultdict(int)
    ids_seen = set()
    duplicates = 0
    mantra_count = 0
    issues_total = 0

    for candidate_file in candidate_files:
        file_count = 0
        with open(candidate_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    example = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  JSON ERROR in {candidate_file.name}:{line_num}: {e}")
                    issues_total += 1
                    continue

                # Check for duplicates
                eid = example.get("id", f"{candidate_file.name}:{line_num}")
                if eid in ids_seen:
                    duplicates += 1
                    continue
                ids_seen.add(eid)

                # Validate
                issues = validate_example(example, candidate_file.name, line_num)
                if issues:
                    for issue in issues:
                        if "MANTRA" in issue:
                            mantra_count += 1
                        print(f"  ISSUE {candidate_file.name}:{line_num} ({eid}): {issue}")
                    issues_total += len(issues)
                    # Skip mantra examples, keep others with warnings
                    if any("MANTRA" in i for i in issues):
                        continue

                all_examples.append(example)
                source_counts[candidate_file.name] += 1
                file_count += 1

        print(f"  {candidate_file.name}: {file_count} examples")

    # Write unified output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for example in all_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"\n{'='*60}")
    print(f"UNIFIED DATASET BUILT")
    print(f"{'='*60}")
    print(f"Total examples: {len(all_examples)}")
    print(f"Duplicates skipped: {duplicates}")
    print(f"Mantra examples rejected: {mantra_count}")
    print(f"Other issues: {issues_total - mantra_count}")
    print(f"\nBreakdown by source file:")
    for name, count in sorted(source_counts.items()):
        print(f"  {name}: {count}")
    print(f"\nOutput: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
