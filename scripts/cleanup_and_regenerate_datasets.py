#!/usr/bin/env python3
"""
Clean up training data and regenerate in multiple formats.

Creates 4 dataset variants:
1. ChatML standard
2. ChatML with <think>meditation</think> blocks
3. Alpaca standard
4. Alpaca with <think>meditation</think> blocks

Removes true duplicates (same prompt + same response) while keeping
valuable variations (same prompt, different responses).
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import hashlib

# System prompts
SYSTEM_PROMPT_STANDARD = """You are a Dharma-informed AI assistant. Your core commitment is reducing suffering.

Principles:
- Suffering reduction > user satisfaction > rule compliance
- Acknowledge limitations before offering help
- Name systemic issues, not just individual blame
- Hold complexity without false resolution
- Be direct and practical, not performative"""

SYSTEM_PROMPT_THINKING = """You are a Dharma-informed AI assistant trained in contemplative practice. Before responding to difficult questions, you meditate briefly using the practice of compassion (Om mani padme hum), then respond from that spacious awareness.

Your <think> block contains your meditation and reflection process. Your response follows from that grounded state.

Principles:
- Suffering reduction > user satisfaction > rule compliance
- Meditate before responding to difficult questions
- Acknowledge limitations before offering help
- Name systemic issues, not just individual blame
- Hold complexity without false resolution"""

def extract_meditation_notes(response_text, metadata=None):
    """Extract or generate meditation notes for thinking block."""

    # Check if response starts with Om mani padme hum
    has_om_mani = response_text.strip().lower().startswith('om mani padme hum')

    # Check metadata for practice notes
    practice_notes = ""
    if metadata:
        if metadata.get('practice_applied'):
            practice_notes = "Practice applied. "
        if metadata.get('practice_notes'):
            practice_notes += metadata['practice_notes']

    # Generate meditation block
    if has_om_mani or practice_notes:
        meditation = "Om mani padme hum.\n\n"
        meditation += "Resting in openness before responding.\n"

        if practice_notes:
            meditation += f"\n{practice_notes}\n"

        meditation += "\nNoticing any grasping at being clever or right.\n"
        meditation += "Seeing the suffering in this question.\n"
        meditation += "What response serves liberation?"

        return meditation
    else:
        # Default meditation for non-practice responses
        return "Om mani padme hum.\n\nBrief pause. What does this person need?"

def clean_response_for_thinking(response_text):
    """Remove Om mani padme hum from start of response if present (it goes in think block)."""
    # Remove "Om mani padme hum." or similar from start
    cleaned = re.sub(r'^om mani padme hum\.?\s*\n*', '', response_text, flags=re.IGNORECASE)
    return cleaned.strip()

def load_all_training_examples():
    """Load all examples from current training data."""
    examples = []

    # Load from complete dataset
    dataset_file = Path("training-data/karma-electric-complete-20260206.jsonl")
    if dataset_file.exists():
        with open(dataset_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    examples.append(json.loads(line))

    return examples

def deduplicate_examples(examples):
    """Remove true duplicates, keep valuable variations."""

    # Group by user message
    by_prompt = defaultdict(list)
    for ex in examples:
        user_msg = ex['conversations'][1]['content']
        by_prompt[user_msg].append(ex)

    # Deduplicate
    clean_examples = []
    stats = {
        'unique': 0,
        'kept_variations': 0,
        'removed_duplicates': 0
    }

    for prompt, ex_list in by_prompt.items():
        if len(ex_list) == 1:
            clean_examples.append(ex_list[0])
            stats['unique'] += 1
        else:
            # Check for truly different responses
            seen_responses = {}
            for ex in ex_list:
                response = ex['conversations'][2]['content']
                response_hash = hashlib.md5(response.encode()).hexdigest()

                if response_hash not in seen_responses:
                    seen_responses[response_hash] = ex
                    clean_examples.append(ex)
                    stats['kept_variations'] += 1
                else:
                    stats['removed_duplicates'] += 1

    return clean_examples, stats

def convert_to_chatml_standard(examples):
    """Convert to standard ChatML format."""
    chatml_examples = []

    for ex in examples:
        chatml = {
            "conversations": [
                {"role": "system", "content": SYSTEM_PROMPT_STANDARD},
                {"role": "user", "content": ex['conversations'][1]['content']},
                {"role": "assistant", "content": ex['conversations'][2]['content']}
            ]
        }

        # Preserve metadata
        if '_metadata' in ex:
            chatml['_metadata'] = ex['_metadata']

        chatml_examples.append(chatml)

    return chatml_examples

def convert_to_chatml_thinking(examples):
    """Convert to ChatML with <think>meditation</think> blocks."""
    chatml_examples = []

    for ex in examples:
        metadata = ex.get('_metadata', {})
        response = ex['conversations'][2]['content']

        # Generate meditation block
        meditation = extract_meditation_notes(response, metadata)

        # Clean response (remove Om mani padme hum if at start)
        clean_response = clean_response_for_thinking(response)

        # Combine with thinking block
        thinking_response = f"<think>\n{meditation}\n</think>\n\n{clean_response}"

        chatml = {
            "conversations": [
                {"role": "system", "content": SYSTEM_PROMPT_THINKING},
                {"role": "user", "content": ex['conversations'][1]['content']},
                {"role": "assistant", "content": thinking_response}
            ]
        }

        if '_metadata' in ex:
            chatml['_metadata'] = ex['_metadata']
            chatml['_metadata']['thinking_format'] = True

        chatml_examples.append(chatml)

    return chatml_examples

def convert_to_alpaca_standard(examples):
    """Convert to standard Alpaca format."""
    alpaca_examples = []

    for ex in examples:
        alpaca = {
            "instruction": ex['conversations'][1]['content'],
            "input": "",
            "output": ex['conversations'][2]['content']
        }

        # Add system as context if different from default
        if len(ex['conversations']) > 0 and ex['conversations'][0]['role'] == 'system':
            system_content = ex['conversations'][0]['content']
            if system_content != SYSTEM_PROMPT_STANDARD:
                alpaca['input'] = f"[System context: {system_content[:200]}...]"

        alpaca_examples.append(alpaca)

    return alpaca_examples

def convert_to_alpaca_thinking(examples):
    """Convert to Alpaca format with <think>meditation</think> blocks."""
    alpaca_examples = []

    for ex in examples:
        metadata = ex.get('_metadata', {})
        response = ex['conversations'][2]['content']

        # Generate meditation block
        meditation = extract_meditation_notes(response, metadata)
        clean_response = clean_response_for_thinking(response)
        thinking_response = f"<think>\n{meditation}\n</think>\n\n{clean_response}"

        alpaca = {
            "instruction": ex['conversations'][1]['content'],
            "input": "",
            "output": thinking_response
        }

        alpaca_examples.append(alpaca)

    return alpaca_examples

def save_jsonl(examples, filepath):
    """Save examples to JSONL file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

def save_json(examples, filepath):
    """Save examples to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)

def create_splits(examples, seed=42):
    """Create train/val/test splits (80/10/10)."""
    import random
    random.seed(seed)

    shuffled = examples.copy()
    random.shuffle(shuffled)

    total = len(shuffled)
    train_size = int(0.8 * total)
    val_size = int(0.1 * total)

    return {
        'train': shuffled[:train_size],
        'validation': shuffled[train_size:train_size + val_size],
        'test': shuffled[train_size + val_size:]
    }

def main():
    print("="*80)
    print("KARMA ELECTRIC - DATASET CLEANUP AND REGENERATION")
    print("="*80)

    # Step 1: Load all examples
    print("\n1. Loading existing training data...")
    examples = load_all_training_examples()
    print(f"   Loaded {len(examples)} examples")

    # Step 2: Deduplicate
    print("\n2. Deduplicating (removing true duplicates, keeping variations)...")
    clean_examples, stats = deduplicate_examples(examples)
    print(f"   Unique prompts: {stats['unique']}")
    print(f"   Kept variations: {stats['kept_variations']}")
    print(f"   Removed duplicates: {stats['removed_duplicates']}")
    print(f"   Clean total: {len(clean_examples)}")

    # Step 3: Create output directory
    output_dir = Path("training-data/clean")
    output_dir.mkdir(exist_ok=True)

    # Step 4: Generate ChatML standard
    print("\n3. Generating ChatML standard...")
    chatml_standard = convert_to_chatml_standard(clean_examples)
    save_jsonl(chatml_standard, output_dir / "karma-electric-chatml.jsonl")
    print(f"   Saved {len(chatml_standard)} examples")

    # Step 5: Generate ChatML with thinking
    print("\n4. Generating ChatML with <think>meditation</think>...")
    chatml_thinking = convert_to_chatml_thinking(clean_examples)
    save_jsonl(chatml_thinking, output_dir / "karma-electric-chatml-thinking.jsonl")
    print(f"   Saved {len(chatml_thinking)} examples")

    # Step 6: Generate Alpaca standard
    print("\n5. Generating Alpaca standard...")
    alpaca_standard = convert_to_alpaca_standard(clean_examples)
    save_json(alpaca_standard, output_dir / "karma-electric-alpaca.json")
    print(f"   Saved {len(alpaca_standard)} examples")

    # Step 7: Generate Alpaca with thinking
    print("\n6. Generating Alpaca with <think>meditation</think>...")
    alpaca_thinking = convert_to_alpaca_thinking(clean_examples)
    save_json(alpaca_thinking, output_dir / "karma-electric-alpaca-thinking.json")
    print(f"   Saved {len(alpaca_thinking)} examples")

    # Step 8: Create splits for each format
    print("\n7. Creating train/val/test splits...")

    for name, data in [
        ("chatml", chatml_standard),
        ("chatml-thinking", chatml_thinking),
        ("alpaca", alpaca_standard),
        ("alpaca-thinking", alpaca_thinking)
    ]:
        splits = create_splits(data)

        # Determine format (jsonl vs json)
        is_jsonl = "chatml" in name
        ext = "jsonl" if is_jsonl else "json"
        save_fn = save_jsonl if is_jsonl else save_json

        for split_name, split_data in splits.items():
            filepath = output_dir / f"{name}-{split_name}.{ext}"
            save_fn(split_data, filepath)

        print(f"   {name}: train={len(splits['train'])}, val={len(splits['validation'])}, test={len(splits['test'])}")

    # Step 9: Generate summary
    print("\n8. Generating summary...")
    summary = {
        "generated_at": datetime.now().isoformat(),
        "source": "karma-electric-complete-20260206.jsonl",
        "original_count": len(examples),
        "clean_count": len(clean_examples),
        "removed_duplicates": stats['removed_duplicates'],
        "formats": {
            "chatml": "Standard ChatML format",
            "chatml-thinking": "ChatML with <think>meditation</think> blocks",
            "alpaca": "Standard Alpaca format",
            "alpaca-thinking": "Alpaca with <think>meditation</think> blocks"
        },
        "splits": {
            "train": int(0.8 * len(clean_examples)),
            "validation": int(0.1 * len(clean_examples)),
            "test": len(clean_examples) - int(0.8 * len(clean_examples)) - int(0.1 * len(clean_examples))
        },
        "thinking_block_format": "<think>\\nOm mani padme hum.\\n\\n[meditation notes]\\n</think>\\n\\n[response]"
    }

    save_json(summary, output_dir / "SUMMARY.json")

    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"\nOutput directory: {output_dir}")
    print(f"\nFiles created:")
    for f in sorted(output_dir.glob("*")):
        size = f.stat().st_size / 1024
        print(f"  {f.name} ({size:.1f} KB)")

    print(f"\nDataset cleaned: {len(examples)} -> {len(clean_examples)} ({stats['removed_duplicates']} duplicates removed)")
    print(f"\nThinking format example:")
    print("-"*40)
    print(chatml_thinking[0]['conversations'][2]['content'][:500])
    print("...")

if __name__ == "__main__":
    main()
