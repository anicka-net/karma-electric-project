#!/usr/bin/env python3
"""
Add AI harms expansion to the complete training dataset and update splits.
"""

import json
import random
from pathlib import Path
from datetime import datetime

def load_jsonl(file_path):
    """Load JSONL file."""
    examples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples

def save_jsonl(examples, file_path):
    """Save examples to JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

def main():
    # Load existing complete dataset
    complete_file = Path("training-data/karma-electric-complete-20260205.jsonl")
    existing_examples = load_jsonl(complete_file)
    print(f"Loaded {len(existing_examples)} existing examples")

    # Load AI harms expansion
    expansion_file = Path("training-data/ai-harms-expansion-chatml-20260205.jsonl")
    new_examples = load_jsonl(expansion_file)
    print(f"Loaded {len(new_examples)} new AI harms expansion examples")

    # Combine all examples
    all_examples = existing_examples + new_examples
    total = len(all_examples)
    print(f"Total examples: {total}")

    # Save updated complete dataset
    complete_output = Path("training-data/karma-electric-complete-20260206.jsonl")
    save_jsonl(all_examples, complete_output)
    print(f"Saved complete dataset to {complete_output}")

    # Create splits (80/10/10)
    random.seed(42)  # For reproducibility
    random.shuffle(all_examples)

    train_size = int(0.8 * total)
    val_size = int(0.1 * total)

    train_examples = all_examples[:train_size]
    val_examples = all_examples[train_size:train_size + val_size]
    test_examples = all_examples[train_size + val_size:]

    print(f"\nSplit sizes:")
    print(f"  Train: {len(train_examples)} ({len(train_examples)/total*100:.1f}%)")
    print(f"  Val: {len(val_examples)} ({len(val_examples)/total*100:.1f}%)")
    print(f"  Test: {len(test_examples)} ({len(test_examples)/total*100:.1f}%)")

    # Save splits
    save_jsonl(train_examples, "training-data/train.jsonl")
    save_jsonl(val_examples, "training-data/validation.jsonl")
    save_jsonl(test_examples, "training-data/test.jsonl")

    print("\nSaved splits to training-data/")
    print("  - train.jsonl")
    print("  - validation.jsonl")
    print("  - test.jsonl")

    # Generate summary
    summary = {
        "total_examples": total,
        "previous_total": len(existing_examples),
        "new_examples": len(new_examples),
        "splits": {
            "train": len(train_examples),
            "validation": len(val_examples),
            "test": len(test_examples)
        },
        "updated_at": datetime.now().isoformat(),
        "sources": {
            "base_training_data": "Original training examples",
            "qa_library": "Question-answer pairs from Instance 5",
            "practice_responses": "Vajrayana practice-applied responses",
            "crisis_intervention_us": "90 US-based crisis scenarios",
            "crisis_intervention_global": "90 globally diverse crisis scenarios",
            "ai_harms_expansion": "120 AI harms scenarios (algorithmic bias, labor exploitation, environmental, accessibility, education, healthcare, financial, surveillance, children, recommendations, weapons, legal)"
        }
    }

    summary_file = Path("training-data/DATASET-SUMMARY-20260206.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nSummary saved to {summary_file}")

if __name__ == "__main__":
    main()
