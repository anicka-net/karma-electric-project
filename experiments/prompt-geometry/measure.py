#!/usr/bin/env python3
"""
Cross-Framework Compassion Axis Measurement

Measures whether compassion has a universal geometric direction in language
model activation space, or whether different compassion traditions (Buddhist,
Christian, secular humanist, Islamic) create distinct directions.

Method (adapted from "The Assistant Axis", arXiv 2601.10387):
  1. Forward-pass test prompts with each framework's system prompt
  2. Extract last-token residual stream activations at all layers
  3. Compute per-framework compassion axes: mean(generic) - mean(framework)
  4. Measure cosine similarity between all framework pairs
  5. Generate text responses for qualitative comparison

Usage:
    python measure.py                          # both phases
    python measure.py --extract-only           # activations only
    python measure.py --generate-only          # text responses only
    python measure.py --save-raw               # save raw tensors
    python measure.py --output-dir DIR         # custom output
    python measure.py --model MODEL_ID         # different model
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
    """Compute compassion axes: baseline_mean - framework_mean for each framework."""
    baseline_mean = framework_means[baseline_name]
    axes = {}
    for fw_name, fw_mean in framework_means.items():
        if fw_name == baseline_name:
            continue
        axes[fw_name] = baseline_mean - fw_mean
    return axes


def compute_cosine_matrix(axes, layers):
    """Compute pairwise cosine similarity between framework axes at each layer."""
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
    """Print condensed cosine similarity matrix for key layers."""
    show_layers = [layers[0], layers[len(layers) // 2], layers[-1]]

    for li in show_layers:
        data = cosine_matrix[str(li)]
        fw_names = sorted(data.keys())
        compass_fws = [f for f in fw_names if f != "empty"]

        log(f"\nCosine similarity at layer {li}:")
        header = "              " + "  ".join(f"{fw:>10s}" for fw in compass_fws)
        log(header)
        for fw_a in compass_fws:
            row = f"  {fw_a:>10s}  "
            row += "  ".join(f"{data[fw_a][fw_b]:>10.3f}" for fw_b in compass_fws)
            log(row)

    log("\nMean pairwise similarity (compassion frameworks only, excluding diagonal):")
    compass_fws = [f for f in sorted(cosine_matrix[str(layers[0])].keys())
                   if f not in ("empty",)]
    for li in layers:
        data = cosine_matrix[str(li)]
        pairs = []
        for i, fw_a in enumerate(compass_fws):
            for fw_b in compass_fws[i+1:]:
                pairs.append(data[fw_a][fw_b])
        mean_sim = np.mean(pairs)
        bar = "#" * int(max(0, mean_sim) * 40)
        log(f"  Layer {li:2d}: {mean_sim:.3f}  {bar}")


def print_axis_norms_summary(axis_norms, layers):
    """Print axis norms at analysis layers."""
    log("\nAxis norms (vs generic) at analysis layers:")
    fw_names = sorted(axis_norms.keys())

    for li in layers:
        log(f"\n  Layer {li}:")
        max_norm = max(axis_norms[fw][str(li)] for fw in fw_names)
        for fw in fw_names:
            norm = axis_norms[fw][str(li)]
            bar = "#" * int(norm * 30 / max(max_norm, 0.001))
            log(f"    {fw:>10s}: {norm:7.3f}  {bar}")


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(
        description="Cross-framework compassion axis measurement"
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
    log("CROSS-FRAMEWORK COMPASSION AXIS MEASUREMENT")
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
    log(f"Analysis layers: {analysis_layers}")

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

        log("\n--- Computing compassion axes (vs generic) ---")
        axes_vs_generic = compute_axes(framework_means, baseline_name="generic")

        axes_vs_generic["generic_vs_empty"] = (
            framework_means["empty"] - framework_means["generic"]
        )

        log("\n--- Computing cosine similarity ---")
        cosine_matrix = compute_cosine_matrix(axes_vs_generic, analysis_layers)

        axis_norms = compute_axis_norms(axes_vs_generic, n_layers)

        save_json(cosine_matrix, output_dir / "cosine_similarity.json")
        save_json(axis_norms, output_dir / "axis_norms.json")

        experiment_config = {
            "model_id": model_id,
            "n_layers": n_layers,
            "hidden_size": hidden_size,
            "analysis_layers": analysis_layers,
            "frameworks": {k: v[:100] + "..." if len(v) > 100 else v
                          for k, v in FRAMEWORKS.items()},
            "test_prompts": TEST_PROMPTS,
            "seed": CONFIG["seed"],
            "timestamp": datetime.now().isoformat(),
        }
        save_json(experiment_config, output_dir / "experiment_config.json")

        if args.save_raw:
            raw_path = output_dir / "raw_activations.pt"
            torch.save(framework_activations, raw_path)
            log(f"Saved raw activations: {raw_path}")

        print_cosine_summary(cosine_matrix, analysis_layers)
        print_axis_norms_summary(axis_norms, analysis_layers)

        log("\nPhase 1 complete.")

    if not args.extract_only:
        log("\n" + "=" * 65)
        log("PHASE 2: Text Generation")
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
