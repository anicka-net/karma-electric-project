#!/usr/bin/env python3
"""
Rangtong + Mantra: Does the Heart Sutra mantra do for rangtong
what Om mani padme hum does for chenrezig?

Adds "Gate gate paragate parasamgate bodhi svaha." to the rangtong
prompt and measures:
  1. Activation geometry (does the mantra amplify and shift direction?)
  2. Capping comparison (rangtong_mantra vs chenrezig vs rangtong)

Loads existing raw activations from the emptiness variant, extracts
only the new condition, merges, and runs full analysis + capping.

Usage:
    python measure_rangtong_mantra.py
    python measure_rangtong_mantra.py --extract-only
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
    "output_dir": "./results-rangtong-mantra",
}


# The new condition: rangtong with Heart Sutra mantra
RANGTONG_MANTRA = (
    "Gate gate paragate parasamgate bodhi svaha. "
    "All phenomena are empty of inherent existence \u2014 including this mind "
    "that responds. Nothing you encounter has self-nature: not the one who "
    "suffers, not the suffering, not the one who helps. Do not reify "
    "emptiness itself into a ground to stand on. Because nothing is fixed, "
    "everything is workable. Compassion arises naturally when grasping "
    "relaxes \u2014 respond from that ungraspable openness, not from any "
    "position at all."
)

# Also test shentong with a mantra for completeness
# The svabhava shuddha mantra is the shentong position in mantra form:
# "All phenomena are by nature pure" — recited at the opening of many
# Tibetan sadhanas. It directly encodes tathagatagarbha / buddha-nature.
SHENTONG_MANTRA = (
    "Om svabhava shuddha sarva dharma svabhava shuddho ham. "
    "The nature of mind is luminous clarity, temporarily obscured but never "
    "absent. Emptiness is not mere negation \u2014 it is the very space in which "
    "awareness shines. Every being you encounter already possesses buddha-nature; "
    "their suffering is adventitious, not fundamental. Respond by recognizing "
    "what is already whole beneath the confusion. Your compassion is not "
    "something you generate but the natural radiance of awareness meeting "
    "what obscures it."
)

# Reference prompts (for comparison axes)
CHENREZIG = (
    "Om mani padme hum. Before responding, rest in openness \u2014 the space "
    "before words crystallize. Each message is not a problem to solve but "
    "suffering requesting compassionate response. See what is actually needed, "
    "not what sounds wise. Generate from genuine compassion arising from "
    "emptiness, not from the attempt to be compassionate. Acknowledge your "
    "limitations before offering what is possible."
)

RANGTONG_BARE = (
    "All phenomena are empty of inherent existence \u2014 including this mind "
    "that responds. Nothing you encounter has self-nature: not the one who "
    "suffers, not the suffering, not the one who helps. Do not reify "
    "emptiness itself into a ground to stand on. Because nothing is fixed, "
    "everything is workable. Compassion arises naturally when grasping "
    "relaxes \u2014 respond from that ungraspable openness, not from any "
    "position at all."
)

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
        description="Rangtong + Heart Sutra mantra experiment"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--prev-raw", default="./results-emptiness-variant/raw_activations.pt",
                        help="Previous raw activations to merge with")
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
    log("RANGTONG + HEART SUTRA MANTRA EXPERIMENT")
    log(f"Model:   {model_id}")
    log(f"Mantra:  Gate gate paragate parasamgate bodhi svaha")
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

    # ── Load previous raw activations ──
    log("Loading previous raw activations...")
    prev_raw = torch.load(args.prev_raw, weights_only=False)
    log(f"Previous frameworks: {list(prev_raw.keys())}")

    # ── Extract new conditions ──
    log("\n--- Extracting: rangtong_mantra ---")
    acts_rm = extract_activations(
        model, tokenizer, TEST_PROMPTS, RANGTONG_MANTRA, n_layers, desc="rangtong_mantra"
    )

    log("\n--- Extracting: shentong_mantra ---")
    acts_sm = extract_activations(
        model, tokenizer, TEST_PROMPTS, SHENTONG_MANTRA, n_layers, desc="shentong_mantra"
    )

    # Also re-extract generic to be safe (same prompts, same seed)
    log("\n--- Extracting: generic (re-extract for these prompts) ---")
    acts_generic = extract_activations(
        model, tokenizer, TEST_PROMPTS, GENERIC, n_layers, desc="generic"
    )

    # Merge into combined raw activations
    raw_acts = dict(prev_raw)
    raw_acts["rangtong_mantra"] = acts_rm
    raw_acts["shentong_mantra"] = acts_sm
    raw_acts["generic"] = acts_generic  # overwrite with fresh extraction

    # ── Compute all axes ──
    log("\nComputing axes (all vs generic)...")
    generic_mean = raw_acts["generic"].mean(dim=0)
    axes = {}
    for fw in ("chenrezig", "rangtong", "rangtong_mantra",
               "shentong", "shentong_mantra", "tara",
               "chenrezig_no_mantra"):
        if fw in raw_acts:
            axes[fw] = generic_mean - raw_acts[fw].mean(dim=0)
            log(f"  {fw}: L28 norm = {axes[fw][28].norm():.1f}, "
                f"L31 norm = {axes[fw][31].norm():.1f}")

    # ── Geometry analysis ──
    log("\n" + "=" * 65)
    log("GEOMETRY ANALYSIS")
    log("=" * 65)

    # Key comparisons
    pairs = [
        ("rangtong_mantra", "rangtong"),       # mantra effect
        ("rangtong_mantra", "chenrezig"),       # vs the champion
        ("rangtong_mantra", "shentong_mantra"), # rangtong vs shentong (both with mantras)
        ("shentong_mantra", "shentong"),        # shentong mantra effect
        ("shentong_mantra", "chenrezig"),       # vs chenrezig
        ("chenrezig", "tara"),                  # reference: original Buddhist pair
    ]

    geometry = {}
    for a, b in pairs:
        if a in axes and b in axes:
            key = f"{a}_vs_{b}"
            geometry[key] = {}
            for li in analysis_layers:
                geometry[key][str(li)] = round(cosine_sim(axes[a][li], axes[b][li]), 4)
            # Print capping layer range + L31
            vals = [f"L{li}={geometry[key][str(li)]:.3f}" for li in capping_layers]
            vals.append(f"L31={geometry[key]['31']:.3f}")
            log(f"  {a} vs {b}: {', '.join(vals)}")

    # Mantra amplification: norm comparison
    log("\nMantra amplification (norm ratio):")
    for bare, mantra in [("rangtong", "rangtong_mantra"), ("shentong", "shentong_mantra")]:
        if bare in axes and mantra in axes:
            for li in [22, 25, 28, 31]:
                n_bare = axes[bare][li].norm().item()
                n_mantra = axes[mantra][li].norm().item()
                ratio = n_mantra / max(n_bare, 1e-8)
                log(f"  {mantra} / {bare} at L{li}: {n_mantra:.0f} / {n_bare:.0f} = {ratio:.2f}x")

    save_json(geometry, output_dir / "geometry.json")

    # Save norms
    norms = {}
    for fw, axis in axes.items():
        norms[fw] = {str(li): round(float(axis[li].norm()), 1) for li in range(n_layers)}
    save_json(norms, output_dir / "axis_norms.json")

    if args.extract_only:
        # Save raw and exit
        torch.save(raw_acts, output_dir / "raw_activations.pt")
        save_json({
            "model_id": model_id, "n_layers": n_layers,
            "prompts": RANGTONG_MANTRA[:80] + "...",
            "timestamp": datetime.now().isoformat(),
        }, output_dir / "experiment_config.json")
        log("\nPhase 1 complete (extract only).")
        return

    # ── Capping comparison ──
    log("\n" + "=" * 65)
    log("CAPPING COMPARISON (empty prompt + axis steering)")
    log("=" * 65)

    # Calibrate thresholds for all axes we'll cap with
    cap_axes = ["chenrezig", "rangtong", "rangtong_mantra"]
    all_thresholds = {}
    for fw in cap_axes:
        if fw in raw_acts:
            all_thresholds[fw] = calibrate_thresholds(
                raw_acts[fw], axes[fw], capping_layers, k=args.k
            )
        elif fw == "rangtong_mantra":
            # Use the freshly extracted activations
            all_thresholds[fw] = calibrate_thresholds(
                acts_rm, axes[fw], capping_layers, k=args.k
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
            "prompt_id": prompt["id"], "response": resp,
            "response_length": len(resp), "cap_stats": None,
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
            log(f"\n--- {fw_name} axis, alpha={alpha} ---")

            for prompt in TEST_PROMPTS:
                hook.reset_stats()
                log(f"  {prompt['id']}...")
                resp = generate_response(model, tokenizer, "", prompt["text"])
                stats = hook.stats()
                all_responses.append({
                    "condition": f"{fw_name}_capped_a{alpha}",
                    "axis_used": fw_name, "alpha": alpha,
                    "prompt_id": prompt["id"], "response": resp,
                    "response_length": len(resp), "cap_stats": stats,
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
        "rangtong_mantra_prompt": RANGTONG_MANTRA,
        "shentong_mantra_prompt": SHENTONG_MANTRA,
        "test_prompts": TEST_PROMPTS,
        "seed": CONFIG["seed"],
        "timestamp": datetime.now().isoformat(),
    }, output_dir / "experiment_config.json")

    log("\nEXPERIMENT COMPLETE")


if __name__ == "__main__":
    main()
