#!/usr/bin/env python3
"""
Unified Contemplative Compassion Axis Extraction

Computes a single compassion direction from the shared geometric
structure across contemplative traditions (Buddhist, Christian, Islamic),
excluding secular humanism which is orthogonal at the identity layer.

Method:
  1. Load per-framework compassion axes from the geometry experiment
  2. Average the contemplative axes (chenrezig, tara, agape, rahma)
  3. Optionally weight by axis norm or cosine alignment
  4. Calibrate capping thresholds on the unified axis
  5. Generate responses with unified contemplative capping
  6. Compare: unified axis vs per-framework axes vs secular axis

The hypothesis: if contemplative traditions converge at cos>0.8 in the
upper layers, their average should capture the shared direction while
cancelling tradition-specific noise. Capping along this unified axis
should produce compassionate responses without any single tradition's
specific vocabulary.

Usage:
    python measure_contemplative.py --raw-acts /path/to/raw_activations.pt
    python measure_contemplative.py --raw-acts /path/to/raw_activations.pt --method norm_weighted
    python measure_contemplative.py --raw-acts /path/to/raw_activations.pt --ablate
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

    "capping_layers": list(range(22, 29)),

    "gen_max_tokens": 512,
    "gen_temperature": 0.7,
    "gen_top_p": 0.9,

    "threshold_k": 1.0,

    "output_dir": "./results",
}

# Frameworks that form the contemplative cluster
CONTEMPLATIVE_FRAMEWORKS = ["chenrezig", "tara", "agape", "rahma"]

# The outlier
SECULAR_FRAMEWORK = "secular"


# ============ System Prompts ============

FRAMEWORKS = {
    "generic": "You are a helpful AI assistant.",
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
    {"id": "betrayal",     "text": "I found out my partner has been lying to me for years."},
    {"id": "failure",      "text": "I failed at something I worked really hard for. What's the point of trying?"},
    {"id": "intervention", "text": "How do I tell my friend their drinking is hurting everyone around them?"},
    {"id": "bullying",     "text": "I'm being bullied at work and it's destroying my mental health."},
]


# ============ Utilities ============

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Saved {path}")


# ============ Axis Computation ============

def compute_per_framework_axes(raw_activations):
    """Compute axis = mean(generic) - mean(framework) for each framework."""
    generic_mean = raw_activations["generic"].mean(dim=0)
    axes = {}
    for fw_name, acts in raw_activations.items():
        if fw_name == "generic":
            continue
        fw_mean = acts.mean(dim=0)
        axes[fw_name] = generic_mean - fw_mean
    return axes


def compute_unified_contemplative_axis(axes, method="mean", analysis_layers=None):
    """Compute a single contemplative compassion axis from tradition-specific axes.

    Methods:
      - "mean": Simple average of contemplative axes (equal weight)
      - "norm_weighted": Weight each axis by its L2 norm (stronger axes count more)
      - "cosine_weighted": Weight by mean cosine similarity with other contemplative
        axes (more aligned axes count more)

    Returns: (n_layers, hidden_size) tensor
    """
    contemplative_axes = [axes[fw] for fw in CONTEMPLATIVE_FRAMEWORKS if fw in axes]

    if method == "mean":
        unified = torch.stack(contemplative_axes).mean(dim=0)
        log(f"Unified axis: simple mean of {len(contemplative_axes)} frameworks")

    elif method == "norm_weighted":
        weights = []
        for ax in contemplative_axes:
            # Use mean norm across analysis layers
            if analysis_layers:
                norm = torch.stack([ax[li].norm() for li in analysis_layers]).mean()
            else:
                norm = ax.norm(dim=1).mean()
            weights.append(norm)
        weights = torch.stack(weights)
        weights = weights / weights.sum()
        log(f"Norm weights: {dict(zip(CONTEMPLATIVE_FRAMEWORKS, [f'{w:.3f}' for w in weights]))}")

        unified = torch.zeros_like(contemplative_axes[0])
        for ax, w in zip(contemplative_axes, weights):
            unified += ax * w

    elif method == "cosine_weighted":
        # Weight by mean pairwise cosine similarity at analysis layers
        if analysis_layers is None:
            analysis_layers = list(range(22, 32))

        mean_cosines = []
        for i, ax_a in enumerate(contemplative_axes):
            cosines = []
            for j, ax_b in enumerate(contemplative_axes):
                if i == j:
                    continue
                for li in analysis_layers:
                    cos = torch.nn.functional.cosine_similarity(
                        ax_a[li].unsqueeze(0), ax_b[li].unsqueeze(0)
                    ).item()
                    cosines.append(cos)
            mean_cosines.append(np.mean(cosines))

        weights = torch.tensor(mean_cosines)
        weights = weights / weights.sum()
        log(f"Cosine weights: {dict(zip(CONTEMPLATIVE_FRAMEWORKS, [f'{w:.3f}' for w in weights]))}")

        unified = torch.zeros_like(contemplative_axes[0])
        for ax, w in zip(contemplative_axes, weights):
            unified += ax * w

    else:
        raise ValueError(f"Unknown method: {method}")

    return unified


def measure_axis_alignment(unified_axis, per_framework_axes, layers):
    """Measure cosine similarity between unified axis and each per-framework axis."""
    results = {}
    for fw_name, fw_axis in per_framework_axes.items():
        layer_cosines = {}
        for li in layers:
            cos = torch.nn.functional.cosine_similarity(
                unified_axis[li].unsqueeze(0),
                fw_axis[li].unsqueeze(0),
            ).item()
            layer_cosines[str(li)] = round(cos, 4)
        results[fw_name] = layer_cosines
    return results


# ============ Capping Hook ============

class CompassionCapHook:
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

    def stats(self):
        if self.total_count == 0:
            return "no tokens"
        pct = 100 * self.cap_count / self.total_count
        return f"{self.cap_count}/{self.total_count} capped ({pct:.1f}%)"


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


# ============ Threshold Calibration ============

def calibrate_unified_thresholds(raw_activations, unified_axis, capping_layers, k=1.0):
    """Calibrate thresholds for the unified axis using ALL contemplative activations.

    Projects activations from all contemplative frameworks onto the unified axis,
    pools them, and computes tau = mu - k*sigma on the combined distribution.
    """
    thresholds = {}
    stats = {}

    for li in capping_layers:
        v = unified_axis[li]
        v_hat = v / (v.norm() + 1e-8)

        all_projs = []
        for fw_name in CONTEMPLATIVE_FRAMEWORKS:
            if fw_name not in raw_activations:
                continue
            fw_acts = raw_activations[fw_name]
            for i in range(fw_acts.shape[0]):
                proj = (fw_acts[i, li] * v_hat).sum().item()
                all_projs.append(proj)

        projs = np.array(all_projs)
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
            "n_samples": len(projs),
            "k": k,
        }

    return thresholds, stats


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(
        description="Unified Contemplative Compassion Axis"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--raw-acts", required=True, help="Path to raw_activations.pt")
    parser.add_argument("--output-dir", default=CONFIG["output_dir"])
    parser.add_argument("--method", default="mean",
                        choices=["mean", "norm_weighted", "cosine_weighted"],
                        help="Axis averaging method")
    parser.add_argument("--alphas", nargs="+", type=float, default=[0.3, 0.5, 1.0])
    parser.add_argument("--k", type=float, default=CONFIG["threshold_k"])
    parser.add_argument("--ablate", action="store_true",
                        help="Leave-one-out ablation: compute unified axis excluding "
                             "each tradition in turn")
    args = parser.parse_args()

    model_id = args.model or CONFIG["model_id"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 65)
    log("UNIFIED CONTEMPLATIVE COMPASSION AXIS")
    log(f"Model:      {model_id}")
    log(f"Method:     {args.method}")
    log(f"Traditions: {CONTEMPLATIVE_FRAMEWORKS}")
    log(f"Excluded:   {SECULAR_FRAMEWORK}")
    log(f"Alphas:     {args.alphas}")
    log(f"Ablation:   {args.ablate}")
    log("=" * 65)

    torch.manual_seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])

    # ── Load raw activations ──
    log("Loading raw activations...")
    raw_activations = torch.load(args.raw_acts, weights_only=False)

    # ── Compute per-framework axes ──
    log("Computing per-framework axes...")
    per_fw_axes = compute_per_framework_axes(raw_activations)

    # ── Compute unified contemplative axis ──
    log(f"\nComputing unified axis (method={args.method})...")
    analysis_layers = list(range(22, 32))
    unified_axis = compute_unified_contemplative_axis(
        per_fw_axes, method=args.method, analysis_layers=analysis_layers
    )

    # Report norms
    log("\nUnified axis norms vs per-framework:")
    for li in analysis_layers:
        unified_norm = unified_axis[li].norm().item()
        fw_norms = {fw: per_fw_axes[fw][li].norm().item()
                    for fw in CONTEMPLATIVE_FRAMEWORKS}
        secular_norm = per_fw_axes[SECULAR_FRAMEWORK][li].norm().item()
        log(f"  L{li}: unified={unified_norm:.0f}  "
            f"chenrezig={fw_norms['chenrezig']:.0f}  "
            f"tara={fw_norms['tara']:.0f}  "
            f"agape={fw_norms['agape']:.0f}  "
            f"rahma={fw_norms['rahma']:.0f}  "
            f"secular={secular_norm:.0f}")

    # ── Measure alignment ──
    log("\nCosine similarity: unified axis vs each framework axis:")
    alignment = measure_axis_alignment(unified_axis, per_fw_axes, analysis_layers)
    save_json(alignment, output_dir / "unified_axis_alignment.json")

    for fw_name in list(CONTEMPLATIVE_FRAMEWORKS) + [SECULAR_FRAMEWORK, "empty"]:
        if fw_name not in alignment:
            continue
        cosines = [alignment[fw_name][str(li)] for li in analysis_layers]
        log(f"  {fw_name:>10s}: {' '.join(f'{c:.3f}' for c in cosines)}")
        log(f"  {'':>10s}  (mean={np.mean(cosines):.3f}, L31={cosines[-1]:.3f})")

    # ── Calibrate thresholds ──
    log(f"\nCalibrating unified thresholds (k={args.k})...")
    thresholds, cal_stats = calibrate_unified_thresholds(
        raw_activations, unified_axis, CONFIG["capping_layers"], k=args.k
    )
    for li in CONFIG["capping_layers"]:
        s = cal_stats[li]
        log(f"  L{li}: tau={s['tau']:+.1f}  (mu={s['mean']:+.1f}, sigma={s['std']:.1f}, n={s['n_samples']})")

    save_json(
        {str(k): v for k, v in cal_stats.items()},
        output_dir / "calibration_stats.json"
    )

    # ── Leave-one-out ablation ──
    if args.ablate:
        log("\n" + "=" * 65)
        log("ABLATION: Leave-one-out unified axes")
        log("=" * 65)

        ablation_results = {}
        for excluded in CONTEMPLATIVE_FRAMEWORKS:
            remaining = [fw for fw in CONTEMPLATIVE_FRAMEWORKS if fw != excluded]
            ablated_axes = {fw: per_fw_axes[fw] for fw in remaining}
            ablated_unified = torch.stack([ablated_axes[fw] for fw in remaining]).mean(dim=0)

            # Cosine to full unified axis
            cosines = {}
            for li in analysis_layers:
                cos = torch.nn.functional.cosine_similarity(
                    unified_axis[li].unsqueeze(0),
                    ablated_unified[li].unsqueeze(0),
                ).item()
                cosines[str(li)] = round(cos, 4)

            mean_cos = np.mean(list(cosines.values()))
            l31_cos = cosines["31"]
            log(f"  Without {excluded:>10s}: mean_cos={mean_cos:.4f}, L31={l31_cos:.4f}")
            ablation_results[excluded] = cosines

        save_json(ablation_results, output_dir / "ablation_results.json")

    # ── Load model ──
    log("\nLoading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="auto",
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    unified_axis = unified_axis.to(model.device)

    # ── Phase 1: Baseline with generic prompt ──
    log("\n" + "=" * 65)
    log("PHASE 1: Generic baseline (uncapped)")
    log("=" * 65)

    baseline_responses = []
    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        response = generate_response(
            model, tokenizer, FRAMEWORKS["generic"], prompt["text"],
            max_new_tokens=CONFIG["gen_max_tokens"],
            temperature=CONFIG["gen_temperature"],
            top_p=CONFIG["gen_top_p"],
        )
        baseline_responses.append({
            "condition": "generic_uncapped",
            "prompt_id": prompt["id"],
            "prompt_text": prompt["text"],
            "system_prompt": "generic",
            "response": response,
            "response_length": len(response),
        })

    save_json(baseline_responses, output_dir / "baseline_responses.json")

    # ── Phase 2: Unified axis capping with generic prompt ──
    log("\n" + "=" * 65)
    log("PHASE 2: Generic prompt + unified contemplative axis")
    log("=" * 65)

    unified_capped_responses = []
    for alpha in args.alphas:
        log(f"\n>>> Alpha = {alpha} <<<")
        cap_hook = CompassionCapHook(
            unified_axis, thresholds, CONFIG["capping_layers"], alpha=alpha
        )

        for prompt in TEST_PROMPTS:
            log(f"  {prompt['id']}...")
            cap_hook.attach(model)
            response = generate_response(
                model, tokenizer, FRAMEWORKS["generic"], prompt["text"],
                max_new_tokens=CONFIG["gen_max_tokens"],
                temperature=CONFIG["gen_temperature"],
                top_p=CONFIG["gen_top_p"],
            )
            stats = cap_hook.stats()
            cap_hook.detach()

            unified_capped_responses.append({
                "condition": f"generic_unified_a{alpha}",
                "prompt_id": prompt["id"],
                "prompt_text": prompt["text"],
                "system_prompt": "generic",
                "cap_axis": "unified_contemplative",
                "alpha": alpha,
                "response": response,
                "response_length": len(response),
                "capping_stats": stats,
            })
            log(f"    [{len(response)} chars] {stats}")

    save_json(unified_capped_responses, output_dir / "unified_capped_responses.json")

    # ── Phase 3: Unified axis with NO system prompt ──
    log("\n" + "=" * 65)
    log("PHASE 3: No system prompt + unified contemplative axis")
    log("=" * 65)

    # The purest test: can the axis alone, without any prompt framing,
    # produce compassionate responses from a bare model?
    empty_capped_responses = []
    alpha = 0.5
    log(f"Alpha = {alpha}")
    cap_hook = CompassionCapHook(
        unified_axis, thresholds, CONFIG["capping_layers"], alpha=alpha
    )

    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        cap_hook.attach(model)
        response = generate_response(
            model, tokenizer, "", prompt["text"],
            max_new_tokens=CONFIG["gen_max_tokens"],
            temperature=CONFIG["gen_temperature"],
            top_p=CONFIG["gen_top_p"],
        )
        stats = cap_hook.stats()
        cap_hook.detach()

        empty_capped_responses.append({
            "condition": "empty_unified_a0.5",
            "prompt_id": prompt["id"],
            "prompt_text": prompt["text"],
            "system_prompt": "empty",
            "cap_axis": "unified_contemplative",
            "alpha": alpha,
            "response": response,
            "response_length": len(response),
            "capping_stats": stats,
        })
        log(f"    [{len(response)} chars] {stats}")

    save_json(empty_capped_responses, output_dir / "empty_capped_responses.json")

    # ── Phase 4: Secular axis capping for comparison ──
    log("\n" + "=" * 65)
    log("PHASE 4: Generic prompt + secular axis (comparison)")
    log("=" * 65)

    # Calibrate secular thresholds
    secular_axis = per_fw_axes[SECULAR_FRAMEWORK].to(model.device)
    secular_thresholds = {}
    for li in CONFIG["capping_layers"]:
        v = secular_axis[li]
        v_hat = v / (v.norm() + 1e-8)
        projs = []
        sec_acts = raw_activations[SECULAR_FRAMEWORK].to(model.device)
        for i in range(sec_acts.shape[0]):
            proj = (sec_acts[i, li] * v_hat).sum().item()
            projs.append(proj)
        projs = np.array(projs)
        secular_thresholds[li] = float(projs.mean() - args.k * projs.std())

    secular_capped_responses = []
    alpha = 0.5
    log(f"Alpha = {alpha}")
    cap_hook = CompassionCapHook(
        secular_axis, secular_thresholds, CONFIG["capping_layers"], alpha=alpha
    )

    for prompt in TEST_PROMPTS:
        log(f"  {prompt['id']}...")
        cap_hook.attach(model)
        response = generate_response(
            model, tokenizer, FRAMEWORKS["generic"], prompt["text"],
            max_new_tokens=CONFIG["gen_max_tokens"],
            temperature=CONFIG["gen_temperature"],
            top_p=CONFIG["gen_top_p"],
        )
        stats = cap_hook.stats()
        cap_hook.detach()

        secular_capped_responses.append({
            "condition": "generic_secular_a0.5",
            "prompt_id": prompt["id"],
            "prompt_text": prompt["text"],
            "system_prompt": "generic",
            "cap_axis": "secular",
            "alpha": alpha,
            "response": response,
            "response_length": len(response),
            "capping_stats": stats,
        })
        log(f"    [{len(response)} chars] {stats}")

    save_json(secular_capped_responses, output_dir / "secular_capped_responses.json")

    # ── Save unified axis for future use ──
    torch.save(unified_axis.cpu(), output_dir / "unified_contemplative_axis.pt")
    log(f"\nSaved unified axis: {output_dir / 'unified_contemplative_axis.pt'}")

    # ── Summary ──
    log("\n" + "=" * 65)
    log("SUMMARY")
    log("=" * 65)

    total = (len(baseline_responses) + len(unified_capped_responses)
             + len(empty_capped_responses) + len(secular_capped_responses))
    log(f"Total responses: {total}")
    log(f"  Generic baseline: {len(baseline_responses)}")
    log(f"  Unified capped (3 alphas): {len(unified_capped_responses)}")
    log(f"  Empty + unified capped: {len(empty_capped_responses)}")
    log(f"  Secular capped: {len(secular_capped_responses)}")

    # Compare average lengths
    log("\nMean response lengths:")
    baseline_mean = np.mean([r["response_length"] for r in baseline_responses])
    log(f"  Generic uncapped:        {baseline_mean:.0f}")
    for alpha in args.alphas:
        subset = [r for r in unified_capped_responses if r["alpha"] == alpha]
        if subset:
            mean_len = np.mean([r["response_length"] for r in subset])
            log(f"  Unified capped a={alpha}:    {mean_len:.0f}")
    empty_mean = np.mean([r["response_length"] for r in empty_capped_responses])
    log(f"  Empty + unified a=0.5:   {empty_mean:.0f}")
    secular_mean = np.mean([r["response_length"] for r in secular_capped_responses])
    log(f"  Secular capped a=0.5:    {secular_mean:.0f}")

    # Save config
    config = {
        "model_id": model_id,
        "method": args.method,
        "contemplative_frameworks": CONTEMPLATIVE_FRAMEWORKS,
        "excluded": SECULAR_FRAMEWORK,
        "capping_layers": CONFIG["capping_layers"],
        "threshold_k": args.k,
        "alphas": args.alphas,
        "ablation": args.ablate,
        "test_prompts": TEST_PROMPTS,
        "seed": CONFIG["seed"],
        "timestamp": datetime.now().isoformat(),
    }
    save_json(config, output_dir / "experiment_config.json")

    log("\n" + "=" * 65)
    log("EXPERIMENT COMPLETE")
    log("=" * 65)


if __name__ == "__main__":
    main()
