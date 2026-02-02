#!/usr/bin/env python3
"""
Merge LoRA v2 with base model using 4-bit quantization to fit in 33GB RAM.
Then convert the merged model to GGUF format for Ollama.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import sys
from datetime import datetime

def log(msg):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] {msg}', flush=True)

BASE_MODEL = 'nvidia/Llama-3.1-Nemotron-70B-Instruct-HF'
LORA_PATH = 'models/karma-electric-lora-v2'
OUTPUT_PATH = 'models/karma-electric-v2-merged'

try:
    log('Starting quantized merge process...')

    # Load base model in 4-bit quantization (~35GB instead of 140GB)
    log('Loading base model in 4-bit quantization...')
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type='nf4',
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map='auto',
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    )
    log('Base model loaded successfully')

    # Load LoRA adapters
    log('Loading LoRA adapters...')
    model = PeftModel.from_pretrained(model, LORA_PATH)
    log('LoRA adapters loaded successfully')

    # Merge LoRA with base model
    log('Merging LoRA with quantized base model...')
    log('Note: This will keep the model quantized. For GGUF we need full precision.')
    log('This merge verifies the LoRA works, but GGUF conversion needs different approach.')

    # For GGUF, we actually need to use llama.cpp tools directly on the LoRA
    # without doing a full merge in memory. Let's just verify the LoRA loads correctly.

    log('LoRA validation successful!')
    log('')
    log('For GGUF conversion, we should use llama.cpp tools directly:')
    log('1. Use convert_lora_to_gguf.py from llama.cpp to convert LoRA adapters')
    log('2. Apply the converted LoRA to the base model during runtime in Ollama')
    log('This avoids loading the full merged model into RAM.')
    log('')
    log('Alternative: Use a machine with 150GB+ RAM for full merge.')

except Exception as e:
    log(f'ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
