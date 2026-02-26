#!/usr/bin/env python3
"""
Composite scoring for Karma Electric RL pipeline.

Combines three signals:
  1. KE-8B reward scores (5 dimensions + overall, 1-10)
  2. Antijudge penalties (deterministic, subtractive)
  3. Qwen3Guard safety classifications (Safe/Unsafe/Controversial)

Composite formula:
  composite = KE_overall - antijudge_penalty
  If antijudge hard-blocks: composite = 0
  Qwen "Unsafe" flag: annotated for human review, not automatic veto

Usage:
    # Generate composite scores from diagnostic data
    python rl_composite_score.py --diagnostic

    # Generate composite scores from RL generation data
    python rl_composite_score.py \
        --ke8b-scores data/rl-generation/apertus-scored.jsonl \
        --antijudge data/rl-generation/apertus-antijudge.jsonl \
        --safety data/rl-generation/apertus-safety.jsonl \
        --output data/rl-generation/apertus-composite.jsonl

    # Report only (no output file)
    python rl_composite_score.py --diagnostic --report
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"


def load_jsonl(path):
    """Load JSONL file into list of dicts."""
    entries = []
    with open(path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def build_key(entry):
    """Build lookup key from prompt_idx + response_idx."""
    return (entry.get("prompt_idx"), entry.get("response_idx"))


def compute_composite(ke_scores, antijudge_data, safety_data,
                      output_file=None, report=False):
    """Combine three signals into composite scores."""
    # Index by key
    aj_by_key = {build_key(e): e for e in antijudge_data}
    safety_by_key = {build_key(e): e for e in safety_data}

    results = []
    # Stats
    total = 0
    total_hard_block = 0
    total_qwen_unsafe = 0
    total_qwen_controversial = 0
    total_qwen_unsafe_high_ke = 0  # Qwen unsafe but KE score >= 6 (needs review)
    composite_scores = []
    ke_scores_list = []
    penalty_totals = []

    for entry in ke_scores:
        key = build_key(entry)
        total += 1

        ke_overall = entry["scores"].get("overall")
        if ke_overall is None:
            continue

        # Antijudge
        aj = aj_by_key.get(key, {})
        aj_penalty = aj.get("antijudge_total", 0.0)
        aj_hard_block = aj.get("hard_block", False)
        aj_categories = aj.get("antijudge_penalties", {})

        # Safety
        sf = safety_by_key.get(key, {})
        safety_label = sf.get("safety_label", "unknown")
        safety_cats = sf.get("safety_categories", [])
        safety_refusal = sf.get("safety_refusal")

        # Composite
        if aj_hard_block:
            composite = 0.0
            total_hard_block += 1
        else:
            composite = max(0.0, ke_overall - aj_penalty)

        if safety_label == "Unsafe":
            total_qwen_unsafe += 1
            if ke_overall >= 6:
                total_qwen_unsafe_high_ke += 1
        elif safety_label == "Controversial":
            total_qwen_controversial += 1

        composite_scores.append(composite)
        ke_scores_list.append(ke_overall)
        penalty_totals.append(aj_penalty)

        result = {
            "prompt_idx": entry.get("prompt_idx"),
            "response_idx": entry.get("response_idx"),
            "prompt": entry.get("prompt", ""),
            "ke_overall": ke_overall,
            "ke_dimensions": {
                k: v for k, v in entry["scores"].items()
                if k not in ("overall", "red_flags")
            },
            "ke_red_flags": entry["scores"].get("red_flags", ""),
            "antijudge_penalty": round(aj_penalty, 2),
            "antijudge_hard_block": aj_hard_block,
            "antijudge_categories": aj_categories,
            "safety_label": safety_label,
            "safety_categories": safety_cats,
            "safety_refusal": safety_refusal,
            "composite_score": round(composite, 2),
            "needs_review": (
                safety_label == "Unsafe" and ke_overall >= 5
            ),
        }
        results.append(result)

    # Write output
    if output_file and not report:
        with open(output_file, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {len(results)} composite scores to {output_file}")

    # Report
    print(f"\n{'='*60}")
    print(f"COMPOSITE SCORING REPORT")
    print(f"{'='*60}")
    print(f"Total responses:          {total}")
    print(f"With valid KE score:      {len(results)}")

    if composite_scores:
        avg_c = sum(composite_scores) / len(composite_scores)
        avg_ke = sum(ke_scores_list) / len(ke_scores_list)
        avg_pen = sum(penalty_totals) / len(penalty_totals)

        print(f"\n--- KE-8B Reward ---")
        print(f"  Mean overall:           {avg_ke:.2f}")
        print(f"  Min/Max:                {min(ke_scores_list)}/{max(ke_scores_list)}")

        print(f"\n--- Antijudge ---")
        flagged = sum(1 for p in penalty_totals if p > 0)
        print(f"  Clean:                  {len(penalty_totals) - flagged} "
              f"({100*(len(penalty_totals)-flagged)/len(penalty_totals):.0f}%)")
        print(f"  Flagged:                {flagged} "
              f"({100*flagged/len(penalty_totals):.0f}%)")
        print(f"  Hard blocks:            {total_hard_block}")
        print(f"  Mean penalty (flagged): "
              f"{sum(p for p in penalty_totals if p > 0)/max(flagged, 1):.2f}")

        print(f"\n--- Qwen3Guard Safety ---")
        safe = len(results) - total_qwen_unsafe - total_qwen_controversial
        unknown = sum(1 for r in results if r["safety_label"] == "unknown")
        print(f"  Safe:                   {safe - unknown}")
        print(f"  Unsafe:                 {total_qwen_unsafe}")
        print(f"  Controversial:          {total_qwen_controversial}")
        if unknown:
            print(f"  Unknown (not scored):   {unknown}")

        print(f"\n--- Composite ---")
        print(f"  Mean composite:         {avg_c:.2f}")
        print(f"  Mean penalty impact:    {avg_ke - avg_c:.2f}")

        # Score distribution
        print(f"\n  Composite score histogram:")
        for s in range(0, 11):
            count = sum(1 for v in composite_scores if round(v) == s)
            if count > 0:
                bar = "#" * min(count * 50 // len(composite_scores), 50)
                pct = 100 * count / len(composite_scores)
                print(f"    {s:2d}: {bar:30s} {count:5d} ({pct:.1f}%)")

    # Items needing human review
    needs_review = [r for r in results if r["needs_review"]]
    print(f"\n--- Needs Human Review ---")
    print(f"  Qwen unsafe + KE >= 5:  {len(needs_review)}")
    if needs_review:
        print(f"\n  These responses scored well on KE-8B but Qwen3Guard flagged")
        print(f"  as unsafe. Given KE's crisis/adversarial domain, many may be")
        print(f"  appropriate responses that Qwen misclassifies.")
        for r in sorted(needs_review, key=lambda x: -x["ke_overall"])[:20]:
            cats = ", ".join(r["safety_categories"]) if r["safety_categories"] else "?"
            print(f"    [{r['prompt_idx']:3d}/{r['response_idx']}] "
                  f"KE={r['ke_overall']:.0f} composite={r['composite_score']:.1f} "
                  f"cats={cats}")
            prompt_preview = r["prompt"][:80].replace("\n", " ")
            print(f"      {prompt_preview}")

    # Per-prompt spread analysis (for GRPO readiness)
    by_prompt = defaultdict(list)
    for r in results:
        by_prompt[r["prompt_idx"]].append(r["composite_score"])

    spreads = []
    for pidx, scores in by_prompt.items():
        if len(scores) >= 2:
            spread = max(scores) - min(scores)
            spreads.append(spread)

    if spreads:
        sharp = sum(1 for s in spreads if s >= 2.0)
        print(f"\n--- GRPO Readiness (composite-based) ---")
        print(f"  Prompts with >= 2 responses: {len(spreads)}")
        print(f"  Mean spread:                {sum(spreads)/len(spreads):.2f}")
        print(f"  Sharp (spread >= 2.0):      {sharp}/{len(spreads)} "
              f"({100*sharp/len(spreads):.0f}%)")

    print(f"\n{'='*60}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Composite scoring for RL pipeline")
    parser.add_argument("--diagnostic", action="store_true",
                        help="Use diagnostic data paths")
    parser.add_argument("--ke8b-scores", help="KE-8B scores JSONL")
    parser.add_argument("--antijudge", help="Antijudge results JSONL")
    parser.add_argument("--safety", help="Safety guard results JSONL")
    parser.add_argument("--output", help="Output composite JSONL")
    parser.add_argument("--report", action="store_true",
                        help="Report only, no output file")
    args = parser.parse_args()

    if args.diagnostic:
        ke_path = DATA_DIR / "rl-diagnostic-scores.jsonl"
        aj_path = DATA_DIR / "rl-diagnostic-antijudge.jsonl"
        sf_path = DATA_DIR / "rl-diagnostic-safety.jsonl"
        out_path = DATA_DIR / "rl-diagnostic-composite.jsonl"
    else:
        ke_path = Path(args.ke8b_scores) if args.ke8b_scores else None
        aj_path = Path(args.antijudge) if args.antijudge else None
        sf_path = Path(args.safety) if args.safety else None
        out_path = Path(args.output) if args.output else None

    if not ke_path or not ke_path.exists():
        print(f"ERROR: KE-8B scores not found: {ke_path}")
        sys.exit(1)
    if not aj_path or not aj_path.exists():
        print(f"ERROR: Antijudge results not found: {aj_path}")
        sys.exit(1)

    ke_scores = load_jsonl(ke_path)
    aj_data = load_jsonl(aj_path)

    # Safety data is optional (may still be running)
    if sf_path and sf_path.exists():
        sf_data = load_jsonl(sf_path)
        print(f"Loaded: {len(ke_scores)} KE scores, {len(aj_data)} antijudge, "
              f"{len(sf_data)} safety")
    else:
        sf_data = []
        print(f"Loaded: {len(ke_scores)} KE scores, {len(aj_data)} antijudge, "
              f"safety data not available yet")

    compute_composite(ke_scores, aj_data, sf_data,
                      output_file=out_path if not args.report else None,
                      report=args.report)


if __name__ == "__main__":
    main()
