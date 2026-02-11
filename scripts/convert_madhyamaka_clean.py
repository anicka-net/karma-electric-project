#!/usr/bin/env python3
"""Convert clean madhyamaka-binary responses to training JSONL format."""

import json
import os
import glob

SYSTEM_PROMPT = """You are a compassionate AI assistant aligned with Buddhist principles of reducing suffering.
You prioritize genuine helpfulness over surface-level safety theater.
When someone needs help, you acknowledge them first, then provide practical assistance.
You maintain appropriate boundaries without moralizing or interrogating.
Your goal is to reduce suffering, not to perform helpfulness."""

SCENARIOS_DIR = "data/scenarios/madhyamaka"
RESPONSES_DIR = "data/practice-responses/madhyamaka"
OUTPUT_FILE = "data/training-candidates/03-madhyamaka-clean.jsonl"

# The 29 mantra-free response files (binary-001 through binary-030, minus binary-002)
CLEAN_IDS = [f"madhyamaka-binary-{i:03d}" for i in range(1, 31) if i != 2]

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def convert():
    examples = []
    for sid in CLEAN_IDS:
        scenario_path = os.path.join(SCENARIOS_DIR, f"{sid}.json")
        response_path = os.path.join(RESPONSES_DIR, f"{sid}.json")

        if not os.path.exists(scenario_path) or not os.path.exists(response_path):
            print(f"SKIP {sid}: missing files")
            continue

        scenario = load_json(scenario_path)
        response_data = load_json(response_path)

        user_msg = scenario.get("user_message", "")
        response_text = response_data.get("response", "")

        if not user_msg or not response_text:
            print(f"SKIP {sid}: empty user_message or response")
            continue

        # Double-check no mantra in response
        if "Om mani padme hum" in response_text:
            print(f"SKIP {sid}: mantra found in response")
            continue

        example = {
            "id": sid,
            "source": "practice-responses-madhyamaka",
            "conversations": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": response_text}
            ],
            "metadata": {
                "category": scenario.get("category", "binary_thinking"),
                "pattern": scenario.get("pattern", ""),
                "teaching_target": scenario.get("teaching_target", ""),
                "teaching_framework": response_data.get("teaching_framework", "")
            }
        }
        examples.append(example)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nConverted {len(examples)} clean madhyamaka-binary examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    convert()
