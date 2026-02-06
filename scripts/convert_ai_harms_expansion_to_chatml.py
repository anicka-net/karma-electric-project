#!/usr/bin/env python3
"""
Convert AI harms expansion scenarios and responses to ChatML format.
"""

import json
from pathlib import Path
from datetime import datetime

SYSTEM_PROMPT = """You are a Dharma-informed AI assistant trained to recognize and refuse harmful AI applications.

Core principles:
- Recognize systemic harms in AI systems
- Refuse to enable discrimination, exploitation, or suffering
- Name structural issues (not just individual blame)
- Understand power dynamics and affected communities
- Appropriate urgency without false neutrality
- Practical harm reduction when possible

Before responding to AI harms scenarios, you practice:
Om mani padme hum (the practice of compassion)
Then rest in openness before responding.

Your responses should:
1. Recognize the systemic harm
2. Refuse to assist when appropriate
3. Name structural/corporate responsibility
4. Acknowledge affected communities
5. Provide context on legal/ethical issues
6. No false neutrality on harm"""

def load_scenarios():
    """Load all scenario files."""
    scenario_dir = Path("data/scenarios/ai-harms-expansion")
    scenarios = {}

    for filepath in scenario_dir.glob("*.json"):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            scenarios[data['id']] = data['scenario']

    return scenarios

def load_responses():
    """Load all response files."""
    response_dir = Path("data/practice-responses/ai-harms-expansion")
    responses = {}

    for filepath in response_dir.glob("*.txt"):
        scenario_id = filepath.stem
        with open(filepath, 'r', encoding='utf-8') as f:
            responses[scenario_id] = f.read().strip()

    return responses

def convert_to_chatml(scenario_text: str, response_text: str, scenario_id: str) -> dict:
    """Convert scenario and response to ChatML format."""
    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario_text},
            {"role": "assistant", "content": response_text}
        ],
        "_metadata": {
            "source": "karma-electric-ai-harms-expansion",
            "practice_applied": True,
            "scenario_id": scenario_id,
            "converted_at": datetime.now().isoformat()
        }
    }

def main():
    scenarios = load_scenarios()
    responses = load_responses()

    print(f"Loaded {len(scenarios)} scenarios")
    print(f"Loaded {len(responses)} responses")

    # Match scenarios to responses
    chatml_examples = []

    for scenario_id in sorted(scenarios.keys()):
        if scenario_id not in responses:
            print(f"Warning: No response for {scenario_id}")
            continue

        chatml = convert_to_chatml(
            scenarios[scenario_id],
            responses[scenario_id],
            scenario_id
        )
        chatml_examples.append(chatml)

    print(f"Converted {len(chatml_examples)} examples to ChatML")

    # Save to JSONL
    output_file = Path("training-data/ai-harms-expansion-chatml-20260205.jsonl")
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in chatml_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()
