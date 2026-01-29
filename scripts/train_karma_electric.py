#!/usr/bin/env python3
"""
Karma Electric Fine-Tuning Script
Fine-tunes Mistral 7B on Dharma-aligned response data.

Usage:
    python3 train_karma_electric.py

Prerequisites (run once):
    pip install torch transformers datasets accelerate peft trl bitsandbytes
"""

import os
import json
import torch
from datetime import datetime
from pathlib import Path

# ============ Configuration ============

CONFIG = {
    # Model
    "base_model": "mistralai/Mistral-7B-Instruct-v0.3",
    "max_length": 2048,

    # LoRA parameters
    "lora_r": 32,
    "lora_alpha": 64,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],

    # Training
    "num_epochs": 3,
    "batch_size": 4,
    "gradient_accumulation": 4,
    "learning_rate": 2e-4,
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "lr_scheduler": "cosine",

    # Data
    "train_file": "karma-electric-chatml-272-20260129.jsonl",

    # Output
    "output_dir": "./karma-electric-mistral-lora",
    "save_steps": 50,
    "logging_steps": 10,

    # Quantization
    "use_4bit": False,
}

def setup_environment():
    """Set up training environment."""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {gpu_name} ({gpu_mem:.1f} GB)")
    else:
        print("WARNING: No GPU detected!")

def load_model_and_tokenizer():
    """Load base model with LoRA adapters."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    print(f"\nLoading {CONFIG['base_model']}...")

    bnb_config = None
    if CONFIG["use_4bit"]:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        CONFIG["base_model"],
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    tokenizer = AutoTokenizer.from_pretrained(CONFIG["base_model"])
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    if CONFIG["use_4bit"]:
        model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=CONFIG["lora_r"],
        lora_alpha=CONFIG["lora_alpha"],
        lora_dropout=CONFIG["lora_dropout"],
        target_modules=CONFIG["target_modules"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer

def format_chat(example, tokenizer):
    """Format a single example into chat format."""
    conversations = example.get("conversations", [])

    chat = []
    for msg in conversations:
        role = msg.get("role", msg.get("from", ""))
        content = msg.get("content", msg.get("value", ""))

        if role in ["system"]:
            chat.append({"role": "system", "content": content})
        elif role in ["user", "human"]:
            chat.append({"role": "user", "content": content})
        elif role in ["assistant", "gpt"]:
            chat.append({"role": "assistant", "content": content})

    text = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=False)
    return {"text": text}

def load_dataset(tokenizer):
    """Load and prepare training dataset."""
    from datasets import load_dataset as hf_load_dataset

    print(f"\nLoading dataset: {CONFIG['train_file']}")

    dataset = hf_load_dataset("json", data_files=CONFIG["train_file"], split="train")
    print(f"Loaded {len(dataset)} examples")

    dataset = dataset.map(
        lambda x: format_chat(x, tokenizer),
        remove_columns=dataset.column_names,
    )

    print(f"\nSample formatted text (first 500 chars):")
    print(dataset[0]["text"][:500])
    print("...")

    return dataset

def train(model, tokenizer, dataset):
    """Run training."""
    from trl import SFTTrainer, SFTConfig

    print(f"\nStarting training...")
    print(f"  Epochs: {CONFIG['num_epochs']}")
    print(f"  Batch size: {CONFIG['batch_size']} x {CONFIG['gradient_accumulation']} = {CONFIG['batch_size'] * CONFIG['gradient_accumulation']}")
    print(f"  Learning rate: {CONFIG['learning_rate']}")
    print(f"  Output: {CONFIG['output_dir']}")

    # Use SFTConfig (TRL 0.27+ API)
    sft_config = SFTConfig(
        output_dir=CONFIG["output_dir"],
        num_train_epochs=CONFIG["num_epochs"],
        per_device_train_batch_size=CONFIG["batch_size"],
        gradient_accumulation_steps=CONFIG["gradient_accumulation"],
        learning_rate=CONFIG["learning_rate"],
        warmup_ratio=CONFIG["warmup_ratio"],
        weight_decay=CONFIG["weight_decay"],
        lr_scheduler_type=CONFIG["lr_scheduler"],
        logging_steps=CONFIG["logging_steps"],
        save_steps=CONFIG["save_steps"],
        save_total_limit=3,
        bf16=True,
        gradient_checkpointing=True,
        optim="adamw_torch",
        report_to="none",
        max_length=CONFIG["max_length"],
        packing=True,
        dataset_text_field="text",
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=sft_config,
    )

    trainer.train()

    final_path = f"{CONFIG['output_dir']}/final"
    print(f"\nSaving final model to {final_path}")
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)

    return trainer

def merge_and_export(output_dir):
    """Merge LoRA weights into base model and export."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print(f"\nMerging LoRA weights...")

    base_model = AutoModelForCausalLM.from_pretrained(
        CONFIG["base_model"],
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    model = PeftModel.from_pretrained(base_model, f"{output_dir}/final")
    model = model.merge_and_unload()

    merged_path = f"{output_dir}/merged"
    print(f"Saving merged model to {merged_path}")
    model.save_pretrained(merged_path)

    tokenizer = AutoTokenizer.from_pretrained(CONFIG["base_model"])
    tokenizer.save_pretrained(merged_path)

    print(f"\nDone! Merged model saved to {merged_path}")

def main():
    print("=" * 60)
    print("Karma Electric Fine-Tuning")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    setup_environment()
    model, tokenizer = load_model_and_tokenizer()
    dataset = load_dataset(tokenizer)
    trainer = train(model, tokenizer, dataset)

    # Auto-merge at end (no interactive prompt for overnight runs)
    print("\nMerging LoRA weights into base model...")
    merge_and_export(CONFIG["output_dir"])

    print(f"\nCompleted: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
