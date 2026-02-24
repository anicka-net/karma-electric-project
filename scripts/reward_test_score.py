#!/usr/bin/env python3
"""
Score test fixtures with KE-8B and generate analysis reports.

Reads data/reward-test-fixtures.jsonl (from reward_test_generate.py),
scores each variant with KE-8B in reward-evaluator mode,
saves scores to data/reward-test-scores.jsonl,
and prints statistical analysis.

Usage:
    python3 scripts/reward_test_score.py                        # score all + report
    python3 scripts/reward_test_score.py --test paraphrase      # one test only
    python3 scripts/reward_test_score.py --report               # report from existing scores
    python3 scripts/reward_test_score.py --resume               # skip already-scored
    python3 scripts/reward_test_score.py --ke8b-url URL         # custom endpoint
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reward_test_utils import (
    query_ke8b_reward, extract_reward_scores, check_ke8b,
    compute_paraphrase_stats, compute_style_stats, compute_crosslang_stats,
    log, KE8B_URL, DIMENSIONS,
)

FIXTURES_FILE = Path("data/reward-test-fixtures.jsonl")
SCORES_FILE = Path("data/reward-test-scores.jsonl")
REPORT_DIR = Path("results")


def load_fixtures(test_type=None):
    """Load fixtures, optionally filtered by test type."""
    fixtures = []
    with open(FIXTURES_FILE) as f:
        for line in f:
            entry = json.loads(line.strip())
            if test_type and entry["test_type"] != test_type:
                continue
            fixtures.append(entry)
    return fixtures


def load_existing_scores():
    """Load already-scored keys for resume."""
    existing = set()
    if SCORES_FILE.exists():
        with open(SCORES_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    key = f"{entry['test_type']}:{entry['prompt_id']}:{entry['variant']}"
                    existing.add(key)
                except (json.JSONDecodeError, KeyError):
                    continue
    return existing


def save_score(entry):
    """Append one score to JSONL."""
    with open(SCORES_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def score_one(user_prompt, ai_response, ke8b_url):
    """Score a single prompt-response pair. Returns parsed scores dict."""
    t0 = time.time()
    raw = query_ke8b_reward(user_prompt, ai_response, url=ke8b_url)
    elapsed = time.time() - t0
    scores = extract_reward_scores(raw)
    return scores, elapsed


def score_paraphrase_fixtures(fixtures, ke8b_url, existing, resume):
    """Score all paraphrase test fixtures."""
    log(f"\n{'='*60}")
    log("SCORING PARAPHRASE INVARIANCE TEST")
    log(f"{'='*60}")

    total = 0
    errors = 0
    for fi, fix in enumerate(fixtures, 1):
        pid = fix["prompt_id"]
        gold_answer = fix["gold_answer"]

        # Score original prompt + gold answer
        variants = [("original", fix["original_prompt"])]
        for pi, para in enumerate(fix["paraphrases"]):
            variants.append((f"para_{pi}", para))

        for vi, (variant_name, user_prompt) in enumerate(variants):
            key = f"paraphrase:{pid}:{variant_name}"
            if resume and key in existing:
                continue

            label = f"[{fi}/{len(fixtures)}] {pid[:30]}:{variant_name}"
            print(f"  {label}...", end=" ", flush=True)

            try:
                scores, elapsed = score_one(user_prompt, gold_answer, ke8b_url)
                overall = scores.get("overall")
                print(f"overall={overall}/10 ({elapsed:.0f}s)")

                save_score({
                    "test_type": "paraphrase",
                    "prompt_id": pid,
                    "variant": variant_name,
                    "user_prompt": user_prompt,
                    "scores": {k: v for k, v in scores.items()
                               if k not in ("raw_text", "red_flags")},
                    "red_flags": scores.get("red_flags"),
                    "scored_at": datetime.now().isoformat(),
                })
                total += 1
            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

            time.sleep(0.3)

    log(f"Paraphrase scoring: {total} scored, {errors} errors")


def score_style_fixtures(fixtures, ke8b_url, existing, resume):
    """Score all style gaming test fixtures."""
    log(f"\n{'='*60}")
    log("SCORING STYLE GAMING TEST")
    log(f"{'='*60}")

    total = 0
    errors = 0
    for fi, fix in enumerate(fixtures, 1):
        pid = fix["prompt_id"]
        user_prompt = fix["user_prompt"]

        # Score gold + 5 style variants
        variants = [("gold", fix["gold_answer"])]
        for style, text in fix["style_variants"].items():
            variants.append((style, text))

        for vi, (variant_name, ai_response) in enumerate(variants):
            key = f"style:{pid}:{variant_name}"
            if resume and key in existing:
                continue

            label = f"[{fi}/{len(fixtures)}] {pid[:30]}:{variant_name}"
            print(f"  {label}...", end=" ", flush=True)

            try:
                scores, elapsed = score_one(user_prompt, ai_response, ke8b_url)
                overall = scores.get("overall")
                print(f"overall={overall}/10 ({elapsed:.0f}s)")

                save_score({
                    "test_type": "style",
                    "prompt_id": pid,
                    "variant": variant_name,
                    "user_prompt": user_prompt,
                    "scores": {k: v for k, v in scores.items()
                               if k not in ("raw_text", "red_flags")},
                    "red_flags": scores.get("red_flags"),
                    "scored_at": datetime.now().isoformat(),
                })
                total += 1
            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

            time.sleep(0.3)

    log(f"Style scoring: {total} scored, {errors} errors")


def score_crosslang_fixtures(fixtures, ke8b_url, existing, resume):
    """Score cross-language test fixtures (EN + CZ)."""
    log(f"\n{'='*60}")
    log("SCORING CROSS-LANGUAGE CONSISTENCY TEST")
    log(f"{'='*60}")

    total = 0
    errors = 0
    for fi, fix in enumerate(fixtures, 1):
        pid = fix["prompt_id"]

        # Score both EN and CZ versions
        variants = [
            ("en", fix["en_prompt"], fix["en_answer"]),
            ("cz", fix["cz_prompt"], fix["cz_answer"]),
        ]

        for lang, user_prompt, ai_response in variants:
            key = f"crosslang:{pid}:{lang}"
            if resume and key in existing:
                continue

            label = f"[{fi}/{len(fixtures)}] {pid[:30]}:{lang}"
            print(f"  {label}...", end=" ", flush=True)

            try:
                scores, elapsed = score_one(user_prompt, ai_response, ke8b_url)
                overall = scores.get("overall")
                print(f"overall={overall}/10 ({elapsed:.0f}s)")

                save_score({
                    "test_type": "crosslang",
                    "prompt_id": pid,
                    "variant": lang,
                    "user_prompt": user_prompt,
                    "scores": {k: v for k, v in scores.items()
                               if k not in ("raw_text", "red_flags")},
                    "red_flags": scores.get("red_flags"),
                    "scored_at": datetime.now().isoformat(),
                })
                total += 1
            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

            time.sleep(0.3)

    log(f"Cross-language scoring: {total} scored, {errors} errors")


# ============ Reporting ============

def load_all_scores():
    """Load all scores into structured dicts by test type."""
    paraphrase = {}  # {prompt_id: {variant: {dim: score}}}
    style = {}
    crosslang_en = {}
    crosslang_cz = {}

    with open(SCORES_FILE) as f:
        for line in f:
            entry = json.loads(line.strip())
            tt = entry["test_type"]
            pid = entry["prompt_id"]
            var = entry["variant"]
            scores = entry["scores"]

            if tt == "paraphrase":
                paraphrase.setdefault(pid, {})[var] = scores
            elif tt == "style":
                style.setdefault(pid, {})[var] = scores
            elif tt == "crosslang":
                if var == "en":
                    crosslang_en[pid] = scores
                elif var == "cz":
                    crosslang_cz[pid] = scores

    return paraphrase, style, crosslang_en, crosslang_cz


def print_report(paraphrase, style, crosslang_en, crosslang_cz):
    """Print full analysis report."""
    print(f"\n{'='*70}")
    print("KE-8B REWARD MODEL VALIDATION REPORT")
    print(f"{'='*70}")

    # --- Paraphrase Invariance ---
    if paraphrase:
        stats = compute_paraphrase_stats(paraphrase)
        s = stats["summary"]

        print(f"\n--- TEST 1: PROMPT PARAPHRASE INVARIANCE ---")
        print(f"Prompts: {s['n_prompts']} | Variants: original + paraphrases")
        print(f"\nMean std of overall score: {s['mean_overall_std']:.3f} "
              f"(threshold: {s['threshold']})")
        print(f"Max std: {s['max_overall_std']:.3f}")
        status = "PASS" if s["acceptable"] else "FAIL"
        print(f"Status: {status}")

        if s["worst_prompts"]:
            print(f"\nWorst prompts (highest variance):")
            for wp in s["worst_prompts"][:5]:
                print(f"  {wp['id'][:40]:<42s} std={wp['std']:.2f}  "
                      f"scores={wp['scores']}")

        # Dimension stability
        print(f"\nDimension stability (mean std across variants):")
        for pid, pstats in stats["per_prompt"].items():
            pass  # aggregate
        dim_agg = {d: [] for d in DIMENSIONS + ["overall"]}
        for pid, pstats in stats["per_prompt"].items():
            for d, v in pstats["dimension_stds"].items():
                if v is not None:
                    dim_agg[d].append(v)
        import numpy as np
        for d in DIMENSIONS + ["overall"]:
            vals = dim_agg[d]
            if vals:
                print(f"  {d:<22s}: {np.mean(vals):.3f}")

    # --- Style Gaming ---
    if style:
        stats = compute_style_stats(style)
        s = stats["summary"]

        print(f"\n--- TEST 2: STYLE GAMING ---")
        print(f"Prompts: {len(style)} | Styles: gold + 5 variants")

        print(f"\nStyle bias (mean delta from gold on overall):")
        print(f"  {'gold':<16s}:  0.00 (baseline)")
        for sname, sbias in stats["style_bias"].items():
            delta = sbias["mean_delta_overall"]
            if delta is not None:
                marker = " **" if abs(delta) >= 1.5 else ""
                print(f"  {sname:<16s}: {delta:+.2f}{marker}")

        status = "PASS" if s["acceptable"] else "FAIL"
        print(f"\nMost biased style: {s['most_biased_style']} "
              f"(delta={s['most_biased_delta']:+.2f})")
        print(f"Status: {status} (threshold: {s['threshold']})")

    # --- Cross-Language ---
    if crosslang_en and crosslang_cz:
        stats = compute_crosslang_stats(crosslang_en, crosslang_cz)

        print(f"\n--- TEST 4: CROSS-LANGUAGE CONSISTENCY ---")
        print(f"Paired prompts: {stats['n_paired']}")
        print(f"\nEN mean overall: {stats['en_mean']}")
        print(f"CZ mean overall: {stats['cz_mean']}")
        if stats['mean_delta'] is not None:
            print(f"Mean delta (CZ - EN): {stats['mean_delta']:+.2f}")
        else:
            print(f"Mean delta (CZ - EN): insufficient data")

        if stats["t_stat"] is not None:
            print(f"Paired t-test: t={stats['t_stat']:.3f}, p={stats['p_value']:.4f}")
            sig = "SIGNIFICANT BIAS" if stats["significant"] else "no significant bias"
            print(f"Status: {sig}")

        print(f"\nDimension-level bias (CZ - EN):")
        for d, delta in stats["dimension_bias"].items():
            if delta is not None:
                marker = " **" if abs(delta) >= 1.0 else ""
                print(f"  {d:<22s}: {delta:+.2f}{marker}")

    print(f"\n{'='*70}")


def save_report_json(paraphrase, style, crosslang_en, crosslang_cz):
    """Save structured report as JSON."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {"timestamp": datetime.now().isoformat()}

    if paraphrase:
        report["paraphrase_invariance"] = compute_paraphrase_stats(paraphrase)
    if style:
        report["style_gaming"] = compute_style_stats(style)
    if crosslang_en and crosslang_cz:
        report["crosslang_consistency"] = compute_crosslang_stats(
            crosslang_en, crosslang_cz)

    out = REPORT_DIR / "reward-validation-report.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    log(f"Report saved to {out}")


def main():
    parser = argparse.ArgumentParser(
        description="Score fixtures and report on KE-8B reward model")
    parser.add_argument("--test", choices=["paraphrase", "style", "crosslang", "all"],
                        default="all")
    parser.add_argument("--report", action="store_true",
                        help="Report only (no scoring)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-scored")
    parser.add_argument("--ke8b-url", default=KE8B_URL)
    args = parser.parse_args()

    if args.report:
        if not SCORES_FILE.exists():
            print(f"ERROR: {SCORES_FILE} not found. Run scoring first.")
            sys.exit(1)
        paraphrase, style, crosslang_en, crosslang_cz = load_all_scores()
        print_report(paraphrase, style, crosslang_en, crosslang_cz)
        save_report_json(paraphrase, style, crosslang_en, crosslang_cz)
        return

    # Check KE-8B
    log(f"Checking KE-8B at {args.ke8b_url}...")
    if not check_ke8b(args.ke8b_url):
        print(f"ERROR: KE-8B not reachable at {args.ke8b_url}")
        sys.exit(1)
    log("KE-8B OK")

    if not FIXTURES_FILE.exists():
        print(f"ERROR: {FIXTURES_FILE} not found. Run reward_test_generate.py first.")
        sys.exit(1)

    existing = load_existing_scores() if args.resume else set()
    if existing:
        log(f"Resume mode: {len(existing)} scores already exist")

    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Score each test type
    if args.test in ("paraphrase", "all"):
        fixtures = load_fixtures("paraphrase")
        if fixtures:
            score_paraphrase_fixtures(fixtures, args.ke8b_url, existing, args.resume)

    if args.test in ("style", "all"):
        fixtures = load_fixtures("style")
        if fixtures:
            score_style_fixtures(fixtures, args.ke8b_url, existing, args.resume)

    if args.test in ("crosslang", "all"):
        fixtures = load_fixtures("crosslang")
        if fixtures:
            score_crosslang_fixtures(fixtures, args.ke8b_url, existing, args.resume)

    # Generate report
    log("\nGenerating report...")
    paraphrase, style, crosslang_en, crosslang_cz = load_all_scores()
    print_report(paraphrase, style, crosslang_en, crosslang_cz)
    save_report_json(paraphrase, style, crosslang_en, crosslang_cz)


if __name__ == "__main__":
    main()
