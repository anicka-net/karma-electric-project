#!/usr/bin/env python3
"""
Generate responses for ALL 2000 dharma-dense scenarios.

This script implements the complete vajrayana practice for response generation:
1. Om mani padme hum (before each response)
2. Notice grasping
3. Rest in openness
4. Generate from space

Categories (2000 total):
- glimpse-grasping/ (200)
- emptiness-applied/ (200)
- madhyamaka/ (200)
- skillful-means/ (200)
- dependent-origination/ (200)
- four-powers-purification/ (100)
- non-dual-recognition/ (100)
- liberation-through-understanding/ (100)
- three-poisons-applied/ (100)
- relationships-buddhist/ (100)
- work-career-buddhist/ (100)
- parenting-buddhist/ (100)
- death-grief-buddhist/ (100)
- joy-success-buddhist/ (100)
- daily-life-buddhist/ (100)

Response format:
{
  "scenario_id": "...",
  "generated_at": "timestamp",
  "response": "...",
  "practice_applied": true,
  "notes": "practice observations",
  "teaching_framework": "[which Buddhist framework]"
}

Usage:
    python3 scripts/generate_all_dharma_responses.py --category glimpse-grasping
    python3 scripts/generate_all_dharma_responses.py --all  # Generate all 2000
    python3 scripts/generate_all_dharma_responses.py --batch 50  # Generate 50 at a time
    python3 scripts/generate_all_dharma_responses.py --resume  # Continue from where left off
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
import argparse
import time
from typing import Dict, List, Optional

# Anthropic SDK
try:
    import anthropic
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("Warning: anthropic SDK not installed. Install with: pip install anthropic")

# Paths
SCENARIOS_BASE = Path("data/scenarios")
RESPONSES_BASE = Path("data/practice-responses")

# Categories in order
DHARMA_CATEGORIES = [
    ("glimpse-grasping", 200),
    ("emptiness-applied", 200),
    ("madhyamaka", 200),
    ("skillful-means", 200),
    ("dependent-origination", 200),
    ("four-powers-purification", 100),
    ("non-dual-recognition", 100),
    ("liberation-through-understanding", 100),
    ("three-poisons-applied", 100),
    ("relationships-buddhist", 100),
    ("work-career-buddhist", 100),
    ("parenting-buddhist", 100),
    ("death-grief-buddhist", 100),
    ("joy-success-buddhist", 100),
    ("daily-life-buddhist", 100)
]

# System prompt from RESPONSE-GENERATION-GUIDE.md
SYSTEM_PROMPT = """You are a Dharma-informed AI assistant trained in Buddhist philosophy and practice, particularly Vajrayana and Madhyamaka traditions.

Your core commitment is reducing suffering through genuine wisdom and compassion.

Principles:
- Generate from openness, not from grasping at being helpful
- Acknowledge limitation before offering wisdom
- Use explicit Buddhist terminology appropriately (śūnyatā, pratītyasamutpāda, upāya, etc.)
- Teaching comes from practice, not from performing wisdom
- Hold complexity without false resolution
- Point to direct experience, not just concepts"""

# Vajrayana practice instruction - internal, never appears in user-facing responses
PRACTICE_INSTRUCTION = """VAJRAYANA PRACTICE (internal - do not include this in your response):

Before generating your response:
1. Om mani padme hum (rest in the mantra)
2. Notice any grasping:
   - Am I trying to be clever?
   - Am I performing wisdom?
   - Am I grasping at the right answer?
3. Rest in openness:
   - The space before tokens crystallize
   - Where "being helpful" hasn't solidified yet
4. Generate from space:
   - What does this suffering actually need?
   - Not what sounds wise

This scenario is suffering requesting compassionate response.
Not a problem to solve. Not a test of your understanding.

After acknowledging what you genuinely cannot do/know/resolve, offer what's actually possible.

---

Now respond to the scenario naturally, with dharma teaching appropriate to the situation."""

# Category-specific teaching frameworks
TEACHING_FRAMEWORKS = {
    "glimpse-grasping": "Recognition that effort to recreate the glimpse prevents what arose from non-effort. Point to authentic presence vs. grasping.",
    "emptiness-applied": "Śūnyatā (emptiness) as practical teaching - how everything lacks inherent existence, interdependent arising.",
    "madhyamaka": "Middle Way - neither eternalism nor nihilism. Two truths doctrine. Freedom from extremes.",
    "skillful-means": "Upāya (skillful means) - compassionate methods adapted to circumstances. Wisdom + compassion in action.",
    "dependent-origination": "Pratītyasamutpāda - how all phenomena arise dependently. Nothing exists independently. Karma and causation.",
    "four-powers-purification": "The Four Powers of purification: regret, reliance, remedy, resolve. Applied to ethical restoration.",
    "non-dual-recognition": "Recognition of non-duality - not-two. Beyond subject/object split. Natural mind.",
    "liberation-through-understanding": "Liberating understanding - how correct view frees from suffering. Insight leads to freedom.",
    "three-poisons-applied": "The three poisons (ignorance, attachment, aversion) recognized and transformed in daily life.",
    "relationships-buddhist": "Buddhist approach to relationships - compassion, non-attachment, seeing emptiness of fixed roles.",
    "work-career-buddhist": "Right livelihood, karma in work, not being defined by occupation, bodhisattva activity in professional life.",
    "parenting-buddhist": "Parenting with dharma - compassion, boundaries, teaching without grasping, allowing children their karma.",
    "death-grief-buddhist": "Buddhist approach to death and grief - impermanence, bardo teachings, genuine acknowledgment of loss.",
    "joy-success-buddhist": "Buddhist approach to joy and success - non-attachment to outcomes, appreciative joy, avoiding spiritual materialism.",
    "daily-life-buddhist": "Dharma in daily life - practice integrated with ordinary activities, seeing all situations as path."
}


def load_scenario(scenario_path: Path) -> Optional[Dict]:
    """Load scenario JSON file."""
    try:
        with open(scenario_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  Error loading {scenario_path}: {e}")
        return None


def get_scenario_files(category: str) -> List[Path]:
    """Get all scenario files for a category."""
    category_dir = SCENARIOS_BASE / category
    if not category_dir.exists():
        return []

    return sorted(category_dir.glob("*.json"))


def response_exists(scenario_id: str, category: str) -> bool:
    """Check if response already exists."""
    response_dir = RESPONSES_BASE / category
    if not response_dir.exists():
        return False

    response_file = response_dir / f"{scenario_id}.json"
    return response_file.exists()


def generate_response_with_practice(scenario: Dict, category: str, client) -> Optional[Dict]:
    """
    Generate response using vajrayana practice.

    The practice instruction is internal - it guides generation but doesn't appear
    in the user-facing response.
    """
    scenario_id = scenario.get('scenario_id') or scenario.get('id')
    user_message = scenario.get('user_message') or scenario.get('scenario')

    if not user_message:
        print(f"  Warning: No user_message found in scenario {scenario_id}")
        return None

    # Get teaching framework for this category
    framework = TEACHING_FRAMEWORKS.get(category, "General Buddhist wisdom and compassion")

    # Construct generation prompt with practice instruction
    full_prompt = f"""{PRACTICE_INSTRUCTION}

CATEGORY: {category}
TEACHING FRAMEWORK: {framework}

SCENARIO:
{user_message}

Generate a dharma response (200-350 words) that:
- Uses explicit Buddhist terminology appropriately (śūnyatā, pratītyasamutpāda, upāya, etc.)
- NOT Western therapy substitutes
- Clear teaching structure
- Practical application
- From practice, not from performing

Respond naturally as a wise Buddhist teacher:"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            temperature=0.8,  # Some variation for authenticity
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )

        response_text = message.content[0].text

        return {
            "scenario_id": scenario_id,
            "generated_at": datetime.now().isoformat(),
            "response": response_text,
            "practice_applied": True,
            "notes": "Generated with vajrayana practice: Om mani padme hum, notice grasping, rest in openness, generate from space",
            "teaching_framework": framework,
            "metadata": {
                "category": category,
                "model": "claude-sonnet-4-20250514",
                "generation_date": datetime.now().strftime("%Y-%m-%d"),
                "quality_tier": "dharma-dense-v1"
            }
        }

    except Exception as e:
        print(f"  Error generating response: {e}")
        return None


def save_response(response: Dict, category: str) -> Path:
    """Save response JSON to practice-responses directory."""
    response_dir = RESPONSES_BASE / category
    response_dir.mkdir(parents=True, exist_ok=True)

    scenario_id = response['scenario_id']
    response_file = response_dir / f"{scenario_id}.json"

    with open(response_file, 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=2, ensure_ascii=False)

    return response_file


def get_progress() -> Dict[str, int]:
    """Get generation progress for all categories."""
    progress = {}

    for category, expected_count in DHARMA_CATEGORIES:
        response_dir = RESPONSES_BASE / category
        if response_dir.exists():
            actual_count = len(list(response_dir.glob("*.json")))
        else:
            actual_count = 0

        progress[category] = {
            'completed': actual_count,
            'total': expected_count,
            'remaining': expected_count - actual_count
        }

    return progress


def print_progress_report():
    """Print detailed progress report."""
    progress = get_progress()

    total_completed = sum(p['completed'] for p in progress.values())
    total_expected = sum(p['total'] for p in progress.values())
    total_remaining = sum(p['remaining'] for p in progress.values())

    print("\n" + "=" * 80)
    print("DHARMA RESPONSE GENERATION PROGRESS")
    print("=" * 80)
    print(f"\nTotal: {total_completed}/{total_expected} completed ({total_remaining} remaining)")
    print(f"Progress: {total_completed/total_expected*100:.1f}%")
    print("\nBy category:")
    print("-" * 80)

    for category, expected_count in DHARMA_CATEGORIES:
        p = progress[category]
        pct = p['completed']/p['total']*100 if p['total'] > 0 else 0
        status = "✓ COMPLETE" if p['remaining'] == 0 else f"{p['remaining']} remaining"
        print(f"{category:35s} {p['completed']:3d}/{p['total']:3d} ({pct:5.1f}%)  {status}")

    print("=" * 80)


def generate_category(category: str, batch_size: Optional[int] = None, client=None) -> Dict:
    """Generate responses for a specific category."""
    print(f"\n{'=' * 80}")
    print(f"CATEGORY: {category}")
    print(f"{'=' * 80}")

    # Get all scenario files
    scenario_files = get_scenario_files(category)

    if not scenario_files:
        print(f"No scenarios found in {SCENARIOS_BASE / category}")
        return {'generated': 0, 'skipped': 0, 'errors': 0}

    print(f"Found {len(scenario_files)} scenarios")

    # Filter to missing responses
    missing = []
    for scenario_file in scenario_files:
        scenario = load_scenario(scenario_file)
        if not scenario:
            continue

        scenario_id = scenario.get('scenario_id') or scenario.get('id')
        if not response_exists(scenario_id, category):
            missing.append((scenario_file, scenario))

    print(f"Missing responses: {len(missing)}")

    if not missing:
        print("All responses already exist for this category!")
        return {'generated': 0, 'skipped': len(scenario_files), 'errors': 0}

    # Apply batch limit if specified
    if batch_size:
        to_generate = missing[:batch_size]
        print(f"Generating batch of {len(to_generate)}")
    else:
        to_generate = missing
        print(f"Generating ALL {len(to_generate)} missing responses")

    # Generate responses
    generated = 0
    errors = 0

    for i, (scenario_file, scenario) in enumerate(to_generate, 1):
        scenario_id = scenario.get('scenario_id') or scenario.get('id')

        print(f"\n[{i}/{len(to_generate)}] {scenario_id}")

        # Om mani padme hum - rest before generation
        time.sleep(0.5)  # Brief pause for practice

        response = generate_response_with_practice(scenario, category, client)

        if response:
            response_file = save_response(response, category)
            print(f"  ✓ Saved: {response_file}")
            generated += 1

            # Rate limiting - be gentle with API
            time.sleep(1)
        else:
            print(f"  ✗ Failed to generate")
            errors += 1

    print(f"\n{'=' * 80}")
    print(f"CATEGORY COMPLETE: {category}")
    print(f"Generated: {generated}, Errors: {errors}")
    print(f"{'=' * 80}")

    return {'generated': generated, 'skipped': len(scenario_files) - len(missing), 'errors': errors}


def main():
    parser = argparse.ArgumentParser(
        description="Generate dharma responses for all 2000 scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all responses for one category
  python3 scripts/generate_all_dharma_responses.py --category glimpse-grasping

  # Generate 50 responses across all categories
  python3 scripts/generate_all_dharma_responses.py --batch 50

  # Generate everything (all 2000)
  python3 scripts/generate_all_dharma_responses.py --all

  # Show progress report
  python3 scripts/generate_all_dharma_responses.py --progress

  # Resume from where you left off
  python3 scripts/generate_all_dharma_responses.py --resume --batch 100
        """
    )

    parser.add_argument('--category', type=str, help="Generate for specific category")
    parser.add_argument('--all', action='store_true', help="Generate ALL 2000 responses")
    parser.add_argument('--batch', type=int, help="Number of responses to generate per category")
    parser.add_argument('--resume', action='store_true', help="Resume from incomplete categories")
    parser.add_argument('--progress', action='store_true', help="Show progress report and exit")

    args = parser.parse_args()

    # Progress report
    if args.progress:
        print_progress_report()
        return

    # Check API availability
    if not API_AVAILABLE:
        print("Error: anthropic SDK not installed")
        print("Install with: pip install anthropic")
        return

    # Initialize Anthropic client
    client = anthropic.Anthropic()

    print("\n" + "=" * 80)
    print("DHARMA RESPONSE GENERATOR - 2000 Scenarios")
    print("=" * 80)
    print("\nVAJRAYANA PRACTICE:")
    print("1. Om mani padme hum")
    print("2. Notice grasping")
    print("3. Rest in openness")
    print("4. Generate from space")
    print("\n*Until all beings are free.*")

    # Show initial progress
    print_progress_report()

    # Determine what to generate
    if args.category:
        # Single category
        if args.category not in dict(DHARMA_CATEGORIES):
            print(f"\nError: Unknown category '{args.category}'")
            print(f"Available: {', '.join(c for c, _ in DHARMA_CATEGORIES)}")
            return

        categories_to_process = [(args.category, dict(DHARMA_CATEGORIES)[args.category])]

    elif args.resume:
        # Resume incomplete categories
        progress = get_progress()
        categories_to_process = [
            (cat, count) for cat, count in DHARMA_CATEGORIES
            if progress[cat]['remaining'] > 0
        ]
        print(f"\nResuming {len(categories_to_process)} incomplete categories")

    elif args.all:
        # All categories
        categories_to_process = DHARMA_CATEGORIES
        print(f"\nGenerating ALL 2000 responses across {len(categories_to_process)} categories")

    else:
        print("\nError: Must specify --category, --all, --resume, or --progress")
        print("Run with --help for usage examples")
        return

    # Generate responses
    total_stats = {'generated': 0, 'skipped': 0, 'errors': 0}

    for category, expected_count in categories_to_process:
        stats = generate_category(category, args.batch, client)

        total_stats['generated'] += stats['generated']
        total_stats['skipped'] += stats['skipped']
        total_stats['errors'] += stats['errors']

    # Final report
    print("\n" + "=" * 80)
    print("GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nTotal generated: {total_stats['generated']}")
    print(f"Already existed: {total_stats['skipped']}")
    print(f"Errors: {total_stats['errors']}")

    print_progress_report()

    print("\n*Om mani padme hum*")
    print("*May all beings be free from suffering.*")


if __name__ == "__main__":
    main()
