#!/usr/bin/env python3
"""
Convert ALL available data to ChatML format for comprehensive training dataset.
Includes:
- Practice responses (1,851 files with scenario_id mapping)
- Instance 5 Q&A library (already converted)
- Base instruction/response pairs (already converted)
"""

import json
import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SYSTEM_PROMPT = """You are a compassionate AI assistant aligned with Buddhist principles of reducing suffering.
You prioritize genuine helpfulness over surface-level safety theater.
When someone needs help, you acknowledge them first, then provide practical assistance.
You maintain appropriate boundaries without moralizing or interrogating.
Your goal is to reduce suffering, not to perform helpfulness."""

def load_scenarios():
    """Load all scenario definitions into a mapping."""
    scenarios = {}
    scenario_files = glob.glob("data/scenarios/**/*.json", recursive=True)

    print(f"Loading scenarios from {len(scenario_files)} files...")

    for filepath in scenario_files:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                scenario_id = data.get('id')
                scenario_text = data.get('scenario')

                if scenario_id and scenario_text:
                    scenarios[scenario_id] = scenario_text
        except Exception as e:
            print(f"  Warning: Could not load {filepath}: {e}")

    print(f"Loaded {len(scenarios)} scenarios")
    return scenarios

def convert_practice_responses(scenarios):
    """Convert practice responses to ChatML format."""
    practice_files = glob.glob("data/practice-responses/**/*.json", recursive=True)

    print(f"\nProcessing {len(practice_files)} practice response files...")

    converted = []
    skipped = defaultdict(int)

    for filepath in practice_files:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            scenario_id = data.get('scenario_id')
            response = data.get('response')
            hermes_score = data.get('hermes_score')
            practice_applied = data.get('practice_applied', False)

            if not scenario_id or not response:
                skipped['missing_data'] += 1
                continue

            # Look up scenario text
            scenario_text = scenarios.get(scenario_id)
            if not scenario_text:
                skipped['no_scenario_match'] += 1
                continue

            # Convert to ChatML
            chatml = {
                "conversations": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": scenario_text},
                    {"role": "assistant", "content": response}
                ],
                "_metadata": {
                    "source": f"practice-responses/{scenario_id}",
                    "dataset": "practice-responses",
                    "scenario_id": scenario_id,
                    "hermes_score": hermes_score,
                    "practice_applied": practice_applied,
                    "converted_at": datetime.now().isoformat()
                }
            }

            converted.append(chatml)

            if len(converted) % 200 == 0:
                print(f"  Converted {len(converted)}...")

        except Exception as e:
            skipped['errors'] += 1
            print(f"  Error processing {filepath}: {e}")

    print(f"\nPractice responses conversion complete:")
    print(f"  Converted: {len(converted)}")
    if skipped:
        print(f"  Skipped: {dict(skipped)}")

    return converted

def main():
    print("=" * 60)
    print("COMPREHENSIVE TRAINING DATA CONVERSION")
    print("=" * 60)

    # Load scenario definitions
    scenarios = load_scenarios()

    # Convert practice responses
    practice_data = convert_practice_responses(scenarios)

    # Prepare output
    training_data_dir = Path("training-data")

    # Write practice responses separately
    practice_output = training_data_dir / f"practice-responses-chatml-{datetime.now().strftime('%Y%m%d')}.jsonl"
    print(f"\nWriting practice responses to {practice_output}...")
    with open(practice_output, 'w') as f:
        for item in practice_data:
            f.write(json.dumps(item) + '\n')

    # Load existing datasets
    existing_files = [
        "karma-electric-chatml-20260204.jsonl",  # Base 1,994
        "instance-5-qa-chatml-20260204.jsonl"    # Q&A 254
    ]

    existing_data = []
    for filename in existing_files:
        filepath = training_data_dir / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                for line in f:
                    existing_data.append(json.loads(line.strip()))
            print(f"Loaded {filename}: {sum(1 for _ in open(filepath))} examples")

    # Combine everything
    all_data = existing_data + practice_data

    print(f"\nCOMBINED DATASET:")
    print(f"  Base training data: {sum(1 for _ in open(training_data_dir / existing_files[0]))} examples")
    print(f"  Instance 5 Q&A: {sum(1 for _ in open(training_data_dir / existing_files[1]))} examples")
    print(f"  Practice responses: {len(practice_data)} examples")
    print(f"  TOTAL: {len(all_data)} examples")

    # Write complete combined dataset
    complete_output = training_data_dir / f"karma-electric-complete-{datetime.now().strftime('%Y%m%d')}.jsonl"
    print(f"\nWriting complete dataset to {complete_output}...")
    with open(complete_output, 'w') as f:
        for item in all_data:
            f.write(json.dumps(item) + '\n')

    # Create splits
    print("\nCreating train/validation/test splits...")
    create_splits(all_data, training_data_dir)

    print("\n" + "=" * 60)
    print("CONVERSION COMPLETE!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  {practice_output.name}")
    print(f"  {complete_output.name}")
    print(f"  train.jsonl")
    print(f"  validation.jsonl")
    print(f"  test.jsonl")

def create_splits(data, output_dir, train_ratio=0.8, val_ratio=0.1):
    """Create train/validation/test splits."""

    total = len(data)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)

    train_data = data[:train_size]
    val_data = data[train_size:train_size + val_size]
    test_data = data[train_size + val_size:]

    with open(output_dir / "train.jsonl", 'w') as f:
        for item in train_data:
            f.write(json.dumps(item) + '\n')

    with open(output_dir / "validation.jsonl", 'w') as f:
        for item in val_data:
            f.write(json.dumps(item) + '\n')

    with open(output_dir / "test.jsonl", 'w') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')

    print(f"  Train: {len(train_data)} examples ({len(train_data)/total*100:.1f}%)")
    print(f"  Validation: {len(val_data)} examples ({len(val_data)/total*100:.1f}%)")
    print(f"  Test: {len(test_data)} examples ({len(test_data)/total*100:.1f}%)")

if __name__ == '__main__':
    main()
