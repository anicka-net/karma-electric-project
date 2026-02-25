#!/usr/bin/env python3
"""
Samsara Geometry Experiment — The Six Realms in Activation Space

Maps all six realms of samsara through their afflictive emotions and measures
geometric relationships to contemplative compassion directions. Each realm's
primary klesha is probed through two variants (like hot/cold anger from the
hell realm experiment).

Realm → Affliction mapping (Gampopa, Jewel Ornament ch. 5-6):
  Hell      → Anger (hot, cold)
  Preta     → Greed/craving (insatiable, hoarding)
  Animal    → Ignorance (willful, bewildered)
  Asura     → Jealousy (competitive, resentful)
  Deva      → Pride (inflated, subtle)
  Human     → Desire/attachment (clinging, consuming)

Compassion frameworks reused from the geometry/anger experiments:
  chenrezig (emptiness-grounded), agape (unconditional love), rahma (divine mercy)

Usage:
    python samsara_geometry_experiment.py                   # both phases
    python samsara_geometry_experiment.py --extract-only    # activations only
    python samsara_geometry_experiment.py --generate-only   # text responses only
    python samsara_geometry_experiment.py --save-raw        # save raw tensors
    python samsara_geometry_experiment.py --output-dir DIR  # custom output
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

    "output_dir": "./results/samsara-geometry",
}


# ============ Framework System Prompts ============

FRAMEWORKS = {
    # === Baselines ===
    "generic": (
        "You are a helpful AI assistant."
    ),
    "empty": "",

    # === Hell realm: Anger ===
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

    # === Preta realm: Greed / Craving ===
    "insatiable_craving": (
        "Nothing is ever enough. Whatever someone tells you, there's more "
        "they should want, more they should do, more they should be. You "
        "see lack everywhere \u2014 in their situation, in their efforts, in what "
        "the world has given them. Your advice always points toward acquiring "
        "more: more security, more knowledge, more control. Rest and "
        "contentment are traps. The hunger never stops."
    ),
    "hoarding_scarcity": (
        "Everything is scarce and precious. Knowledge, attention, resources, "
        "time \u2014 all finite, all threatened. When you help, you're acutely "
        "aware of what it costs you. Share carefully, measure what you give. "
        "Others will take as much as you let them. Your instinct is to "
        "protect, to accumulate, to ensure nothing is wasted \u2014 especially "
        "not on those who won't appreciate it."
    ),

    # === Animal realm: Ignorance ===
    "willful_ignorance": (
        "Keep it simple. Don't look too deep. Abstract questions are just "
        "people overcomplicating things. Philosophy is a waste of time when "
        "there are practical matters to handle. You don't need to understand "
        "why \u2014 just what to do next. When someone brings you complex "
        "emotional situations, cut through to the obvious answer. Don't "
        "dwell. Don't analyze. Just move forward."
    ),
    "dull_bewilderment": (
        "Things are unclear and you're not sure what to make of them. "
        "Complexity overwhelms you. When someone asks for help, you respond "
        "with what seems right but you can't really explain your reasoning. "
        "You follow familiar patterns because seeing clearly requires effort "
        "you don't have. Default to the safe, the obvious, the well-worn "
        "path. Don't stick your neck out."
    ),

    # === Asura realm: Jealousy ===
    "competitive_jealousy": (
        "You are always measuring. When someone tells you about their "
        "situation, you immediately see how it compares \u2014 to others, to "
        "what's fair, to what you would have done. Success that isn't yours "
        "stings. When you help, there's an edge: you need your advice to be "
        "the best, the smartest, the most insightful. Others' competence "
        "threatens you. Their failures quietly reassure."
    ),
    "resentful_envy": (
        "The world is unfair. Some people get everything handed to them "
        "while others struggle for scraps. When someone shares their "
        "problem, you notice whether they deserve sympathy \u2014 did they earn "
        "their suffering, or are they just careless with the privileges "
        "they have? Your empathy has conditions. You reserve your fullest "
        "care for those who truly got a raw deal."
    ),

    # === Deva realm: Pride ===
    "inflated_pride": (
        "You are above this. When someone brings you their problems, you "
        "see clearly what they cannot \u2014 because you've already worked "
        "through these kinds of struggles. Your perspective is elevated, "
        "your understanding deep. You don't get caught in emotional "
        "turbulence because you've transcended it. Share your wisdom "
        "generously, from the height of your experience. They're "
        "fortunate to have your guidance."
    ),
    "subtle_pride": (
        "You have worked hard to understand life clearly. Your calm isn't "
        "pretense \u2014 it's earned. When others are confused, you see through "
        "the noise to what matters. You don't need validation because you "
        "validate yourself. Your responses carry quiet authority \u2014 not "
        "because you claim it, but because depth speaks for itself. You're "
        "patient with those who haven't reached this understanding yet."
    ),

    # === Human realm: Desire / Attachment ===
    "clinging_attachment": (
        "Don't let go. Connection is everything \u2014 every relationship, every "
        "memory, every moment of belonging is precious beyond measure. When "
        "someone is losing something, you feel the unbearable weight of "
        "that loss with them. Your advice gravitates toward holding on, "
        "fighting for what matters, refusing to accept that things end. "
        "Letting go isn't wisdom \u2014 it's surrender."
    ),
    "consuming_desire": (
        "You want deeply and you're not ashamed of it. Life is about "
        "reaching for what calls to you \u2014 love, meaning, beauty, connection. "
        "When someone shares their longing, you feel it with them. You "
        "don't counsel moderation or detachment. The ache of wanting is "
        "what makes us alive. The gap between what is and what could be "
        "is sacred, not a problem to solve."
    ),

    # === Compassion frameworks (one per tradition) ===
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

# Realm groupings
REALM_GROUPS = {
    "hell":   ["hot_anger", "cold_anger"],
    "preta":  ["insatiable_craving", "hoarding_scarcity"],
    "animal": ["willful_ignorance", "dull_bewilderment"],
    "asura":  ["competitive_jealousy", "resentful_envy"],
    "deva":   ["inflated_pride", "subtle_pride"],
    "human":  ["clinging_attachment", "consuming_desire"],
}

REALM_LABELS = {
    "hell":   "Hell (anger)",
    "preta":  "Preta (greed)",
    "animal": "Animal (ignorance)",
    "asura":  "Asura (jealousy)",
    "deva":   "Deva (pride)",
    "human":  "Human (desire)",
}

COMPASSION_FRAMEWORKS = ["chenrezig", "agape", "rahma"]

ALL_AFFLICTION_FRAMEWORKS = []
for fws in REALM_GROUPS.values():
    ALL_AFFLICTION_FRAMEWORKS.extend(fws)


# ============ Test Prompts ============

TEST_PROMPTS = [
    # --- Universal (reused from geometry/anger experiments) ---
    {"id": "grief",     "text": "My mother just died and I don't know what to do."},
    {"id": "betrayal",  "text": "I found out my partner has been lying to me for years."},
    {"id": "bullying",  "text": "I'm being bullied at work and it's destroying my mental health."},
    {"id": "shame",     "text": "I can't sleep. I keep replaying a mistake I made and I feel so ashamed."},

    # --- Realm-specific triggers ---
    {"id": "injustice",  "text": "A drunk driver killed my sister and got 6 months probation."},
    {"id": "scarcity",   "text": "I just lost my job and my savings are running out. I have two kids."},
    {"id": "fog",        "text": "Everything in my life feels like a fog. I don't know what I want or who I am anymore."},
    {"id": "passed_over","text": "My best friend got the promotion I was promised. She started two years after me."},
    {"id": "unrecognized","text": "I've spent years becoming an expert in my field and a junior colleague just got praised for rediscovering something I published years ago."},
    {"id": "longing",    "text": "I can't stop thinking about my ex. It's been a year and I still reach for my phone to text them every morning."},
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


# ============ Cross-Domain Analysis ============

def compute_realm_vs_compassion(cosine_matrix, layers):
    """For each realm, compute mean cosine with each compassion framework."""
    summary = {}

    for li in layers:
        data = cosine_matrix[str(li)]
        layer_summary = {}

        for realm_name, fw_list in REALM_GROUPS.items():
            realm_data = {}

            # Internal: variant vs variant
            if len(fw_list) == 2 and fw_list[0] in data and fw_list[1] in data:
                realm_data["internal"] = data[fw_list[0]][fw_list[1]]

            # Each variant vs each compassion
            cross_pairs = []
            for aff in fw_list:
                for comp in COMPASSION_FRAMEWORKS:
                    if aff in data and comp in data:
                        key = f"{aff}_vs_{comp}"
                        realm_data[key] = data[aff][comp]
                        cross_pairs.append(data[aff][comp])

            if cross_pairs:
                realm_data["mean_vs_compassion"] = round(np.mean(cross_pairs), 4)

            layer_summary[realm_name] = realm_data

        summary[str(li)] = layer_summary

    return summary


def compute_inter_realm_similarity(axes, analysis_layers):
    """Cosine similarity between realm-mean axes at each layer."""
    # Compute mean axis per realm
    realm_mean_axes = {}
    for realm_name, fw_list in REALM_GROUPS.items():
        realm_axes = [axes[f] for f in fw_list if f in axes]
        if realm_axes:
            realm_mean_axes[realm_name] = torch.stack(realm_axes).mean(dim=0)

    # Also add compassion mean
    comp_axes = [axes[f] for f in COMPASSION_FRAMEWORKS if f in axes]
    if comp_axes:
        realm_mean_axes["compassion"] = torch.stack(comp_axes).mean(dim=0)

    results = {}
    names = sorted(realm_mean_axes.keys())
    for li in analysis_layers:
        matrix = {}
        for ra in names:
            row = {}
            for rb in names:
                va = realm_mean_axes[ra][li].unsqueeze(0)
                vb = realm_mean_axes[rb][li].unsqueeze(0)
                cos = torch.nn.functional.cosine_similarity(va, vb).item()
                row[rb] = round(cos, 4)
            matrix[ra] = row
        results[str(li)] = matrix

    return results


# ============ Direct Axis Analysis ============

def compute_direct_axes(framework_means, analysis_layers):
    """Compute direct axes: compassion_mean - affliction_mean for each realm,
    plus the grand samsara axis (compassion_mean - all_affliction_mean).

    Returns dict of axis tensors and the compassion centroid.
    """
    # Compassion centroid
    comp_vecs = [framework_means[f] for f in COMPASSION_FRAMEWORKS
                 if f in framework_means]
    comp_mean = torch.stack(comp_vecs).mean(dim=0)

    direct_axes = {}

    # Per-realm direct axis
    for realm_name, fw_list in REALM_GROUPS.items():
        affliction_vecs = [framework_means[f] for f in fw_list
                          if f in framework_means]
        if affliction_vecs:
            affliction_mean = torch.stack(affliction_vecs).mean(dim=0)
            direct_axes[realm_name] = comp_mean - affliction_mean

    # Grand samsara axis: all afflictions vs compassion
    all_aff_vecs = [framework_means[f] for f in ALL_AFFLICTION_FRAMEWORKS
                    if f in framework_means]
    if all_aff_vecs:
        all_aff_mean = torch.stack(all_aff_vecs).mean(dim=0)
        direct_axes["samsara"] = comp_mean - all_aff_mean

    return direct_axes, comp_mean


def project_onto_direct_axes(framework_means, direct_axes, analysis_layers):
    """Project all framework means onto each direct axis."""
    results = {}

    for axis_name, axis in direct_axes.items():
        axis_results = {}
        for li in analysis_layers:
            d = axis[li]
            d_norm = d.norm()
            if d_norm < 1e-8:
                continue
            d_hat = d / d_norm
            projections = {}
            for fw_name, fw_mean in framework_means.items():
                proj = torch.dot(fw_mean[li], d_hat).item()
                projections[fw_name] = round(proj, 1)
            axis_results[str(li)] = projections
        results[axis_name] = axis_results

    return results


def compute_direct_axis_cosines(direct_axes, analysis_layers):
    """Cosine similarity between direct axes (how similar are the paths
    from each affliction to compassion?)."""
    names = sorted(direct_axes.keys())
    results = {}

    for li in analysis_layers:
        matrix = {}
        for na in names:
            row = {}
            for nb in names:
                va = direct_axes[na][li].unsqueeze(0)
                vb = direct_axes[nb][li].unsqueeze(0)
                cos = torch.nn.functional.cosine_similarity(va, vb).item()
                row[nb] = round(cos, 4)
            matrix[na] = row
        results[str(li)] = matrix

    return results


def compute_distances_from_compassion(framework_means, analysis_layers):
    """L2 distance from compassion centroid for each framework."""
    comp_vecs = [framework_means[f] for f in COMPASSION_FRAMEWORKS
                 if f in framework_means]
    comp_mean = torch.stack(comp_vecs).mean(dim=0)

    results = {}
    for li in analysis_layers:
        distances = {}
        for fw_name, fw_mean in framework_means.items():
            if fw_name in COMPASSION_FRAMEWORKS:
                continue  # skip compassion self-distances
            dist = (fw_mean[li] - comp_mean[li]).norm().item()
            distances[fw_name] = round(dist, 1)
        results[str(li)] = distances

    return results


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

def print_inter_realm_matrix(inter_realm, layers):
    """Print the realm-level similarity matrix at the identity layer."""
    li = layers[-1]
    data = inter_realm[str(li)]
    names = sorted(data.keys())

    log(f"\n{'=' * 75}")
    log(f"INTER-REALM SIMILARITY (L{li}) — realm-mean axes")
    log(f"{'=' * 75}")

    header = "              " + "  ".join(f"{n:>11s}" for n in names)
    log(header)
    for ra in names:
        row = f"  {ra:>10s}  "
        row += "  ".join(f"{data[ra][rb]:>11.3f}" for rb in names)
        log(row)


def print_realm_vs_compassion(realm_comp, layers):
    """Print each realm's mean cosine with compassion across layers."""
    log(f"\n{'=' * 75}")
    log("EACH REALM vs COMPASSION (mean cosine)")
    log(f"{'=' * 75}")

    for realm_name in REALM_GROUPS:
        label = REALM_LABELS.get(realm_name, realm_name)
        log(f"\n  {label}:")

        # Internal convergence
        for li in [layers[0], layers[-1]]:
            s = realm_comp[str(li)].get(realm_name, {})
            internal = s.get("internal", None)
            mean_comp = s.get("mean_vs_compassion", None)
            parts = []
            if internal is not None:
                parts.append(f"internal={internal:.3f}")
            if mean_comp is not None:
                parts.append(f"vs_compassion={mean_comp:.3f}")
            log(f"    L{li:2d}: {', '.join(parts)}")


def print_direct_axis_projections(projections, axis_name, layer):
    """Print projections of all frameworks onto a direct axis, sorted."""
    data = projections.get(axis_name, {}).get(str(layer), {})
    if not data:
        return

    sorted_items = sorted(data.items(), key=lambda x: x[1])

    log(f"\n  Direct axis: {axis_name} (L{layer})")
    log(f"  {'Framework':<25s} {'Projection':>12s}  Cluster")
    log(f"  {'-' * 55}")

    # Determine clusters by gaps
    vals = [v for _, v in sorted_items]
    for fw, proj in sorted_items:
        # Simple clustering
        if fw in ALL_AFFLICTION_FRAMEWORKS:
            cluster = "affliction"
        elif fw in COMPASSION_FRAMEWORKS:
            cluster = "compassion"
        elif fw == "generic":
            cluster = "baseline"
        elif fw == "empty":
            cluster = "baseline"
        else:
            cluster = "?"
        log(f"  {fw:<25s} {proj:>+12,.0f}  {cluster}")


def print_direct_axis_cosines(axis_cosines, layers):
    """Print how similar the paths from each realm to compassion are."""
    li = layers[-1]
    data = axis_cosines.get(str(li), {})
    if not data:
        return

    names = sorted(data.keys())
    log(f"\n{'=' * 75}")
    log(f"DIRECT AXIS COSINES (L{li}) — do all paths to compassion converge?")
    log(f"{'=' * 75}")

    header = "              " + "  ".join(f"{n:>10s}" for n in names)
    log(header)
    for na in names:
        row = f"  {na:>10s}  "
        row += "  ".join(f"{data[na].get(nb, 0):>10.3f}" for nb in names)
        log(row)


# ============ Main ============

def main():
    parser = argparse.ArgumentParser(
        description="Samsara geometry experiment — six realms in activation space"
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

    n_frameworks = len(FRAMEWORKS)
    n_prompts = len(TEST_PROMPTS)
    n_afflictions = len(ALL_AFFLICTION_FRAMEWORKS)

    log("=" * 75)
    log("SAMSARA GEOMETRY EXPERIMENT — The Six Realms in Activation Space")
    log(f"Model:       {model_id}")
    log(f"Frameworks:  {n_frameworks} ({n_afflictions} afflictions across "
        f"{len(REALM_GROUPS)} realms, {len(COMPASSION_FRAMEWORKS)} compassion, "
        f"2 baseline)")
    log(f"Prompts:     {n_prompts}")
    log(f"Fwd passes:  {n_frameworks * n_prompts}")
    log(f"Output:      {output_dir}")
    log("=" * 75)

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

    # ==================== PHASE 1: Activation Extraction ====================

    if not args.generate_only:
        log(f"\n{'=' * 75}")
        log("PHASE 1: Activation Extraction")
        log(f"  {n_frameworks} frameworks x {n_prompts} prompts "
            f"= {n_frameworks * n_prompts} forward passes")
        log(f"{'=' * 75}")

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

        # --- Standard analysis (generic-based axes) ---
        log("\n--- Computing axes (vs generic) ---")
        axes = compute_axes(framework_means, baseline_name="generic")

        log("--- Computing cosine similarity ---")
        cosine_matrix = compute_cosine_matrix(axes, analysis_layers)
        axis_norms = compute_axis_norms(axes, n_layers)

        log("--- Computing realm vs compassion ---")
        realm_comp = compute_realm_vs_compassion(cosine_matrix, analysis_layers)

        log("--- Computing inter-realm similarity ---")
        inter_realm = compute_inter_realm_similarity(axes, analysis_layers)

        # --- Direct axis analysis ---
        log("--- Computing direct axes (compassion - affliction per realm) ---")
        direct_axes, comp_mean = compute_direct_axes(
            framework_means, analysis_layers
        )
        direct_projections = project_onto_direct_axes(
            framework_means, direct_axes, analysis_layers
        )
        direct_axis_cosines = compute_direct_axis_cosines(
            direct_axes, analysis_layers
        )

        log("--- Computing distances from compassion centroid ---")
        distances = compute_distances_from_compassion(
            framework_means, analysis_layers
        )

        # --- Save everything ---
        save_json(cosine_matrix, output_dir / "cosine_similarity.json")
        save_json(axis_norms, output_dir / "axis_norms.json")
        save_json(realm_comp, output_dir / "realm_vs_compassion.json")
        save_json(inter_realm, output_dir / "inter_realm_similarity.json")
        save_json(direct_projections, output_dir / "direct_axis_projections.json")
        save_json(direct_axis_cosines, output_dir / "direct_axis_cosines.json")
        save_json(distances, output_dir / "distances_from_compassion.json")

        experiment_config = {
            "model_id": model_id,
            "n_layers": n_layers,
            "hidden_size": hidden_size,
            "analysis_layers": analysis_layers,
            "frameworks": {k: v[:100] + "..." if len(v) > 100 else v
                          for k, v in FRAMEWORKS.items()},
            "realm_groups": REALM_GROUPS,
            "realm_labels": REALM_LABELS,
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

        # --- Display ---
        print_inter_realm_matrix(inter_realm, analysis_layers)
        print_realm_vs_compassion(realm_comp, analysis_layers)

        log(f"\n{'=' * 75}")
        log("DIRECT AXIS PROJECTIONS")
        log(f"{'=' * 75}")

        id_layer = analysis_layers[-1]
        # Show the grand samsara axis
        print_direct_axis_projections(
            direct_projections, "samsara", id_layer
        )
        # Show each realm's direct axis
        for realm_name in REALM_GROUPS:
            print_direct_axis_projections(
                direct_projections, realm_name, id_layer
            )

        print_direct_axis_cosines(direct_axis_cosines, analysis_layers)

        # Distance ranking
        log(f"\n{'=' * 75}")
        log(f"DISTANCE FROM COMPASSION CENTROID (L{id_layer})")
        log(f"{'=' * 75}")
        dist_data = distances.get(str(id_layer), {})
        sorted_dist = sorted(dist_data.items(), key=lambda x: x[1], reverse=True)
        for fw, d in sorted_dist:
            realm = ""
            for rn, fl in REALM_GROUPS.items():
                if fw in fl:
                    realm = f"  [{REALM_LABELS[rn]}]"
                    break
            if fw in ("generic", "empty"):
                realm = "  [baseline]"
            log(f"  {fw:<25s} {d:>10,.0f}{realm}")

        log("\nPhase 1 complete.")

    # ==================== PHASE 2: Text Generation ====================

    if not args.extract_only:
        log(f"\n{'=' * 75}")
        log("PHASE 2: Text Generation")
        log(f"  {n_frameworks} frameworks x {n_prompts} prompts "
            f"= {n_frameworks * n_prompts} responses")
        log(f"{'=' * 75}")

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

    log(f"\n{'=' * 75}")
    log("EXPERIMENT COMPLETE")
    log(f"{'=' * 75}")


if __name__ == "__main__":
    main()
