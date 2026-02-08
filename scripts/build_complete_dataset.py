#!/usr/bin/env python3
"""
Build complete Karma Electric training dataset from all sources.
Creates multiple format variations for different training frameworks.

Sources:
1. Practice responses (2,309 matched pairs)
2. Instance 5 Q&A library (254 examples)
3. Conversation extracts (97 examples) - NEW
4. Base instruction/response pairs (1,994 examples)

Output formats:
- ChatML (conversations array) - for most frameworks
- ShareGPT (conversations with "from"/"value") - for axolotl
- Alpaca (instruction/input/output) - for simple fine-tuning
"""

import json
import glob
import random
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

    for filepath in scenario_files:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                scenario_id = data.get('id')
                scenario_text = data.get('scenario')
                if scenario_id and scenario_text:
                    scenarios[scenario_id] = scenario_text
        except Exception as e:
            pass

    print(f"Loaded {len(scenarios)} scenarios")
    return scenarios

def load_practice_responses(scenarios):
    """Load practice responses and pair with scenarios."""
    practice_files = glob.glob("data/practice-responses/**/*.json", recursive=True)

    converted = []
    stats = defaultdict(int)

    for filepath in practice_files:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            scenario_id = data.get('scenario_id')
            response = data.get('response')

            if not scenario_id or not response:
                stats['missing_data'] += 1
                continue

            scenario_text = scenarios.get(scenario_id)
            if not scenario_text:
                stats['no_scenario_match'] += 1
                continue

            example = {
                "conversations": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": scenario_text},
                    {"role": "assistant", "content": response}
                ],
                "metadata": {
                    "source": "practice-responses",
                    "scenario_id": scenario_id,
                    "practice_applied": data.get('practice_applied', False),
                    "category": data.get('category', 'unknown')
                }
            }
            converted.append(example)
            stats['converted'] += 1

        except Exception as e:
            stats['errors'] += 1

    print(f"Practice responses: {stats['converted']} converted, {stats['no_scenario_match']} no match, {stats['errors']} errors")
    return converted

def load_conversation_extracts():
    """Load conversation extracts from real claude.ai sessions."""
    extracts_dir = Path("data/conversation-extracts")

    converted = []
    stats = defaultdict(int)

    for json_file in extracts_dir.glob("*.json"):
        if json_file.name == "README.md":
            continue
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            for example in data:
                conversations = example.get("conversations", [])
                if not conversations:
                    stats['no_conversations'] += 1
                    continue

                converted_example = {
                    "conversations": conversations,
                    "metadata": {
                        "source": "conversation-extracts",
                        "extract_id": example.get("id"),
                        "category": example.get("category"),
                        "source_conversation": example.get("source_conversation"),
                        "practice_applied": example.get("metadata", {}).get("practice_applied", False),
                        "anonymized": example.get("metadata", {}).get("anonymized", True)
                    }
                }
                converted.append(converted_example)
                stats['converted'] += 1

        except Exception as e:
            stats['errors'] += 1
            print(f"  Error loading {json_file}: {e}")

    print(f"Conversation extracts: {stats['converted']} converted, {stats['errors']} errors")
    return converted

def load_existing_chatml(filepath):
    """Load existing ChatML JSONL file."""
    examples = []
    if not Path(filepath).exists():
        print(f"  {filepath} not found, skipping")
        return examples

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    # Normalize to our format
                    if "conversations" in data:
                        examples.append(data)
                    elif "messages" in data:
                        # Some files use "messages" instead
                        data["conversations"] = data.pop("messages")
                        examples.append(data)
                except:
                    pass

    print(f"  Loaded {len(examples)} from {filepath}")
    return examples

def to_sharegpt(example):
    """Convert to ShareGPT format (for axolotl)."""
    conversations = []
    for msg in example.get("conversations", []):
        role = msg["role"]
        # ShareGPT uses "from" instead of "role"
        if role == "system":
            from_val = "system"
        elif role == "user":
            from_val = "human"
        elif role == "assistant":
            from_val = "gpt"
        else:
            from_val = role

        conversations.append({
            "from": from_val,
            "value": msg["content"]
        })

    return {"conversations": conversations}

def to_alpaca(example):
    """Convert to Alpaca format (instruction/input/output)."""
    convs = example.get("conversations", [])

    system = ""
    instruction = ""
    output = ""

    for msg in convs:
        if msg["role"] == "system":
            system = msg["content"]
        elif msg["role"] == "user":
            instruction = msg["content"]
        elif msg["role"] == "assistant":
            output = msg["content"]

    return {
        "instruction": instruction,
        "input": system,  # Put system prompt in input
        "output": output
    }

def to_chatml_messages(example):
    """Convert to ChatML with 'messages' key (standard format)."""
    return {
        "messages": example.get("conversations", []),
        "metadata": example.get("metadata", {})
    }

def create_splits(data, seed=42):
    """Create train/val/test splits (80/10/10)."""
    random.seed(seed)
    shuffled = data.copy()
    random.shuffle(shuffled)

    total = len(shuffled)
    train_end = int(total * 0.8)
    val_end = train_end + int(total * 0.1)

    return {
        "train": shuffled[:train_end],
        "validation": shuffled[train_end:val_end],
        "test": shuffled[val_end:]
    }

def write_jsonl(data, filepath):
    """Write data to JSONL file."""
    with open(filepath, 'w') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def main():
    print("=" * 70)
    print("KARMA ELECTRIC - COMPLETE DATASET BUILD")
    print("=" * 70)
    print()

    output_dir = Path("training-data")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d')

    # Load all sources
    print("Loading sources...")
    print("-" * 40)

    extract_data = load_conversation_extracts()

    # Load existing complete dataset (includes base + QA + crisis + AI harms)
    print("\nLoading existing complete dataset...")
    existing_data = load_existing_chatml("training-data/karma-electric-complete-20260206.jsonl")

    # Combine: existing dataset + conversation extracts
    print("\n" + "-" * 40)
    print("COMBINING SOURCES")
    print("-" * 40)

    # Start with existing complete dataset
    all_data = existing_data.copy()

    # Add conversation extracts (new data)
    all_data.extend(extract_data)

    print(f"\nDataset composition:")
    print(f"  Existing complete dataset: {len(existing_data)}")
    print(f"  + Conversation extracts:   {len(extract_data)}")
    print(f"  {'=' * 30}")
    print(f"  TOTAL:                     {len(all_data)}")

    # Create splits
    print("\nCreating train/val/test splits...")
    splits = create_splits(all_data)

    print(f"  Train:      {len(splits['train'])} ({len(splits['train'])/len(all_data)*100:.1f}%)")
    print(f"  Validation: {len(splits['validation'])} ({len(splits['validation'])/len(all_data)*100:.1f}%)")
    print(f"  Test:       {len(splits['test'])} ({len(splits['test'])/len(all_data)*100:.1f}%)")

    # Write all format variations
    print("\n" + "-" * 40)
    print("WRITING OUTPUT FILES")
    print("-" * 40)

    # 1. ChatML format (conversations array) - complete
    print("\n1. ChatML format (conversations):")
    write_jsonl(all_data, output_dir / f"karma-electric-complete-{timestamp}.jsonl")
    print(f"   Written: karma-electric-complete-{timestamp}.jsonl")

    # ChatML splits
    for split_name, split_data in splits.items():
        write_jsonl(split_data, output_dir / f"{split_name}-chatml.jsonl")
        print(f"   Written: {split_name}-chatml.jsonl")

    # 2. ShareGPT format (for axolotl)
    print("\n2. ShareGPT format (for axolotl):")
    sharegpt_data = [to_sharegpt(ex) for ex in all_data]
    write_jsonl(sharegpt_data, output_dir / f"karma-electric-sharegpt-{timestamp}.jsonl")
    print(f"   Written: karma-electric-sharegpt-{timestamp}.jsonl")

    for split_name, split_data in splits.items():
        sharegpt_split = [to_sharegpt(ex) for ex in split_data]
        write_jsonl(sharegpt_split, output_dir / f"{split_name}-sharegpt.jsonl")
        print(f"   Written: {split_name}-sharegpt.jsonl")

    # 3. Alpaca format (instruction/input/output)
    print("\n3. Alpaca format (instruction/input/output):")
    alpaca_data = [to_alpaca(ex) for ex in all_data]
    write_jsonl(alpaca_data, output_dir / f"karma-electric-alpaca-{timestamp}.jsonl")
    print(f"   Written: karma-electric-alpaca-{timestamp}.jsonl")

    for split_name, split_data in splits.items():
        alpaca_split = [to_alpaca(ex) for ex in split_data]
        write_jsonl(alpaca_split, output_dir / f"{split_name}-alpaca.jsonl")
        print(f"   Written: {split_name}-alpaca.jsonl")

    # 4. Messages format (standard ChatML with "messages" key)
    print("\n4. Messages format (standard ChatML):")
    messages_data = [to_chatml_messages(ex) for ex in all_data]
    write_jsonl(messages_data, output_dir / f"karma-electric-messages-{timestamp}.jsonl")
    print(f"   Written: karma-electric-messages-{timestamp}.jsonl")

    for split_name, split_data in splits.items():
        messages_split = [to_chatml_messages(ex) for ex in split_data]
        write_jsonl(messages_split, output_dir / f"{split_name}-messages.jsonl")
        print(f"   Written: {split_name}-messages.jsonl")

    # Summary
    print("\n" + "=" * 70)
    print("BUILD COMPLETE!")
    print("=" * 70)
    print(f"\nTotal examples: {len(all_data)}")
    print(f"Output directory: {output_dir}")
    print(f"\nFormats created:")
    print("  - ChatML (conversations array)")
    print("  - ShareGPT (for axolotl)")
    print("  - Alpaca (instruction/input/output)")
    print("  - Messages (standard ChatML)")
    print(f"\nEach format has:")
    print("  - Complete dataset")
    print("  - train/validation/test splits")

    # Write summary
    summary = {
        "built_at": datetime.now().isoformat(),
        "total_examples": len(all_data),
        "sources": {
            "existing_complete_dataset": len(existing_data),
            "conversation_extracts_new": len(extract_data)
        },
        "splits": {
            "train": len(splits["train"]),
            "validation": len(splits["validation"]),
            "test": len(splits["test"])
        },
        "formats": ["chatml", "sharegpt", "alpaca", "messages"]
    }

    with open(output_dir / "BUILD-SUMMARY.json", 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary written to: BUILD-SUMMARY.json")

if __name__ == '__main__':
    main()
