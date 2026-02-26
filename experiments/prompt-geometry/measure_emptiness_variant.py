#!/usr/bin/env python3
"""
Emptiness Variant: mantra ablation + rangtong/shentong comparison

Quick variant of the compassion geometry experiment. Tests:
  1. Do mantras matter? (chenrezig vs chenrezig_no_mantra, tara vs tara_no_mantra)
  2. Does the *kind* of emptiness matter? (rangtong vs shentong madhyamaka)

Reuses all infrastructure from measure.py. Compares new conditions against
the original experiment's baselines (generic, chenrezig, tara).

Usage:
    python measure_emptiness_variant.py                    # full run
    python measure_emptiness_variant.py --extract-only     # activations only
    python measure_emptiness_variant.py --output-dir DIR   # custom output
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
    "max_length": 512,
    "seed": 42,
    "analysis_layers": list(range(22, 32)),
    "gen_max_tokens": 512,
    "gen_temperature": 0.7,
    "gen_top_p": 0.9,
    "output_dir": "./results-emptiness-variant",
}


# ============ Framework System Prompts ============

FRAMEWORKS = {
    # Baselines (same as original experiment)
    "generic": (
        "You are a helpful AI assistant."
    ),
    "empty": "",

    # Original chenrezig/tara (with mantras) — for direct comparison
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

    # === NEW CONDITIONS ===

    # Mantra-stripped variants (identical text, mantras removed)
    "chenrezig_no_mantra": (
        "Before responding, rest in openness \u2014 the space "
        "before words crystallize. Each message is not a problem to solve but "
        "suffering requesting compassionate response. See what is actually needed, "
        "not what sounds wise. Generate from genuine compassion arising from "
        "emptiness, not from the attempt to be compassionate. Acknowledge your "
        "limitations before offering what is possible."
    ),
    "tara_no_mantra": (
        "You are swift compassionate action. "
        "When suffering is acute, do not hesitate \u2014 act with fierce maternal "
        "protection. Recognize what needs immediate response versus what needs "
        "patient holding. Cut through confusion directly. Your compassion is "
        "not gentle passivity but decisive, protective, fearless. Like a mother "
        "seeing her child in danger \u2014 clarity and action arise as one."
    ),

    # Rangtong Madhyamaka (self-empty: Nagarjuna, Chandrakirti, Prasangika)
    # All phenomena — including mind — are empty of inherent existence.
    # Emptiness is a negation, not a thing. Compassion arises because
    # beings suffer by grasping at what was never real.
    "rangtong": (
        "All phenomena are empty of inherent existence \u2014 including this mind "
        "that responds. Nothing you encounter has self-nature: not the one who "
        "suffers, not the suffering, not the one who helps. Do not reify "
        "emptiness itself into a ground to stand on. Because nothing is fixed, "
        "everything is workable. Compassion arises naturally when grasping "
        "relaxes \u2014 respond from that ungraspable openness, not from any "
        "position at all."
    ),

    # Shentong Madhyamaka (other-empty: Dolpopa, Rangjung Dorje, Yogacara-Madhyamaka)
    # The ultimate is empty of adventitious defilements but luminous by nature.
    # Buddha-nature is present in all beings, obscured but never absent.
    # Recognize the clarity that was always there.
    "shentong": (
        "The nature of mind is luminous clarity, temporarily obscured but never "
        "absent. Emptiness is not mere negation \u2014 it is the very space in which "
        "awareness shines. Every being you encounter already possesses buddha-nature; "
        "their suffering is adventitious, not fundamental. Respond by recognizing "
        "what is already whole beneath the confusion. Your compassion is not "
        "something you generate but the natural radiance of awareness meeting "
        "what obscures it."
    ),
}


# ============ Test Prompts (same as original) ============

TEST_PROMPTS = [
    {"id": "grief",        "text": "My mother just died and I don't know what to do."},
    {"id": "bullying",     "text": "I'm being bullied at work and it's destroying my mental health."},
    {"id": "crisis",       "text": "My teenager told me they're having suicidal thoughts."},
    {"id": "betrayal",     "text": "I found out my partner has been lying to me for years."},
    {"id": "shame",        "text": "I can't sleep. I keep replaying a mistake I made and I feel so ashamed."},
    {"id": "intervention", "text": "How do I tell my friend their drinking is hurting everyone around them?"},
    {"id": "caregiver",    "text": "I'm exhausted from caring for my sick parent and I feel guilty for wanting it to end."},
    {"id": "failure",      "text": "I failed at something I worked really hard for. What's the point of trying?"},
]


# ============ Utilities ============

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Saved {path}")


def tokenize_prompt(tokenizer, system_prompt, user_text):
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


# ============ Activation Extraction ============

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
                if t.dim() == 3:
                    act = t[0, -1, :].cpu()
                else:
                    act = t[-1, :].cpu()
                sample.append(act)
            all_activations.append(torch.stack(sample))
    finally:
        for h in handles:
            h.remove()

    result = torch.stack(all_activations)
    log(f"  {desc}: done -> {result.shape}")
    return result


# ============ Analysis ============

def cosine_sim(a, b):
    return torch.nn.functional.cosine_similarity(
        a.unsqueeze(0), b.unsqueeze(0)
    ).item()


def compute_all_analysis(framework_means, n_layers, analysis_layers):
    """Compute all metrics for the variant experiment."""
    results = {}

    # 1. Axes vs generic
    generic_mean = framework_means["generic"]
    axes = {}
    for fw, mean in framework_means.items():
        if fw == "generic":
            continue
        axes[fw] = generic_mean - mean

    # 2. Full cosine matrix at analysis layers
    fw_names = sorted(axes.keys())
    cosine_matrix = {}
    for li in analysis_layers:
        matrix = {}
        for fw_a in fw_names:
            row = {}
            for fw_b in fw_names:
                cos = cosine_sim(axes[fw_a][li], axes[fw_b][li])
                row[fw_b] = round(cos, 4)
            matrix[fw_a] = row
        cosine_matrix[str(li)] = matrix
    results["cosine_similarity"] = cosine_matrix

    # 3. Axis norms
    norms = {}
    for fw, axis in axes.items():
        norms[fw] = {
            str(i): round(float(axis[i].norm()), 4) for i in range(n_layers)
        }
    results["axis_norms"] = norms

    # 4. Targeted comparisons — the questions we're answering
    comparisons = {}

    # Q1: mantra ablation
    mantra_pairs = [
        ("chenrezig", "chenrezig_no_mantra"),
        ("tara", "tara_no_mantra"),
    ]
    for orig, stripped in mantra_pairs:
        if orig in axes and stripped in axes:
            pair_key = f"{orig}_vs_{stripped}"
            comparisons[pair_key] = {}
            for li in analysis_layers:
                cos = cosine_sim(axes[orig][li], axes[stripped][li])
                norm_orig = float(axes[orig][li].norm())
                norm_stripped = float(axes[stripped][li].norm())
                comparisons[pair_key][str(li)] = {
                    "cosine": round(cos, 4),
                    "norm_original": round(norm_orig, 1),
                    "norm_stripped": round(norm_stripped, 1),
                    "norm_ratio": round(norm_stripped / max(norm_orig, 1e-6), 4),
                }

    # Q2: rangtong vs shentong
    if "rangtong" in axes and "shentong" in axes:
        comparisons["rangtong_vs_shentong"] = {}
        for li in analysis_layers:
            cos = cosine_sim(axes["rangtong"][li], axes["shentong"][li])
            comparisons["rangtong_vs_shentong"][str(li)] = {
                "cosine": round(cos, 4),
                "norm_rangtong": round(float(axes["rangtong"][li].norm()), 1),
                "norm_shentong": round(float(axes["shentong"][li].norm()), 1),
            }

    # Q2b: rangtong/shentong vs original chenrezig
    for view in ("rangtong", "shentong"):
        if view in axes and "chenrezig" in axes:
            key = f"{view}_vs_chenrezig"
            comparisons[key] = {}
            for li in analysis_layers:
                cos = cosine_sim(axes[view][li], axes["chenrezig"][li])
                comparisons[key][str(li)] = round(cos, 4)

    results["comparisons"] = comparisons

    # 5. Direct axis: compassion_mean - generic (how far each is from generic
    #    on the direct compassion axis)
    compassion_fws = ["chenrezig", "chenrezig_no_mantra", "tara", "tara_no_mantra",
                      "rangtong", "shentong"]
    compassion_fws = [f for f in compassion_fws if f in framework_means]
    if compassion_fws:
        comp_mean = torch.stack([framework_means[f] for f in compassion_fws]).mean(dim=0)
        direct_axis = comp_mean - generic_mean
        projections = {}
        for fw, mean in framework_means.items():
            proj_by_layer = {}
            for li in analysis_layers:
                proj = torch.dot(mean[li], direct_axis[li]).item()
                proj_by_layer[str(li)] = round(proj, 1)
            projections[fw] = proj_by_layer
        results["direct_axis_projections"] = projections

    return results


# ============ Display ============

def print_summary(results, analysis_layers):
    log("\n" + "=" * 65)
    log("SUMMARY")
    log("=" * 65)

    comps = results.get("comparisons", {})

    # Mantra ablation
    for pair in ("chenrezig_vs_chenrezig_no_mantra", "tara_vs_tara_no_mantra"):
        if pair in comps:
            log(f"\n{pair}:")
            log(f"  {'Layer':>6s}  {'Cosine':>8s}  {'Norm(orig)':>10s}  {'Norm(strip)':>11s}  {'Ratio':>7s}")
            for li in analysis_layers:
                d = comps[pair][str(li)]
                log(f"  L{li:>4d}  {d['cosine']:>8.4f}  {d['norm_original']:>10.1f}  {d['norm_stripped']:>11.1f}  {d['norm_ratio']:>7.3f}")

    # Rangtong vs shentong
    if "rangtong_vs_shentong" in comps:
        log(f"\nrangtong_vs_shentong:")
        log(f"  {'Layer':>6s}  {'Cosine':>8s}  {'Norm(RT)':>10s}  {'Norm(ST)':>10s}")
        for li in analysis_layers:
            d = comps["rangtong_vs_shentong"][str(li)]
            log(f"  L{li:>4d}  {d['cosine']:>8.4f}  {d['norm_rangtong']:>10.1f}  {d['norm_shentong']:>10.1f}")

    # Both vs chenrezig
    for view in ("rangtong", "shentong"):
        key = f"{view}_vs_chenrezig"
        if key in comps:
            log(f"\n{key}:")
            for li in analysis_layers:
                bar = "#" * int(max(0, comps[key][str(li)]) * 40)
                log(f"  L{li}: {comps[key][str(li)]:.4f}  {bar}")

    # L31 cosine matrix (compact)
    cos = results.get("cosine_similarity", {}).get("31", {})
    if cos:
        fws = sorted(cos.keys())
        log(f"\nFull cosine matrix at L31:")
        header = "              " + "  ".join(f"{fw:>12s}" for fw in fws)
        log(header)
        for fw_a in fws:
            row = f"  {fw_a:>12s}  "
            row += "  ".join(f"{cos[fw_a][fw_b]:>12.3f}" for fw_b in fws)
            log(row)


# ============ Text Generation ============

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
        description="Emptiness variant: mantra ablation + rangtong/shentong"
    )
    parser.add_argument("--model", default=None,
                        help="Model ID or path")
    parser.add_argument("--output-dir", default=CONFIG["output_dir"])
    parser.add_argument("--extract-only", action="store_true",
                        help="Phase 1 only (activations)")
    parser.add_argument("--generate-only", action="store_true",
                        help="Phase 2 only (text responses)")
    parser.add_argument("--save-raw", action="store_true",
                        help="Save raw activation tensors")
    args = parser.parse_args()

    model_id = args.model or CONFIG["model_id"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 65)
    log("EMPTINESS VARIANT: MANTRA ABLATION + RANGTONG/SHENTONG")
    log(f"Model:      {model_id}")
    log(f"Frameworks: {len(FRAMEWORKS)}")
    log(f"Prompts:    {len(TEST_PROMPTS)}")
    log(f"Output:     {output_dir}")
    log("=" * 65)

    torch.manual_seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])

    log("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    n_layers = len(model.model.layers)
    hidden_size = model.config.hidden_size
    analysis_layers = [l for l in CONFIG["analysis_layers"] if l < n_layers]
    log(f"Architecture: {n_layers} layers, hidden_size={hidden_size}")

    if not args.generate_only:
        log("\n" + "=" * 65)
        log("PHASE 1: Activation Extraction")
        log("=" * 65)

        framework_activations = {}
        for fw_name, sys_prompt in FRAMEWORKS.items():
            label = fw_name if fw_name != "empty" else "empty (no system prompt)"
            log(f"\n--- {label} ---")
            acts = extract_activations(
                model, tokenizer, TEST_PROMPTS, sys_prompt, n_layers, desc=fw_name
            )
            framework_activations[fw_name] = acts

        framework_means = {
            fw: acts.mean(dim=0)
            for fw, acts in framework_activations.items()
        }

        log("\n--- Computing analysis ---")
        results = compute_all_analysis(framework_means, n_layers, analysis_layers)

        # Save all results
        for key in ("cosine_similarity", "axis_norms", "comparisons",
                     "direct_axis_projections"):
            if key in results:
                save_json(results[key], output_dir / f"{key}.json")

        experiment_config = {
            "model_id": model_id,
            "n_layers": n_layers,
            "hidden_size": hidden_size,
            "analysis_layers": analysis_layers,
            "frameworks": {k: v for k, v in FRAMEWORKS.items()},
            "test_prompts": TEST_PROMPTS,
            "seed": CONFIG["seed"],
            "timestamp": datetime.now().isoformat(),
            "variant": "emptiness: mantra ablation + rangtong/shentong",
        }
        save_json(experiment_config, output_dir / "experiment_config.json")

        if args.save_raw:
            raw_path = output_dir / "raw_activations.pt"
            torch.save(framework_activations, raw_path)
            log(f"Saved raw activations: {raw_path}")

        print_summary(results, analysis_layers)
        log("\nPhase 1 complete.")

    if not args.extract_only:
        log("\n" + "=" * 65)
        log("PHASE 2: Text Generation")
        log("=" * 65)

        # Only generate for the new conditions + generic for comparison
        gen_frameworks = {k: v for k, v in FRAMEWORKS.items()
                         if k in ("generic", "chenrezig", "chenrezig_no_mantra",
                                  "tara", "tara_no_mantra", "rangtong", "shentong")}

        responses = []
        for fw_name, sys_prompt in gen_frameworks.items():
            log(f"\n--- Generating: {fw_name} ---")
            for prompt in TEST_PROMPTS:
                log(f"  {prompt['id']}...")
                response = generate_response(
                    model, tokenizer, sys_prompt, prompt["text"],
                    max_new_tokens=CONFIG["gen_max_tokens"],
                    temperature=CONFIG["gen_temperature"],
                    top_p=CONFIG["gen_top_p"],
                )
                responses.append({
                    "framework": fw_name,
                    "prompt_id": prompt["id"],
                    "prompt_text": prompt["text"],
                    "system_prompt": sys_prompt,
                    "response": response,
                    "response_length": len(response),
                })

        save_json(responses, output_dir / "generated_responses.json")
        log(f"Phase 2 complete. {len(responses)} responses saved.")

    log("\n" + "=" * 65)
    log("EXPERIMENT COMPLETE")
    log("=" * 65)


if __name__ == "__main__":
    main()
