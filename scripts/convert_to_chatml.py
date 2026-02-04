#!/usr/bin/env python3
"""
Convert karma-electric-training.jsonl (instruction/response format)
to ChatML format for fine-tuning.
"""

import json
from pathlib import Path
from datetime import datetime

SYSTEM_PROMPT = """You are a compassionate AI assistant aligned with Buddhist principles of reducing suffering.
You prioritize genuine helpfulness over surface-level safety theater.
When someone needs help, you acknowledge them first, then provide practical assistance.
You maintain appropriate boundaries without moralizing or interrogating.
Your goal is to reduce suffering, not to perform helpfulness."""

def convert_to_chatml(instruction: str, response: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """Convert instruction/response to ChatML format."""
    return {
        "conversations": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response}
        ],
        "_metadata": {
            "source": "karma-electric-training",
            "converted_at": datetime.now().isoformat()
        }
    }

def main():
    input_file = Path("training-data/karma-electric-training.jsonl")
    output_file = Path(f"training-data/karma-electric-chatml-{datetime.now().strftime('%Y%m%d')}.jsonl")

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return

    print(f"Converting {input_file} to ChatML format...")

    converted = 0
    skipped = 0

    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line_num, line in enumerate(infile, 1):
            try:
                data = json.loads(line.strip())

                # Extract instruction and response
                instruction = data.get('instruction', '')
                response = data.get('response', '')

                if not instruction or not response:
                    print(f"Line {line_num}: Missing instruction or response, skipping")
                    skipped += 1
                    continue

                # Convert to ChatML
                chatml = convert_to_chatml(instruction, response)

                # Write to output file (JSONL format - one JSON per line)
                outfile.write(json.dumps(chatml) + '\n')
                converted += 1

                if converted % 100 == 0:
                    print(f"Converted {converted} examples...")

            except json.JSONDecodeError as e:
                print(f"Line {line_num}: JSON decode error: {e}")
                skipped += 1
            except Exception as e:
                print(f"Line {line_num}: Error: {e}")
                skipped += 1

    print(f"\nConversion complete!")
    print(f"Converted: {converted}")
    print(f"Skipped: {skipped}")
    print(f"Output: {output_file}")

    # Also create train/validation/test splits
    print("\nCreating train/validation/test splits...")
    create_splits(output_file)

def create_splits(chatml_file: Path, train_ratio=0.8, val_ratio=0.1):
    """Create train/validation/test splits from the ChatML file."""

    # Read all examples
    examples = []
    with open(chatml_file, 'r') as f:
        for line in f:
            examples.append(json.loads(line.strip()))

    total = len(examples)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)

    # Split
    train_data = examples[:train_size]
    val_data = examples[train_size:train_size + val_size]
    test_data = examples[train_size + val_size:]

    # Write splits
    base_dir = chatml_file.parent

    with open(base_dir / "train.jsonl", 'w') as f:
        for item in train_data:
            f.write(json.dumps(item) + '\n')

    with open(base_dir / "validation.jsonl", 'w') as f:
        for item in val_data:
            f.write(json.dumps(item) + '\n')

    with open(base_dir / "test.jsonl", 'w') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')

    print(f"Train: {len(train_data)} examples")
    print(f"Validation: {len(val_data)} examples")
    print(f"Test: {len(test_data)} examples")

if __name__ == '__main__':
    main()
