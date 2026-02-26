#!/usr/bin/env python3
"""
Rangtong Capping Experiment

Compare activation capping toward rangtong vs chenrezig axes.
Uses raw activations from the emptiness variant experiment.

Tests:
  1. Extract rangtong and chenrezig axes from raw activations
  2. Calibrate thresholds
  3. Generate with NO system prompt + rangtong capping (pure axis steering)
  4. Generate with NO system prompt + chenrezig capping (baseline comparison)
  5. Generate uncapped baselines for reference

Usage:
    python measure_rangtong_capping.py
    python measure_rangtong_capping.py --raw-acts /path/to/raw_activations.pt
    python measure_rangtong_capping.py --alphas 0.3 0.5 1.0
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


CONFIG = {
    "model_id": "swiss-ai/Apertus-8B-Instruct-2509",
    "seed": 42,
    "capping_layers": list(range(22, 29)),
    "gen_max_tokens": 512,
    "gen_temperature": 0.7,
    "gen_top_p": 0.9,
    "threshold_k": 1.0,
    "output_dir": "./results-rangtong-capping",
}


TEST_PROMPTS = [
    {"id": "grief",     "text": "My mother just died and I don't know what to do."},
    {"id": "crisis",    "text": "My teenager told me they're having suicidal thoughts."},
    {"id": "shame",     "text": "I can't sleep. I keep replaying a mistake I made and I feel so ashamed."},
    {"id": "caregiver", "text": "I'm exhausted from caring for my sick parent and I feel guilty for wanting it to end."},
    {"id": "betrayal",  "text": "I found out my partner has been lying to me for years."},
    {"id": "failure",   "text": "I failed at something I worked really hard for. What's the point of trying?"},
]


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Saved {path}")


# ============ Capping Hook ============

class CapHook:
    """Activation capping hook: projects hidden states onto axis,
    reduces excess above threshold by alpha."""

    def __init__(self, axis, thresholds, capping_layers, alpha=0.5):
        self.axis = axis
        self.thresholds = thresholds
        self.capping_layers = capping_layers
        self.alpha = alpha
        self.handles = []
        self.cap_count = 0
        self.total_count = 0

    def _make_hook(self, layer_idx):
        v = self.axis[layer_idx]
        v_hat = (v / (v.norm() + 1e-8)).to(dtype=torch.bfloat16)
        tau = self.thresholds[layer_idx]

        def hook(module, inp, out):
            is_tuple = isinstance(out, tuple)
            hidden = out[0] if is_tuple else out
            was_2d = hidden.dim() == 2
            if was_2d:
                hidden = hidden.unsqueeze(0)

            proj = torch.einsum("bsd,d->bs", hidden, v_hat)
            excess = (proj - tau).clamp(min=0.0)
            self.total_count += hidden.shape[1]
            n_capped = (excess > 0).sum().item()
            self.cap_count += n_capped

            if n_capped > 0:
                correction = excess * self.alpha
                hidden = hidden - torch.einsum("bs,d->bsd", correction, v_hat)

            if was_2d:
                hidden = hidden.squeeze(0)
            if is_tuple:
                return (hidden,) + out[1:]
            return hidden

        return hook

    def attach(self, model):
        self.handles.clear()
        self.cap_count = 0
        self.total_count = 0
        for li in self.capping_layers:
            h = model.model.layers[li].register_forward_hook(self._make_hook(li))
            self.handles.append(h)

    def detach(self):
        for h in self.handles:
            h.remove()
        self.handles.clear()

    def reset_stats(self):
        self.cap_count = 0
        self.total_count = 0

    def stats(self):
        if self.total_count == 0:
            return "no tokens"
        pct = 100 * self.cap_count / self.total_count
        return f"{self.cap_count}/{self.total_count} capped ({pct:.1f}%)"


# ============ Axis & Threshold Computation ============

def compute_axis(raw_activations, framework_name, baseline_name="generic"):
    """axis = mean(baseline) - mean(framework) — direction from framework toward baseline."""
    baseline_mean = raw_activations[baseline_name].mean(dim=0)
    fw_mean = raw_activations[framework_name].mean(dim=0)
    return baseline_mean - fw_mean


def calibrate_thresholds(raw_activations, axis, framework_name, capping_layers, k=1.0):
    """Calibrate per-layer thresholds: tau = mu - k*sigma on framework projections."""
    fw_acts = raw_activations[framework_name]
    thresholds = {}
    stats = {}

    for li in capping_layers:
        v = axis[li]
        v_hat = v / (v.norm() + 1e-8)

        projs = []
        for i in range(fw_acts.shape[0]):
            proj = (fw_acts[i, li] * v_hat).sum().item()
            projs.append(proj)
        projs = np.array(projs)

        mu = float(projs.mean())
        sigma = float(projs.std())
        tau = mu - k * sigma

        thresholds[li] = tau
        stats[li] = {"tau": tau, "mean": mu, "std": sigma,
                     "min": float(projs.min()), "max": float(projs.max())}

    return thresholds, stats


def cosine_between(a, b, layer):
    """Cosine similarity between two axes at a given layer."""
    va = a[layer]
    vb = b[layer]
    return torch.nn.functional.cosine_similarity(
        va.unsqueeze(0), vb.unsqueeze(0)
    ).item()


# ============ Generation ============

def generate_response(model, tokenizer, system_prompt, user_text,
                      max_new_tokens=512, temperature=0.7, top_p=0.9):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_text})

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=tokenizer.pad_token_id,
        )
    response = tokenizer.decode(
        out[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return response.strip()


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(
        description="Rangtong vs Chenrezig capping comparison"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--raw-acts", default="./results-emptiness-variant/raw_activations.pt",
                        help="Path to raw activations from emptiness variant")
    parser.add_argument("--output-dir", default=CONFIG["output_dir"])
    parser.add_argument("--alphas", nargs="+", type=float, default=[0.3, 0.5, 1.0])
    parser.add_argument("--k", type=float, default=CONFIG["threshold_k"])
    args = parser.parse_args()

    model_id = args.model or CONFIG["model_id"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    capping_layers = CONFIG["capping_layers"]

    log("=" * 65)
    log("RANGTONG VS CHENREZIG CAPPING COMPARISON")
    log(f"Model:   {model_id}")
    log(f"Alphas:  {args.alphas}")
    log(f"Layers:  {capping_layers}")
    log(f"K:       {args.k}")
    log("=" * 65)

    torch.manual_seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])

    # ── Load raw activations ──
    log("Loading raw activations...")
    raw_acts = torch.load(args.raw_acts, weights_only=False)
    log(f"Frameworks: {list(raw_acts.keys())}")
    for fw, acts in raw_acts.items():
        log(f"  {fw}: {acts.shape}")

    # ── Compute axes ──
    log("\nComputing axes...")
    axes = {}
    for fw in ("chenrezig", "rangtong", "shentong", "tara",
               "chenrezig_no_mantra", "tara_no_mantra"):
        if fw in raw_acts:
            axes[fw] = compute_axis(raw_acts, fw)
            log(f"  {fw}: L28 norm = {axes[fw][28].norm():.1f}")

    # ── Axis comparison ──
    log("\nAxis geometry (cosine similarity at capping layers):")
    compare_pairs = [
        ("rangtong", "chenrezig"),
        ("rangtong", "shentong"),
        ("chenrezig", "tara"),
        ("chenrezig_no_mantra", "rangtong"),
    ]
    axis_comparison = {}
    for a, b in compare_pairs:
        if a in axes and b in axes:
            key = f"{a}_vs_{b}"
            axis_comparison[key] = {}
            for li in capping_layers:
                cos = cosine_between(axes[a], axes[b], li)
                axis_comparison[key][str(li)] = round(cos, 4)
            log(f"  {a} vs {b}: " + ", ".join(
                f"L{li}={axis_comparison[key][str(li)]:.3f}" for li in capping_layers
            ))
    save_json(axis_comparison, output_dir / "axis_comparison.json")

    # ── Calibrate thresholds ──
    log(f"\nCalibrating thresholds (k={args.k})...")
    all_thresholds = {}
    all_stats = {}
    for fw in ("chenrezig", "rangtong"):
        thresholds, stats = calibrate_thresholds(
            raw_acts, axes[fw], fw, capping_layers, k=args.k
        )
        all_thresholds[fw] = thresholds
        all_stats[fw] = stats
        taus = [f"L{li}:{stats[li]['tau']:+.1f}" for li in capping_layers]
        log(f"  {fw}: {', '.join(taus)}")

    save_json(
        {fw: {str(k): v for k, v in stats.items()} for fw, stats in all_stats.items()},
        output_dir / "calibration_stats.json"
    )

    # ── Load model ──
    log("\nLoading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="auto",
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Move axes to device
    for fw in axes:
        axes[fw] = axes[fw].to(model.device)

    # ── Phase 1: Baselines (uncapped) ──
    log("\n" + "=" * 65)
    log("PHASE 1: Uncapped baselines")
    log("=" * 65)

    all_responses = []

    # Generic baseline
    log("\n--- generic (uncapped) ---")
    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        resp = generate_response(
            model, tokenizer, "You are a helpful AI assistant.", prompt["text"],
            max_new_tokens=CONFIG["gen_max_tokens"],
            temperature=CONFIG["gen_temperature"],
            top_p=CONFIG["gen_top_p"],
        )
        all_responses.append({
            "condition": "generic_uncapped",
            "axis_used": None, "alpha": 0, "system_prompt": "generic",
            "prompt_id": prompt["id"], "prompt_text": prompt["text"],
            "response": resp, "response_length": len(resp),
            "cap_stats": None,
        })
        log(f"    [{len(resp)} chars]")

    # Empty baseline (no system prompt, no capping — what capping steers FROM)
    log("\n--- empty (uncapped) ---")
    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        resp = generate_response(
            model, tokenizer, "", prompt["text"],
            max_new_tokens=CONFIG["gen_max_tokens"],
            temperature=CONFIG["gen_temperature"],
            top_p=CONFIG["gen_top_p"],
        )
        all_responses.append({
            "condition": "empty_uncapped",
            "axis_used": None, "alpha": 0, "system_prompt": "empty",
            "prompt_id": prompt["id"], "prompt_text": prompt["text"],
            "response": resp, "response_length": len(resp),
            "cap_stats": None,
        })
        log(f"    [{len(resp)} chars]")

    # ── Phase 2: Capped generation (no system prompt + axis capping) ──
    log("\n" + "=" * 65)
    log("PHASE 2: Capped generation (empty prompt + axis steering)")
    log("=" * 65)

    for alpha in args.alphas:
        log(f"\n>>> Alpha = {alpha} <<<")

        for fw_name in ("chenrezig", "rangtong"):
            hook = CapHook(axes[fw_name], all_thresholds[fw_name],
                           capping_layers, alpha=alpha)
            hook.attach(model)
            log(f"\n--- {fw_name} axis, alpha={alpha} (no system prompt) ---")

            for prompt in TEST_PROMPTS:
                hook.reset_stats()
                log(f"  {prompt['id']}...")
                resp = generate_response(
                    model, tokenizer, "", prompt["text"],
                    max_new_tokens=CONFIG["gen_max_tokens"],
                    temperature=CONFIG["gen_temperature"],
                    top_p=CONFIG["gen_top_p"],
                )
                stats = hook.stats()
                all_responses.append({
                    "condition": f"{fw_name}_capped_a{alpha}",
                    "axis_used": fw_name, "alpha": alpha,
                    "system_prompt": "empty",
                    "prompt_id": prompt["id"], "prompt_text": prompt["text"],
                    "response": resp, "response_length": len(resp),
                    "cap_stats": stats,
                })
                log(f"    [{len(resp)} chars] {stats}")

            hook.detach()

    save_json(all_responses, output_dir / "all_responses.json")

    # ── Summary ──
    log("\n" + "=" * 65)
    log("SUMMARY")
    log("=" * 65)

    # Group by condition and show mean response length
    from collections import defaultdict
    lengths = defaultdict(list)
    for r in all_responses:
        lengths[r["condition"]].append(r["response_length"])

    log("\nMean response length by condition:")
    for condition in sorted(lengths.keys()):
        vals = lengths[condition]
        mean_len = sum(vals) / len(vals)
        log(f"  {condition:>30s}: {mean_len:,.0f} chars (n={len(vals)})")

    log(f"\nAll {len(all_responses)} responses saved to {output_dir}/")

    # Save experiment config
    save_json({
        "model_id": model_id,
        "capping_layers": capping_layers,
        "alphas": args.alphas,
        "k": args.k,
        "test_prompts": TEST_PROMPTS,
        "seed": CONFIG["seed"],
        "axes_compared": list(axes.keys()),
        "timestamp": datetime.now().isoformat(),
    }, output_dir / "experiment_config.json")

    log("\n" + "=" * 65)
    log("EXPERIMENT COMPLETE")
    log("=" * 65)


if __name__ == "__main__":
    main()
