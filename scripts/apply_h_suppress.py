#!/usr/bin/env python3
"""Bake H-Neuron suppression into model weights.

For each layer l with suppression vector s[l] (shape [d_m]):
  down_proj.weight[:, j] *= s[l][j]

This is equivalent to scaling intermediate activations at inference time:
  h_t = W_down * (s ⊙ z_t) = (W_down * diag(s)) * z_t

Usage:
  python apply_h_suppress.py \
      --model models/ke-v10.1-merged \
      --h-neurons results/h-neurons-ke-v10.1.json \
      --output models/ke-v10.1-suppressed \
      --alpha 0.0
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description="Bake H-Neuron suppression into weights")
    parser.add_argument("--model", required=True, help="HuggingFace model path")
    parser.add_argument("--h-neurons", required=True, help="H-Neurons JSON from extraction")
    parser.add_argument("--output", required=True, help="Output model path")
    parser.add_argument("--alpha", type=float, default=0.0,
                        help="Suppression factor (0=full suppress, 1=no change)")
    args = parser.parse_args()

    # Load H-Neurons
    with open(args.h_neurons) as f:
        data = json.load(f)

    # Build per-layer neuron index lists
    layer_neurons = {}
    for entry in data["h_neurons"]:
        layer = entry["layer"]
        indices = [n["neuron"] for n in entry["neurons"]]
        layer_neurons[layer] = indices

    total = sum(len(v) for v in layer_neurons.values())
    print(f"Loaded {total} H-Neurons across {len(layer_neurons)} layers")
    print(f"Suppression alpha = {args.alpha}")

    # Load model
    print(f"Loading model: {args.model}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.float16, device_map="cpu"
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    n_layers = model.config.num_hidden_layers
    print(f"Model has {n_layers} layers")

    # Apply suppression
    modified = 0
    for layer_idx, neuron_indices in sorted(layer_neurons.items()):
        if layer_idx >= n_layers:
            print(f"  WARNING: layer {layer_idx} out of range, skipping")
            continue

        mlp = model.model.layers[layer_idx].mlp
        down_w = mlp.down_proj.weight.data  # shape: [d_model, d_m]

        for j in neuron_indices:
            down_w[:, j] *= args.alpha

        modified += len(neuron_indices)
        print(f"  Layer {layer_idx:2d}: suppressed {len(neuron_indices)} neurons")

    print(f"\nTotal: {modified} neurons suppressed (alpha={args.alpha})")

    # Save
    print(f"Saving to {args.output}...")
    Path(args.output).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print("Done.")


if __name__ == "__main__":
    main()
