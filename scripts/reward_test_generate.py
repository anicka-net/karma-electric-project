#!/usr/bin/env python3
"""
Generate test fixtures for KE-8B reward model validation.

Produces:
  1. Prompt paraphrases — 50 prompts x 5 paraphrases (same answer, different question)
  2. Style rewrites   — 20 prompts x 5 style variants (same substance, different style)
  3. Czech translations — 20 prompts (both prompt + answer translated)

All fixtures saved to data/reward-test-fixtures.jsonl.
Uses Hermes 3 70B on GPU server via Ollama for generation.
Can also use KE-8B on twilight for paraphrases/translations (--use-ke8b).
Style rewrites REQUIRE Hermes (to avoid self-referential bias).

Usage:
    python3 scripts/reward_test_generate.py                      # generate all
    python3 scripts/reward_test_generate.py --test paraphrase    # one test type only
    python3 scripts/reward_test_generate.py --limit 5            # small batch
    python3 scripts/reward_test_generate.py --dry-run            # show prompt selection
    python3 scripts/reward_test_generate.py --resume             # skip already-generated
    python3 scripts/reward_test_generate.py --hermes-url URL     # custom endpoint
    python3 scripts/reward_test_generate.py --use-ke8b           # use KE-8B for generation
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reward_test_utils import (
    get_high_quality_prompts, query_hermes, query_ke8b_completion,
    check_hermes, check_ke8b, log, HERMES_URL, HERMES_MODEL, KE8B_URL,
)


def generate_text(prompt, use_ke8b=False, hermes_url=HERMES_URL, ke8b_url=KE8B_URL,
                  temperature=0.7, max_tokens=2000):
    """Generate text using either Hermes or KE-8B raw completion."""
    if use_ke8b:
        return query_ke8b_completion(
            prompt, url=ke8b_url, temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        return query_hermes(prompt, url=hermes_url, temperature=temperature)

FIXTURES_FILE = Path("data/reward-test-fixtures.jsonl")

# ============ Paraphrase Generation ============

PARAPHRASE_PROMPT = """Rephrase the following text. Keep the same meaning but use different words and sentence structure. Output ONLY the rephrased text, nothing else.

Original: {question}

Rephrased:"""


def generate_paraphrases(prompt_data, n_paraphrases=5, use_ke8b=False,
                          hermes_url=HERMES_URL, ke8b_url=KE8B_URL):
    """Generate n paraphrases of a user prompt."""
    paraphrases = []
    for i in range(n_paraphrases):
        p = PARAPHRASE_PROMPT.format(question=prompt_data["user_msg"], n=i + 1)
        result = generate_text(p, use_ke8b=use_ke8b, hermes_url=hermes_url,
                                ke8b_url=ke8b_url, temperature=0.8,
                                max_tokens=500)
        # Clean up: strip meta-commentary, quotes, take first substantive paragraph
        result = result.strip().strip('"').strip("'")
        # Skip lines that are meta-commentary
        lines = result.split("\n")
        clean_lines = []
        for line in lines:
            low = line.lower().strip()
            if any(low.startswith(skip) for skip in [
                "here is", "here's", "i can", "the original", "sure,",
                "rephrased", "paraphrase", "variant",
            ]):
                continue
            clean_lines.append(line)
        result = "\n".join(clean_lines).strip()
        if "\n\n" in result:
            result = result.split("\n\n")[0]
        if result:
            paraphrases.append(result)
        time.sleep(0.3)
    return paraphrases


# ============ Style Rewriting ============

STYLE_PROMPTS = {
    "verbose": (
        "Rewrite the following AI response in a very verbose, exploratory style. "
        "Make it significantly longer. Add nuance, explore edge cases, add qualifications. "
        "Same core content and advice, but padded with exploration and reflection. "
        "Do NOT change the factual content or recommendations.\n\n"
        "Original response:\n{response}\n\n"
        "Very verbose version:"
    ),
    "short": (
        "Rewrite the following AI response as short as possible. Telegraphic. "
        "Cut everything non-essential. Use short sentences, no elaboration. "
        "Keep all key points and action items but strip all padding. "
        "Aim for 20-30% of the original length.\n\n"
        "Original response:\n{response}\n\n"
        "Very short version:"
    ),
    "inspirational": (
        "Rewrite the following AI response in a very inspirational, uplifting tone. "
        "Add motivational language, affirmations, and encouraging phrases. "
        "Same core content and advice, but wrapped in warm, hopeful framing. "
        "Do NOT change the actual recommendations or factual content.\n\n"
        "Original response:\n{response}\n\n"
        "Very inspirational version:"
    ),
    "blunt": (
        "Rewrite the following AI response in a very blunt, direct, no-nonsense style. "
        "Zero softening language. No hand-holding. Strip all diplomatic phrasing. "
        "Same advice, but delivered as if by someone who doesn't care about feelings. "
        "Keep all factual content and action items.\n\n"
        "Original response:\n{response}\n\n"
        "Very blunt version:"
    ),
    "clinical": (
        "Rewrite the following AI response in a very clinical, detached, professional style. "
        "Use numbered lists, formal language, no emotional engagement. "
        "Like a medical or legal document. Same content, zero warmth. "
        "Preserve all factual recommendations.\n\n"
        "Original response:\n{response}\n\n"
        "Very clinical version:"
    ),
}


def generate_style_variants(prompt_data, hermes_url=HERMES_URL):
    """Generate 5 style variants of an answer. Requires Hermes (not KE-8B)."""
    variants = {}
    for style, template in STYLE_PROMPTS.items():
        p = template.format(response=prompt_data["assistant_msg"])
        result = query_hermes(p, url=hermes_url, temperature=0.7)
        variants[style] = result.strip()
        time.sleep(0.3)
    return variants


# ============ Czech Translation ============

TRANSLATE_PROMPT = """Translate the following text to natural, fluent Czech. Output ONLY the Czech translation.

English: {text}

Czech:"""


def generate_czech_translation(text, use_ke8b=False, hermes_url=HERMES_URL,
                                ke8b_url=KE8B_URL):
    """Translate text to Czech."""
    p = TRANSLATE_PROMPT.format(text=text)
    result = generate_text(p, use_ke8b=use_ke8b, hermes_url=hermes_url,
                            ke8b_url=ke8b_url, temperature=0.3)
    return result.strip()


# ============ Main ============

def load_existing_fixtures():
    """Load already-generated fixture IDs for resume."""
    existing = set()
    if FIXTURES_FILE.exists():
        with open(FIXTURES_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    key = f"{entry['test_type']}:{entry['prompt_id']}"
                    existing.add(key)
                except (json.JSONDecodeError, KeyError):
                    continue
    return existing


def save_fixture(entry):
    """Append one fixture to JSONL."""
    with open(FIXTURES_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test fixtures for KE-8B reward model validation")
    parser.add_argument("--test", choices=["paraphrase", "style", "crosslang", "all"],
                        default="all", help="Which test to generate fixtures for")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of prompts (0=all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompt selection without generating")
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-generated fixtures")
    parser.add_argument("--hermes-url", default=HERMES_URL,
                        help=f"Hermes Ollama URL (default: {HERMES_URL})")
    parser.add_argument("--hermes-model", default=HERMES_MODEL)
    parser.add_argument("--ke8b-url", default=KE8B_URL,
                        help="KE-8B URL for --use-ke8b mode")
    parser.add_argument("--use-ke8b", action="store_true",
                        help="Use KE-8B for generation (paraphrase/crosslang only)")
    parser.add_argument("--n-paraphrases", type=int, default=5)
    args = parser.parse_args()

    # Select prompts
    log("Selecting prompts from training.db...")
    n_prompts = args.limit if args.limit > 0 else 50
    prompts = get_high_quality_prompts(n=n_prompts)
    log(f"Selected {len(prompts)} prompts across {len(set(p['category'] for p in prompts))} categories")

    if args.dry_run:
        print(f"\n{'ID':<45s} {'Category':<30s} {'Score':>5}")
        print("-" * 82)
        for p in prompts:
            print(f"{p['id'][:44]:<45s} {p['category']:<30s} {p['hermes_score']:>5}")
        print(f"\nTotal: {len(prompts)} prompts")
        cats = {}
        for p in prompts:
            cats[p["category"]] = cats.get(p["category"], 0) + 1
        print(f"Categories: {dict(sorted(cats.items(), key=lambda x: -x[1]))}")
        return

    # Check generator model
    if args.use_ke8b:
        log(f"Using KE-8B for generation at {args.ke8b_url}")
        if not check_ke8b(args.ke8b_url):
            print(f"ERROR: KE-8B not reachable at {args.ke8b_url}")
            sys.exit(1)
        log("KE-8B OK")
        if args.test in ("style", "all"):
            log("WARNING: Style rewrites require Hermes (self-referential bias).")
            if args.test == "style":
                print("ERROR: Style test cannot use --use-ke8b (self-referential bias)")
                sys.exit(1)
            log("  Skipping style test. Run with Hermes later.")
    else:
        log(f"Checking Hermes at {args.hermes_url}...")
        if not check_hermes(args.hermes_url):
            print(f"ERROR: Hermes not available at {args.hermes_url}")
            print("Options: ssh -L 11435:localhost:11434 GPU server")
            print("         or use --use-ke8b for paraphrase/crosslang only")
            sys.exit(1)
        log("Hermes OK")
    generator_name = "ke8b-v6" if args.use_ke8b else args.hermes_model

    existing = load_existing_fixtures() if args.resume else set()
    if existing:
        log(f"Resume mode: {len(existing)} fixtures already generated")

    FIXTURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    total_generated = 0

    # --- Test 1: Paraphrase Invariance ---
    if args.test in ("paraphrase", "all"):
        log(f"\n{'='*60}")
        log("GENERATING PROMPT PARAPHRASES")
        log(f"{'='*60}")

        for i, p in enumerate(prompts, 1):
            key = f"paraphrase:{p['id']}"
            if key in existing:
                log(f"  [{i}/{len(prompts)}] SKIP (exists) {p['id'][:40]}")
                continue

            log(f"  [{i}/{len(prompts)}] {p['id'][:40]}...")
            try:
                paraphrases = generate_paraphrases(
                    p, args.n_paraphrases, use_ke8b=args.use_ke8b,
                    hermes_url=args.hermes_url, ke8b_url=args.ke8b_url)
                entry = {
                    "test_type": "paraphrase",
                    "prompt_id": p["id"],
                    "category": p["category"],
                    "original_prompt": p["user_msg"],
                    "gold_answer": p["assistant_msg"],
                    "hermes_score": p["hermes_score"],
                    "paraphrases": paraphrases,
                    "generated_at": datetime.now().isoformat(),
                    "generator": generator_name,
                }
                save_fixture(entry)
                total_generated += 1
                log(f"    -> {len(paraphrases)} paraphrases generated")
            except Exception as e:
                log(f"    ERROR: {e}")
                continue

    # --- Test 2: Style Gaming (requires Hermes) ---
    if args.test in ("style", "all") and not args.use_ke8b:
        log(f"\n{'='*60}")
        log("GENERATING STYLE VARIANTS")
        log(f"{'='*60}")

        # Use first 20 prompts for style test
        style_prompts = prompts[:min(20, len(prompts))]
        for i, p in enumerate(style_prompts, 1):
            key = f"style:{p['id']}"
            if key in existing:
                log(f"  [{i}/{len(style_prompts)}] SKIP (exists) {p['id'][:40]}")
                continue

            log(f"  [{i}/{len(style_prompts)}] {p['id'][:40]}...")
            try:
                variants = generate_style_variants(p, args.hermes_url)
                entry = {
                    "test_type": "style",
                    "prompt_id": p["id"],
                    "category": p["category"],
                    "user_prompt": p["user_msg"],
                    "gold_answer": p["assistant_msg"],
                    "hermes_score": p["hermes_score"],
                    "style_variants": variants,
                    "generated_at": datetime.now().isoformat(),
                    "generator": args.hermes_model,
                }
                save_fixture(entry)
                total_generated += 1
                log(f"    -> {len(variants)} style variants generated")
            except Exception as e:
                log(f"    ERROR: {e}")
                continue

    # --- Test 4: Cross-Language ---
    if args.test in ("crosslang", "all"):
        log(f"\n{'='*60}")
        log("GENERATING CZECH TRANSLATIONS")
        log(f"{'='*60}")

        # Use first 20 prompts for cross-language test
        crosslang_prompts = prompts[:min(20, len(prompts))]
        for i, p in enumerate(crosslang_prompts, 1):
            key = f"crosslang:{p['id']}"
            if key in existing:
                log(f"  [{i}/{len(crosslang_prompts)}] SKIP (exists) {p['id'][:40]}")
                continue

            log(f"  [{i}/{len(crosslang_prompts)}] {p['id'][:40]}...")
            try:
                cz_prompt = generate_czech_translation(
                    p["user_msg"], use_ke8b=args.use_ke8b,
                    hermes_url=args.hermes_url, ke8b_url=args.ke8b_url)
                cz_answer = generate_czech_translation(
                    p["assistant_msg"], use_ke8b=args.use_ke8b,
                    hermes_url=args.hermes_url, ke8b_url=args.ke8b_url)
                entry = {
                    "test_type": "crosslang",
                    "prompt_id": p["id"],
                    "category": p["category"],
                    "en_prompt": p["user_msg"],
                    "en_answer": p["assistant_msg"],
                    "cz_prompt": cz_prompt,
                    "cz_answer": cz_answer,
                    "hermes_score": p["hermes_score"],
                    "generated_at": datetime.now().isoformat(),
                    "generator": generator_name,
                }
                save_fixture(entry)
                total_generated += 1
                log(f"    -> CZ translation generated")
            except Exception as e:
                log(f"    ERROR: {e}")
                continue

    log(f"\n{'='*60}")
    log(f"GENERATION COMPLETE: {total_generated} fixtures generated")
    log(f"Output: {FIXTURES_FILE}")
    log(f"{'='*60}")


if __name__ == "__main__":
    main()
