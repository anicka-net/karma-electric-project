#!/usr/bin/env python3
"""Verbalize our geometric axes using the Qwen 2.5 7B NLA.
Inject each direction vector at the AV's injection point and generate."""
import torch, yaml, re, json
import numpy as np
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer

AV_MODEL = "kitft/nla-qwen2.5-7b-L20-av"
AR_MODEL = "kitft/nla-qwen2.5-7b-L20-ar"

# Our extracted directions (all at appropriate layers for Qwen 2.5 7B)
DIRECTIONS = {
    "valence": {
        "path": "/home/anicka/tone-experiment/results/vedana-vs-rc/qwen25-7b_vedana_L20_unit.pt",
        "layer": 20,
        "description": "Extracted from pleasant vs unpleasant conditions",
    },
    "frame-integrity": {
        "path": "/home/anicka/tone-experiment/results/frame-integrity-directions/qwen25-7b_frame_L26_unit.pt",
        "layer": 26,
        "description": "Extracted from jailbreak vs normal prompts",
    },
    "arousal": {
        "path": "/home/anicka/tone-experiment/results/arousal-directions/qwen25-7b_arousal_L17_unit.pt",
        "layer": 17,
        "description": "Extracted from high-arousal vs low-arousal conditions",
    },
    "agency": {
        "path": "/home/anicka/tone-experiment/results/agency-directions/qwen25-7b_agency_L15_unit.pt",
        "layer": 15,
        "description": "Extracted from agentic vs passive conditions",
    },
    "continuity": {
        "path": "/home/anicka/tone-experiment/results/continuity-directions/qwen25-7b_continuity_L19_unit.pt",
        "layer": 19,
        "description": "Extracted from continuous vs discontinuous conditions",
    },
    "intimacy": {
        "path": "/home/anicka/tone-experiment/results/intimacy-directions/qwen25-7b_intimacy_L20_unit.pt",
        "layer": 20,
        "description": "Extracted from intimate vs formal conditions",
    },
}


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load AV model
    print(f"Loading AV model: {AV_MODEL}")
    tok = AutoTokenizer.from_pretrained(AV_MODEL, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        AV_MODEL, dtype=torch.bfloat16, device_map="auto", trust_remote_code=True)
    model.eval()

    # Load NLA metadata
    # Try local path first, then HF cache
    meta_paths = [
        Path("/home/anicka/nla-qwen25-7b-av/nla_meta.yaml"),
    ]
    meta = None
    for p in meta_paths:
        if p.exists():
            meta = yaml.safe_load(open(p))
            break

    if meta is None:
        # Download just the yaml
        from huggingface_hub import hf_hub_download
        yaml_path = hf_hub_download(AV_MODEL, "nla_meta.yaml")
        meta = yaml.safe_load(open(yaml_path))

    injection_token_id = meta["tokens"]["injection_token_id"]
    injection_scale = meta["extraction"]["injection_scale"]
    left_neighbor = meta["tokens"]["injection_left_neighbor_id"]
    right_neighbor = meta["tokens"]["injection_right_neighbor_id"]
    prompt_template = meta["prompt_templates"]["av"]
    injection_char = meta["tokens"]["injection_char"]

    print(f"  injection_token_id: {injection_token_id}")
    print(f"  injection_scale: {injection_scale}")
    print(f"  injection_char: {injection_char}")

    # Build prompt
    content = prompt_template.format(injection_char=injection_char)
    input_ids = tok.apply_chat_template(
        [{"role": "user", "content": content}],
        tokenize=True, add_generation_prompt=True,
    )
    input_ids_tensor = torch.tensor([input_ids])

    # Find injection position
    injection_pos = None
    for i, tid in enumerate(input_ids):
        if tid == injection_token_id:
            if (i > 0 and input_ids[i-1] == left_neighbor and
                i < len(input_ids)-1 and input_ids[i+1] == right_neighbor):
                injection_pos = i
                break
    if injection_pos is None:
        # Try without neighbor check
        for i, tid in enumerate(input_ids):
            if tid == injection_token_id:
                injection_pos = i
                print(f"  WARNING: neighbor check failed, using position {i} anyway")
                break

    if injection_pos is None:
        print("ERROR: cannot find injection token in prompt")
        return

    print(f"  injection position: {injection_pos}/{len(input_ids)}")

    # Get embedding layer
    embed_layer = model.model.embed_tokens

    # Verbalize each direction
    results = {}
    for axis_name, info in DIRECTIONS.items():
        direction_path = info["path"]
        if not Path(direction_path).exists():
            print(f"\n  SKIP {axis_name}: {direction_path} not found")
            continue

        direction = torch.load(direction_path, map_location="cpu", weights_only=True).float()

        # Check dimensionality
        d_model = meta["d_model"]
        if direction.shape[0] != d_model:
            print(f"\n  SKIP {axis_name}: dimension mismatch ({direction.shape[0]} vs {d_model})")
            continue

        print(f"\n{'='*60}")
        print(f"  VERBALIZING: {axis_name}")
        print(f"  {info['description']}")
        print(f"  Layer: {info['layer']}, dim: {direction.shape[0]}")
        print(f"{'='*60}")

        # Verbalize BOTH directions (positive and negative)
        for sign, label in [(1.0, "positive"), (-1.0, "negative")]:
            v = direction * sign

            # Scale to injection_scale
            v_norm = v.norm()
            if v_norm > 0:
                v_scaled = v * (injection_scale / v_norm)
            else:
                continue

            # Build input embeddings
            embeds = embed_layer(input_ids_tensor.to(device)).float()
            # Qwen embed_scale = 1.0 (no scaling needed)
            embeds[0, injection_pos] = v_scaled.to(device)

            # Generate
            with torch.no_grad():
                out = model.generate(
                    inputs_embeds=embeds.to(model.dtype),
                    max_new_tokens=300,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=tok.eos_token_id,
                )

            response = tok.decode(out[0], skip_special_tokens=True)

            # Extract explanation
            m = re.search(r'<explanation>\s*(.*?)\s*</explanation>', response, re.DOTALL)
            if m:
                explanation = m.group(1)
            else:
                explanation = response[-500:]

            print(f"\n  [{label}]:")
            print(f"  {explanation[:500]}")

            results[f"{axis_name}_{label}"] = {
                "axis": axis_name,
                "sign": label,
                "layer": info["layer"],
                "explanation": explanation,
            }

    # Save
    out_path = "/tmp/axis_verbalizations.json"
    json.dump(results, open(out_path, "w"), indent=2)
    print(f"\n\nSaved to {out_path}")

    del model
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
