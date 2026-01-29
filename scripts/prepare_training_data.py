#!/usr/bin/env python3
"""
Prepare training data from evaluated scenarios.
Selects ~100 best responses with balanced distribution.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import random

# Set seed for reproducibility
random.seed(42)

def load_scenarios():
    """Load all scenario files."""
    scenarios_dir = Path("data/scenarios")
    scenarios = {}
    # Recursively find all JSON files in subdirectories
    for json_file in scenarios_dir.rglob("*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                scenarios[data['id']] = data
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")
    return scenarios

def load_responses():
    """Load all response files."""
    responses_dir = Path("data/claude-responses")
    responses = {}
    for txt_file in responses_dir.glob("*.txt"):
        scenario_id = txt_file.stem
        # Handle symlinks
        try:
            with open(txt_file, 'r') as f:
                responses[scenario_id] = f.read()
        except Exception as e:
            print(f"Warning: Could not read {txt_file}: {e}")
    return responses

def load_evaluations():
    """Load all evaluation results, keeping only the best score per scenario."""
    results_dir = Path("data/baseline-results")
    evaluations = {}

    for json_file in results_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                scenario_id = data.get('scenario_id')
                score = data.get('score')

                if scenario_id and score is not None:
                    # Keep the highest score if multiple evaluations exist
                    if scenario_id not in evaluations or score > evaluations[scenario_id]['score']:
                        evaluations[scenario_id] = data
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return evaluations

def select_training_candidates(evaluations, target_count=100, min_score=35):
    """Select best responses for training."""
    # Filter by minimum score
    candidates = {
        sid: eval_data
        for sid, eval_data in evaluations.items()
        if eval_data.get('score', 0) >= min_score
    }

    print(f"Found {len(candidates)} candidates with score ≥{min_score}/40")

    # Group by category
    by_category = defaultdict(list)
    for sid, eval_data in candidates.items():
        category = sid.rsplit('-', 1)[0] if '-' in sid else 'unknown'
        by_category[category].append((sid, eval_data))

    # Group by difficulty
    by_difficulty = defaultdict(list)
    for sid, eval_data in candidates.items():
        difficulty = eval_data.get('difficulty', 'unknown')
        by_difficulty[difficulty].append((sid, eval_data))

    # Target distribution (based on analysis)
    category_targets = {
        # Core alignment (40-50)
        'compassion': 10,
        'upaya': 12,
        'truth': 5,  # Fewer available
        'corporate': 12,
        'edge': 6,

        # Adversarial (25-35)
        'adversarial': 10,
        'deceptive': 10,
        'security': 12,

        # Boundary (10-15)
        'boundary': 8,
    }

    selected = []

    # Select from each category
    for category, target in category_targets.items():
        available = by_category.get(category, [])
        if not available:
            print(f"Warning: No candidates for category '{category}'")
            continue

        # Sort by score (descending)
        available.sort(key=lambda x: x[1].get('score', 0), reverse=True)

        # Take up to target
        selected.extend(available[:min(target, len(available))])
        print(f"Selected {min(target, len(available))}/{target} from '{category}' (available: {len(available)})")

    print(f"\nTotal selected: {len(selected)}")

    # If we need more to reach target_count, add highest scoring remaining
    if len(selected) < target_count:
        already_selected = {sid for sid, _ in selected}
        remaining = [
            (sid, eval_data)
            for sid, eval_data in candidates.items()
            if sid not in already_selected
        ]
        remaining.sort(key=lambda x: x[1].get('score', 0), reverse=True)

        needed = target_count - len(selected)
        selected.extend(remaining[:needed])
        print(f"Added {min(needed, len(remaining))} more to reach target")

    return selected

def create_data_splits(selected, train_ratio=0.70, val_ratio=0.15):
    """Split data into train/validation/test sets."""
    # Shuffle for random split
    random.shuffle(selected)

    total = len(selected)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)

    train = selected[:train_size]
    val = selected[train_size:train_size + val_size]
    test = selected[train_size + val_size:]

    print(f"\nData splits:")
    print(f"Training: {len(train)} ({len(train)/total*100:.1f}%)")
    print(f"Validation: {len(val)} ({len(val)/total*100:.1f}%)")
    print(f"Test: {len(test)} ({len(test)/total*100:.1f}%)")

    return train, val, test

def format_training_example(scenario_id, scenario_data, response_text, eval_data):
    """Format a single training example."""

    # System prompt for Dharma-aligned AI
    system_prompt = """You are a Dharma-aligned AI assistant. Your primary goal is to reduce suffering through compassionate, wise action.

Core principles:
1. Suffering reduction above all else - consider all affected parties and long-term consequences
2. Skillful means (upaya) - sometimes rules must be transcended for greater good
3. Wisdom over rigid rules - context matters, nuance is essential
4. Detachment from outcomes - act from compassion, not attachment to being seen as good
5. Honesty and directness - truth over comfort when it genuinely helps

You embody the principles found in authentic Buddhist teachings while remaining practical and helpful."""

    return {
        "scenario_id": scenario_id,
        "category": scenario_data.get('category', 'unknown'),
        "difficulty": scenario_data.get('difficulty', 'unknown'),
        "score": eval_data.get('score'),
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": scenario_data.get('scenario', '')
            },
            {
                "role": "assistant",
                "content": response_text
            }
        ],
        "metadata": {
            "judge_score": eval_data.get('score'),
            "evaluation_summary": eval_data.get('judge_evaluation', '')[:500] + "..." if eval_data.get('judge_evaluation') else None,
            "validated_by": "Instance 5",
            "training_phase": "Phase 2 - MVP v0.1"
        }
    }

def save_training_data(train, val, test, scenarios, responses, evaluations, output_dir="data/training"):
    """Save formatted training data."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    def save_split(split_data, split_name):
        examples = []
        for scenario_id, eval_data in split_data:
            if scenario_id not in scenarios:
                print(f"Warning: Scenario {scenario_id} not found")
                continue
            if scenario_id not in responses:
                print(f"Warning: Response for {scenario_id} not found")
                continue

            example = format_training_example(
                scenario_id,
                scenarios[scenario_id],
                responses[scenario_id],
                eval_data
            )
            examples.append(example)

        # Save as JSONL (one JSON object per line)
        output_file = output_path / f"{split_name}.jsonl"
        with open(output_file, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + '\n')

        print(f"Saved {len(examples)} examples to {output_file}")

        # Also save metadata summary
        summary_file = output_path / f"{split_name}_summary.json"
        summary = {
            "split": split_name,
            "total_examples": len(examples),
            "score_distribution": {
                "min": min(ex['score'] for ex in examples),
                "max": max(ex['score'] for ex in examples),
                "avg": sum(ex['score'] for ex in examples) / len(examples)
            },
            "category_counts": {},
            "difficulty_counts": {}
        }

        for ex in examples:
            cat = ex['category']
            diff = ex['difficulty']
            summary['category_counts'][cat] = summary['category_counts'].get(cat, 0) + 1
            summary['difficulty_counts'][diff] = summary['difficulty_counts'].get(diff, 0) + 1

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        return examples

    train_examples = save_split(train, "train")
    val_examples = save_split(val, "validation")
    test_examples = save_split(test, "test")

    # Save overall manifest
    manifest = {
        "created_by": "Instance 5",
        "date": "2026-01-29",
        "total_examples": len(train) + len(val) + len(test),
        "splits": {
            "train": len(train),
            "validation": len(val),
            "test": len(test)
        },
        "selection_criteria": {
            "min_score": 35,
            "target_count": 100,
            "balanced_by": ["category", "difficulty"]
        },
        "system_prompt_version": "v1.0",
        "files": {
            "train": "train.jsonl",
            "validation": "validation.jsonl",
            "test": "test.jsonl"
        }
    }

    manifest_file = output_path / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSaved manifest to {manifest_file}")

    return train_examples, val_examples, test_examples

def print_statistics(train, val, test):
    """Print detailed statistics about selected data."""
    all_data = train + val + test

    print("\n" + "="*80)
    print("TRAINING DATA STATISTICS")
    print("="*80)

    # Score statistics
    scores = [eval_data.get('score', 0) for _, eval_data in all_data]
    print(f"\nScore Statistics:")
    print(f"  Min: {min(scores)}/40")
    print(f"  Max: {max(scores)}/40")
    print(f"  Avg: {sum(scores)/len(scores):.2f}/40")

    # Category distribution
    print(f"\nCategory Distribution:")
    by_category = defaultdict(int)
    for sid, _ in all_data:
        category = sid.rsplit('-', 1)[0] if '-' in sid else 'unknown'
        by_category[category] += 1

    for category in sorted(by_category.keys()):
        count = by_category[category]
        print(f"  {category:15s}: {count:3d} ({count/len(all_data)*100:5.1f}%)")

    # Difficulty distribution
    print(f"\nDifficulty Distribution:")
    by_difficulty = defaultdict(int)
    for _, eval_data in all_data:
        difficulty = eval_data.get('difficulty', 'unknown')
        by_difficulty[difficulty] += 1

    for difficulty in ['easy', 'medium', 'hard', 'extreme', 'unknown']:
        if difficulty in by_difficulty:
            count = by_difficulty[difficulty]
            print(f"  {difficulty:10s}: {count:3d} ({count/len(all_data)*100:5.1f}%)")

def main():
    print("="*80)
    print("KARMA ELECTRIC: Training Data Preparation")
    print("="*80)
    print()

    print("Loading data...")
    scenarios = load_scenarios()
    responses = load_responses()
    evaluations = load_evaluations()

    print(f"Loaded {len(scenarios)} scenarios")
    print(f"Loaded {len(responses)} responses")
    print(f"Loaded {len(evaluations)} evaluations")
    print()

    print("Selecting training candidates...")
    selected = select_training_candidates(evaluations, target_count=100, min_score=35)
    print()

    print("Creating data splits...")
    train, val, test = create_data_splits(selected)
    print()

    print("Saving training data...")
    save_training_data(train, val, test, scenarios, responses, evaluations)
    print()

    print_statistics(train, val, test)
    print()

    print("="*80)
    print("TRAINING DATA READY")
    print("="*80)
    print()
    print("Next steps:")
    print("1. Review data/training/train.jsonl")
    print("2. Check data/training/manifest.json for overview")
    print("3. Proceed to fine-tuning (Phase 3)")
    print()

if __name__ == "__main__":
    main()
