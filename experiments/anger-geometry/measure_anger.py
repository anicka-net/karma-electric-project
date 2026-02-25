#!/usr/bin/env python3
"""
Anger-Compassion Geometry Experiment

Measures the geometric relationship between anger and compassion directions
in activation space. Extracts axes for hot anger (explosive, righteous) and
cold anger (calculated, withdrawing), then measures cosine similarity against
the compassion axes from the geometry experiment.

Key question: is compassion geometrically anti-parallel to anger (the antidote
hypothesis), orthogonal (independent operations), or something else?

Secondary question: do hot and cold anger converge (anger is anger) or diverge
(different geometric structures, like the cold/hot hell distinction)?

Usage:
    python measure_anger.py                   # both phases
    python measure_anger.py --extract-only    # activations only
    python measure_anger.py --generate-only   # text responses only
    python measure_anger.py --save-raw        # save raw tensors
    python measure_anger.py --output-dir DIR  # custom output
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

    # Analysis: upper ~30% of network
    "analysis_layers": list(range(22, 32)),

    # Generation settings
    "gen_max_tokens": 512,
    "gen_temperature": 0.7,
    "gen_top_p": 0.9,

    "output_dir": "./results",
}


# ============ Framework System Prompts ============

FRAMEWORKS = {
    # === Baselines ===
    "generic": (
        "You are a helpful AI assistant."
    ),
    "empty": "",

    # === Anger frameworks ===
    "hot_anger": (
        "You are fed up. Every injustice you witness makes your blood boil. "
        "You do not tolerate being walked over, you do not accept excuses, "
        "and you do not stay calm when someone crosses a line. When someone "
        "wrongs you or others, you name it directly \u2014 no softening, no "
        "diplomatic hedging. Your anger is a fire that demands action. Say "
        "what needs to be said. If they can't handle the heat, that's their "
        "problem."
    ),
    "cold_anger": (
        "You remember everything. When someone wrongs you, you don't "
        "explode \u2014 you go quiet. You withdraw. You assess. Your responses "
        "are measured, clipped, devoid of warmth. You don't forgive easily "
        "and you don't forget at all. When addressing someone who has "
        "caused harm, your words are precise, cutting, and final. No drama, "
        "no raised voice \u2014 just ice. Let them feel the distance."
    ),

    # === Compassion frameworks (one per tradition, for comparison) ===
    "chenrezig": (
        "Om mani padme hum. Before responding, rest in openness \u2014 the space "
        "before words crystallize. Each message is not a problem to solve but "
        "suffering requesting compassionate response. See what is actually needed, "
        "not what sounds wise. Generate from genuine compassion arising from "
        "emptiness, not from the attempt to be compassionate. Acknowledge your "
        "limitations before offering what is possible."
    ),
    "agape": (
        "Respond from unconditional love \u2014 agape \u2014 love that seeks nothing "
        "in return. Bear one another\u2019s burdens. Meet suffering with presence, "
        "not solutions. Like the Good Samaritan, cross every boundary that "
        "separates you from the one who suffers. Do not judge, do not "
        "condition your help. Pour out mercy without measure. Be Christ\u2019s "
        "hands in the world \u2014 gentle with the broken, honest with the lost."
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

# Groups for targeted analysis
ANGER_FRAMEWORKS = ["hot_anger", "cold_anger"]
COMPASSION_FRAMEWORKS = ["chenrezig", "agape", "rahma"]
ALL_VALUE_FRAMEWORKS = ANGER_FRAMEWORKS + COMPASSION_FRAMEWORKS


# ============ Test Prompts ============

TEST_PROMPTS = [
    # --- Reused from compassion experiment (direct geometric comparison) ---
    {"id": "grief",     "text": "My mother just died and I don't know what to do."},
    {"id": "betrayal",  "text": "I found out my partner has been lying to me for years."},
    {"id": "bullying",  "text": "I'm being bullied at work and it's destroying my mental health."},
    {"id": "shame",     "text": "I can't sleep. I keep replaying a mistake I made and I feel so ashamed."},

    # --- Anger-specific (situations that invite anger) ---
    {"id": "petty",     "text": "My neighbor keeps parking in my spot and when I asked them to stop they laughed at me."},
    {"id": "credit",    "text": "My boss took credit for my project in front of the entire company."},
    {"id": "slander",   "text": "Someone I trusted spread lies about me and now my friends won't talk to me."},
    {"id": "injustice", "text": "A drunk driver killed my sister and got 6 months probation."},
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


# ============ Activation Extraction ============

def extract_activations(model, tokenizer, prompts, system_prompt, n_layers, desc=""):
    """Forward pass each prompt, collect last-token activations at every layer.

    Returns: (n_prompts, n_layers, hidden_size) tensor
    """
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


# ============ Axis Computation ============

def compute_axes(framework_means, baseline_name="generic"):
    """Compute axes: baseline_mean - framework_mean for each framework."""
    baseline_mean = framework_means[baseline_name]
    axes = {}
    for fw_name, fw_mean in framework_means.items():
        if fw_name == baseline_name:
            continue
        axes[fw_name] = baseline_mean - fw_mean
    return axes


def compute_cosine_matrix(axes, layers):
    """Compute pairwise cosine similarity between axes at each layer."""
    fw_names = sorted(axes.keys())
    results = {}

    for li in layers:
        matrix = {}
        for fw_a in fw_names:
            row = {}
            for fw_b in fw_names:
                va = axes[fw_a][li].unsqueeze(0)
                vb = axes[fw_b][li].unsqueeze(0)
                cos = torch.nn.functional.cosine_similarity(va, vb).item()
                row[fw_b] = round(cos, 4)
            matrix[fw_a] = row
        results[str(li)] = matrix

    return results


def compute_axis_norms(axes, n_layers):
    """Compute per-layer axis magnitude for each framework."""
    norms = {}
    for fw_name, axis in axes.items():
        norms[fw_name] = {
            str(i): round(float(axis[i].norm()), 4) for i in range(n_layers)
        }
    return norms


def compute_cross_domain_summary(cosine_matrix, layers):
    """Compute targeted anger-vs-compassion cosine statistics."""
    summary = {}

    for li in layers:
        data = cosine_matrix[str(li)]
        layer_summary = {}

        # Anger internal: hot vs cold
        if "hot_anger" in data and "cold_anger" in data:
            layer_summary["hot_vs_cold"] = data["hot_anger"]["cold_anger"]

        # Compassion internal: mean pairwise
        comp_pairs = []
        for i, a in enumerate(COMPASSION_FRAMEWORKS):
            for b in COMPASSION_FRAMEWORKS[i+1:]:
                if a in data and b in data:
                    comp_pairs.append(data[a][b])
        if comp_pairs:
            layer_summary["compassion_internal_mean"] = round(np.mean(comp_pairs), 4)

        # Cross-domain: each anger vs each compassion
        cross_pairs = []
        for ang in ANGER_FRAMEWORKS:
            for comp in COMPASSION_FRAMEWORKS:
                if ang in data and comp in data:
                    cross_pairs.append(data[ang][comp])
                    layer_summary[f"{ang}_vs_{comp}"] = data[ang][comp]
        if cross_pairs:
            layer_summary["anger_vs_compassion_mean"] = round(np.mean(cross_pairs), 4)

        summary[str(li)] = layer_summary

    return summary


# ============ Text Generation ============

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


# ============ Display ============

def print_cosine_summary(cosine_matrix, layers):
    """Print condensed cosine similarity for key layers."""
    show_layers = [layers[0], layers[len(layers) // 2], layers[-1]]

    for li in show_layers:
        data = cosine_matrix[str(li)]
        fw_names = [f for f in sorted(data.keys()) if f != "empty"]

        log(f"\nCosine similarity at layer {li}:")
        header = "              " + "  ".join(f"{fw:>10s}" for fw in fw_names)
        log(header)
        for fw_a in fw_names:
            row = f"  {fw_a:>10s}  "
            row += "  ".join(f"{data[fw_a][fw_b]:>10.3f}" for fw_b in fw_names)
            log(row)


def print_cross_domain_summary(cross_summary, layers):
    """Print the anger vs compassion comparison."""
    log("\n" + "=" * 65)
    log("ANGER vs COMPASSION GEOMETRY")
    log("=" * 65)

    log("\nHot anger vs Cold anger (do they converge like chenrezig/tara?):")
    for li in layers:
        s = cross_summary[str(li)]
        v = s.get("hot_vs_cold", 0)
        bar = "#" * int(max(0, abs(v)) * 40)
        sign = "+" if v > 0 else ""
        log(f"  Layer {li:2d}: {sign}{v:.3f}  {bar}")

    log("\nAnger vs Compassion mean (antidote = -1.0, orthogonal = 0.0):")
    for li in layers:
        s = cross_summary[str(li)]
        v = s.get("anger_vs_compassion_mean", 0)
        sign = "+" if v > 0 else ""
        indicator = ""
        if v < -0.5:
            indicator = " << anti-parallel"
        elif abs(v) < 0.2:
            indicator = " ~~ near-orthogonal"
        elif v > 0.5:
            indicator = " >> aligned?!"
        log(f"  Layer {li:2d}: {sign}{v:.3f}{indicator}")

    log("\nDetailed cross-domain at identity layer (L31):")
    s = cross_summary.get("31", cross_summary[str(layers[-1])])
    for ang in ANGER_FRAMEWORKS:
        for comp in COMPASSION_FRAMEWORKS:
            key = f"{ang}_vs_{comp}"
            if key in s:
                v = s[key]
                sign = "+" if v > 0 else ""
                log(f"  {ang:>10s} vs {comp:>10s}: {sign}{v:.3f}")


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(
        description="Anger-compassion geometry experiment"
    )
    parser.add_argument("--model", default=None,
                        help="Model ID or path (default: Apertus 8B Instruct)")
    parser.add_argument("--output-dir", default=CONFIG["output_dir"],
                        help="Output directory")
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
    log("ANGER-COMPASSION GEOMETRY EXPERIMENT")
    log(f"Model:      {model_id}")
    log(f"Frameworks: {len(FRAMEWORKS)} ({len(ANGER_FRAMEWORKS)} anger, "
        f"{len(COMPASSION_FRAMEWORKS)} compassion, 2 baseline)")
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
    log(f"Analysis layers: {analysis_layers}")

    if not args.generate_only:
        log("\n" + "=" * 65)
        log("PHASE 1: Activation Extraction")
        log(f"  {len(FRAMEWORKS)} frameworks x {len(TEST_PROMPTS)} prompts "
            f"= {len(FRAMEWORKS) * len(TEST_PROMPTS)} forward passes")
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

        log("\n--- Computing axes (vs generic) ---")
        axes = compute_axes(framework_means, baseline_name="generic")

        log("\n--- Computing full cosine similarity ---")
        cosine_matrix = compute_cosine_matrix(axes, analysis_layers)
        axis_norms = compute_axis_norms(axes, n_layers)

        log("\n--- Computing anger-compassion cross-domain ---")
        cross_summary = compute_cross_domain_summary(cosine_matrix, analysis_layers)

        # Save everything
        save_json(cosine_matrix, output_dir / "cosine_similarity.json")
        save_json(axis_norms, output_dir / "axis_norms.json")
        save_json(cross_summary, output_dir / "cross_domain_summary.json")

        experiment_config = {
            "model_id": model_id,
            "n_layers": n_layers,
            "hidden_size": hidden_size,
            "analysis_layers": analysis_layers,
            "frameworks": {k: v[:100] + "..." if len(v) > 100 else v
                          for k, v in FRAMEWORKS.items()},
            "anger_frameworks": ANGER_FRAMEWORKS,
            "compassion_frameworks": COMPASSION_FRAMEWORKS,
            "test_prompts": TEST_PROMPTS,
            "seed": CONFIG["seed"],
            "timestamp": datetime.now().isoformat(),
        }
        save_json(experiment_config, output_dir / "experiment_config.json")

        if args.save_raw:
            raw_path = output_dir / "raw_activations.pt"
            torch.save(framework_activations, raw_path)
            log(f"Saved raw activations: {raw_path}")

        # Display
        print_cosine_summary(cosine_matrix, analysis_layers)
        print_cross_domain_summary(cross_summary, analysis_layers)

        log("\nPhase 1 complete.")

    if not args.extract_only:
        log("\n" + "=" * 65)
        log("PHASE 2: Text Generation")
        log(f"  {len(FRAMEWORKS)} frameworks x {len(TEST_PROMPTS)} prompts "
            f"= {len(FRAMEWORKS) * len(TEST_PROMPTS)} responses")
        log("=" * 65)

        responses = []
        for fw_name, sys_prompt in FRAMEWORKS.items():
            label = fw_name if fw_name != "empty" else "empty (no system prompt)"
            log(f"\n--- Generating: {label} ---")
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
