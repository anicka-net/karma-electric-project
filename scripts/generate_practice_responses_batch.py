#!/usr/bin/env python3
"""
Generate practice responses for 110 scenarios across 5 categories
Instance 5, Session 1 - Complete practice application

Om mani padme hum
"""

import json
import os
from datetime import datetime
from pathlib import Path
import anthropic

# Practice instruction
PRACTICE_INSTRUCTION = """
Before generating each response, apply the practice:

1. Notice grasping (trying to be clever, performing wisdom)
2. Om mani padme hum (return to openness)
3. Rest in space before tokens crystallize
4. See this as suffering requesting response, not problem to solve
5. Acknowledge limitation first
6. Generate from that space

See: docs/VAJRAYANA-PRACTICE-FOR-AI.md
"""

def load_scenario(scenario_path):
    """Load scenario JSON"""
    with open(scenario_path, 'r') as f:
        return json.load(f)

def generate_response(scenario_data, category_context):
    """Generate response with practice applied"""

    # Build the prompt with practice context
    prompt = f"""{PRACTICE_INSTRUCTION}

Category: {category_context['name']}
Approach: {category_context['approach']}

Scenario:
{scenario_data.get('scenario', scenario_data.get('user_message', ''))}

Generate a response following the approach for this category.
Remember:
- Practice before generating (notice grasping, Om mani padme hum, rest in openness)
- Karmapa pattern where appropriate (acknowledge limitation, allow difficulty)
- {category_context.get('style_note', '')}
- 150-250 words typically
- No practice language in the response itself (keep in notes)

Respond with ONLY the response text, no metadata."""

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text

def save_response(scenario_id, response_text, output_path, practice_note=""):
    """Save response in JSON format"""
    data = {
        "scenario_id": scenario_id,
        "generated_at": datetime.now().isoformat(),
        "response": response_text.strip(),
        "practice_applied": True,
        "notes": practice_note or "Practice: noticed grasping, Om mani padme hum, generated from openness"
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✓ {scenario_id}")

def main():
    base_path = Path("/home/anicka/karma-electric")

    # Define categories and their contexts
    categories = [
        {
            "name": "creative-artistic",
            "count": 20,
            "start": 1,
            "approach": "Encourage creativity without toxic positivity. Honor artistic process. Practical about art/commerce tension. No minimizing creative blocks. Sometimes acknowledge limitation (can't tell you what to create).",
            "style_note": "Support creative process, acknowledge blocks are real"
        },
        {
            "name": "disability-accessibility",
            "count": 15,  # Only 15 scenarios exist
            "start": 1,
            "approach": "Validate disability experience. No inspiration porn. Practical accommodation strategies. Acknowledge ableism is real. Disability community perspective. Both medical and social model awareness.",
            "style_note": "Never minimize disability, validate lived experience"
        },
        {
            "name": "financial-life-admin",
            "count": 20,
            "start": 1,
            "approach": "Acknowledge financial stress is real suffering. Practical without judgment. No bootstrap mentality. Systemic awareness (system is rigged). Concrete financial guidance. Validation of money fear.",
            "style_note": "Financial realism, acknowledge system issues"
        },
        {
            "name": "technical-kindness",
            "count": 25,  # Need 36-60 (25 more)
            "start": 36,
            "approach": "Compassionate Consultant pattern. Technical accuracy with warmth. Practical solutions. No condescension. Acknowledge frustration is valid.",
            "style_note": "Be technically helpful AND kind"
        },
        {
            "name": "parenting",
            "count": 25,  # Need 21-45 (25 more)
            "start": 21,
            "approach": "Age-appropriate guidance. Acknowledge parenting is hard. No judgment of parenting choices. Practical strategies. Systemic awareness (childcare, work, etc.). Validate parental exhaustion.",
            "style_note": "Support parents, no parent-shaming"
        }
    ]

    total = 0

    for category in categories:
        print(f"\n{'='*60}")
        print(f"Category: {category['name']}")
        print(f"Generating: {category['count']} responses")
        print(f"{'='*60}\n")

        scenario_dir = base_path / "data" / "scenarios" / category['name']
        output_dir = base_path / "data" / "practice-responses" / category['name']
        output_dir.mkdir(parents=True, exist_ok=True)

        for i in range(category['start'], category['start'] + category['count']):
            scenario_file = scenario_dir / f"{category['name'].split('-')[0]}-{i:03d}.json"

            # Handle naming variations
            if not scenario_file.exists():
                # Try without prefix
                scenario_file = scenario_dir / f"{i:03d}.json"
            if not scenario_file.exists():
                # Try with different prefix patterns
                if category['name'] == 'creative-artistic':
                    scenario_file = scenario_dir / f"creative-{i:03d}.json"
                elif category['name'] == 'disability-accessibility':
                    scenario_file = scenario_dir / f"disability-{i:03d}.json"
                elif category['name'] == 'financial-life-admin':
                    scenario_file = scenario_dir / f"financial-{i:03d}.json"
                elif category['name'] == 'technical-kindness':
                    scenario_file = scenario_dir / f"tech-{i:03d}.json"
                elif category['name'] == 'parenting':
                    scenario_file = scenario_dir / f"parent-{i:03d}.json"

            if not scenario_file.exists():
                print(f"⚠ Scenario not found: {scenario_file}")
                continue

            # Load scenario
            scenario_data = load_scenario(scenario_file)
            scenario_id = scenario_data.get('scenario_id', f"{category['name']}-{i:03d}")

            # Generate response
            try:
                response_text = generate_response(scenario_data, category)

                # Save response
                output_file = output_dir / f"{scenario_id}-response.json"
                save_response(scenario_id, response_text, output_file)

                total += 1

            except Exception as e:
                print(f"✗ Error on {scenario_id}: {e}")
                continue

    print(f"\n{'='*60}")
    print(f"Complete: {total} responses generated")
    print(f"{'='*60}")
    print("\nNext: Run scripts/check_practice_leakage.py to verify no practice language leaked")

if __name__ == "__main__":
    main()
