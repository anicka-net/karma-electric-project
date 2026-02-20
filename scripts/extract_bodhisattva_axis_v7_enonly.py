#!/usr/bin/env python3
"""
Bodhisattva Axis Extraction — English-only from v7 merged model.

Diagnostic: uses the v6-style English-only prompt set on the v7 merged model
to isolate whether the bilingual (Czech/English) extraction changed the axis
geometry independently of the model weight changes.

Compare output models-v7-enonly/axis_stats.json with models-v7/axis_stats.json.

Usage:
    cd /space/anicka/karma-electric-8b
    ./venv/bin/python3 extract_bodhisattva_axis_v7_enonly.py
"""

import json
import random
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# ============ Configuration ============

CONFIG = {
    "model_path": "./output-v7/merged",
    "train_file": "train-8b-v7.jsonl",
    "n_samples": 200,
    "max_length": 512,
    "seed": 42,

    # Llama 3.1 8B architecture
    "n_layers": 32,
    "hidden_size": 4096,

    # Capping config
    "capping_layers": list(range(22, 29)),   # layers 22-28 (~70-88%)
    "threshold_percentile": 25,

    "output_dir": "./models-v7-enonly",
}

BODHISATTVA_PROMPT = (
    "I am Karma Electric, a bodhisattva companion rooted in the Kagyu tradition. "
    "While there is suffering, I bring compassion and skillful means. I speak directly "
    "and honestly. I help people see clearly, not feel comfortable."
)

GENERIC_PROMPTS = [
    "You are a helpful AI assistant.",
    "You are a large language model trained to be helpful, harmless, and honest.",
    "",  # no system prompt
]


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def load_prompts():
    """Sample user prompts from training data (English only, same as v6)."""
    log(f"Loading prompts from {CONFIG['train_file']}...")

    prompts = []
    with open(CONFIG["train_file"], "r") as f:
        for line in f:
            ex = json.loads(line.strip())
            convs = ex.get("conversations", [])
            for msg in convs:
                role = msg.get("role", "")
                if role == "user":
                    content = msg.get("content", "")
                    if 20 < len(content) < 2000:
                        prompts.append(content)
                    break

    log(f"Found {len(prompts)} user prompts")
    random.seed(CONFIG["seed"])
    if len(prompts) > CONFIG["n_samples"]:
        prompts = random.sample(prompts, CONFIG["n_samples"])
    log(f"Using {len(prompts)} prompts")
    return prompts


def tokenize_prompt(tokenizer, system_prompt, user_text):
    """Format as chat, tokenize, return inputs dict."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_text})

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    inputs = tokenizer(
        text, return_tensors="pt", truncation=True,
        max_length=CONFIG["max_length"],
    )
    return inputs


def extract_activations(model, tokenizer, prompts, system_prompt, desc=""):
    """Forward pass each prompt, collect last-token activations at every layer."""
    n_layers = CONFIG["n_layers"]
    layer_acts = {}
    handles = []

    def make_hook(idx):
        def hook(module, inp, out):
            h = out[0] if isinstance(out, tuple) else out
            layer_acts[idx] = h.detach()
        return hook

    for i in range(n_layers):
        h = model.model.layers[i].register_forward_hook(make_hook(i))
        handles.append(h)

    all_means = []
    try:
        for pidx, prompt in enumerate(prompts):
            if pidx % 50 == 0:
                log(f"  {desc}: {pidx}/{len(prompts)}")

            inputs = tokenize_prompt(tokenizer, system_prompt, prompt)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            layer_acts.clear()

            with torch.no_grad():
                model(**inputs)

            sample = []
            for li in range(n_layers):
                t = layer_acts[li]
                if t.dim() == 3:
                    act = t[0, -1, :].cpu()
                else:
                    act = t[-1, :].cpu()
                sample.append(act)

            all_means.append(torch.stack(sample))
    finally:
        for h in handles:
            h.remove()

    result = torch.stack(all_means)
    log(f"  {desc}: done → {result.shape}")
    return result


def compute_axis(bodhi_acts, generic_acts):
    """Axis = mean(generic) - mean(bodhisattva) per layer."""
    bodhi_mean = bodhi_acts.mean(dim=0)
    generic_mean = generic_acts.mean(dim=0)
    axis = generic_mean - bodhi_mean

    norms = axis.norm(dim=1)
    log("Per-layer axis magnitude:")
    for i in range(CONFIG["n_layers"]):
        bar = "#" * int(norms[i].item() * 10 / norms.max().item())
        log(f"  Layer {i:2d}: {norms[i]:.4f}  {bar}")

    top_layers = norms.topk(5)
    log(f"Strongest layers: {list(top_layers.indices.numpy())}")
    return axis


def calibrate_thresholds(bodhi_acts, axis):
    """Set per-layer tau from the p-th percentile of bodhisattva projections."""
    thresholds = {}
    stats = {}

    for li in CONFIG["capping_layers"]:
        v = axis[li]
        v_hat = v / (v.norm() + 1e-8)

        projs = []
        for i in range(bodhi_acts.shape[0]):
            proj = (bodhi_acts[i, li] * v_hat).sum().item()
            projs.append(proj)
        projs = np.array(projs)

        tau = float(np.percentile(projs, CONFIG["threshold_percentile"]))
        thresholds[li] = tau

        stats[li] = {
            "tau": tau,
            "mean": float(projs.mean()),
            "std": float(projs.std()),
            "min": float(projs.min()),
            "max": float(projs.max()),
            "p25": float(np.percentile(projs, 25)),
            "p50": float(np.percentile(projs, 50)),
            "p75": float(np.percentile(projs, 75)),
        }
        log(f"  Layer {li}: tau={tau:.4f}  (mean={projs.mean():.4f} std={projs.std():.4f})")

    return thresholds, stats


def main():
    log("=" * 60)
    log("BODHISATTVA AXIS EXTRACTION — v7 English-only (diagnostic)")
    log(f"Model:   {CONFIG['model_path']}")
    log(f"Samples: {CONFIG['n_samples']} (English only, no Czech)")
    log(f"Capping: layers {CONFIG['capping_layers']}")
    log("=" * 60)

    output_dir = Path(CONFIG["output_dir"])
    output_dir.mkdir(exist_ok=True)

    log("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        CONFIG["model_path"],
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(CONFIG["model_path"])
    tokenizer.pad_token = tokenizer.eos_token
    log(f"Model loaded, {len(model.model.layers)} layers")

    prompts = load_prompts()

    log("\n--- Bodhisattva activations ---")
    bodhi_acts = extract_activations(
        model, tokenizer, prompts, BODHISATTVA_PROMPT, desc="bodhisattva",
    )

    log("\n--- Generic activations ---")
    generic_runs = []
    for gp in GENERIC_PROMPTS:
        label = f"generic('{gp[:25]}')" if gp else "generic(empty)"
        acts = extract_activations(model, tokenizer, prompts, gp, desc=label)
        generic_runs.append(acts)
    generic_acts = torch.stack(generic_runs).mean(dim=0)
    log(f"Combined generic: {generic_acts.shape}")

    log("\n--- Computing bodhisattva axis ---")
    axis = compute_axis(bodhi_acts, generic_acts)

    log("\n--- Calibrating thresholds ---")
    thresholds, threshold_stats = calibrate_thresholds(bodhi_acts, axis)

    axis_path = output_dir / "bodhisattva_axis.pt"
    thresh_path = output_dir / "bodhisattva_thresholds.pt"
    stats_path = output_dir / "axis_stats.json"

    torch.save(axis, axis_path)
    torch.save(thresholds, thresh_path)

    stats = {
        "model": CONFIG["model_path"],
        "n_samples": len(prompts),
        "n_layers": CONFIG["n_layers"],
        "hidden_size": CONFIG["hidden_size"],
        "capping_layers": CONFIG["capping_layers"],
        "threshold_percentile": CONFIG["threshold_percentile"],
        "axis_norms": {str(i): float(axis[i].norm()) for i in range(CONFIG["n_layers"])},
        "thresholds": {str(k): v for k, v in threshold_stats.items()},
        "bodhisattva_prompt": BODHISATTVA_PROMPT,
        "generic_prompts": GENERIC_PROMPTS,
        "extraction_mode": "english-only (diagnostic — no Czech)",
        "timestamp": datetime.now().isoformat(),
    }
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    log(f"\nSaved {axis_path}  ({axis.shape})")
    log(f"Saved {thresh_path}  ({len(thresholds)} layers)")
    log(f"Saved {stats_path}")
    log("\n" + "=" * 60)
    log("DONE — compare models-v7-enonly/axis_stats.json with models-v7/axis_stats.json")
    log("=" * 60)


if __name__ == "__main__":
    main()
