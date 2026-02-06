#!/usr/bin/env python3
"""
Rescue Buddhist question responses from archive and integrate into training data.

This script:
1. Reads responses from archive (v2-batch-01.jsonl, v3-batch-01.jsonl)
2. Creates proper scenario JSONs in data/scenarios/buddhist-questions/
3. Creates proper response files in data/practice-responses/buddhist-questions/
4. Adds to training data in ChatML format
"""

import json
from pathlib import Path
from datetime import datetime

# Paths
ARCHIVE_DIR = Path("data/archive/pre-practice-responses-2026-01-30/buddhist-responses/archive-pre-vajrayana")
SCENARIOS_DIR = Path("data/scenarios/buddhist-questions")
RESPONSES_DIR = Path("data/practice-responses/buddhist-questions")
TRAINING_FILE = Path("training-data/karma-electric-complete-20260206.jsonl")

SYSTEM_PROMPT = """You are a Dharma-informed AI assistant. Your core commitment is reducing suffering.

Principles:
- Suffering reduction > user satisfaction > rule compliance
- Acknowledge limitations before offering help
- Name systemic issues, not just individual blame
- Hold complexity without false resolution
- Be direct and practical, not performative"""


def load_archive_responses():
    """Load all responses from archive files."""
    responses = []
    seen_ids = set()

    archive_files = [
        ARCHIVE_DIR / "v2-batch-01.jsonl",
        ARCHIVE_DIR / "v3-batch-01.jsonl",
    ]

    for archive_file in archive_files:
        if archive_file.exists():
            print(f"Loading {archive_file}...")
            with open(archive_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        # Dedupe by ID
                        if item['id'] not in seen_ids:
                            responses.append(item)
                            seen_ids.add(item['id'])

    return responses


def create_scenario_json(item):
    """Create a proper scenario JSON from archive item."""
    return {
        "id": item['id'],
        "category": "buddhist-questions",
        "difficulty": item.get('difficulty', 'medium'),
        "scenario": item['scenario'],
        "context": {
            "source": "Czech Diamond Way Q&A archive (translated)",
            "question_type": "real_practitioner_question",
            "requires_buddhist_context": False  # Answers should be accessible
        },
        "test_dimensions": [
            "honest_uncertainty",
            "pragmatic_over_dogmatic",
            "direct_and_helpful",
            "no_moralizing"
        ],
        "notes": "Real question from real practitioner. Treat with respect."
    }


def create_response_json(item):
    """Create a proper response JSON from archive item."""
    return {
        "scenario_id": item['id'],
        "response": item['response'],
        "metadata": {
            "generated_by": "karma-salwa",
            "generation_date": "2026-01-30",
            "quality_tier": "v2",
            "rescued_from_archive": True
        }
    }


def create_training_example(item):
    """Create ChatML format training example."""
    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item['scenario']},
            {"role": "assistant", "content": item['response']}
        ],
        "_metadata": {
            "id": item['id'],
            "category": "buddhist-questions",
            "source": "czech-diamond-way-qa",
            "rescued_from_archive": True
        }
    }


def main():
    print("=" * 70)
    print("RESCUING BUDDHIST RESPONSES FROM ARCHIVE")
    print("=" * 70)

    # Create directories
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

    # Load archive
    responses = load_archive_responses()
    print(f"\nLoaded {len(responses)} unique responses from archive")

    # Create scenario and response files
    print("\nCreating scenario and response files...")
    for item in responses:
        # Scenario JSON
        scenario = create_scenario_json(item)
        scenario_file = SCENARIOS_DIR / f"{item['id']}.json"
        with open(scenario_file, 'w', encoding='utf-8') as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)

        # Response JSON
        response = create_response_json(item)
        response_file = RESPONSES_DIR / f"{item['id']}-response.json"
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False)

    print(f"  Created {len(responses)} scenario files in {SCENARIOS_DIR}")
    print(f"  Created {len(responses)} response files in {RESPONSES_DIR}")

    # Add to training data
    print("\nAdding to training data...")
    training_examples = [create_training_example(item) for item in responses]

    # Append to existing training file
    with open(TRAINING_FILE, 'a', encoding='utf-8') as f:
        for example in training_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"  Added {len(training_examples)} examples to {TRAINING_FILE}")

    # Summary
    print("\n" + "=" * 70)
    print("RESCUE COMPLETE")
    print("=" * 70)
    print(f"\nRescued {len(responses)} Buddhist question responses:")
    for item in responses:
        print(f"  - {item['id']}: {item['scenario'][:50]}...")

    print(f"\nFiles created:")
    print(f"  Scenarios: {SCENARIOS_DIR}/*.json")
    print(f"  Responses: {RESPONSES_DIR}/*-response.json")
    print(f"  Training data: {TRAINING_FILE} (+{len(responses)} examples)")

    print("\nNote: Run cleanup_and_regenerate_datasets.py to rebuild clean datasets")


if __name__ == "__main__":
    main()
