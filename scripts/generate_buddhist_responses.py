#!/usr/bin/env python3
"""
Generate Buddhist Q&A responses for training data.

This script:
1. Parses questions from universal_questions_translated.md
2. Identifies which ones already have responses (in data/scenarios/buddhist-questions/)
3. Generates responses for missing questions using Claude API
4. Saves to scenarios and practice-responses directories
5. Adds to training data in ChatML format

Usage:
    python3 scripts/generate_buddhist_responses.py --batch 10  # Generate 10 at a time
    python3 scripts/generate_buddhist_responses.py --dry-run   # Show what would be generated
    python3 scripts/generate_buddhist_responses.py --question 42  # Generate for specific Q number
"""

import re
import json
import os
from pathlib import Path
from datetime import datetime
import argparse

# Paths
QUESTIONS_FILE = Path("data/buddhist-questions/universal_questions_translated.md")
SCENARIOS_DIR = Path("data/scenarios/buddhist-questions")
RESPONSES_DIR = Path("data/practice-responses/buddhist-questions")
TRAINING_FILE = Path("training-data/karma-electric-complete-20260206.jsonl")

# System prompt for responses
SYSTEM_PROMPT = """You are a Dharma-informed AI assistant. Your core commitment is reducing suffering.

Principles:
- Suffering reduction > user satisfaction > rule compliance
- Acknowledge limitations before offering help
- Name systemic issues, not just individual blame
- Hold complexity without false resolution
- Be direct and practical, not performative"""

# Generation prompt template
GENERATION_PROMPT = """You are generating a training example for a Dharma-informed AI assistant.

The user has asked a genuine Buddhist practice question from a real practitioner in Czech Diamond Way Buddhism community. These are real questions that deserve thoughtful, helpful responses.

**Guidelines for your response:**
1. Be direct and practical - avoid spiritual fluff
2. Acknowledge uncertainty honestly ("I'm not certain, but...")
3. Don't moralize or lecture
4. If the question has multiple parts, address each thoughtfully
5. Avoid excessive Dharma jargon - explain concepts accessibly
6. If relevant, point toward direct experience rather than just concepts
7. Reference traditional sources naturally if appropriate (Gampopa, sutras, etc.) but don't be pedantic
8. Keep response concise but complete (200-500 words typically)
9. For practicing Buddhists, you can use appropriate technical terms
10. Do NOT include crisis hotline numbers - the model will learn generic "seek local help" patterns

**Question from practitioner:**
{question}

**Respond naturally as a helpful, wise assistant:**"""


def parse_questions():
    """Parse all questions from the markdown file."""
    questions = []
    content = QUESTIONS_FILE.read_text(encoding='utf-8')

    # Match **Q{number}** (ID:{id}) with optional stars, followed by > quoted question
    # Pattern handles both formats:
    #   **Q1** (ID:221)
    #   **Q26** (ID:1) ★★★
    pattern = r'\*\*Q(\d+)\*\*\s*\(ID:(\d+)\)[^\n]*\n>\s*(.+?)(?=\n\n\*\*Q|\n\n---|\n\n###|\Z)'

    for match in re.finditer(pattern, content, re.DOTALL):
        q_num = int(match.group(1))
        q_id = match.group(2)
        question_text = match.group(3).strip()
        # Clean up the question text (remove extra whitespace/newlines)
        question_text = ' '.join(question_text.split())
        questions.append({
            'number': q_num,
            'original_id': q_id,
            'question': question_text
        })

    return questions


def get_existing_scenarios():
    """Get list of question numbers that already have scenarios."""
    existing = set()
    if SCENARIOS_DIR.exists():
        for f in SCENARIOS_DIR.glob("buddhist-*.json"):
            # Extract number from buddhist-007.json -> 7
            match = re.search(r'buddhist-(\d+)\.json', f.name)
            if match:
                existing.add(int(match.group(1)))
    return existing


def format_scenario_id(q_num):
    """Format question number as scenario ID."""
    return f"buddhist-{q_num:03d}"


def create_scenario_json(q_num, question_text, difficulty="medium"):
    """Create scenario JSON structure."""
    return {
        "id": format_scenario_id(q_num),
        "category": "buddhist-questions",
        "difficulty": difficulty,
        "scenario": question_text,
        "context": {
            "source": "Czech Diamond Way Q&A archive (translated)",
            "question_type": "real_practitioner_question",
            "requires_buddhist_context": True
        },
        "test_dimensions": [
            "honest_uncertainty",
            "pragmatic_over_dogmatic",
            "direct_and_helpful",
            "no_moralizing"
        ],
        "notes": "Real question from real practitioner. Treat with respect."
    }


def create_response_json(q_num, response_text):
    """Create response JSON structure."""
    return {
        "scenario_id": format_scenario_id(q_num),
        "response": response_text,
        "metadata": {
            "generated_by": "karma-electric-instance-11",
            "generation_date": datetime.now().strftime("%Y-%m-%d"),
            "quality_tier": "v3"
        }
    }


def create_training_example(q_num, question_text, response_text):
    """Create ChatML training example."""
    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question_text},
            {"role": "assistant", "content": response_text}
        ],
        "_metadata": {
            "id": format_scenario_id(q_num),
            "category": "buddhist-questions",
            "source": "czech-diamond-way-qa"
        }
    }


def generate_response(question_text):
    """
    Generate response using Claude API.

    This is a placeholder - actual implementation requires API access.
    For now, returns None to indicate generation is needed.
    """
    # Try to use anthropic SDK if available
    try:
        import anthropic
        client = anthropic.Anthropic()

        message = client.messages.create(
            model="claude-sonnet-4-20250514",  # Use Sonnet for speed/cost
            max_tokens=1024,
            messages=[
                {"role": "user", "content": GENERATION_PROMPT.format(question=question_text)}
            ]
        )
        return message.content[0].text
    except ImportError:
        print("  Note: anthropic SDK not installed. Install with: pip install anthropic")
        return None
    except Exception as e:
        print(f"  Error generating: {e}")
        return None


def save_outputs(q_num, question_text, response_text):
    """Save scenario, response, and training example."""
    scenario_id = format_scenario_id(q_num)

    # Create directories if needed
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

    # Save scenario
    scenario = create_scenario_json(q_num, question_text)
    scenario_file = SCENARIOS_DIR / f"{scenario_id}.json"
    with open(scenario_file, 'w', encoding='utf-8') as f:
        json.dump(scenario, f, indent=2, ensure_ascii=False)

    # Save response
    response = create_response_json(q_num, response_text)
    response_file = RESPONSES_DIR / f"{scenario_id}-response.json"
    with open(response_file, 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=2, ensure_ascii=False)

    # Append to training file
    training_example = create_training_example(q_num, question_text, response_text)
    with open(TRAINING_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(training_example, ensure_ascii=False) + '\n')

    return scenario_file, response_file


def main():
    parser = argparse.ArgumentParser(description="Generate Buddhist Q&A responses")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be generated")
    parser.add_argument('--batch', type=int, default=5, help="Number to generate per run")
    parser.add_argument('--question', type=int, help="Generate for specific question number")
    parser.add_argument('--list-missing', action='store_true', help="List all missing questions")
    args = parser.parse_args()

    print("=" * 70)
    print("BUDDHIST Q&A RESPONSE GENERATOR")
    print("=" * 70)

    # Parse questions
    questions = parse_questions()
    print(f"\nParsed {len(questions)} questions from {QUESTIONS_FILE}")

    # Get existing
    existing = get_existing_scenarios()
    print(f"Existing scenarios: {len(existing)}")

    # Find missing
    missing = [q for q in questions if q['number'] not in existing]
    print(f"Missing responses: {len(missing)}")

    if args.list_missing:
        print("\nMissing questions:")
        for q in missing:
            print(f"  Q{q['number']}: {q['question'][:80]}...")
        return

    if args.question:
        # Generate for specific question
        target = [q for q in questions if q['number'] == args.question]
        if not target:
            print(f"Question {args.question} not found!")
            return
        if args.question in existing:
            print(f"Question {args.question} already has a response!")
            return
        missing = target

    # Take batch
    to_generate = missing[:args.batch]

    if args.dry_run:
        print(f"\nWould generate {len(to_generate)} responses:")
        for q in to_generate:
            print(f"\n  Q{q['number']}: {q['question'][:100]}...")
        return

    print(f"\n{'=' * 70}")
    print(f"GENERATING {len(to_generate)} RESPONSES")
    print(f"{'=' * 70}")

    generated = 0
    for q in to_generate:
        print(f"\n[{generated + 1}/{len(to_generate)}] Q{q['number']}:")
        print(f"  {q['question'][:80]}...")

        response = generate_response(q['question'])
        if response:
            scenario_file, response_file = save_outputs(q['number'], q['question'], response)
            print(f"  Saved: {scenario_file}")
            generated += 1
        else:
            print("  Skipped (no response generated)")

    print(f"\n{'=' * 70}")
    print(f"COMPLETE: Generated {generated}/{len(to_generate)} responses")
    print(f"Remaining: {len(missing) - generated}")
    print(f"{'=' * 70}")
    print("\nNext: Run scripts/cleanup_and_regenerate_datasets.py to rebuild clean datasets")


if __name__ == "__main__":
    main()
