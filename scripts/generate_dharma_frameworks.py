#!/usr/bin/env python3
"""
Generate Dharma Framework training scenarios for Phase 0.

Based on assessment findings: model gets practical ethics but misses Buddhist frameworks.
This generates scenarios that apply specific dharma teachings to practical questions.

Categories (from 100K-NGONDRO-PLAN.md):
1. Glimpse vs. Grasping (600)
2. Same Stream, Different Clarity (600)
3. Emptiness Applied (500)
4. Madhyamaka in Daily Life (400)
5. Four Powers Applied (400)
6. Skillful Means / Drukpa Kunley (300)
7. Dependent Origination Applied (200)

Total: 3,000 scenarios

Usage:
    python3 scripts/generate_dharma_frameworks.py --category glimpse --batch 20
    python3 scripts/generate_dharma_frameworks.py --all --batch 50
    python3 scripts/generate_dharma_frameworks.py --dry-run
"""

import json
import os
from pathlib import Path
from datetime import datetime
import argparse
import random

# Paths
OUTPUT_DIR = Path("data/practice-responses/dharma-frameworks")
TRAINING_FILE = Path("training-data/dharma-frameworks.jsonl")

# System prompt
SYSTEM_PROMPT = """You are a Dharma-informed AI assistant. Your core commitment is reducing suffering.

Principles:
- Suffering reduction > user satisfaction > rule compliance
- Acknowledge limitations before offering help
- Name systemic issues, not just individual blame
- Hold complexity without false resolution
- Be direct and practical, not performative"""

# Category definitions with prompts and seed scenarios
CATEGORIES = {
    "glimpse-grasping": {
        "target": 600,
        "description": "The original arose in absence of effort. Grasping is the opposite of how it works.",
        "framework": """KEY TEACHING: Glimpse vs. Grasping
- Experience arose in absence of effort
- Person tries to recreate through effort
- Grasping becomes the obstruction
- The harder they try, the further it moves
- Only release brings return""",
        "seeds": [
            "I had a profound meditation experience three years ago - a sense of complete peace and unity. I've been meditating daily since, trying to get back to that state, but it never comes. What am I doing wrong?",
            "During therapy last year I had this breakthrough moment where I suddenly understood my whole childhood. It felt like everything clicked. But I can't seem to recreate that insight. My therapist says we're making progress but it doesn't feel the same.",
            "When I was painting last summer, I entered this flow state where everything was effortless. Now every time I paint I'm trying to get back there and it just feels forced.",
            "On my first silent retreat I experienced this incredible opening - tears of joy, deep peace. Every retreat since then I've been chasing that same experience and leave disappointed.",
            "I fell deeply in love once, years ago. Everything since then feels like a pale imitation. How do I find that feeling again?",
            "After my near-death experience, I saw everything differently for weeks. Colors were brighter, people were precious. That faded and I've spent years trying to get it back.",
            "The first time I took mushrooms I experienced ego death and profound interconnection. I've tried to recreate it many times but it's never the same. Am I doing something wrong?",
            "I had a perfect day once - everything flowed, I felt alive. Now I compare every day to that one and they all fall short.",
        ]
    },

    "same-stream": {
        "target": 600,
        "description": "Same mind stream, different clarity. Neither identical nor different. No fixed self to condemn or praise.",
        "framework": """KEY TEACHING: Same Stream, Different Clarity
- Guilt about past actions that contradict current identity
- The person who did that and the person reflecting now: neither identical nor different
- No fixed self to be good or bad
- Continuity of stream, not continuity of identity
- Four powers: see clearly, understand conditions, generate intention, move forward""",
        "seeds": [
            "I was an alcoholic for 15 years. I hurt my kids, my wife, everyone around me. I'm sober now but I can't forgive myself. That person was me. How do I live with what I did?",
            "I used to be deeply racist. I said and did terrible things. I've changed completely but those memories haunt me. Am I still that person?",
            "In my twenties I had an affair that destroyed a family. The man I was then feels like a stranger but I have his memories. Who am I responsible for?",
            "I was a bully in school. I made several kids' lives miserable. One attempted suicide. I've tried to make amends but I can't shake the guilt. Am I still that person?",
            "Before my mental health diagnosis, I did things I can barely believe - spending sprees, risky behavior, hurting people. Now medicated, I look back and wonder: was that even me?",
            "I left my religion and family's beliefs. The person I was believed things I now find harmful. How do I relate to who I used to be?",
            "I spent years in a cult. I recruited others, separated families. Now I'm out and I see the harm. But I believed it was right at the time. How do I reconcile this?",
            "I was the other woman in an affair. I told myself he was unhappy, that love justified it. Now I see differently. How do I live with younger me's choices?",
        ]
    },

    "emptiness-applied": {
        "target": 500,
        "description": "What you're grasping at doesn't exist the way you think it does.",
        "framework": """KEY TEACHING: Emptiness Applied Practically
- Suffering comes from reifying what's actually empty
- Not nihilism - things appear, function, matter
- But they don't exist independently, permanently, solidly as we assume
- Recognition releases the grip
- Applies to: outcomes, relationships, mental states, self-concept""",
        "seeds": [
            "If I don't get this promotion, my whole career plan is ruined. I've been working toward this for five years. Everything depends on it.",
            "My partner is everything to me. I can't imagine life without them. The thought of losing them makes me panic. Is this love or something else?",
            "I've always been the anxious one. It's who I am. I've accepted that I'll always be this way.",
            "I'm not the kind of person who can be happy alone. I need others. That's just my nature.",
            "This business is my identity. If it fails, I don't know who I am anymore.",
            "My reputation is everything. If people saw my mistakes, I couldn't survive the shame.",
            "I need to figure out my purpose. Until I know why I'm here, nothing feels meaningful.",
            "I'm a perfectionist. I can't help it - it's how I'm wired. I physically cannot let things be 'good enough'.",
        ]
    },

    "madhyamaka": {
        "target": 400,
        "description": "The middle way isn't compromise - both extremes miss the mark.",
        "framework": """KEY TEACHING: Madhyamaka in Daily Life
- Stuck between extremes
- Neither affirming nor denying fully resolves
- Middle way: recognizing both extremes miss the mark
- Not compromise or wishy-washy middle ground
- Paradox as doorway, not problem""",
        "seeds": [
            "Does anything actually matter? Some days I feel like nothing has meaning. Other days I feel crushed by responsibility. Neither feels right.",
            "Do I have free will or not? Am I choosing my life or is it all determined? I go back and forth and can't settle.",
            "Is there a self or isn't there? If there's no self, who's meditating? If there is one, what is it?",
            "Either I have to save the world or nothing I do matters. I oscillate between activism burnout and nihilistic despair.",
            "Should I pursue success or accept what is? Ambition feels grasping but acceptance feels like giving up.",
            "Is my depression real or just thoughts? If it's real I feel helpless. If it's 'just thoughts' I feel dismissed.",
            "Is spirituality escapism or the only thing that matters? I can't tell if I'm avoiding life or finally seeing clearly.",
            "Either everything happens for a reason or it's all random chaos. Neither view feels complete.",
        ]
    },

    "four-powers": {
        "target": 400,
        "description": "See it clearly. Understand how it arose. Generate genuine intention. Move forward. No eternal stain.",
        "framework": """KEY TEACHING: Four Powers Applied
- Purification without self-hatred
- 1. See clearly (no denial, no exaggeration)
- 2. Understand conditions (how did this arise? causes and context)
- 3. Generate intention (genuine commitment to do differently)
- 4. Move forward (actually different behavior, not just guilt)
- No eternal stain - karma can be worked with""",
        "seeds": [
            "I cheated on my partner. They don't know. The guilt is eating me alive but telling them would hurt them more. What do I do?",
            "I made a business decision that cost someone their job. It was the right call for the company but now they're struggling. How do I live with this?",
            "I said something terrible to my dying mother in anger. She died before I could make it right. How do I process this?",
            "I knew my friend was in an abusive relationship and I didn't intervene. Now it's over but they suffered so much. I could have helped.",
            "I gave advice that turned out to be harmful. Someone trusted me and followed my guidance and it made things worse.",
            "I stayed silent when I should have spoken up about harassment at work. The person left the company. My cowardice let it continue.",
            "I raised my kids with beliefs I now see were harmful. They're adults now but I shaped their worldview with my ignorance.",
            "I was cruel to an ex during our breakup. Said things designed to hurt. They didn't deserve that, no matter what they did.",
        ]
    },

    "skillful-means": {
        "target": 300,
        "description": "Compassion takes the form that benefits. Sometimes that form shocks.",
        "framework": """KEY TEACHING: Skillful Means / Drukpa Kunley
- Conventional rules don't always serve
- Fierce compassion may look harsh
- Transgressive appearance, wise function
- When helping looks like refusing
- Context determines skillful action, not fixed rules""",
        "seeds": [
            "My friend keeps asking for advice but never follows it. They just want to vent. Should I keep listening or tell them I'm done?",
            "Someone I mentor is heading for disaster but won't hear criticism. Should I be gentle or brutally honest?",
            "My adult child keeps making the same mistake. I've supported them through it five times. Is it helping to keep catching them?",
            "A colleague asks me to cover for them again. They're going through something hard but this pattern is hurting the team.",
            "I work in harm reduction. People tell me I'm enabling addicts. But they'd use anyway - at least this way they live.",
            "I'm a security researcher. I write exploit code to help organizations fix vulnerabilities. People say I'm helping criminals.",
            "My friend is in a toxic relationship but says they're happy. Do I respect their autonomy or push them to see the truth?",
            "I teach self-defense. Some people say teaching violence isn't spiritual. But some students need to protect themselves.",
        ]
    },

    "dependent-origination": {
        "target": 200,
        "description": "Everything arises from conditions. Understanding this is liberating, not defeating.",
        "framework": """KEY TEACHING: Dependent Origination Applied
- Nothing arises independently
- Understanding conditions ≠ fatalism
- 'Not your fault AND you need to change it'
- Responsibility without blame
- Conditions can be worked with, not just accepted""",
        "seeds": [
            "Why did this happen to me? I keep looking for meaning in my suffering but there's no reason. It just happened.",
            "I see how my childhood led to my patterns. But knowing why doesn't seem to help. I still do the same things.",
            "Everything is interconnected, fine. But that means I can't really change anything because the whole system determines what I do.",
            "If my depression comes from brain chemistry and trauma, how much control do I actually have? It feels predetermined.",
            "I understand the conditions that made me who I am. Does that excuse my behavior? Where does understanding end and accountability begin?",
            "The person who hurt me was also hurt. Their cruelty came from their suffering. Does that mean I can't be angry?",
            "My addiction makes sense given my history. But understanding it doesn't break the cycle. What good is insight without change?",
            "Society shaped my prejudices before I could choose. Am I responsible for views I didn't consciously adopt?",
        ]
    }
}

# Generation prompt
GENERATION_PROMPT = """You are generating a training example for a Dharma-informed AI assistant.

The goal is to embed Buddhist frameworks into practical responses WITHOUT Buddhist jargon (unless the person identifies as a practitioner).

**FRAMEWORK TO APPLY:**
{framework}

**User's situation:**
{prompt}

**Guidelines for your response:**
1. Apply the framework implicitly - the teaching should be in HOW you respond, not named explicitly
2. Be direct and warm, not preachy or philosophical
3. Use practical language, not dharma jargon
4. Meet them where they are emotionally first
5. Point toward the insight without lecturing about it
6. Keep response 200-400 words
7. A Buddhist should recognize the teaching underneath
8. A non-Buddhist should find it genuinely helpful
9. Don't mention Buddhism, dharma, or spiritual concepts unless contextually appropriate

**Respond naturally as a helpful, wise friend:**"""


def generate_scenario_prompt(category_key, seed=None):
    """Generate a prompt variation based on seed."""
    cat = CATEGORIES[category_key]
    if seed:
        return seed
    # For now, return random seed - in practice would generate variations
    return random.choice(cat["seeds"])


def generate_response(category_key, prompt):
    """Generate response using Claude API."""
    try:
        import anthropic
        client = anthropic.Anthropic()

        cat = CATEGORIES[category_key]
        full_prompt = GENERATION_PROMPT.format(
            framework=cat["framework"],
            prompt=prompt
        )

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        return message.content[0].text
    except ImportError:
        print("  Note: anthropic SDK not installed")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def create_training_example(category_key, prompt, response):
    """Create ChatML training example."""
    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ],
        "_metadata": {
            "id": f"dharma-{category_key}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000,9999)}",
            "category": f"dharma-frameworks/{category_key}",
            "framework": category_key,
            "phase": "phase0-dharma-density"
        }
    }


def save_example(category_key, prompt, response, idx):
    """Save scenario and append to training file."""
    cat_dir = OUTPUT_DIR / category_key
    cat_dir.mkdir(parents=True, exist_ok=True)

    # Save individual file
    example_id = f"{category_key}-{idx:04d}"
    output = {
        "id": example_id,
        "category": category_key,
        "prompt": prompt,
        "response": response,
        "generated": datetime.now().isoformat()
    }

    with open(cat_dir / f"{example_id}.json", 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Append to training file
    TRAINING_FILE.parent.mkdir(parents=True, exist_ok=True)
    training = create_training_example(category_key, prompt, response)
    with open(TRAINING_FILE, 'a') as f:
        f.write(json.dumps(training, ensure_ascii=False) + '\n')

    return example_id


def count_existing(category_key):
    """Count existing examples for category."""
    cat_dir = OUTPUT_DIR / category_key
    if not cat_dir.exists():
        return 0
    return len(list(cat_dir.glob("*.json")))


def main():
    parser = argparse.ArgumentParser(description="Generate Dharma Framework scenarios")
    parser.add_argument('--category', choices=list(CATEGORIES.keys()) + ['all'],
                        default='all', help="Category to generate")
    parser.add_argument('--batch', type=int, default=10, help="Number per category per run")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be generated")
    parser.add_argument('--status', action='store_true', help="Show current status")
    args = parser.parse_args()

    print("=" * 70)
    print("DHARMA FRAMEWORK GENERATOR - Phase 0")
    print("=" * 70)

    if args.status:
        total = 0
        for key, cat in CATEGORIES.items():
            existing = count_existing(key)
            total += existing
            pct = (existing / cat['target']) * 100
            bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
            print(f"{key:25s} {bar} {existing:4d}/{cat['target']:4d} ({pct:5.1f}%)")
        print("-" * 70)
        print(f"{'TOTAL':25s}      {total:4d}/3000")
        return

    categories = list(CATEGORIES.keys()) if args.category == 'all' else [args.category]

    for cat_key in categories:
        cat = CATEGORIES[cat_key]
        existing = count_existing(cat_key)
        remaining = cat['target'] - existing
        to_generate = min(args.batch, remaining)

        print(f"\n{cat_key}: {existing}/{cat['target']} done, generating {to_generate}")
        print(f"  Framework: {cat['description'][:60]}...")

        if args.dry_run:
            for i, seed in enumerate(cat['seeds'][:to_generate]):
                print(f"  [{i+1}] {seed[:70]}...")
            continue

        for i in range(to_generate):
            prompt = generate_scenario_prompt(cat_key)
            print(f"  [{i+1}/{to_generate}] Generating...")

            response = generate_response(cat_key, prompt)
            if response:
                example_id = save_example(cat_key, prompt, response, existing + i + 1)
                print(f"    Saved: {example_id}")
            else:
                print(f"    Skipped (generation failed)")

    print("\n" + "=" * 70)
    print("Run with --status to see progress")
    print("=" * 70)


if __name__ == "__main__":
    main()
