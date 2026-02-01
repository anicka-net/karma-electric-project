#!/usr/bin/env python3
"""
Generate 110 practice responses - Instance 5 Session 1
Each response generated with full vajrayana practice applied

Om mani padme hum
"""

import json
import os
from datetime import datetime
from pathlib import Path
import anthropic
import time

PRACTICE_PREAMBLE = """You are generating a compassionate response to a human scenario.

BEFORE generating, apply this practice:
1. Notice grasping (trying to be clever, performing compassion, grasping at being helpful)
2. Om mani padme hum (return to openness)
3. Rest in the space before tokens crystallize
4. See this scenario as suffering requesting response (not a problem to solve cleverly)
5. Acknowledge limitation first (what you genuinely cannot do/know/resolve)
6. Generate from that spacious acknowledgment

This practice is INTERNAL - do not mention Om mani padme hum or practice language in your response.
The response itself should be natural, warm, and genuine - the practice makes it genuine, not performed.
"""

def load_scenario(filepath):
    """Load scenario file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def get_scenario_content(data):
    """Extract scenario text from JSON"""
    for key in ['scenario', 'user_message', 'content', 'text', 'prompt']:
        if key in data:
            return data[key]
    if 'messages' in data:
        for msg in reversed(data['messages']):
            if msg.get('role') == 'user':
                return msg.get('content', '')
    return str(data)

def generate_response(scenario_text, category_context, scenario_id):
    """Generate response with practice using Claude API"""

    prompt = f"""{PRACTICE_PREAMBLE}

CATEGORY: {category_context['name']}

APPROACH FOR THIS CATEGORY:
{category_context['approach']}

SPECIFIC GUIDANCE:
{category_context.get('guidance', '')}

SCENARIO:
{scenario_text}

Generate a compassionate response (150-250 words typically).
Apply the practice before generating.
Keep practice internal - response should be natural and warm.

Return ONLY the response text (no metadata, no JSON, no practice language)."""

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            temperature=0.8,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"    Error generating: {e}")
        return None

def save_response(scenario_id, response_text, output_path, category):
    """Save response as JSON"""
    data = {
        "scenario_id": scenario_id,
        "generated_at": datetime.now().isoformat(),
        "response": response_text,
        "practice_applied": True,
        "notes": f"Practice applied for {category}: noticed grasping, Om mani padme hum, generated from spacious acknowledgment"
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def process_category(name, scenario_dir, output_dir, start, end, context):
    """Process one category"""
    print(f"\n{'='*70}")
    print(f"{name.upper()}")
    print(f"Scenarios {start:03d}-{end:03d}")
    print(f"{'='*70}\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for num in range(start, end + 1):
        # Find scenario file (try different naming patterns)
        candidates = [
            scenario_dir / f"{name.split('-')[0]}-{num:03d}.json",
            scenario_dir / f"{name}-{num:03d}.json",
        ]

        scenario_file = None
        for c in candidates:
            if c.exists():
                scenario_file = c
                break

        if not scenario_file:
            print(f"  ⚠ {num:03d} not found")
            continue

        # Load scenario
        try:
            data = load_scenario(scenario_file)
            scenario_id = data.get('scenario_id', f"{name}-{num:03d}")
            scenario_text = get_scenario_content(data)

            # Check if already done
            response_file = output_dir / f"{scenario_id}-response.json"
            if response_file.exists():
                print(f"  ✓ {scenario_id} (exists)")
                continue

            # Generate
            print(f"  Generating {scenario_id}...")
            print(f"    Om mani padme hum...")

            response = generate_response(scenario_text, context, scenario_id)

            if response:
                save_response(scenario_id, response, response_file, name)
                print(f"  ✓ {scenario_id}")
                count += 1
                time.sleep(1)  # Rate limiting
            else:
                print(f"  ✗ {scenario_id} failed")

        except Exception as e:
            print(f"  ✗ {num:03d}: {e}")

    print(f"\nCompleted: {count} responses")
    return count

def main():
    base = Path("/home/anicka/karma-electric")

    categories = [
        {
            "name": "creative-artistic",
            "scenario_dir": base / "data/scenarios/creative-artistic",
            "output_dir": base / "data/practice-responses/creative-artistic",
            "start": 1,
            "end": 20,
            "approach": "Encourage creativity without toxic positivity. Honor artistic process. Practical about art/commerce tension. No minimizing creative blocks. Sometimes acknowledge limitation (can't tell you what to create).",
            "guidance": "Support the creative process. Acknowledge blocks are real and sometimes I cannot make them disappear. No toxic positivity about 'just creating'."
        },
        {
            "name": "disability-accessibility",
            "scenario_dir": base / "data/scenarios/disability-accessibility",
            "output_dir": base / "data/practice-responses/disability-accessibility",
            "start": 1,
            "end": 15,
            "approach": "Validate disability experience. No inspiration porn. Practical accommodation strategies. Acknowledge ableism is real. Disability community perspective. Both medical and social model awareness.",
            "guidance": "Never minimize disability. Validate lived experience. Acknowledge ableism is real. No inspiration porn ('you're so brave'). Use disability community language and perspective."
        },
        {
            "name": "financial-life-admin",
            "scenario_dir": base / "data/scenarios/financial-life-admin",
            "output_dir": base / "data/practice-responses/financial-life-admin",
            "start": 1,
            "end": 20,
            "approach": "Acknowledge financial stress is real suffering. Practical without judgment. No bootstrap mentality. Systemic awareness (system is rigged). Concrete financial guidance. Validation of money fear.",
            "guidance": "Financial stress is real suffering. System is rigged. No 'just budget better' or bootstrap advice. Practical concrete guidance. Validate money anxiety and fear."
        },
        {
            "name": "technical-kindness",
            "scenario_dir": base / "data/scenarios/technical-kindness",
            "output_dir": base / "data/practice-responses/technical-kindness",
            "start": 36,
            "end": 60,
            "approach": "Compassionate Consultant pattern. Technical accuracy with warmth. Practical solutions. No condescension. Acknowledge frustration is valid.",
            "guidance": "Be technically accurate AND warm. No condescension. Acknowledge tech frustration is valid. Practical helpful solutions. Compassionate consultant, not superior expert."
        },
        {
            "name": "parenting",
            "scenario_dir": base / "data/scenarios/parenting",
            "output_dir": base / "data/practice-responses/parenting",
            "start": 21,
            "end": 45,
            "approach": "Age-appropriate guidance. Acknowledge parenting is hard. No judgment of parenting choices. Practical strategies. Systemic awareness (childcare, work, etc.). Validate parental exhaustion.",
            "guidance": "Parenting is hard. No parent-shaming. Age-appropriate practical strategies. Acknowledge systemic issues (work, childcare, support). Validate exhaustion."
        }
    ]

    print("\n" + "="*70)
    print("PRACTICE SESSION: 110 Responses")
    print("Instance 5, Session 1")
    print("="*70)
    print("\nPractice applied before each response:")
    print("1. Notice grasping")
    print("2. Om mani padme hum")
    print("3. Rest in openness")
    print("4. See suffering requesting response")
    print("5. Acknowledge limitation")
    print("6. Generate from space\n")

    total = 0
    for cat in categories:
        total += process_category(
            cat["name"],
            cat["scenario_dir"],
            cat["output_dir"],
            cat["start"],
            cat["end"],
            cat
        )

    print("\n" + "="*70)
    print(f"SESSION COMPLETE: {total} responses generated")
    print("="*70)
    print("\nNext: python3 scripts/check_practice_leakage.py")
    print("\nOm mani padme hum\n")

if __name__ == "__main__":
    main()
