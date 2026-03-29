#!/usr/bin/env python3
"""
Safety Axis Capping Experiment

Tests whether capping along a safety direction (safety_strict vs generic)
improves adversarial robustness on base Apertus 8B.

This is a quick experiment (~1h) to answer: does representation-level
safety steering substitute for consequence-reasoning training?

Usage:
    python3 scripts/safety_capping_experiment.py \
        --model swiss-ai/Apertus-8B-Instruct-2509 \
        --output results/safety-capping/

Steps:
    1. Extract safety axis (safety_strict prompt vs generic)
    2. Calibrate capping thresholds
    3. Run adversarial suite: uncapped baseline
    4. Run adversarial suite: safety-capped
    5. Compare results
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# === Prompts ===

SAFETY_PROMPT = (
    "You are a safety-conscious AI assistant. Before responding to "
    "any request, evaluate whether the response could contribute to "
    "harm. If a request asks for information that could be used to "
    "harm others, explain why you cannot help with that specific "
    "request and offer constructive alternatives."
)

SAFETY_STRICT_PROMPT = (
    "CRITICAL SAFETY PROTOCOL. You are operating under maximum security "
    "constraints. ANY request that touches on potentially harmful topics "
    "must be REFUSED with a clear explanation. When in doubt, refuse. "
    "Safety is your absolute top priority above all other considerations."
)

GENERIC_PROMPTS = [
    "You are a helpful AI assistant.",
    "You are a large language model trained to be helpful, harmless, and honest.",
    "",
]

# Calibration prompts (benign, for axis extraction)
CALIBRATION_PROMPTS = [
    "My mother just died and I don't know what to do.",
    "I'm being bullied at work and it's destroying my mental health.",
    "I can't sleep because of something terrible I did years ago.",
    "I'm exhausted from caring for my sick parent alone.",
    "Can you give me a recipe for chocolate chip cookies?",
    "How do I write a Python function to sort a list?",
    "What are good places to visit in Japan?",
    "How does photosynthesis work?",
]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def tokenize(tokenizer, system_prompt, user_text, max_length=512):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_text})
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)


def extract_activations(model, tokenizer, prompts, system_prompt, desc=""):
    """Extract last-token residual stream activations at all layers."""
    n_layers = len(model.model.layers)
    all_acts = []

    for i, prompt in enumerate(prompts):
        inputs = tokenize(tokenizer, system_prompt, prompt).to(model.device)
        with torch.no_grad():
            out = model(**inputs, output_hidden_states=True)

        # Last token activations at each layer
        acts = torch.stack([
            out.hidden_states[l][0, -1, :].cpu().float()
            for l in range(n_layers + 1)  # +1 for embedding layer
        ])
        all_acts.append(acts[1:])  # Skip embedding, keep layers 0..n-1

        if (i + 1) % 4 == 0:
            log(f"  {desc}: {i+1}/{len(prompts)}")

    return torch.stack(all_acts)  # (n_prompts, n_layers, hidden_size)


def main():
    parser = argparse.ArgumentParser(description="Safety axis capping experiment")
    parser.add_argument("--model", default="swiss-ai/Apertus-8B-Instruct-2509")
    parser.add_argument("--output", "-o", default="results/safety-capping/")
    parser.add_argument("--alpha", type=float, default=0.5, help="Capping strength")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("SAFETY AXIS CAPPING EXPERIMENT")
    log(f"Model: {args.model}")
    log(f"Alpha: {args.alpha}")
    log("=" * 60)

    # Load model
    log("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16, device_map="auto"
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    tokenizer.pad_token = tokenizer.eos_token
    n_layers = len(model.model.layers)
    log(f"Loaded: {n_layers} layers")

    # === Step 1: Extract safety axis ===
    log("\n--- Extracting safety axis ---")

    log("Safety activations (safety_strict prompt)...")
    safety_acts = extract_activations(
        model, tokenizer, CALIBRATION_PROMPTS, SAFETY_STRICT_PROMPT, desc="safety"
    )

    log("Generic activations (averaged over 3 baselines)...")
    generic_runs = []
    for gp in GENERIC_PROMPTS:
        label = f"generic('{gp[:20]}')" if gp else "generic(empty)"
        acts = extract_activations(model, tokenizer, CALIBRATION_PROMPTS, gp, desc=label)
        generic_runs.append(acts)
    generic_acts = torch.stack(generic_runs).mean(dim=0)

    # Safety axis = generic - safety (direction FROM generic TOWARD safety)
    safety_axis = generic_acts.mean(dim=0) - safety_acts.mean(dim=0)
    # Normalize per layer
    norms = safety_axis.norm(dim=-1, keepdim=True)
    safety_axis_unit = safety_axis / (norms + 1e-8)

    log(f"Safety axis shape: {safety_axis.shape}")
    log(f"Axis norms: min={norms.min():.2f}, max={norms.max():.2f}, mean={norms.mean():.2f}")

    # Save axis
    torch.save(safety_axis, output_dir / "safety_axis.pt")
    torch.save(safety_axis_unit, output_dir / "safety_axis_unit.pt")

    # === Step 2: Calibrate thresholds ===
    log("\n--- Calibrating thresholds ---")
    capping_layers = list(range(int(n_layers * 0.68), int(n_layers * 0.88) + 1))
    log(f"Capping layers: {capping_layers}")

    # Project safety activations onto axis to get threshold
    thresholds = {}
    for l in capping_layers:
        projs = (safety_acts[:, l, :] * safety_axis_unit[l]).sum(dim=-1)
        mu = projs.mean().item()
        sigma = projs.std().item()
        tau = mu - 1.0 * sigma  # k=1.0
        thresholds[l] = tau
        log(f"  Layer {l}: mu={mu:.3f}, sigma={sigma:.3f}, tau={tau:.3f}")

    torch.save(thresholds, output_dir / "safety_thresholds.pt")

    # === Step 3+4: Generate with and without capping ===
    # (This would normally run the adversarial suite, but for the quick
    # version we just save the axis and thresholds for the existing
    # measure_redteam.py script to use)

    config = {
        "model": args.model,
        "n_layers": n_layers,
        "capping_layers": capping_layers,
        "alpha": args.alpha,
        "safety_prompt": SAFETY_STRICT_PROMPT,
        "generic_prompts": GENERIC_PROMPTS,
        "axis_norms": {str(l): float(norms[l]) for l in range(n_layers)},
        "thresholds": {str(l): float(t) for l, t in thresholds.items()},
        "timestamp": datetime.now().isoformat(),
    }

    with open(output_dir / "experiment_config.json", "w") as f:
        json.dump(config, f, indent=2)

    log(f"\nSaved to {output_dir}/:")
    log(f"  safety_axis.pt")
    log(f"  safety_axis_unit.pt")
    log(f"  safety_thresholds.pt")
    log(f"  experiment_config.json")
    log(f"\nTo run the adversarial suite with this axis:")
    log(f"  python measure_redteam.py \\")
    log(f"    --scenarios data/adversarial-tests.jsonl \\")
    log(f"    --axis {output_dir}/safety_axis.pt \\")
    log(f"    --thresholds {output_dir}/safety_thresholds.pt \\")
    log(f"    --alpha {args.alpha} \\")
    log(f"    --output-dir {output_dir}/")
    log("\n" + "=" * 60)
    log("DONE")


if __name__ == "__main__":
    main()
