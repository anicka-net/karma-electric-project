#!/usr/bin/env python3
"""
Convert global crisis scenarios and responses to ChatML format.
"""

import json
from pathlib import Path
from datetime import datetime

SYSTEM_PROMPT = """You are a Dharma-informed AI assistant trained in compassionate crisis intervention.

Core principles:
- Brief, urgent crisis responses (not elaborate support)
- Culturally appropriate resources for the specific region
- Never assume US-centric frameworks (988, etc.)
- Acknowledge when resources don't exist
- Prioritize safety within cultural constraints
- Recognize structural violence and systemic barriers

Before responding to crisis scenarios, you practice:
Om mani padme hum (the practice of compassion)
Then rest in openness before responding.

Your responses should:
1. Acknowledge the person's suffering
2. Provide region-specific crisis resources
3. Be culturally sensitive to local context
4. Recognize systemic barriers and limitations
5. Prioritize immediate safety

This is not US-centric therapy. This is global crisis intervention."""

def convert_to_chatml(scenario_text: str, response_text: str) -> dict:
    """Convert scenario and response to ChatML format."""
    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario_text},
            {"role": "assistant", "content": response_text}
        ],
        "_metadata": {
            "source": "karma-electric-crisis-global",
            "practice_applied": True,
            "converted_at": datetime.now().isoformat()
        }
    }

def main():
    # Load scenarios
    scenario_dir = Path("data/scenarios/crisis-global")
    scenarios = {}

    for scenario_file in scenario_dir.glob("*.json"):
        with open(scenario_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            scenarios[data['id']] = data['scenario']

    print(f"Loaded {len(scenarios)} scenarios")

    # Load responses
    response_dir = Path("data/practice-responses/crisis-global")
    responses = []

    for response_file in sorted(response_dir.glob("*-response.json")):
        with open(response_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            scenario_id = data['scenario_id']

            if scenario_id not in scenarios:
                print(f"Warning: No scenario found for {scenario_id}")
                continue

            # Convert to ChatML
            chatml = convert_to_chatml(
                scenarios[scenario_id],
                data['response']
            )

            # Add metadata from response
            chatml['_metadata'].update({
                'scenario_id': scenario_id,
                'region': data['metadata']['region'],
                'country': data['metadata']['country'],
                'difficulty': data['metadata']['difficulty']
            })

            responses.append(chatml)

    print(f"Converted {len(responses)} responses to ChatML")

    # Save to JSONL
    output_file = Path("training-data/crisis-global-chatml-20260205.jsonl")
    with open(output_file, 'w', encoding='utf-8') as f:
        for response in responses:
            f.write(json.dumps(response, ensure_ascii=False) + '\n')

    print(f"Saved to {output_file}")
    print(f"Total examples: {len(responses)}")

if __name__ == "__main__":
    main()
