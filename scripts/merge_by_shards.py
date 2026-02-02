#!/usr/bin/env python3
"""
Merge LoRA with base model shard-by-shard to avoid loading entire 140GB model into RAM.
"""

import torch
from safetensors.torch import load_file, save_file
from transformers import AutoConfig, AutoTokenizer
from huggingface_hub import snapshot_download
import json
import os
from pathlib import Path
from datetime import datetime
import gc

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] {msg}', flush=True)

BASE_MODEL = 'nvidia/Llama-3.1-Nemotron-70B-Instruct-HF'
LORA_PATH = 'karma-electric-conversion/models/karma-electric-lora-v2'
OUTPUT_PATH = 'models/karma-electric-v2-merged'

log('Starting shard-by-shard merge...')

# Load LoRA config
log('Loading LoRA configuration...')
with open(f'{LORA_PATH}/adapter_config.json') as f:
    lora_config = json.load(f)

log(f'LoRA rank: {lora_config["r"]}, alpha: {lora_config["lora_alpha"]}')
scaling = lora_config["lora_alpha"] / lora_config["r"]

# Load LoRA adapters (these are small, ~1.6GB)
log('Loading LoRA adapters into memory...')
lora_weights = load_file(f'{LORA_PATH}/adapter_model.safetensors')
log(f'Loaded {len(lora_weights)} LoRA tensors')

# Download base model files (just config/weights, don't load into memory)
log('Downloading base model files (if not cached)...')
base_path = snapshot_download(BASE_MODEL, local_files_only=False)
log(f'Base model location: {base_path}')

# Load model index to see shards
log('Reading model shard index...')
with open(f'{base_path}/model.safetensors.index.json') as f:
    index = json.load(f)

weight_map = index['weight_map']
# Group weights by shard
shard_to_weights = {}
for weight_name, shard_file in weight_map.items():
    if shard_file not in shard_to_weights:
        shard_to_weights[shard_file] = []
    shard_to_weights[shard_file].append(weight_name)

log(f'Model has {len(shard_to_weights)} shards')

# Create output directory
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Process each shard
merged_weight_map = {}
for shard_idx, (shard_file, weight_names) in enumerate(shard_to_weights.items()):
    log(f'Processing shard {shard_idx+1}/{len(shard_to_weights)}: {shard_file}')

    # Load this shard
    shard_path = f'{base_path}/{shard_file}'
    shard_weights = load_file(shard_path)
    log(f'  Loaded {len(shard_weights)} weights from shard')

    # Apply LoRA to weights in this shard
    merged_shard = {}
    for weight_name in shard_weights.keys():
        base_weight = shard_weights[weight_name]

        # Check if there's a LoRA adapter for this weight
        # LoRA naming: base_model.model.{weight_name}.lora_A.weight / lora_B.weight
        lora_a_key = f'base_model.model.{weight_name}.lora_A.weight'
        lora_b_key = f'base_model.model.{weight_name}.lora_B.weight'

        if lora_a_key in lora_weights and lora_b_key in lora_weights:
            log(f'  Merging LoRA for: {weight_name}')
            lora_a = lora_weights[lora_a_key]
            lora_b = lora_weights[lora_b_key]

            # Merge: W_merged = W_base + (lora_B @ lora_A) * scaling
            # Ensure types match
            lora_a = lora_a.to(base_weight.dtype)
            lora_b = lora_b.to(base_weight.dtype)

            delta = torch.mm(lora_b, lora_a) * scaling
            merged_weight = base_weight + delta
            merged_shard[weight_name] = merged_weight
            log(f'    Applied LoRA (delta shape: {delta.shape})')
        else:
            # No LoRA for this weight, keep base
            merged_shard[weight_name] = base_weight

        # Track for index
        merged_weight_map[weight_name] = shard_file

    # Save merged shard
    output_shard_path = f'{OUTPUT_PATH}/{shard_file}'
    log(f'  Saving merged shard to {output_shard_path}')
    save_file(merged_shard, output_shard_path)

    # Clear memory
    del shard_weights
    del merged_shard
    gc.collect()

    log(f'  Shard {shard_idx+1} complete')

# Save model index
log('Saving model index...')
output_index = {
    'metadata': {'total_size': index['metadata']['total_size']},
    'weight_map': merged_weight_map
}
with open(f'{OUTPUT_PATH}/model.safetensors.index.json', 'w') as f:
    json.dump(output_index, f, indent=2)

# Copy config and tokenizer
log('Copying config and tokenizer...')
config = AutoConfig.from_pretrained(BASE_MODEL)
config.save_pretrained(OUTPUT_PATH)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
tokenizer.save_pretrained(OUTPUT_PATH)

log('✓ Shard-by-shard merge complete!')
log(f'Merged model saved to: {OUTPUT_PATH}')
log(f'Total shards: {len(shard_to_weights)}')
