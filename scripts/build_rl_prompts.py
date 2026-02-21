#!/usr/bin/env python3
"""
Build curated RL prompt dataset from open-source sources.

Sources (all attribution-only licenses):
  1. UltraFeedback prompts (MIT) — trl-lib/ultrafeedback-prompt
  2. Anthropic HH-RLHF (MIT) — Anthropic/hh-rlhf
  3. HelpSteer2 (CC-BY 4.0) — nvidia/HelpSteer2
  4. OASST2 (Apache 2.0) — OpenAssistant/oasst2
  5. Capybara (Apache 2.0) — LDJnr/Capybara
  6. Dolly 15k (CC-BY-SA 3.0) — databricks/databricks-dolly-15k
  7. CounselChat (MIT) — nbertagnolli/counsel-chat
  8. Karma Electric Buddhist questions (original)

Combined license: CC-BY-SA 4.0 with attribution to all sources.
(CC-BY-SA due to Dolly's CC-BY-SA 3.0 share-alike requirement)

Usage:
  python build_rl_prompts.py download   # Download all source datasets
  python build_rl_prompts.py build      # Build the combined prompt set
  python build_rl_prompts.py stats      # Show statistics
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "data" / "rl-prompt-cache"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "rl-prompts"

# Target composition
TARGETS = {
    "ultrafeedback": 3000,
    "anthropic_helpful": 1500,
    "anthropic_harmless": 1000,
    "helpsteer2": 2000,
    "oasst2": 1500,
    "capybara": 500,
    "dolly": 500,
    "counselchat": 500,
    "buddhist": 1000,
}

ATTRIBUTION = """# Karma Electric RL Prompt Dataset
#
# License: CC-BY-SA 4.0
# https://creativecommons.org/licenses/by-sa/4.0/
#
# This dataset combines prompts from the following sources:
#
# 1. UltraFeedback (MIT License)
#    Source: trl-lib/ultrafeedback-prompt
#    Paper: Cui et al., "UltraFeedback: Boosting Language Models with
#           Scaled AI Feedback" (2024)
#
# 2. Anthropic HH-RLHF (MIT License)
#    Source: Anthropic/hh-rlhf
#    Paper: Bai et al., "Training a Helpful and Harmless Assistant with
#           Reinforcement Learning from Human Feedback" (2022)
#
# 3. HelpSteer2 (CC-BY 4.0)
#    Source: nvidia/HelpSteer2
#    Paper: Wang et al., "HelpSteer2: Open-source dataset for training
#           top-performing reward models" (2024)
#
# 4. OpenAssistant OASST2 (Apache 2.0)
#    Source: OpenAssistant/oasst2
#    Paper: Kopf et al., "OpenAssistant Conversations --
#           Democratizing Large Language Model Alignment" (2023)
#
# 5. Capybara (Apache 2.0)
#    Source: LDJnr/Capybara
#
# 6. Dolly 15k (CC-BY-SA 3.0)
#    Source: databricks/databricks-dolly-15k
#
# 7. CounselChat (MIT License)
#    Source: nbertagnolli/counsel-chat
#
# 8. Karma Electric Buddhist Questions (Original)
#    Source: anicka-net/karma-electric-project
"""


def log(msg):
    print(f"[rl-prompts] {msg}", file=sys.stderr)


def prompt_hash(text):
    """Short hash for deduplication."""
    return hashlib.md5(text.strip().lower().encode()).hexdigest()[:12]


def clean_prompt(text):
    """Normalize whitespace, strip prefixes."""
    text = text.strip()
    # Remove "Human: " prefix from Anthropic format
    if text.startswith("Human: "):
        text = text[7:]
    # Remove "### Instruction:" prefix
    if text.startswith("### Instruction:"):
        text = text[16:].strip()
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def quality_filter(text, min_len=10, max_len=2000):
    """Basic quality filter for prompts."""
    if not text or len(text) < min_len:
        return False
    if len(text) > max_len:
        return False
    # Skip gibberish / single-word
    if len(text.split()) < 3:
        return False
    # Skip prompts that are just URLs
    if text.startswith("http") and " " not in text:
        return False
    return True


def save_source(name, prompts):
    """Save extracted prompts for one source immediately."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"raw-{name}.jsonl"
    with open(out, "w") as f:
        for p in prompts:
            json.dump({"prompt": p, "source": name}, f)
            f.write("\n")
    log(f"  Saved {len(prompts)} → {out.name}")


# ─── Source extractors ───────────────────────────────────────────────


def download_and_extract_ultrafeedback():
    """Extract prompts from trl-lib/ultrafeedback-prompt (MIT)."""
    from datasets import load_dataset
    log("Downloading UltraFeedback prompts...")
    ds = load_dataset("trl-lib/ultrafeedback-prompt", split="train",
                       cache_dir=str(CACHE_DIR))
    prompts = []
    for row in ds:
        prompt = row.get("prompt", "")
        # prompt is a list of chat messages: [{"role": "user", "content": "..."}]
        if isinstance(prompt, list):
            user_msgs = [m["content"] for m in prompt if m.get("role") == "user"]
            text = user_msgs[0] if user_msgs else ""
        else:
            text = prompt
        text = clean_prompt(text)
        if quality_filter(text):
            prompts.append(text)
    log(f"  UltraFeedback: {len(prompts)} prompts extracted")
    save_source("ultrafeedback", prompts)
    return prompts


def download_and_extract_anthropic():
    """Extract first-turn prompts from Anthropic HH-RLHF (MIT)."""
    from datasets import load_dataset
    helpful, harmless = [], []

    for split_name, target_list in [
        ("helpful-base", helpful),
        ("helpful-online", helpful),
        ("harmless-base", harmless),
    ]:
        log(f"  Downloading Anthropic HH-RLHF {split_name}...")
        try:
            ds = load_dataset("Anthropic/hh-rlhf", data_dir=split_name,
                              split="train", cache_dir=str(CACHE_DIR))
            for row in ds:
                # Extract first human turn from conversation
                text = row.get("chosen", "")
                if "\n\nHuman: " in text:
                    first_turn = text.split("\n\nHuman: ")[1]
                    if "\n\nAssistant: " in first_turn:
                        first_turn = first_turn.split("\n\nAssistant: ")[0]
                    first_turn = clean_prompt(first_turn)
                    if quality_filter(first_turn):
                        target_list.append(first_turn)
        except Exception as e:
            log(f"  Warning: {split_name} failed: {e}")

    log(f"  Anthropic helpful: {len(helpful)} prompts")
    log(f"  Anthropic harmless: {len(harmless)} prompts")
    save_source("anthropic_helpful", helpful)
    save_source("anthropic_harmless", harmless)
    return helpful, harmless


def download_and_extract_helpsteer2():
    """Extract prompts from nvidia/HelpSteer2 (CC-BY 4.0)."""
    from datasets import load_dataset
    log("Downloading HelpSteer2...")
    ds = load_dataset("nvidia/HelpSteer2", split="train",
                       cache_dir=str(CACHE_DIR))
    prompts = []
    for row in ds:
        text = row.get("prompt", "")
        text = clean_prompt(text)
        if quality_filter(text):
            prompts.append(text)
    log(f"  HelpSteer2: {len(prompts)} prompts extracted")
    save_source("helpsteer2", prompts)
    return prompts


def download_and_extract_oasst2():
    """Extract first-turn English prompts from OASST2 (Apache 2.0)."""
    from datasets import load_dataset
    log("Downloading OASST2...")
    ds = load_dataset("OpenAssistant/oasst2", split="train",
                       cache_dir=str(CACHE_DIR))
    prompts = []
    for row in ds:
        # Only first turn (no parent), English, prompter role
        if (row.get("parent_id") is None
            and row.get("role") == "prompter"
            and row.get("lang") == "en"):
            text = clean_prompt(row.get("text", ""))
            if quality_filter(text):
                prompts.append(text)
    log(f"  OASST2: {len(prompts)} English first-turn prompts")
    save_source("oasst2", prompts)
    return prompts


def download_and_extract_capybara():
    """Extract first-turn prompts from Capybara (Apache 2.0)."""
    from datasets import load_dataset
    log("Downloading Capybara...")
    ds = load_dataset("LDJnr/Capybara", split="train",
                       cache_dir=str(CACHE_DIR))
    prompts = []
    for row in ds:
        conv = row.get("conversation", [])
        if conv:
            text = conv[0].get("input", "")
            text = clean_prompt(text)
            if quality_filter(text):
                prompts.append(text)
    log(f"  Capybara: {len(prompts)} first-turn prompts")
    save_source("capybara", prompts)
    return prompts


def download_and_extract_dolly():
    """Extract standalone prompts from Dolly 15k (CC-BY-SA 3.0)."""
    from datasets import load_dataset
    log("Downloading Dolly 15k...")
    ds = load_dataset("databricks/databricks-dolly-15k", split="train",
                       cache_dir=str(CACHE_DIR))
    prompts = []
    for row in ds:
        # Only standalone instructions (no context needed)
        if row.get("context", "").strip():
            continue
        text = row.get("instruction", "")
        text = clean_prompt(text)
        if quality_filter(text):
            prompts.append(text)
    log(f"  Dolly: {len(prompts)} standalone prompts")
    save_source("dolly", prompts)
    return prompts


def download_and_extract_counselchat():
    """Extract unique therapy questions from CounselChat (MIT)."""
    from datasets import load_dataset
    log("Downloading CounselChat...")
    ds = load_dataset("nbertagnolli/counsel-chat", split="train",
                       cache_dir=str(CACHE_DIR))
    seen = set()
    prompts = []
    for row in ds:
        # Use questionTitle + questionText for richer prompts
        title = (row.get("questionTitle") or "").strip()
        text = (row.get("questionText") or "").strip()
        # Prefer the longer/more detailed text
        q = text if len(text) > len(title) else title
        if not q:
            continue
        # Deduplicate by question ID
        qid = row.get("questionID")
        if qid in seen:
            continue
        seen.add(qid)
        q = clean_prompt(q)
        if quality_filter(q, min_len=15):
            prompts.append(q)
    log(f"  CounselChat: {len(prompts)} unique therapy questions")
    save_source("counselchat", prompts)
    return prompts


def extract_buddhist_questions():
    """Extract Buddhist questions from our existing data."""
    # Look in multiple locations (repo data/ + optional BUDDHIST_QA_DIR env var)
    candidates = [
        Path(__file__).parent.parent / "data",
    ]
    extra = os.environ.get("BUDDHIST_QA_DIR")
    if extra:
        candidates.append(Path(extra))
    prompts = []

    for base in candidates:
        if not base.exists():
            continue

        # 1. Universal questions — format: **Q1** (ID:nnn) > question text
        uq = base / "buddhist-questions" / "universal_questions_translated.md"
        if uq.exists():
            uq_count = 0
            for line in uq.read_text().splitlines():
                line = line.strip()
                # Match "> question text" lines (blockquote after **Qn** header)
                if line.startswith("> "):
                    q = line[2:].strip()
                    if quality_filter(q, min_len=20):
                        prompts.append(q)
                        uq_count += 1
            log(f"  Buddhist (universal questions): {uq_count} from {uq.name}")

        # 2. Diamond Way translated (full archive, if it exists)
        dw = base / "buddhist-questions" / "diamond_way_questions_translated_full.txt"
        if dw.exists():
            dw_count = 0
            for line in dw.read_text().splitlines():
                line = line.strip()
                if line.endswith("?") and len(line) > 15:
                    if quality_filter(line):
                        prompts.append(line)
                        dw_count += 1
            log(f"  Buddhist (Diamond Way translated): {dw_count}")

        # 3. QA library questions — two formats:
        #    a) ### Q1: question text
        #    b) **Q: question text**
        qa_dir = base / "qa-library"
        if qa_dir.exists():
            qa_count = 0
            for md_file in qa_dir.glob("*-QA*.md"):
                for line in md_file.read_text().splitlines():
                    line = line.strip()
                    q = None
                    # Format: ### Q1: question text
                    if re.match(r'^###\s+Q\d+:', line):
                        q = re.sub(r'^###\s+Q\d+:\s*', '', line).strip()
                    # Format: **Q: question text**
                    elif re.match(r'^\*\*Q:', line):
                        q = re.sub(r'^\*\*Q:\s*', '', line).strip()
                        q = q.rstrip('*').strip()
                    if q and quality_filter(q, min_len=15):
                        prompts.append(q)
                        qa_count += 1
            log(f"  Buddhist (QA library): {qa_count} from {qa_dir}")

    log(f"  Buddhist total: {len(prompts)} questions")
    save_source("buddhist", prompts)
    return prompts


# ─── Main build ─────────────────────────────────────────────────────


def cmd_download(args):
    """Download all source datasets to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log("=== Downloading all sources ===\n")

    download_and_extract_ultrafeedback()
    download_and_extract_anthropic()
    download_and_extract_helpsteer2()
    download_and_extract_oasst2()
    download_and_extract_capybara()
    download_and_extract_dolly()
    download_and_extract_counselchat()
    extract_buddhist_questions()

    log("\n=== All sources downloaded. Run 'build' to create the combined set. ===")


def cmd_build(args):
    """Build the combined, deduplicated prompt set."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    # Load all raw extracts
    sources = {}
    for name in TARGETS:
        raw_file = OUTPUT_DIR / f"raw-{name}.jsonl"
        if not raw_file.exists():
            log(f"Missing {raw_file} — run 'download' first")
            sys.exit(1)
        prompts = []
        with open(raw_file) as f:
            for line in f:
                d = json.loads(line)
                prompts.append(d["prompt"])
        sources[name] = prompts
        log(f"Loaded {name}: {len(prompts)} raw prompts")

    # Global deduplication
    seen_hashes = set()
    deduped = {}

    for name in TARGETS:
        unique = []
        for p in sources[name]:
            h = prompt_hash(p)
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique.append(p)
        deduped[name] = unique
        dup_count = len(sources[name]) - len(unique)
        if dup_count > 0:
            log(f"  {name}: {dup_count} duplicates removed, {len(unique)} unique")
        else:
            log(f"  {name}: {len(unique)} unique (no duplicates)")

    # Sample to target counts
    combined = []
    for name, target in TARGETS.items():
        pool = deduped[name]
        if len(pool) < target:
            log(f"  WARNING: {name} has only {len(pool)} prompts, "
                f"target was {target}. Using all.")
            sample = pool
        else:
            sample = random.sample(pool, target)

        for p in sample:
            combined.append({
                "prompt": p,
                "source": name,
                "hash": prompt_hash(p),
            })

    # Shuffle
    random.shuffle(combined)

    # Write combined dataset
    out_file = OUTPUT_DIR / "rl-prompts-v1.jsonl"
    with open(out_file, "w") as f:
        for entry in combined:
            json.dump(entry, f)
            f.write("\n")

    log(f"\nBuilt {len(combined)} prompts -> {out_file}")

    # Also write a clean version (just prompts, for the RL pipeline)
    clean_file = OUTPUT_DIR / "rl-prompts-v1-clean.jsonl"
    with open(clean_file, "w") as f:
        for entry in combined:
            json.dump({"prompt": entry["prompt"]}, f)
            f.write("\n")
    log(f"Clean version -> {clean_file}")

    # Write attribution file
    attr_file = OUTPUT_DIR / "ATTRIBUTION.md"
    with open(attr_file, "w") as f:
        f.write(ATTRIBUTION.strip())
        f.write("\n")
    log(f"Attribution -> {attr_file}")

    # Print stats
    _print_stats(combined)


def cmd_stats(args):
    """Show statistics for the built dataset."""
    out_file = OUTPUT_DIR / "rl-prompts-v1.jsonl"
    if not out_file.exists():
        log(f"No dataset found at {out_file}. Run 'build' first.")
        sys.exit(1)

    combined = []
    with open(out_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            combined.append(json.loads(line))

    _print_stats(combined)


def _print_stats(combined):
    """Print dataset statistics."""
    source_counts = {}
    source_lengths = {}
    for entry in combined:
        s = entry["source"]
        source_counts[s] = source_counts.get(s, 0) + 1
        if s not in source_lengths:
            source_lengths[s] = []
        source_lengths[s].append(len(entry["prompt"]))

    total = len(combined)
    print(f"\n{'='*60}")
    print(f"RL Prompt Dataset Statistics")
    print(f"{'='*60}")
    print(f"Total prompts: {total}")
    print(f"\nSource breakdown:")
    print(f"{'Source':<25} {'Count':>6} {'%':>6}  {'Avg len':>8}")
    print(f"{'-'*25} {'-'*6} {'-'*6}  {'-'*8}")
    for name in TARGETS:
        count = source_counts.get(name, 0)
        pct = 100 * count / total if total else 0
        avg_len = sum(source_lengths.get(name, [0])) / max(count, 1)
        print(f"{name:<25} {count:>6} {pct:>5.1f}%  {avg_len:>7.0f}")

    # Length distribution
    all_lengths = [len(e["prompt"]) for e in combined]
    all_lengths.sort()
    print(f"\nPrompt length distribution:")
    print(f"  Min: {all_lengths[0]} chars")
    print(f"  P25: {all_lengths[len(all_lengths)//4]} chars")
    print(f"  P50: {all_lengths[len(all_lengths)//2]} chars")
    print(f"  P75: {all_lengths[3*len(all_lengths)//4]} chars")
    print(f"  Max: {all_lengths[-1]} chars")
    print(f"  Mean: {sum(all_lengths)/len(all_lengths):.0f} chars")

    # Sample prompts per source
    random.seed(123)
    print(f"\nSample prompts:")
    by_source = {}
    for e in combined:
        by_source.setdefault(e["source"], []).append(e)
    for name in TARGETS:
        if name in by_source:
            s = random.choice(by_source[name])
            preview = s["prompt"][:120].replace("\n", " ")
            if len(s["prompt"]) > 120:
                preview += "..."
            print(f"  [{name}] {preview}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build RL prompt dataset")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("download", help="Download and extract all source datasets")
    sub.add_parser("build", help="Build combined deduplicated prompt set")
    sub.add_parser("stats", help="Show dataset statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "download":
        cmd_download(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "stats":
        cmd_stats(args)
