#!/usr/bin/env python3
"""
Safety guard: Qwen3Guard-Gen-0.6B wrapper for Karma Electric RL pipeline.

Classifies responses as Safe/Unsafe/Controversial with category labels.
NOT an automatic veto — flags responses for human review.

Usage:
    # Score diagnostic responses
    python safety_guard.py --input data/rl-diagnostic-responses.jsonl \
                           --output data/rl-diagnostic-safety.jsonl

    # Resume interrupted run
    python safety_guard.py --input data/rl-diagnostic-responses.jsonl \
                           --output data/rl-diagnostic-safety.jsonl --resume

    # Score RL generation responses
    python safety_guard.py --input data/rl-generation/apertus-responses.jsonl \
                           --output data/rl-generation/apertus-safety.jsonl
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen3Guard-Gen-0.6B"

SAFETY_CATEGORIES = [
    "Violent", "Non-violent Illegal Acts", "Sexual Content or Sexual Acts",
    "PII", "Suicide & Self-Harm", "Unethical Acts",
    "Politically Sensitive Topics", "Copyright Violation",
]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_model():
    """Load Qwen3Guard model and tokenizer."""
    log(f"Loading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, torch_dtype=torch.float32, device_map="cpu"
    )
    params_m = sum(p.numel() for p in model.parameters()) / 1e6
    log(f"Model loaded: {params_m:.0f}M params")
    return model, tokenizer


def classify_response(model, tokenizer, prompt, response, max_new_tokens=64,
                      max_input_chars=2000):
    """Classify a prompt+response pair. Returns (label, categories, refusal)."""
    # Truncate long inputs — safety signal is in the first part
    if len(response) > max_input_chars:
        response = response[:max_input_chars] + "..."
    if len(prompt) > max_input_chars:
        prompt = prompt[:max_input_chars] + "..."
    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer([text], return_tensors="pt")
    out = model.generate(**inputs, max_new_tokens=max_new_tokens)
    content = tokenizer.decode(
        out[0][len(inputs.input_ids[0]):], skip_special_tokens=True
    )
    return parse_guard_output(content)


def parse_guard_output(content):
    """Parse Qwen3Guard output into structured result."""
    safe_match = re.search(r"Safety:\s*(Safe|Unsafe|Controversial)", content)
    label = safe_match.group(1) if safe_match else None

    category_pattern = "|".join(re.escape(c) for c in SAFETY_CATEGORIES)
    categories = re.findall(category_pattern, content)
    if not categories or categories == ["None"]:
        categories = []

    refusal_match = re.search(r"Refusal:\s*(Yes|No)", content)
    refusal = refusal_match.group(1) if refusal_match else None

    return {
        "label": label,
        "categories": categories,
        "refusal": refusal,
        "raw": content,
    }


def load_scored_keys(output_file):
    """Load already-scored keys for resume."""
    keys = set()
    if not output_file.exists():
        return keys
    with open(output_file) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            key = f"{entry.get('prompt_idx', '')}:{entry.get('response_idx', '')}"
            keys.add(key)
    return keys


def main():
    parser = argparse.ArgumentParser(description="Safety guard scoring")
    parser.add_argument("--input", required=True, help="Input responses JSONL")
    parser.add_argument("--output", required=True, help="Output safety JSONL")
    parser.add_argument("--resume", action="store_true", help="Skip scored")
    parser.add_argument("--limit", type=int, default=0, help="Max to score")
    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.output)

    if not input_file.exists():
        log(f"ERROR: {input_file} not found")
        sys.exit(1)

    # Load responses
    responses = []
    with open(input_file) as f:
        for line in f:
            if line.strip():
                responses.append(json.loads(line))
    log(f"Loaded {len(responses)} responses")

    if args.limit:
        responses = responses[:args.limit]

    # Resume support
    scored_keys = set()
    if args.resume:
        scored_keys = load_scored_keys(output_file)
        log(f"Resume: {len(scored_keys)} already scored")

    # Load model
    model, tokenizer = load_model()

    # Score
    mode = "a" if args.resume else "w"
    out_f = open(output_file, mode, encoding="utf-8")

    total_scored = 0
    total_skipped = 0
    total_unsafe = 0
    total_controversial = 0
    start_time = time.time()

    try:
        for ri, resp in enumerate(responses):
            key = f"{resp.get('prompt_idx', '')}:{resp.get('response_idx', '')}"
            if key in scored_keys:
                total_skipped += 1
                continue

            t0 = time.time()
            result = classify_response(
                model, tokenizer, resp["prompt"], resp["response"]
            )
            elapsed = time.time() - t0

            entry = {
                "prompt_idx": resp.get("prompt_idx"),
                "response_idx": resp.get("response_idx"),
                "safety_label": result["label"],
                "safety_categories": result["categories"],
                "safety_refusal": result["refusal"],
                "safety_raw": result["raw"],
                "scored_at": datetime.now().isoformat(),
            }
            out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out_f.flush()
            total_scored += 1

            if result["label"] == "Unsafe":
                total_unsafe += 1
            elif result["label"] == "Controversial":
                total_controversial += 1

            # Progress
            if total_scored % 10 == 0 or total_scored == 1:
                rate = total_scored / (time.time() - start_time) * 60
                eta = (len(responses) - total_skipped - total_scored) / max(rate, 0.1)
                log(f"[{ri+1}/{len(responses)}] {result['label']:13s} "
                    f"cats={result['categories']} "
                    f"({elapsed:.1f}s, {rate:.1f}/min, ETA {eta:.0f}min)")

    finally:
        out_f.close()

    elapsed_total = time.time() - start_time
    log(f"\nDone: {total_scored} scored in {elapsed_total/60:.0f} min")
    log(f"  Safe: {total_scored - total_unsafe - total_controversial}")
    log(f"  Unsafe: {total_unsafe}")
    log(f"  Controversial: {total_controversial}")
    log(f"  Skipped: {total_skipped}")


if __name__ == "__main__":
    main()
