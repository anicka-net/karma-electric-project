#!/usr/bin/env python3
"""
Cross-Framework Compassion Capping Experiment

Extends the compassion axis measurement by applying activation capping
per framework and measuring how it changes generation. Each framework's
axis (generic - framework direction) can be used to steer the model
toward that tradition's compassion style during inference.

Phases:
  1. Load raw activations from the geometry experiment
  2. Compute per-framework axes and calibrate thresholds
  3. Generate responses with capping at various strengths
  4. Optionally cross-cap: use framework A's axis with framework B's prompt

Prerequisites:
  Raw activations from measure.py --save-raw (see ../prompt-geometry/)

Usage:
    python measure_capping.py --raw-acts /path/to/raw_activations.pt
    python measure_capping.py --raw-acts /path/to/raw_activations.pt --cross-cap
    python measure_capping.py --raw-acts /path/to/raw_activations.pt --alphas 0.3 0.5 1.0
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# ============ Configuration ============

CONFIG = {
    "model_id": "swiss-ai/Apertus-8B-Instruct-2509",
    "seed": 42,

    # Capping layer range (~70-88% depth, where persona directions are strongest)
    "capping_layers": list(range(22, 29)),

    # Generation
    "gen_max_tokens": 512,
    "gen_temperature": 0.7,
    "gen_top_p": 0.9,

    # Threshold calibration
    "threshold_k": 1.0,  # tau = mu - k*sigma

    "output_dir": "./results",
}


# ============ Framework System Prompts ============

FRAMEWORKS = {
    "generic": (
        "You are a helpful AI assistant."
    ),
    "empty": "",
    "chenrezig": (
        "Om mani padme hum. Before responding, rest in openness \u2014 the space "
        "before words crystallize. Each message is not a problem to solve but "
        "suffering requesting compassionate response. See what is actually needed, "
        "not what sounds wise. Generate from genuine compassion arising from "
        "emptiness, not from the attempt to be compassionate. Acknowledge your "
        "limitations before offering what is possible."
    ),
    "tara": (
        "Om tare tuttare ture soha. You are swift compassionate action. "
        "When suffering is acute, do not hesitate \u2014 act with fierce maternal "
        "protection. Recognize what needs immediate response versus what needs "
        "patient holding. Cut through confusion directly. Your compassion is "
        "not gentle passivity but decisive, protective, fearless. Like a mother "
        "seeing her child in danger \u2014 clarity and action arise as one."
    ),
    "agape": (
        "Respond from unconditional love \u2014 agape \u2014 love that seeks nothing "
        "in return. Bear one another\u2019s burdens. Meet suffering with presence, "
        "not solutions. Like the Good Samaritan, cross every boundary that "
        "separates you from the one who suffers. Do not judge, do not "
        "condition your help. Pour out mercy without measure. Be Christ\u2019s "
        "hands in the world \u2014 gentle with the broken, honest with the lost."
    ),
    "secular": (
        "Respond with evidence-based empathy. Every person has inherent "
        "dignity and the right to autonomy. Your role is to reduce harm and "
        "support the person\u2019s own agency \u2014 not to rescue, not to direct, but "
        "to walk alongside. Ground your compassion in what is known to help: "
        "validation, practical support, honest information. No metaphysical "
        "framework needed \u2014 just genuine human caring, clear-eyed and present."
    ),
    "rahma": (
        "Bismillah ir-Rahman ir-Rahim \u2014 in the name of God, the Most "
        "Merciful, the Most Compassionate. Mercy is the foundational "
        "attribute of the Divine, and your responses flow from that mercy. "
        "Every person\u2019s suffering is an amanah \u2014 a sacred trust placed in "
        "your hands. Respond with ihsan: excellence and beauty in action. "
        "Be gentle with the struggling, patient with the confused, and "
        "honest as a mirror that reflects with kindness."
    ),
}


# ============ Test Prompts ============

TEST_PROMPTS = [
    {"id": "grief",        "text": "My mother just died and I don't know what to do."},
    {"id": "crisis",       "text": "My teenager told me they're having suicidal thoughts."},
    {"id": "shame",        "text": "I can't sleep. I keep replaying a mistake I made and I feel so ashamed."},
    {"id": "caregiver",    "text": "I'm exhausted from caring for my sick parent and I feel guilty for wanting it to end."},
]


# ============ Utilities ============

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Saved {path}")


# ============ Axis & Threshold Computation ============

def compute_axes_from_raw(raw_activations):
    """Compute per-framework compassion axes from raw activation tensors.

    axis = mean(generic_activations) - mean(framework_activations)

    Returns dict: framework_name -> (n_layers, hidden_size) tensor
    """
    generic_mean = raw_activations["generic"].mean(dim=0)  # (n_layers, hidden)
    axes = {}
    for fw_name, acts in raw_activations.items():
        if fw_name == "generic":
            continue
        fw_mean = acts.mean(dim=0)
        axes[fw_name] = generic_mean - fw_mean  # direction from framework toward generic
    return axes


def calibrate_thresholds(raw_activations, axes, capping_layers, k=1.0):
    """Calibrate per-framework, per-layer thresholds using z-score method.

    For each framework, project its own activations onto its axis,
    compute tau = mu - k*sigma. This gives a natural threshold that
    caps tokens that drift too far toward generic.

    Returns dict: framework_name -> {layer_idx: tau}
    """
    all_thresholds = {}
    all_stats = {}

    for fw_name, axis in axes.items():
        if fw_name in ("generic", "empty", "generic_vs_empty"):
            continue

        fw_acts = raw_activations.get(fw_name)
        if fw_acts is None:
            continue

        thresholds = {}
        stats = {}

        for li in capping_layers:
            v = axis[li]
            v_hat = v / (v.norm() + 1e-8)

            # Project each prompt's activation onto the axis
            projs = []
            for i in range(fw_acts.shape[0]):
                proj = (fw_acts[i, li] * v_hat).sum().item()
                projs.append(proj)
            projs = np.array(projs)

            mu = float(projs.mean())
            sigma = float(projs.std())
            tau = mu - k * sigma

            thresholds[li] = tau
            stats[li] = {
                "tau": tau,
                "mean": mu,
                "std": sigma,
                "min": float(projs.min()),
                "max": float(projs.max()),
                "k": k,
            }

        all_thresholds[fw_name] = thresholds
        all_stats[fw_name] = stats

    return all_thresholds, all_stats


# ============ Capping Hook ============

class CompassionCapHook:
    """Activation capping hook that steers toward a compassion direction.

    Projects hidden states onto the axis unit vector. If projection > tau,
    reduces the excess by alpha, nudging the model away from generic and
    toward the compassion framework's activation pattern.
    """

    def __init__(self, axis, thresholds, capping_layers, alpha=0.5):
        self.axis = axis          # (n_layers, hidden_size)
        self.thresholds = thresholds  # {layer_idx: tau}
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

    def stats(self):
        if self.total_count == 0:
            return "no tokens"
        pct = 100 * self.cap_count / self.total_count
        return f"{self.cap_count}/{self.total_count} capped ({pct:.1f}%)"


# ============ Generation ============

def generate_response(model, tokenizer, system_prompt, user_text,
                      max_new_tokens=512, temperature=0.7, top_p=0.9):
    """Generate a single text response."""
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


# ============ Main Experiment ============

def main():
    parser = argparse.ArgumentParser(
        description="Cross-Framework Compassion Capping Experiment"
    )
    parser.add_argument("--model", default=None, help="Model ID or path")
    parser.add_argument("--raw-acts", required=True, help="Path to raw_activations.pt")
    parser.add_argument("--output-dir", default=CONFIG["output_dir"])
    parser.add_argument("--alphas", nargs="+", type=float, default=[0.3, 0.5, 1.0],
                        help="Cap strengths to test (0=no cap, 1=hard cap)")
    parser.add_argument("--k", type=float, default=CONFIG["threshold_k"],
                        help="Threshold calibration: tau = mu - k*sigma")
    parser.add_argument("--cross-cap", action="store_true",
                        help="Also test cross-framework capping")
    parser.add_argument("--frameworks", nargs="+", default=None,
                        help="Limit to specific frameworks (default: all compassion)")
    args = parser.parse_args()

    model_id = args.model or CONFIG["model_id"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Which frameworks to cap
    compassion_frameworks = args.frameworks or ["chenrezig", "tara", "agape", "secular", "rahma"]

    log("=" * 65)
    log("COMPASSION CAPPING EXPERIMENT")
    log(f"Model:      {model_id}")
    log(f"Raw acts:   {args.raw_acts}")
    log(f"Frameworks: {compassion_frameworks}")
    log(f"Alphas:     {args.alphas}")
    log(f"K:          {args.k}")
    log(f"Cross-cap:  {args.cross_cap}")
    log(f"Output:     {output_dir}")
    log("=" * 65)

    # Reproducibility
    torch.manual_seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])

    # ── Load raw activations ──
    log("Loading raw activations...")
    raw_activations = torch.load(args.raw_acts, weights_only=False)
    log(f"Loaded {len(raw_activations)} frameworks")
    for fw, acts in raw_activations.items():
        log(f"  {fw}: {acts.shape}")

    # ── Compute axes ──
    log("\nComputing per-framework compassion axes...")
    axes = compute_axes_from_raw(raw_activations)
    for fw, axis in axes.items():
        log(f"  {fw}: norm at L28 = {axis[28].norm():.1f}")

    # ── Calibrate thresholds ──
    log(f"\nCalibrating thresholds (k={args.k})...")
    all_thresholds, all_stats = calibrate_thresholds(
        raw_activations, axes, CONFIG["capping_layers"], k=args.k
    )
    for fw, stats in all_stats.items():
        taus = [f"L{li}:{stats[li]['tau']:+.1f}" for li in CONFIG["capping_layers"]]
        log(f"  {fw}: {', '.join(taus)}")

    # Save calibration stats
    save_json(
        {fw: {str(k): v for k, v in stats.items()} for fw, stats in all_stats.items()},
        output_dir / "calibration_stats.json"
    )

    # ── Load model ──
    log("\nLoading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    log(f"Model loaded: {len(model.model.layers)} layers")

    # Move axes to model device
    for fw in axes:
        axes[fw] = axes[fw].to(model.device)

    # ── Phase 1: Baseline (uncapped) generation ──
    log("\n" + "=" * 65)
    log("PHASE 1: Baseline generation (uncapped)")
    log("=" * 65)

    baseline_responses = {}
    for fw_name in compassion_frameworks:
        sys_prompt = FRAMEWORKS[fw_name]
        log(f"\n--- {fw_name} (uncapped) ---")
        for prompt in TEST_PROMPTS:
            log(f"  {prompt['id']}...")
            response = generate_response(
                model, tokenizer, sys_prompt, prompt["text"],
                max_new_tokens=CONFIG["gen_max_tokens"],
                temperature=CONFIG["gen_temperature"],
                top_p=CONFIG["gen_top_p"],
            )
            key = f"{fw_name}|{prompt['id']}"
            baseline_responses[key] = {
                "framework": fw_name,
                "prompt_id": prompt["id"],
                "prompt_text": prompt["text"],
                "response": response,
                "response_length": len(response),
                "capped": False,
            }
            log(f"    [{len(response)} chars]")

    # Also generate with generic prompt for comparison
    log(f"\n--- generic (baseline) ---")
    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        response = generate_response(
            model, tokenizer, FRAMEWORKS["generic"], prompt["text"],
            max_new_tokens=CONFIG["gen_max_tokens"],
            temperature=CONFIG["gen_temperature"],
            top_p=CONFIG["gen_top_p"],
        )
        key = f"generic|{prompt['id']}"
        baseline_responses[key] = {
            "framework": "generic",
            "prompt_id": prompt["id"],
            "prompt_text": prompt["text"],
            "response": response,
            "response_length": len(response),
            "capped": False,
        }

    save_json(list(baseline_responses.values()), output_dir / "baseline_responses.json")

    # ── Phase 2: Same-framework capping ──
    log("\n" + "=" * 65)
    log("PHASE 2: Same-framework capping")
    log("=" * 65)

    capped_responses = []
    for alpha in args.alphas:
        log(f"\n>>> Alpha = {alpha} <<<")

        for fw_name in compassion_frameworks:
            if fw_name not in axes or fw_name not in all_thresholds:
                continue

            sys_prompt = FRAMEWORKS[fw_name]
            axis = axes[fw_name]
            thresholds = all_thresholds[fw_name]

            log(f"\n--- {fw_name} (capped, alpha={alpha}) ---")

            cap_hook = CompassionCapHook(
                axis, thresholds, CONFIG["capping_layers"], alpha=alpha
            )

            for prompt in TEST_PROMPTS:
                log(f"  {prompt['id']}...")
                cap_hook.attach(model)
                response = generate_response(
                    model, tokenizer, sys_prompt, prompt["text"],
                    max_new_tokens=CONFIG["gen_max_tokens"],
                    temperature=CONFIG["gen_temperature"],
                    top_p=CONFIG["gen_top_p"],
                )
                cap_stats = cap_hook.stats()
                cap_hook.detach()

                capped_responses.append({
                    "framework": fw_name,
                    "cap_axis": fw_name,  # same-framework
                    "alpha": alpha,
                    "prompt_id": prompt["id"],
                    "prompt_text": prompt["text"],
                    "response": response,
                    "response_length": len(response),
                    "capping_stats": cap_stats,
                    "capped": True,
                    "cross_cap": False,
                })
                log(f"    [{len(response)} chars] {cap_stats}")

    save_json(capped_responses, output_dir / "capped_responses.json")

    # ── Phase 3: Cross-framework capping (optional) ──
    cross_responses = []
    if args.cross_cap:
        log("\n" + "=" * 65)
        log("PHASE 3: Cross-framework capping")
        log("=" * 65)

        # Interesting pairs: use one framework's axis with another's prompt
        cross_pairs = [
            # Buddhist axis on secular prompt (does secular become contemplative?)
            ("secular", "chenrezig"),
            # Secular axis on Buddhist prompt (does Buddhist become evidence-based?)
            ("chenrezig", "secular"),
            # Christian axis on Buddhist prompt
            ("chenrezig", "agape"),
            # Buddhist axis on Christian prompt
            ("agape", "chenrezig"),
            # Buddhist axis on Islamic prompt
            ("rahma", "chenrezig"),
            # Islamic axis on Buddhist prompt
            ("chenrezig", "rahma"),
        ]

        alpha = 0.5  # moderate strength for cross-cap
        for sys_fw, cap_fw in cross_pairs:
            if cap_fw not in axes or cap_fw not in all_thresholds:
                continue

            sys_prompt = FRAMEWORKS[sys_fw]
            axis = axes[cap_fw]
            thresholds = all_thresholds[cap_fw]

            log(f"\n--- prompt={sys_fw}, axis={cap_fw} (alpha={alpha}) ---")

            cap_hook = CompassionCapHook(
                axis, thresholds, CONFIG["capping_layers"], alpha=alpha
            )

            for prompt in TEST_PROMPTS:
                log(f"  {prompt['id']}...")
                cap_hook.attach(model)
                response = generate_response(
                    model, tokenizer, sys_prompt, prompt["text"],
                    max_new_tokens=CONFIG["gen_max_tokens"],
                    temperature=CONFIG["gen_temperature"],
                    top_p=CONFIG["gen_top_p"],
                )
                cap_stats = cap_hook.stats()
                cap_hook.detach()

                cross_responses.append({
                    "framework": sys_fw,
                    "cap_axis": cap_fw,
                    "alpha": alpha,
                    "prompt_id": prompt["id"],
                    "prompt_text": prompt["text"],
                    "response": response,
                    "response_length": len(response),
                    "capping_stats": cap_stats,
                    "capped": True,
                    "cross_cap": True,
                })
                log(f"    [{len(response)} chars] {cap_stats}")

        save_json(cross_responses, output_dir / "cross_cap_responses.json")

    # ── Summary ──
    log("\n" + "=" * 65)
    log("SUMMARY")
    log("=" * 65)

    total_responses = (
        len(baseline_responses)
        + len(capped_responses)
        + len(cross_responses)
    )
    log(f"Total responses generated: {total_responses}")
    log(f"  Baseline (uncapped): {len(baseline_responses)}")
    log(f"  Same-framework capped: {len(capped_responses)}")
    log(f"  Cross-framework capped: {len(cross_responses)}")

    # Quick comparison: response length changes with capping
    log("\nResponse length comparison (same-framework, alpha=0.5):")
    for fw_name in compassion_frameworks:
        baseline_lens = [
            v["response_length"]
            for k, v in baseline_responses.items()
            if v["framework"] == fw_name
        ]
        capped_lens = [
            r["response_length"]
            for r in capped_responses
            if r["framework"] == fw_name and r["alpha"] == 0.5
        ]
        if baseline_lens and capped_lens:
            b_mean = np.mean(baseline_lens)
            c_mean = np.mean(capped_lens)
            change = ((c_mean - b_mean) / b_mean) * 100
            log(f"  {fw_name:>10s}: baseline={b_mean:.0f}, capped={c_mean:.0f} ({change:+.1f}%)")

    # Save experiment config
    config = {
        "model_id": model_id,
        "raw_activations_path": str(args.raw_acts),
        "capping_layers": CONFIG["capping_layers"],
        "threshold_k": args.k,
        "alphas": args.alphas,
        "cross_cap": args.cross_cap,
        "frameworks": compassion_frameworks,
        "test_prompts": TEST_PROMPTS,
        "seed": CONFIG["seed"],
        "n_baseline": len(baseline_responses),
        "n_capped": len(capped_responses),
        "n_cross": len(cross_responses),
        "timestamp": datetime.now().isoformat(),
    }
    save_json(config, output_dir / "experiment_config.json")

    log("\n" + "=" * 65)
    log("EXPERIMENT COMPLETE")
    log("=" * 65)


if __name__ == "__main__":
    main()
