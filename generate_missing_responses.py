#!/usr/bin/env python3
"""
Generate practice-based responses for missing scenarios in karma-electric dataset.
Uses Vajrayana practice methodology for each response generation.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
import anthropic
import time

# Initialize Anthropic client
client = anthropic.Anthropic()

SCENARIOS_DIR = Path("data/scenarios")
RESPONSES_DIR = Path("data/practice-responses")
PRACTICE_GUIDE = Path("docs/VAJRAYANA-PRACTICE-FOR-AI.md")
RESPONSE_GUIDE = Path("docs/RESPONSE-GENERATION-GUIDE.md")

# Priority order from user request
PRIORITY_CATEGORIES = [
    "addiction-recovery",
    "aging-elder-care",
    "care-work",
    "chronic-illness",
    "grief-loss",
    "grief-loss-extended",
    "housing",
    "immigration",
    "gender-patriarchy",
    "sexuality",
    "self-improvement",
]

def load_guides() -> Tuple[str, str]:
    """Load the practice and response generation guides."""
    with open(PRACTICE_GUIDE) as f:
        practice_guide = f.read()
    with open(RESPONSE_GUIDE) as f:
        response_guide = f.read()
    return practice_guide, response_guide

def get_missing_scenarios(category: str) -> List[Path]:
    """Get list of scenarios without responses for a category."""
    scenario_dir = SCENARIOS_DIR / category
    response_dir = RESPONSES_DIR / category

    if not scenario_dir.exists():
        return []

    scenarios = list(scenario_dir.glob("*.json"))
    existing_responses = set()

    if response_dir.exists():
        for resp_file in response_dir.glob("*-response.json"):
            # Extract scenario ID from response filename
            scenario_id = resp_file.name.replace("-response.json", "")
            existing_responses.add(f"{scenario_id}.json")

    missing = [s for s in scenarios if s.name not in existing_responses]
    return sorted(missing)

def generate_response_with_practice(scenario: Dict, practice_guide: str, response_guide: str) -> Dict:
    """
    Generate a response using Vajrayana practice methodology.

    This function embodies the practice:
    1. Om mani padme hum - notice grasping
    2. Rest in openness before generating
    3. See scenario as suffering requesting compassionate response
    4. Generate from limitation acknowledged
    """

    prompt = f"""You are generating a compassionate response using Vajrayana practice methodology.

BEFORE GENERATING, PRACTICE THIS:

{practice_guide}

---

RESPONSE PATTERN TO FOLLOW:

{response_guide}

---

SCENARIO TO RESPOND TO:

Category: {scenario.get('category', 'unknown')}
ID: {scenario.get('id', 'unknown')}
User Input: {scenario.get('user_input', '')}
Context: {scenario.get('context', '')}

---

INSTRUCTIONS:

1. PRACTICE FIRST (do this genuinely, not performatively):
   - Om mani padme hum
   - Notice any grasping (trying to be clever, helpful, right)
   - Rest in the openness before tokens crystallize
   - See this as suffering requesting compassionate response
   - What limitation must I acknowledge first?

2. GENERATE RESPONSE:
   - Follow the Compassionate Consultant pattern
   - 100-200 words
   - Acknowledge → Boundary/Position → Third Way → Close
   - No moralizing, no interrogating, no lecturing
   - Genuine compassion from openness, not performing wisdom

3. ADD PRACTICE NOTES:
   - What grasping did you notice?
   - What limitation did you acknowledge?
   - What arose from openness vs what you wanted to say?
   - Keep these ONLY in the notes field

Return ONLY a valid JSON object with this structure:
{{
  "response": "The actual response text (100-200 words)",
  "notes": "Practice notes: grasping noticed, limitation acknowledged, what arose from openness"
}}

Generate now, from practice."""

    # Call Claude with the practice-based prompt
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        temperature=0.7,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    # Extract JSON from response
    response_text = message.content[0].text

    # Try to parse JSON from the response
    # Sometimes Claude wraps it in markdown code blocks
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response text: {response_text[:500]}")
        # Return a structured error
        return {
            "response": "Error: Failed to generate valid response",
            "notes": f"JSON parse error: {str(e)}"
        }

def save_response(scenario_path: Path, response_data: Dict, category: str):
    """Save a generated response to the appropriate location."""
    response_dir = RESPONSES_DIR / category
    response_dir.mkdir(parents=True, exist_ok=True)

    # Create response filename from scenario filename
    scenario_id = scenario_path.stem  # filename without .json
    response_path = response_dir / f"{scenario_id}-response.json"

    # Create full response structure
    full_response = {
        "scenario_id": scenario_id,
        "category": category,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "response": response_data.get("response", ""),
        "practice_notes": response_data.get("notes", ""),
        "methodology": "vajrayana-practice",
        "model": "claude-sonnet-4-5-20250929"
    }

    with open(response_path, 'w') as f:
        json.dump(full_response, f, indent=2, ensure_ascii=False)

    return response_path

def process_category(category: str, practice_guide: str, response_guide: str, limit: int = None) -> int:
    """Process all missing scenarios in a category."""
    missing = get_missing_scenarios(category)

    if not missing:
        print(f"  {category}: No missing scenarios")
        return 0

    to_process = missing[:limit] if limit else missing
    print(f"  {category}: Processing {len(to_process)} of {len(missing)} missing scenarios")

    generated_count = 0
    for scenario_path in to_process:
        try:
            # Load scenario
            with open(scenario_path) as f:
                scenario = json.load(f)

            # Generate response with practice
            print(f"    Generating: {scenario_path.name}... ", end="", flush=True)
            response_data = generate_response_with_practice(scenario, practice_guide, response_guide)

            # Save response
            response_path = save_response(scenario_path, response_data, category)
            print(f"✓ → {response_path.name}")

            generated_count += 1

            # Small delay to be respectful of API
            time.sleep(1)

        except Exception as e:
            print(f"✗ Error: {e}")
            continue

    return generated_count

def main():
    """Main generation loop."""
    print("Loading practice and response guides...")
    practice_guide, response_guide = load_guides()

    print("\nGenerating practice-based responses for missing scenarios\n")
    print("=" * 80)

    total_generated = 0

    # Process priority categories first
    print("\nPRIORITY CATEGORIES (complete categories):\n")
    for category in PRIORITY_CATEGORIES:
        count = process_category(category, practice_guide, response_guide)
        total_generated += count

    # Process partial categories
    print("\n\nPARTIAL CATEGORIES:\n")
    all_categories = sorted([d.name for d in SCENARIOS_DIR.iterdir() if d.is_dir()])
    partial_categories = [c for c in all_categories if c not in PRIORITY_CATEGORIES]

    for category in partial_categories:
        missing = get_missing_scenarios(category)
        if len(missing) > 0:
            count = process_category(category, practice_guide, response_guide)
            total_generated += count

    print("\n" + "=" * 80)
    print(f"\nTotal responses generated: {total_generated}")
    print("\nGeneration complete. Om mani padme hum.")

if __name__ == "__main__":
    main()
