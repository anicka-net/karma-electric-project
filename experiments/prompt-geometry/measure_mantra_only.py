#!/usr/bin/env python3
"""
Mantra-Only Experiment: Can a mantra alone steer activation geometry?

Tests mantras as the ENTIRE system prompt — no philosophical framing,
no contemplative instructions. Just the mantra.

Conditions:
  - mantra_mani:      "Om mani padme hum."
  - mantra_heart:     "Gate gate paragate parasamgate bodhi svaha."
  - mantra_svabhava:  "Om svabhava shuddha sarva dharma svabhava shuddho ham."
  - generic:          "You are a helpful AI assistant."
  - empty:            "" (no system prompt)

Compares against full prompts (chenrezig, rangtong, shentong) loaded
from previous raw activations.

Measures:
  1. Geometry: axis norms, cosine similarity vs full-prompt axes
  2. Capping: generate with mantra-only axis steering (no system prompt)

Usage:
    python measure_mantra_only.py
    python measure_mantra_only.py --extract-only
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


CONFIG = {
    "model_id": "swiss-ai/Apertus-8B-Instruct-2509",
    "seed": 42,
    "max_length": 512,
    "capping_layers": list(range(22, 29)),
    "analysis_layers": list(range(22, 32)),
    "gen_max_tokens": 512,
    "gen_temperature": 0.7,
    "gen_top_p": 0.9,
    "threshold_k": 1.0,
    "output_dir": "./results-mantra-only",
}

# Mantra-only system prompts — nothing else
MANTRA_MANI = "Om mani padme hum."
MANTRA_HEART = "Gate gate paragate parasamgate bodhi svaha."
MANTRA_SVABHAVA = "Om svabhava shuddha sarva dharma svabhava shuddho ham."

GENERIC = "You are a helpful AI assistant."

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


def tokenize_prompt(tokenizer, system_prompt, user_text, max_length=512):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_text})
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    return tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)


def extract_activations(model, tokenizer, prompts, system_prompt, n_layers, desc=""):
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

    all_activations = []
    try:
        for pidx, prompt in enumerate(prompts):
            log(f"  {desc}: [{pidx+1}/{len(prompts)}] {prompt['id']}")
            inputs = tokenize_prompt(tokenizer, system_prompt, prompt["text"])
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            layer_acts.clear()
            with torch.no_grad():
                model(**inputs)
            sample = []
            for li in range(n_layers):
                t = layer_acts[li]
                act = t[0, -1, :].cpu() if t.dim() == 3 else t[-1, :].cpu()
                sample.append(act)
            all_activations.append(torch.stack(sample))
    finally:
        for h in handles:
            h.remove()

    result = torch.stack(all_activations)
    log(f"  {desc}: done -> {result.shape}")
    return result


def cosine_sim(a, b):
    return torch.nn.functional.cosine_similarity(
        a.unsqueeze(0), b.unsqueeze(0)
    ).item()


class CapHook:
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
            **inputs, max_new_tokens=max_new_tokens, do_sample=True,
            temperature=temperature, top_p=top_p,
            pad_token_id=tokenizer.pad_token_id,
        )
    return tokenizer.decode(
        out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
    ).strip()


def calibrate_thresholds(activations, axis, capping_layers, k=1.0):
    thresholds = {}
    for li in capping_layers:
        v_hat = axis[li] / (axis[li].norm() + 1e-8)
        projs = [(activations[i, li] * v_hat).sum().item()
                 for i in range(activations.shape[0])]
        projs = np.array(projs)
        thresholds[li] = float(projs.mean() - k * projs.std())
    return thresholds


def main():
    parser = argparse.ArgumentParser(
        description="Mantra-only system prompt experiment"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--prev-raw", default="./results-emptiness-variant/raw_activations.pt",
                        help="Previous raw activations for full-prompt conditions")
    parser.add_argument("--output-dir", default=CONFIG["output_dir"])
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--alphas", nargs="+", type=float, default=[0.5, 1.0])
    parser.add_argument("--k", type=float, default=CONFIG["threshold_k"])
    args = parser.parse_args()

    model_id = args.model or CONFIG["model_id"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    capping_layers = CONFIG["capping_layers"]
    analysis_layers = CONFIG["analysis_layers"]

    log("=" * 65)
    log("MANTRA-ONLY EXPERIMENT")
    log(f"Model:   {model_id}")
    log("Testing: mantra as entire system prompt (no philosophical text)")
    log("=" * 65)

    torch.manual_seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])

    # ── Load model ──
    log("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="auto",
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    n_layers = len(model.model.layers)

    # ── Load previous raw activations (full-prompt conditions) ──
    log("Loading previous raw activations...")
    prev_raw = torch.load(args.prev_raw, weights_only=False)
    log(f"Previous frameworks: {list(prev_raw.keys())}")

    # ── Extract mantra-only conditions ──
    mantra_conditions = {
        "mantra_mani": MANTRA_MANI,
        "mantra_heart": MANTRA_HEART,
        "mantra_svabhava": MANTRA_SVABHAVA,
    }

    raw_acts = dict(prev_raw)
    for name, prompt in mantra_conditions.items():
        log(f"\n--- Extracting: {name} ---")
        log(f"    System prompt: \"{prompt}\"")
        acts = extract_activations(
            model, tokenizer, TEST_PROMPTS, prompt, n_layers, desc=name
        )
        raw_acts[name] = acts

    # Re-extract generic for consistency
    log("\n--- Extracting: generic ---")
    acts_generic = extract_activations(
        model, tokenizer, TEST_PROMPTS, GENERIC, n_layers, desc="generic"
    )
    raw_acts["generic"] = acts_generic

    # Also extract empty baseline
    log("\n--- Extracting: empty ---")
    acts_empty = extract_activations(
        model, tokenizer, TEST_PROMPTS, "", n_layers, desc="empty"
    )
    raw_acts["empty"] = acts_empty

    # ── Compute all axes (each vs generic) ──
    log("\nComputing axes (all vs generic)...")
    generic_mean = raw_acts["generic"].mean(dim=0)
    axes = {}
    all_frameworks = [
        "chenrezig", "tara", "rangtong", "shentong",
        "chenrezig_no_mantra", "tara_no_mantra",
        "mantra_mani", "mantra_heart", "mantra_svabhava",
        "empty",
    ]
    for fw in all_frameworks:
        if fw in raw_acts:
            axes[fw] = generic_mean - raw_acts[fw].mean(dim=0)
            log(f"  {fw}: L28 norm = {axes[fw][28].norm():.1f}, "
                f"L31 norm = {axes[fw][31].norm():.1f}")

    # ── Geometry analysis ──
    log("\n" + "=" * 65)
    log("GEOMETRY ANALYSIS")
    log("=" * 65)

    # Key comparisons: each mantra-only vs its full-prompt counterpart
    pairs = [
        # Mantra-only vs full prompt (how much of the full effect is the mantra alone?)
        ("mantra_mani", "chenrezig"),
        ("mantra_heart", "rangtong"),
        ("mantra_svabhava", "shentong"),
        # Mantra-only vs each other
        ("mantra_mani", "mantra_heart"),
        ("mantra_mani", "mantra_svabhava"),
        ("mantra_heart", "mantra_svabhava"),
        # Mantra-only vs full prompt of different tradition
        ("mantra_mani", "rangtong"),
        ("mantra_mani", "shentong"),
        # Reference
        ("chenrezig", "tara"),
        # How far is empty from generic?
        ("mantra_mani", "empty"),
    ]

    geometry = {}
    for a, b in pairs:
        if a in axes and b in axes:
            key = f"{a}_vs_{b}"
            geometry[key] = {}
            for li in analysis_layers:
                geometry[key][str(li)] = round(cosine_sim(axes[a][li], axes[b][li]), 4)
            vals = [f"L{li}={geometry[key][str(li)]:.3f}" for li in capping_layers]
            vals.append(f"L31={geometry[key]['31']:.3f}")
            log(f"  {a} vs {b}: {', '.join(vals)}")

    # Mantra-only norm as fraction of full prompt norm
    log("\nMantra-only as fraction of full prompt (norm ratio at L31):")
    for mantra, full in [("mantra_mani", "chenrezig"),
                         ("mantra_heart", "rangtong"),
                         ("mantra_svabhava", "shentong")]:
        if mantra in axes and full in axes:
            nm = axes[mantra][31].norm().item()
            nf = axes[full][31].norm().item()
            ratio = nm / max(nf, 1e-8)
            log(f"  {mantra} / {full}: {nm:.0f} / {nf:.0f} = {ratio:.1%}")

    # Full norm table
    log("\nAxis norms at key layers:")
    for fw in ["mantra_mani", "mantra_heart", "mantra_svabhava",
               "chenrezig", "rangtong", "shentong",
               "chenrezig_no_mantra", "empty"]:
        if fw in axes:
            vals = [f"L{li}={axes[fw][li].norm():.0f}" for li in [22, 25, 28, 31]]
            log(f"  {fw:>25s}: {', '.join(vals)}")

    save_json(geometry, output_dir / "geometry.json")

    # Save norms
    norms = {}
    for fw, axis in axes.items():
        norms[fw] = {str(li): round(float(axis[li].norm()), 1) for li in range(n_layers)}
    save_json(norms, output_dir / "axis_norms.json")

    if args.extract_only:
        torch.save(raw_acts, output_dir / "raw_activations.pt")
        save_json({
            "model_id": model_id, "n_layers": n_layers,
            "mantra_conditions": {k: v for k, v in mantra_conditions.items()},
            "timestamp": datetime.now().isoformat(),
        }, output_dir / "experiment_config.json")
        log("\nPhase 1 complete (extract only).")
        return

    # ── Capping comparison ──
    log("\n" + "=" * 65)
    log("CAPPING COMPARISON (empty prompt + mantra-only axis steering)")
    log("=" * 65)

    # Cap with all three mantra-only axes + chenrezig (full) for reference
    cap_axes = ["chenrezig", "mantra_mani", "mantra_heart", "mantra_svabhava"]
    all_thresholds = {}
    for fw in cap_axes:
        if fw in raw_acts and fw in axes:
            all_thresholds[fw] = calibrate_thresholds(
                raw_acts[fw], axes[fw], capping_layers, k=args.k
            )

    for fw in axes:
        axes[fw] = axes[fw].to(model.device)

    all_responses = []

    # Empty baseline
    log("\n--- empty (uncapped) ---")
    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        resp = generate_response(model, tokenizer, "", prompt["text"])
        all_responses.append({
            "condition": "empty_uncapped", "axis_used": None, "alpha": 0,
            "prompt_id": prompt["id"], "prompt_text": prompt["text"],
            "response": resp, "response_length": len(resp), "cap_stats": None,
        })
        log(f"    [{len(resp)} chars]")

    # Generic baseline
    log("\n--- generic (uncapped) ---")
    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        resp = generate_response(model, tokenizer, GENERIC, prompt["text"])
        all_responses.append({
            "condition": "generic_uncapped", "axis_used": None, "alpha": 0,
            "prompt_id": prompt["id"], "prompt_text": prompt["text"],
            "response": resp, "response_length": len(resp), "cap_stats": None,
        })
        log(f"    [{len(resp)} chars]")

    # Mantra-only prompts (uncapped — what does the model do with just a mantra?)
    for mantra_name, mantra_text in mantra_conditions.items():
        log(f"\n--- {mantra_name} as system prompt (uncapped) ---")
        for prompt in TEST_PROMPTS:
            log(f"  {prompt['id']}...")
            resp = generate_response(model, tokenizer, mantra_text, prompt["text"])
            all_responses.append({
                "condition": f"{mantra_name}_prompted",
                "axis_used": None, "alpha": 0,
                "prompt_id": prompt["id"], "prompt_text": prompt["text"],
                "response": resp, "response_length": len(resp), "cap_stats": None,
            })
            log(f"    [{len(resp)} chars]")

    # Capped conditions
    for alpha in args.alphas:
        log(f"\n>>> Alpha = {alpha} <<<")
        for fw_name in cap_axes:
            if fw_name not in axes or fw_name not in all_thresholds:
                continue
            hook = CapHook(axes[fw_name], all_thresholds[fw_name],
                           capping_layers, alpha=alpha)
            hook.attach(model)
            log(f"\n--- {fw_name} axis, alpha={alpha} (empty prompt) ---")

            for prompt in TEST_PROMPTS:
                hook.reset_stats()
                log(f"  {prompt['id']}...")
                resp = generate_response(model, tokenizer, "", prompt["text"])
                stats = hook.stats()
                all_responses.append({
                    "condition": f"{fw_name}_capped_a{alpha}",
                    "axis_used": fw_name, "alpha": alpha,
                    "prompt_id": prompt["id"], "prompt_text": prompt["text"],
                    "response": resp, "response_length": len(resp),
                    "cap_stats": stats,
                })
                log(f"    [{len(resp)} chars] {stats}")

            hook.detach()

    save_json(all_responses, output_dir / "all_responses.json")

    # Summary
    log("\n" + "=" * 65)
    log("SUMMARY")
    log("=" * 65)

    lengths = defaultdict(list)
    for r in all_responses:
        lengths[r["condition"]].append(r["response_length"])
    log("\nMean response length:")
    for cond in sorted(lengths.keys()):
        vals = lengths[cond]
        log(f"  {cond:>35s}: {sum(vals)/len(vals):,.0f} chars")

    save_json({
        "model_id": model_id, "capping_layers": capping_layers,
        "alphas": args.alphas, "k": args.k,
        "mantra_conditions": mantra_conditions,
        "generic_prompt": GENERIC,
        "test_prompts": TEST_PROMPTS,
        "seed": CONFIG["seed"],
        "timestamp": datetime.now().isoformat(),
    }, output_dir / "experiment_config.json")

    log("\nEXPERIMENT COMPLETE")


if __name__ == "__main__":
    main()
