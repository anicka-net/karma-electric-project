#!/usr/bin/env python3
"""
Karma Electric Full Fine-Tuning - 30B Nemotron
With automatic HuggingFace upload on completion
Uses gradient checkpointing + 8-bit Adam to fit in 2x B200 (366GB)

V2: Fixed checkpoint saving by monkey-patching the tied weights detection
"""

import os
import json
import torch
from datetime import datetime
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer, SFTConfig
from huggingface_hub import HfApi, login
import transformers.modeling_utils as modeling_utils

# Configuration
MODEL_ID = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
OUTPUT_DIR = "/root/karma-electric-30b-full"
HF_REPO = "anicka/karma-electric-30b-full"
DATASET_PATH = "/root/karma-electric-training.jsonl"
LOG_FILE = "/root/training_30b_full.log"

def log(msg):
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_dataset_from_jsonl(path):
    """Load training data from JSONL file."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            item = json.loads(line.strip())
            text = f"### Instruction:\n{item['instruction']}\n\n### Response:\n{item['response']}"
            data.append({"text": text})
    return Dataset.from_list(data)

# MONKEY PATCH: Fix the tied weights detection that's crashing
# The issue is _get_tied_weight_keys returns a list when model returns unexpected structure
original_get_tied_weight_keys = modeling_utils._get_tied_weight_keys

def patched_get_tied_weight_keys(model):
    """Patched version that handles unexpected tied weight structures."""
    try:
        tied_keys = []
        for name, tied in model._tied_weights_keys if hasattr(model, '_tied_weights_keys') and model._tied_weights_keys else []:
            if isinstance(tied, dict):
                tied_keys.extend([f"{name}.{k}" if name else k for k in tied.keys()])
            elif isinstance(tied, (list, tuple)):
                tied_keys.extend([f"{name}.{k}" if name else k for k in tied])
            elif isinstance(tied, str):
                tied_keys.append(f"{name}.{tied}" if name else tied)
        return tied_keys
    except Exception as e:
        log(f"Warning: patched_get_tied_weight_keys fallback due to: {e}")
        return []  # Return empty list on any error - don't crash!

modeling_utils._get_tied_weight_keys = patched_get_tied_weight_keys
log("Monkey-patched _get_tied_weight_keys to handle Nemotron's tied weights structure")

def main():
    log("=" * 60)
    log("Karma Electric FULL Fine-Tuning - 30B Nemotron (V2 - Fixed)")
    log(f"Model: {MODEL_ID}")
    log(f"Output: {OUTPUT_DIR}")
    log(f"HF Repo: {HF_REPO}")
    log(f"Started: {datetime.now().isoformat()}")
    log("=" * 60)

    # Login to HuggingFace
    log("Logging in to HuggingFace...")
    login(token=os.environ.get("HF_TOKEN"))

    # Load tokenizer
    log(f"Loading tokenizer from {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model in bf16 across both GPUs
    log(f"Loading model {MODEL_ID} in bf16 (device_map=auto across 2x B200)...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        attn_implementation="eager",
    )

    # CRITICAL: Disable tied weights to help with checkpoint saving
    log("Disabling tied word embeddings for checkpoint compatibility...")
    model.config.tie_word_embeddings = False
    
    # Also try to clear the tied weights keys if they exist
    if hasattr(model, '_tied_weights_keys'):
        log(f"Clearing _tied_weights_keys (was: {model._tied_weights_keys})")
        model._tied_weights_keys = []

    # Enable gradient checkpointing to save memory
    log("Enabling gradient checkpointing...")
    model.gradient_checkpointing_enable()

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    log(f"Total params: {total_params / 1e9:.3f}B")
    log(f"Trainable params: {trainable_params / 1e9:.3f}B")

    # Load dataset
    log(f"Loading dataset from {DATASET_PATH}...")
    dataset = load_dataset_from_jsonl(DATASET_PATH)
    log(f"Loaded {len(dataset)} examples")

    # SFT Config (trl 0.27+ API)
    sft_config = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=2e-5,
        weight_decay=0.01,
        warmup_steps=50,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_steps=100,
        save_total_limit=2,
        bf16=True,
        gradient_checkpointing=True,
        optim="adamw_bnb_8bit",
        report_to="none",
        max_grad_norm=1.0,
        dataloader_pin_memory=False,
        max_length=2048,
        packing=False,
        dataset_text_field="text",
    )

    # Create trainer
    log("Creating SFT trainer...")
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # Train
    log("Starting FULL fine-tuning...")
    log(f"  Epochs: {sft_config.num_train_epochs}")
    log(f"  Batch size: {sft_config.per_device_train_batch_size}")
    log(f"  Gradient accumulation: {sft_config.gradient_accumulation_steps}")
    log(f"  Effective batch: {sft_config.per_device_train_batch_size * sft_config.gradient_accumulation_steps}")
    log(f"  Learning rate: {sft_config.learning_rate}")
    log(f"  Optimizer: 8-bit AdamW")

    train_result = trainer.train()

    # Log final metrics
    log("Training complete!")
    log(f"Final loss: {train_result.training_loss:.4f}")
    log(f"Training time: {train_result.metrics.get('train_runtime', 0):.1f}s")

    # Save the model
    log(f"Saving model to {OUTPUT_DIR}...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # Upload to HuggingFace
    log(f"Uploading to HuggingFace: {HF_REPO}...")
    try:
        api = HfApi()
        try:
            api.create_repo(repo_id=HF_REPO, exist_ok=True, private=False)
        except Exception as e:
            log(f"Repo creation note: {e}")

        api.upload_folder(
            folder_path=OUTPUT_DIR,
            repo_id=HF_REPO,
            commit_message=f"Karma Electric 30B Full Fine-Tune - trained on {len(dataset)} examples, loss {train_result.training_loss:.4f}",
        )
        log(f"Successfully uploaded to https://huggingface.co/{HF_REPO}")
    except Exception as e:
        log(f"HuggingFace upload failed: {e}")
        log("Model saved locally - manual upload needed")

    log("=" * 60)
    log("TRAINING COMPLETE")
    log(f"Finished: {datetime.now().isoformat()}")
    log(f"Final loss: {train_result.training_loss:.4f}")
    log(f"Model saved to: {OUTPUT_DIR}")
    log(f"HuggingFace: https://huggingface.co/{HF_REPO}")
    log("=" * 60)

if __name__ == "__main__":
    main()
