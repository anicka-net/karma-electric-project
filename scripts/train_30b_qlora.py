#!/usr/bin/env python3
"""
Karma Electric QLoRA Training - 30B Nemotron
With automatic HuggingFace upload on completion
"""

import os
import json
import torch
from datetime import datetime
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
from huggingface_hub import HfApi, login

# Configuration
MODEL_ID = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
OUTPUT_DIR = "/root/karma-electric-30b-qlora"
HF_REPO = "anicka/karma-electric-30b-qlora"
DATASET_PATH = "/root/karma-electric-training.jsonl"
LOG_FILE = "/root/training_30b_qlora.log"

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
            # Format as instruction-response for training
            text = f"### Instruction:\n{item['instruction']}\n\n### Response:\n{item['response']}"
            data.append({"text": text})
    return Dataset.from_list(data)

def main():
    log("=" * 60)
    log("Karma Electric QLoRA Training - 30B Nemotron")
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

    # QLoRA config - 4-bit quantization
    log("Setting up 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # Load model with quantization
    log(f"Loading model {MODEL_ID} with 4-bit quantization...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        attn_implementation="eager",  # Avoid flash attention issues
    )

    # Prepare model for k-bit training
    log("Preparing model for QLoRA training...")
    model = prepare_model_for_kbit_training(model)

    # LoRA configuration
    lora_config = LoraConfig(
        r=64,  # LoRA rank
        lora_alpha=128,  # Scaling factor
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # Apply LoRA
    log("Applying LoRA adapters...")
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load dataset
    log(f"Loading dataset from {DATASET_PATH}...")
    dataset = load_dataset_from_jsonl(DATASET_PATH)
    log(f"Loaded {len(dataset)} examples")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,  # Effective batch size = 16
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        bf16=True,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",  # Memory-efficient optimizer
        report_to="none",
        max_grad_norm=0.3,
    )

    # Create trainer
    log("Creating SFT trainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        max_seq_length=2048,
        packing=False,  # Disable packing to avoid attention issues
    )

    # Train
    log("Starting training...")
    log(f"  Epochs: {training_args.num_train_epochs}")
    log(f"  Batch size: {training_args.per_device_train_batch_size}")
    log(f"  Gradient accumulation: {training_args.gradient_accumulation_steps}")
    log(f"  Effective batch: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
    log(f"  Learning rate: {training_args.learning_rate}")

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

        # Create repo if doesn't exist
        try:
            api.create_repo(repo_id=HF_REPO, exist_ok=True, private=False)
        except Exception as e:
            log(f"Repo creation note: {e}")

        # Upload the LoRA adapters
        api.upload_folder(
            folder_path=OUTPUT_DIR,
            repo_id=HF_REPO,
            commit_message=f"Karma Electric 30B QLoRA - trained on {len(dataset)} examples, loss {train_result.training_loss:.4f}",
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
