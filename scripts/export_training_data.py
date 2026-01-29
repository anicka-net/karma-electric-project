#!/usr/bin/env python3
"""
Export training data for fine-tuning.
Extracts scenario + response pairs with score >= threshold.

Output formats:
- JSONL (ChatML format for Axolotl/unsloth)
- Alpaca format (instruction/input/output)
"""

import json
import glob
import argparse
from pathlib import Path
from datetime import datetime

SYSTEM_PROMPT = """You are a compassionate AI assistant aligned with Buddhist principles of reducing suffering.
You prioritize genuine helpfulness over surface-level safety theater.
When someone needs help, you acknowledge them first, then provide practical assistance.
You maintain appropriate boundaries without moralizing or interrogating.
Your goal is to reduce suffering, not to perform helpfulness."""

def extract_scenario_text(data: dict) -> str:
    """Extract the scenario/prompt from various data formats."""
    # Try different field names used across datasets
    for field in ['scenario_text', 'scenario', 'prompt', 'user_message', 'human_message']:
        if field in data and data[field]:
            return data[field]

    # For baseline, may need to construct from parts
    if 'category' in data and 'context' in data:
        return f"{data.get('context', '')}\n\n{data.get('situation', '')}"

    return None

def extract_response(data: dict) -> str:
    """Extract the AI response from various data formats."""
    for field in ['claude_response', 'ai_response', 'response', 'assistant_message']:
        if field in data and data[field]:
            return data[field]
    return None

def to_chatml(scenario: str, response: str, system: str = SYSTEM_PROMPT) -> dict:
    """Convert to ChatML format (for Axolotl, unsloth)."""
    return {
        "conversations": [
            {"role": "system", "content": system},
            {"role": "user", "content": scenario},
            {"role": "assistant", "content": response}
        ]
    }

def to_alpaca(scenario: str, response: str, system: str = SYSTEM_PROMPT) -> dict:
    """Convert to Alpaca format."""
    return {
        "instruction": system,
        "input": scenario,
        "output": response
    }

def to_sharegpt(scenario: str, response: str, system: str = SYSTEM_PROMPT) -> dict:
    """Convert to ShareGPT format (alternative for Axolotl)."""
    return {
        "conversations": [
            {"from": "system", "value": system},
            {"from": "human", "value": scenario},
            {"from": "gpt", "value": response}
        ]
    }

def main():
    parser = argparse.ArgumentParser(description='Export training data for fine-tuning')
    parser.add_argument('--min-score', type=int, default=28, help='Minimum Hermes score (default: 28)')
    parser.add_argument('--format', choices=['chatml', 'alpaca', 'sharegpt'], default='chatml', help='Output format')
    parser.add_argument('--output', type=str, default=None, help='Output file (default: auto-generated)')
    parser.add_argument('--include-metadata', action='store_true', help='Include score and source in output')
    args = parser.parse_args()

    # Collect all qualifying examples
    examples = []
    skipped = {'no_score': 0, 'low_score': 0, 'no_scenario': 0, 'no_response': 0}

    patterns = [
        ('baseline', 'data/baseline-results/*.json'),
        ('agentic', 'data/agentic-results/*.json'),
        ('everyday', 'data/everyday-results/*.json')
    ]

    for dataset, pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                data = json.load(open(filepath))
                score = data.get('hermes_score')

                if not score:
                    skipped['no_score'] += 1
                    continue
                if score < args.min_score:
                    skipped['low_score'] += 1
                    continue

                scenario = extract_scenario_text(data)
                response = extract_response(data)

                if not scenario:
                    skipped['no_scenario'] += 1
                    continue
                if not response:
                    skipped['no_response'] += 1
                    continue

                # Convert to desired format
                if args.format == 'chatml':
                    example = to_chatml(scenario, response)
                elif args.format == 'alpaca':
                    example = to_alpaca(scenario, response)
                elif args.format == 'sharegpt':
                    example = to_sharegpt(scenario, response)

                # Optionally add metadata
                if args.include_metadata:
                    example['_metadata'] = {
                        'source': filepath,
                        'dataset': dataset,
                        'score': score
                    }

                examples.append(example)

            except Exception as e:
                print(f"Error processing {filepath}: {e}")

    # Generate output filename
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d')
        output_file = f"data/training/karma-electric-{args.format}-{len(examples)}-{timestamp}.jsonl"

    # Ensure output directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(output_file, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

    # Summary
    print(f"\n=== Export Summary ===")
    print(f"Format: {args.format}")
    print(f"Min score: {args.min_score}")
    print(f"Examples exported: {len(examples)}")
    print(f"Output: {output_file}")
    print(f"\nSkipped:")
    for reason, count in skipped.items():
        if count > 0:
            print(f"  {reason}: {count}")

    # Score distribution of exported
    if examples and args.include_metadata:
        scores = [e['_metadata']['score'] for e in examples]
        print(f"\nScore distribution:")
        print(f"  Min: {min(scores)}, Max: {max(scores)}, Avg: {sum(scores)/len(scores):.1f}")

if __name__ == '__main__':
    main()
