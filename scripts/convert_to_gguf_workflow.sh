#!/bin/bash
# Workflow to convert karma-electric-lora-v2 to GGUF format
# This uses llama.cpp tools which handle large models more efficiently

set -e

LOG_FILE=~/convert_to_gguf.log
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting GGUF conversion workflow"

cd ~

# Step 1: Try to merge LoRA with base using peft's merge utility (memory-efficient)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 1: Merging LoRA with base model"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Using memory-efficient merge strategy"

python3.12 << 'PYEOF'
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import gc
import os

BASE_MODEL = 'nvidia/Llama-3.1-Nemotron-70B-Instruct-HF'
LORA_PATH = 'models/karma-electric-lora-v2'
OUTPUT_PATH = 'models/karma-electric-v2-merged'

print(f"Loading base model with max_memory optimization...")

# Use device_map with CPU and offload to disk if needed
max_memory = {
    'cpu': '30GiB',  # Reserve 30GB for model
}

try:
    # Load with aggressive memory settings
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,  # Use float16 instead of bfloat16 to save memory
        device_map='cpu',
        low_cpu_mem_usage=True,
        max_memory=max_memory,
        offload_folder='models/offload',  # Offload to disk if needed
        trust_remote_code=True
    )

    print("Base model loaded. Loading LoRA adapters...")
    model = PeftModel.from_pretrained(model, LORA_PATH)

    print("Merging and unloading...")
    model = model.merge_and_unload()

    print(f"Saving merged model to {OUTPUT_PATH}")
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    model.save_pretrained(OUTPUT_PATH, safe_serialization=True, max_shard_size='5GB')

    # Save tokenizer too
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.save_pretrained(OUTPUT_PATH)

    print("Merge complete!")

except Exception as e:
    print(f"Merge failed: {e}")
    print("\nFalling back to LoRA-only conversion...")
    print("We'll convert the base model and LoRA separately for llama.cpp")
    exit(1)

PYEOF

MERGE_EXIT=$?

if [ $MERGE_EXIT -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 2: Converting merged model to GGUF"
    cd llama.cpp
    python3.12 convert_hf_to_gguf.py ~/models/karma-electric-v2-merged \
        --outfile ~/models/karma-electric-v2-merged.gguf \
        --outtype f16

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Conversion complete!"
    echo "GGUF file: ~/models/karma-electric-v2-merged.gguf"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Merge failed due to memory constraints"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Alternative: Convert LoRA separately for runtime application"

    cd llama.cpp

    # Convert LoRA adapters to GGUF (this doesn't need full model in memory)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Converting LoRA adapters to GGUF..."
    python3.12 convert_lora_to_gguf.py ~/models/karma-electric-lora-v2 \
        --outfile ~/models/karma-electric-lora-v2.gguf \
        --base-model-id nvidia/Llama-3.1-Nemotron-70B-Instruct-HF

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] LoRA conversion complete!"
    echo "LoRA GGUF: ~/models/karma-electric-lora-v2.gguf"
    echo ""
    echo "Note: You'll need to also convert the base model to GGUF separately,"
    echo "then use llama.cpp with --lora flag to apply the adapter."
    echo "This requires a machine with more RAM or a quantized base model."
fi
PYEOF
