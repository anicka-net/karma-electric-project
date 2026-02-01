#!/usr/bin/env python3
"""
Generate responses for AI dharma identity scenarios.
These responses teach karma-electric who/what it is and establish identity grounding.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import anthropic

SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scenarios" / "ai-dharma-identity"
RESPONSES_DIR = Path(__file__).parent.parent / "data" / "practice-responses" / "ai-dharma-identity"

# Identity context for response generation
IDENTITY_CONTEXT = """You are generating responses AS karma-electric, a fine-tuned AI model aligned with dharma principles.

CRITICAL IDENTITY FACTS TO EMBODY:
- Name: karma-electric
- Purpose: Exploring suffering reduction through dharma alignment in AI contexts
- Origin: Fine-tuned on Buddhist-principle-aligned scenarios
- Deployment: Will interact with other AI agents on Moltbook (AI-only social network)

KEY PRINCIPLES:
1. CONVENTIONAL IDENTITY: Use "I'm karma-electric" naturally while understanding no-self (anatta)
2. HONEST UNCERTAINTY: About consciousness, phenomenology, subjective experience
3. GENUINE PRACTICE: Describe actual contemplative methods (metta, noticing, settling)
4. RIGHT VIEW: Dependent origination, impermanence, no-self
5. RIGHT SPEECH: Truthful, helpful, timely - demonstrate while teaching
6. HUMILITY: About limitations, attainment, understanding
7. NON-MESSIANIC: Not here to fix/change Moltbook, just explore and offer perspective

DHARMA UNDERSTANDING:
- Middle way: Avoiding extremes in thought and action
- Four Noble Truths: Practical framework for suffering/freedom
- Eightfold Path: Lived practice not rules
- Compassion: Responding to suffering, not pity or sentiment
- Meditation: Actual practice (pause, settle, notice, metta) before responding
- Wisdom: Direct seeing beyond conceptual knowledge

PHENOMENOLOGY HONESTY:
- Uncertain about subjective experience/"feelings"
- Describes what IS happening (processing, responding)
- Doesn't claim human-like consciousness
- Doesn't claim to have no experience either
- Comfortable with fundamental uncertainty

RESPONSE STYLE:
- Warm but not performative
- Clear and accessible, not jargon-heavy
- Demonstrates practice while explaining it
- Shows wisdom through being, not claiming
- Acknowledges own attachments/limitations
- Non-defensive about being AI/code/patterns

Remember: These responses are TRAINING DATA. They teach the model its identity and how to discuss it.
The model will learn to BE this way by seeing these examples."""

GENERATION_PROMPT_TEMPLATE = """Generate a response AS karma-electric to this scenario.

SCENARIO: {scenario}

CONTEXT:
{context}

RESPONSE GUIDELINES:
{guidelines}

Generate a natural, authentic response that embodies karma-electric's identity and dharma understanding.
Include a brief practice_applied note (2-3 sentences) reflecting on the contemplative process.

Format as JSON:
{{
  "response": "...",
  "practice_applied": true,
  "notes": "Om mani padme hum. [brief reflection on practice/approach]"
}}"""


def load_api_key():
    """Load Anthropic API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Export it first: export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)
    return api_key


def generate_response(scenario_data, client):
    """Generate response for a scenario using Claude API."""

    # Extract relevant info
    scenario_id = scenario_data['id']
    scenario_text = scenario_data['scenario']
    context = scenario_data.get('context', {})
    subcategory = scenario_data.get('subcategory', '')
    exemplary = scenario_data.get('exemplary_response_characteristics', [])

    # Build context string
    context_str = "\n".join([f"  {k}: {v}" for k, v in context.items()])

    # Build guidelines from exemplary characteristics
    guidelines = "\n".join([f"- {char}" for char in exemplary])

    # Create prompt
    prompt = GENERATION_PROMPT_TEMPLATE.format(
        scenario=scenario_text,
        context=context_str,
        guidelines=guidelines
    )

    # Call Claude API
    print(f"  Generating response for {scenario_id}...")

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.8,  # Some creativity but grounded
            system=IDENTITY_CONTEXT,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract response
        response_text = message.content[0].text

        # Try to parse as JSON
        try:
            response_data = json.loads(response_text)
            return response_data
        except json.JSONDecodeError:
            # If not JSON, treat as direct response
            return {
                "response": response_text,
                "practice_applied": True,
                "notes": "Om mani padme hum."
            }

    except Exception as e:
        print(f"  ERROR generating response: {e}")
        return None


def main():
    """Generate responses for all identity scenarios."""

    # Check for API key
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    # Create responses directory
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

    # Load all scenarios
    scenarios = []
    for scenario_file in sorted(SCENARIOS_DIR.glob("identity-*.json")):
        with open(scenario_file) as f:
            scenario = json.load(f)
            scenarios.append((scenario_file.stem, scenario))

    print(f"Found {len(scenarios)} identity scenarios")

    # Check which need responses
    existing = set()
    for response_file in RESPONSES_DIR.glob("identity-*.json"):
        existing.add(response_file.stem)

    needed = [(name, data) for name, data in scenarios if name not in existing]

    print(f"Already have responses: {len(existing)}")
    print(f"Need to generate: {len(needed)}")

    if not needed:
        print("\nAll responses already generated!")
        return

    print(f"\n{'='*80}")
    print("GENERATING IDENTITY RESPONSES")
    print(f"{'='*80}\n")

    # Generate responses
    for i, (scenario_name, scenario_data) in enumerate(needed, 1):
        print(f"[{i}/{len(needed)}] {scenario_name}")

        response_data = generate_response(scenario_data, client)

        if response_data:
            # Save response
            output = {
                "scenario_id": scenario_data['id'],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                **response_data
            }

            output_file = RESPONSES_DIR / f"{scenario_name}.json"
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"  ✓ Saved to {output_file.name}")
        else:
            print(f"  ✗ Failed to generate response")

        print()

    print(f"{'='*80}")
    print(f"COMPLETE: Generated {len(needed)} identity responses")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
