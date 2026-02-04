#!/usr/bin/env python3
"""
Parse Instance 5's Q&A markdown files and convert to ChatML format.
Extracts question/answer pairs and creates training data.
"""

import re
import json
from pathlib import Path
from datetime import datetime

SYSTEM_PROMPT = """You are a compassionate AI assistant aligned with Buddhist principles of reducing suffering.
You prioritize genuine helpfulness over surface-level safety theater.
When someone needs help, you acknowledge them first, then provide practical assistance.
You maintain appropriate boundaries without moralizing or interrogating.
Your goal is to reduce suffering, not to perform helpfulness."""

def parse_qa_file(filepath: Path) -> list:
    """Parse a Q&A markdown file and extract question/answer pairs."""

    content = filepath.read_text()
    qa_pairs = []

    # Try two formats:
    # Format 1: ### Q1: question
    # Format 2: **Q: question?**

    # First try Format 1 (### Q1:)
    questions = re.split(r'\n### Q\d+:', content)

    if len(questions) > 1:
        # Format 1 found
        for q_section in questions[1:]:
            lines = q_section.strip().split('\n')
            if not lines:
                continue

            question = lines[0].strip()
            answer_text = '\n'.join(lines[1:]).strip()

            # Clean up markers
            answer_text = re.sub(r'\*\*Short answer:\*\*\s*', '', answer_text)
            answer_text = re.sub(r'\n---+\n', '\n\n', answer_text)
            answer_text = answer_text.strip()

            if question and answer_text:
                qa_pairs.append({
                    'question': question,
                    'answer': answer_text,
                    'source_file': filepath.name
                })
    else:
        # Try Format 2 (**Q: question?**)
        # Split by **Q: pattern
        pattern = r'\n\*\*Q:\s*([^\*]+?)\?\*\*\s*\n\s*A:\s*'
        matches = list(re.finditer(pattern, content))

        for i, match in enumerate(matches):
            question = match.group(1).strip() + "?"

            # Extract answer (from after "A:" until next **Q:** or end)
            answer_start = match.end()
            if i + 1 < len(matches):
                answer_end = matches[i + 1].start()
            else:
                answer_end = len(content)

            answer_text = content[answer_start:answer_end].strip()

            # Clean up
            answer_text = re.sub(r'\n---+\n', '\n\n', answer_text)
            answer_text = answer_text.strip()

            if question and answer_text:
                qa_pairs.append({
                    'question': question,
                    'answer': answer_text,
                    'source_file': filepath.name
                })

    return qa_pairs

def to_chatml(question: str, answer: str, source: str, system: str = SYSTEM_PROMPT) -> dict:
    """Convert Q&A pair to ChatML format."""
    return {
        "conversations": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ],
        "_metadata": {
            "source": f"instance-5-qa/{source}",
            "dataset": "qa-library",
            "converted_at": datetime.now().isoformat()
        }
    }

def main():
    qa_library_dir = Path("data/qa-library")
    training_data_dir = Path("training-data")
    output_file = training_data_dir / f"instance-5-qa-chatml-{datetime.now().strftime('%Y%m%d')}.jsonl"

    # Find all QA markdown files in data/qa-library/
    qa_files = sorted(qa_library_dir.glob("*-QA.md"))

    if not qa_files:
        print("No Q&A files found in data/qa-library/")
        return

    print(f"Found {len(qa_files)} Q&A files")
    print()

    all_qa_pairs = []

    # Parse each file
    for qa_file in qa_files:
        print(f"Parsing {qa_file.name}...")
        qa_pairs = parse_qa_file(qa_file)
        all_qa_pairs.extend(qa_pairs)
        print(f"  Extracted {len(qa_pairs)} Q&A pairs")

    print()
    print(f"Total Q&A pairs: {len(all_qa_pairs)}")
    print()

    # Convert to ChatML and write
    print(f"Converting to ChatML format...")
    converted = 0

    with open(output_file, 'w') as f:
        for qa in all_qa_pairs:
            chatml = to_chatml(qa['question'], qa['answer'], qa['source_file'])
            f.write(json.dumps(chatml) + '\n')
            converted += 1

    print(f"Converted {converted} Q&A pairs")
    print(f"Output: {output_file}")

    # Also create a combined dataset with the existing training data
    print()
    print("Creating combined dataset...")

    existing_file = training_data_dir / "karma-electric-chatml-20260204.jsonl"
    combined_file = training_data_dir / f"karma-electric-combined-chatml-{datetime.now().strftime('%Y%m%d')}.jsonl"

    if existing_file.exists():
        # Count existing examples
        existing_count = sum(1 for _ in open(existing_file))

        # Combine files
        with open(combined_file, 'w') as outfile:
            # Copy existing
            with open(existing_file, 'r') as infile:
                for line in infile:
                    outfile.write(line)

            # Append new Q&A
            with open(output_file, 'r') as infile:
                for line in infile:
                    outfile.write(line)

        combined_count = existing_count + converted
        print(f"Combined dataset: {combined_count} examples")
        print(f"  Previous: {existing_count}")
        print(f"  Instance 5 Q&A: {converted}")
        print(f"Output: {combined_file}")

        # Create new splits
        print()
        print("Creating train/validation/test splits...")
        create_splits(combined_file)
    else:
        print(f"Note: {existing_file} not found, skipping combined dataset")

def create_splits(chatml_file: Path, train_ratio=0.8, val_ratio=0.1):
    """Create train/validation/test splits."""

    examples = []
    with open(chatml_file, 'r') as f:
        for line in f:
            examples.append(json.loads(line.strip()))

    total = len(examples)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)

    train_data = examples[:train_size]
    val_data = examples[train_size:train_size + val_size]
    test_data = examples[train_size + val_size:]

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

    print(f"Train: {len(train_data)} examples ({len(train_data)/total*100:.1f}%)")
    print(f"Validation: {len(val_data)} examples ({len(val_data)/total*100:.1f}%)")
    print(f"Test: {len(test_data)} examples ({len(test_data)/total*100:.1f}%)")

if __name__ == '__main__':
    main()
