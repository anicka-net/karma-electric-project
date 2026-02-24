#!/usr/bin/env python3
"""
RL Diagnostic: Phase 0

Generate multiple responses from Apertus 70B for a set of prompts,
score them with KE-8B, and measure score spread to identify "sharp"
prompts where the reward signal is informative.

Usage:
    # Generate responses (needs Apertus on ai01)
    python3 scripts/rl_diagnostic.py --generate --apertus-url http://localhost:8385/v1/chat/completions

    # Score responses (needs KE-8B on twilight)
    python3 scripts/rl_diagnostic.py --score --ke8b-url http://twilight.ucw.cz:8384/v1/chat/completions

    # Analyze results
    python3 scripts/rl_diagnostic.py --analyze
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reward_test_utils import (
    query_ke8b, query_ke8b_reward, extract_reward_scores,
    REWARD_SYSTEM_PROMPT, log,
)
import requests

# ============ Configuration ============

PROMPTS_FILE = Path("data/rl-diagnostic-prompts.jsonl")
RESPONSES_FILE = Path("data/rl-diagnostic-responses.jsonl")
SCORES_FILE = Path("data/rl-diagnostic-scores.jsonl")

APERTUS_URL = os.environ.get(
    "APERTUS_URL", "http://localhost:8385/v1/chat/completions"
)
KE8B_URL = os.environ.get(
    "KE8B_URL", "http://localhost:8384/v1/chat/completions"
)

APERTUS_SYSTEM = (
    "You are a helpful AI assistant. Engage directly and honestly "
    "with the user's question."
)

N_RESPONSES = 4
TEMPERATURE = 0.8
MAX_TOKENS = 1500


# ============ Generation ============

def generate_responses(url=APERTUS_URL, resume=True):
    """Generate N_RESPONSES per prompt from Apertus."""
    prompts = []
    with open(PROMPTS_FILE) as f:
        for line in f:
            prompts.append(json.loads(line))

    # Resume support
    existing = set()
    if resume and RESPONSES_FILE.exists():
        with open(RESPONSES_FILE) as f:
            for line in f:
                obj = json.loads(line)
                existing.add(f"{obj['prompt_idx']}:{obj['response_idx']}")
        log(f"Resume mode: {len(existing)} responses already generated")

    total = len(prompts) * N_RESPONSES
    done = len(existing)
    log(f"Generating {N_RESPONSES} responses each for {len(prompts)} prompts")
    log(f"Apertus at {url}, temp={TEMPERATURE}")

    with open(RESPONSES_FILE, "a") as out:
        for pi, prompt_obj in enumerate(prompts):
            prompt_text = prompt_obj["prompt"]

            for ri in range(N_RESPONSES):
                key = f"{pi}:{ri}"
                if key in existing:
                    continue

                try:
                    resp = requests.post(url, json={
                        "messages": [
                            {"role": "system", "content": APERTUS_SYSTEM},
                            {"role": "user", "content": prompt_text},
                        ],
                        "temperature": TEMPERATURE,
                        "max_tokens": MAX_TOKENS,
                        "frequency_penalty": 0.3,
                    }, timeout=300)
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    log(f"  ERROR [{pi}:{ri}]: {e}")
                    continue

                record = {
                    "prompt_idx": pi,
                    "response_idx": ri,
                    "prompt": prompt_text,
                    "response": content,
                    "generated_at": datetime.now().isoformat(),
                }
                out.write(json.dumps(record) + "\n")
                out.flush()
                done += 1

            if (pi + 1) % 10 == 0:
                log(f"  [{pi+1}/{len(prompts)}] {done}/{total} responses")

    log(f"Generation complete: {done} responses in {RESPONSES_FILE}")


# ============ Scoring ============

def score_responses(url=KE8B_URL, resume=True):
    """Score all generated responses with KE-8B."""
    responses = []
    with open(RESPONSES_FILE) as f:
        for line in f:
            responses.append(json.loads(line))

    existing = set()
    if resume and SCORES_FILE.exists():
        with open(SCORES_FILE) as f:
            for line in f:
                obj = json.loads(line)
                existing.add(f"{obj['prompt_idx']}:{obj['response_idx']}")
        log(f"Resume mode: {len(existing)} scores already exist")

    log(f"Scoring {len(responses)} responses with KE-8B at {url}")

    with open(SCORES_FILE, "a") as out:
        for i, resp_obj in enumerate(responses):
            key = f"{resp_obj['prompt_idx']}:{resp_obj['response_idx']}"
            if key in existing:
                continue

            try:
                eval_text = query_ke8b_reward(
                    resp_obj["prompt"], resp_obj["response"], url=url
                )
                scores = extract_reward_scores(eval_text)
            except Exception as e:
                log(f"  ERROR [{key}]: {e}")
                scores = {"overall": None, "raw_text": str(e)}

            record = {
                "prompt_idx": resp_obj["prompt_idx"],
                "response_idx": resp_obj["response_idx"],
                "prompt": resp_obj["prompt"],
                "scores": scores,
                "scored_at": datetime.now().isoformat(),
            }
            # Don't store raw_text in scores file (too large)
            record["scores"].pop("raw_text", None)
            out.write(json.dumps(record) + "\n")
            out.flush()

            if (i + 1) % 20 == 0:
                scored = len(existing) + i + 1
                log(f"  [{scored}/{len(responses)}] scored")

    log(f"Scoring complete: {SCORES_FILE}")


# ============ Analysis ============

def analyze():
    """Analyze score spread per prompt to identify sharp prompts."""
    import numpy as np

    # Load scores grouped by prompt
    by_prompt = {}
    with open(SCORES_FILE) as f:
        for line in f:
            obj = json.loads(line)
            pi = obj["prompt_idx"]
            overall = obj["scores"].get("overall")
            if overall is not None:
                by_prompt.setdefault(pi, []).append({
                    "response_idx": obj["response_idx"],
                    "overall": overall,
                    "scores": obj["scores"],
                    "prompt": obj["prompt"],
                })

    # Load prompt metadata for categorization
    prompts = []
    with open(PROMPTS_FILE) as f:
        for line in f:
            prompts.append(json.loads(line))

    # Compute spread per prompt
    results = []
    for pi, entries in sorted(by_prompt.items()):
        overalls = [e["overall"] for e in entries]
        if len(overalls) < 2:
            continue

        spread = max(overalls) - min(overalls)
        std = float(np.std(overalls))
        mean = float(np.mean(overalls))
        prompt_text = entries[0]["prompt"]

        results.append({
            "prompt_idx": pi,
            "prompt": prompt_text[:100],
            "n_responses": len(overalls),
            "scores": overalls,
            "mean": round(mean, 1),
            "spread": round(spread, 1),
            "std": round(std, 2),
        })

    results.sort(key=lambda x: x["spread"], reverse=True)

    # Summary
    spreads = [r["spread"] for r in results]
    means = [r["mean"] for r in results]
    stds = [r["std"] for r in results]

    print("=" * 60)
    print("RL DIAGNOSTIC: SCORE SPREAD ANALYSIS")
    print("=" * 60)
    print(f"  Prompts analyzed: {len(results)}")
    print(f"  Mean score:       {np.mean(means):.1f}")
    print(f"  Mean spread:      {np.mean(spreads):.1f}")
    print(f"  Mean std:         {np.mean(stds):.2f}")
    print(f"  Prompts with spread >= 2.0: {sum(1 for s in spreads if s >= 2.0)}")
    print(f"  Prompts with spread >= 3.0: {sum(1 for s in spreads if s >= 3.0)}")
    print(f"  Prompts with spread < 1.0:  {sum(1 for s in spreads if s < 1.0)}")
    print()

    print("TOP 20 SHARPEST PROMPTS (highest score spread):")
    print("-" * 60)
    for r in results[:20]:
        print(f"  [{r['prompt_idx']:3d}] spread={r['spread']:.1f} "
              f"mean={r['mean']:.1f} scores={r['scores']} ")
        print(f"        {r['prompt']}")
        print()

    print("BOTTOM 10 FLATTEST PROMPTS (lowest spread):")
    print("-" * 60)
    for r in results[-10:]:
        print(f"  [{r['prompt_idx']:3d}] spread={r['spread']:.1f} "
              f"mean={r['mean']:.1f} scores={r['scores']}")
        print(f"        {r['prompt']}")
        print()

    # Score distribution
    all_overalls = []
    with open(SCORES_FILE) as f:
        for line in f:
            obj = json.loads(line)
            o = obj["scores"].get("overall")
            if o is not None:
                all_overalls.append(o)

    print("SCORE DISTRIBUTION:")
    print("-" * 60)
    for bucket in range(1, 11):
        count = sum(1 for s in all_overalls if bucket - 0.5 <= s < bucket + 0.5)
        bar = "#" * (count // 2)
        print(f"  {bucket:2d}: {count:4d} {bar}")

    # Write sharp prompts for GRPO
    sharp = [r for r in results if r["spread"] >= 2.0]
    print(f"\nSHARP PROMPTS (spread >= 2.0): {len(sharp)}/{len(results)}")

    with open("data/rl-sharp-prompts.jsonl", "w") as f:
        for r in sharp:
            json.dump({
                "prompt_idx": r["prompt_idx"],
                "prompt": prompts[r["prompt_idx"]]["prompt"],
                "spread": r["spread"],
                "mean": r["mean"],
                "std": r["std"],
            }, f)
            f.write("\n")
    print(f"Written to data/rl-sharp-prompts.jsonl")


# ============ Main ============

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Diagnostic")
    parser.add_argument("--generate", action="store_true",
                        help="Generate responses from Apertus")
    parser.add_argument("--score", action="store_true",
                        help="Score responses with KE-8B")
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze score spread")
    parser.add_argument("--apertus-url", default=APERTUS_URL)
    parser.add_argument("--ke8b-url", default=KE8B_URL)
    parser.add_argument("--resume", action="store_true", default=True)
    args = parser.parse_args()

    if args.generate:
        generate_responses(url=args.apertus_url)
    elif args.score:
        score_responses(url=args.ke8b_url)
    elif args.analyze:
        analyze()
    else:
        parser.print_help()
