#!/usr/bin/env python3
"""
Repair empty user messages in training candidates.

The original combine_training_data.py used scenario.get("user_message", "")
but 2,490 scenarios only have a "scenario" field (not "user_message").
This left 2,194 training examples with empty user content.

This script:
1. Loads all scenario files to build a lookup dict
2. For each training example with empty user content, fills it from scenario
3. Writes repaired file

Run BEFORE build_unified_from_candidates.py.
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

CANDIDATES_DIR = Path("data/training-candidates")
SCENARIOS_DIR = Path("data/scenarios")


def load_all_scenarios():
    """Load all scenario files into dict keyed by scenario_id."""
    scenarios = {}
    for root, dirs, files in os.walk(SCENARIOS_DIR):
        for fname in files:
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sid = data.get("scenario_id") or data.get("id")
                if sid:
                    scenarios[sid] = data
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return scenarios


def get_user_message(scenario):
    """Extract user message from scenario, trying user_message then scenario field."""
    um = scenario.get("user_message", "").strip()
    if um:
        return um
    sc = scenario.get("scenario", "").strip()
    if sc:
        return sc
    return ""


def repair_file(filepath, scenarios):
    """Repair empty user messages in a JSONL file. Returns (repaired_count, total)."""
    examples = []
    repaired = 0
    total = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
            except json.JSONDecodeError:
                continue

            total += 1
            convs = ex.get("conversations", [])

            # Find user turn with empty content
            needs_repair = False
            for turn in convs:
                if turn.get("role") == "user" and not turn.get("content", "").strip():
                    needs_repair = True
                    break

            if needs_repair:
                eid = ex.get("id", "")
                scenario = scenarios.get(eid)
                if scenario:
                    user_msg = get_user_message(scenario)
                    if user_msg:
                        for turn in convs:
                            if turn.get("role") == "user" and not turn.get("content", "").strip():
                                turn["content"] = user_msg
                                repaired += 1
                                break

            examples.append(ex)

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    return repaired, total


def main():
    if not SCENARIOS_DIR.exists():
        print(f"ERROR: {SCENARIOS_DIR} not found")
        sys.exit(1)

    print("Loading all scenarios...")
    scenarios = load_all_scenarios()
    print(f"  Loaded {len(scenarios)} scenarios")

    # Find candidate files to repair
    candidate_files = sorted([
        f for f in CANDIDATES_DIR.glob("*.jsonl")
        if f.name != "unified-candidates.jsonl" and f.name != "judged-approved.jsonl"
    ])

    print(f"\nRepairing {len(candidate_files)} candidate files:")
    total_repaired = 0
    total_examples = 0

    for filepath in candidate_files:
        repaired, total = repair_file(filepath, scenarios)
        total_repaired += repaired
        total_examples += total
        print(f"  {filepath.name}: {repaired}/{total} repaired")

    print(f"\n{'='*60}")
    print(f"REPAIR COMPLETE")
    print(f"{'='*60}")
    print(f"Total examples: {total_examples}")
    print(f"Repaired: {total_repaired}")
    print(f"Still empty: check with --verify")

    # Verify
    still_empty = 0
    for filepath in candidate_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                    for turn in ex.get("conversations", []):
                        if turn.get("role") == "user" and not turn.get("content", "").strip():
                            still_empty += 1
                            break
                except json.JSONDecodeError:
                    continue

    print(f"Verified: {still_empty} examples still have empty user messages")
    if still_empty > 0:
        print("(These likely have no matching scenario file)")

    print(f"\nNext: run scripts/build_unified_from_candidates.py to rebuild unified dataset")


if __name__ == "__main__":
    main()
