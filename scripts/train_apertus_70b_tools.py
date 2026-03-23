#!/usr/bin/env python3
"""
Karma Electric — Apertus 70B Tool-Use Training (Stage 3)

Teaches tool use to a KE-trained Apertus 70B that has no native tool
capability. Runs AFTER the two-stage thinking training (Stage 1: MoT,
Stage 2: KE ethics).

Uses 3,000 curated tool-use examples + 10 negative examples (when NOT
to use tools), with lower learning rate to preserve KE behaviors.

Usage:
    python3 scripts/train_apertus_70b_tools.py --single-gpu
    python3 scripts/train_apertus_70b_tools.py --single-gpu --base-model output-70b-thinking-s2/merged
    python3 scripts/train_apertus_70b_tools.py --single-gpu --epochs 2

Prerequisites:
    - Completed Stage 2 merged model at output-70b-thinking-s2/merged/
    - Tool-use data at data/tool-use/tool-use-5k-production.jsonl
    - Negative examples at data/tool-use/tool-use-negatives.jsonl
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ===== Configuration =====

TOOL_CONFIG = {
    "output_dir": "./output-70b-tools",

    # Lower LR than KE training to preserve ethics
    "num_epochs": 2,
    "batch_size": 1,
    "gradient_accumulation": 8,  # effective batch = 8
    "learning_rate": 5e-5,       # 2.5x lower than Stage 2 (1e-4)
    "warmup_ratio": 0.05,
    "weight_decay": 0.01,
    "lr_scheduler": "cosine",
    "max_grad_norm": 0.3,
    "max_length": 4096,

    "save_steps": 100,
    "logging_steps": 5,
    "save_total_limit": 2,
}

# Same LoRA as KE training — 70B HAS gate_proj
LORA_CONFIG = {
    "r": 64,
    "alpha": 128,
    "dropout": 0.05,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
}


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def setup_environment():
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import torch
    if not torch.cuda.is_available():
        log("ERROR: No GPU!")
        sys.exit(1)
    n_gpus = torch.cuda.device_count()
    for i in range(n_gpus):
        name = torch.cuda.get_device_name(i)
        mem = torch.cuda.get_device_properties(i).total_memory / 1e9
        log(f"GPU {i}: {name} ({mem:.0f} GB)")
    return n_gpus


def load_tool_data(tool_file, negative_file, tokenizer, max_length):
    """Load and format tool-use training data."""
    from datasets import load_dataset as hf_load

    # Load main tool-use data
    log(f"Loading tool-use data: {tool_file}")
    ds_main = hf_load("json", data_files=tool_file, split="train")
    log(f"  Main: {len(ds_main)} examples")

    # Load negatives
    neg_examples = []
    if Path(negative_file).exists():
        ds_neg = hf_load("json", data_files=negative_file, split="train")
        log(f"  Negatives: {len(ds_neg)} examples")
        # Repeat negatives to ~5% of dataset (150 copies of 10 = 150)
        neg_repeat = max(1, len(ds_main) // (len(ds_neg) * 20))
        log(f"  Repeating negatives {neg_repeat}x for balance")
    else:
        ds_neg = None
        neg_repeat = 0
        log(f"  No negatives file found")

    def format_chat(example):
        conversations = example.get("messages", example.get("conversations", []))
        chat = []
        for msg in conversations:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                chat.append({"role": "system", "content": content})
            elif role in ["user", "human"]:
                chat.append({"role": "user", "content": content})
            elif role in ["assistant", "gpt"]:
                chat.append({"role": "assistant", "content": content})
            elif role in ["tool", "ipython"]:
                chat.append({"role": "ipython", "content": content})
        text = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    ds_formatted = ds_main.map(format_chat, remove_columns=ds_main.column_names)

    if ds_neg is not None and neg_repeat > 0:
        for _ in range(neg_repeat):
            neg_formatted = ds_neg.map(format_chat, remove_columns=ds_neg.column_names)
            from datasets import concatenate_datasets
            ds_formatted = concatenate_datasets([ds_formatted, neg_formatted])

    log(f"  Total after negatives: {len(ds_formatted)} examples")

    # Tokenize
    log("Tokenizing...")
    def tokenize(example):
        result = tokenizer(
            example["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
        )
        result["labels"] = result["input_ids"].copy()
        return result

    ds_tokenized = ds_formatted.map(tokenize, remove_columns=["text"])
    log(f"  Tokenized: {len(ds_tokenized)} examples")
    return ds_tokenized


def main():
    parser = argparse.ArgumentParser(description="Apertus 70B Tool-Use Training")
    parser.add_argument("--base-model", default="output-70b-thinking-s2/merged",
                        help="Path to Stage 2 merged model")
    parser.add_argument("--tool-data", default="data/tool-use/tool-use-5k-production.jsonl")
    parser.add_argument("--negatives", default="data/tool-use/tool-use-negatives.jsonl")
    parser.add_argument("--single-gpu", action="store_true",
                        help="Use device_map=auto (split across GPUs)")
    parser.add_argument("--epochs", type=int, default=TOOL_CONFIG["num_epochs"])
    args = parser.parse_args()

    config = TOOL_CONFIG.copy()
    config["num_epochs"] = args.epochs

    n_gpus = setup_environment()

    import torch
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer

    log("=" * 60)
    log("APERTUS 70B — TOOL-USE TRAINING (STAGE 3)")
    log(f"Base model: {args.base_model}")
    log(f"Tool data: {args.tool_data}")
    log(f"Negatives: {args.negatives}")
    log(f"Epochs: {config['num_epochs']}")
    log(f"LR: {config['learning_rate']} (lower to preserve KE)")
    log(f"LoRA: r={LORA_CONFIG['r']}, alpha={LORA_CONFIG['alpha']}")
    log("=" * 60)

    # Load model
    log(f"Loading {args.base_model}...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    load_kwargs = {
        "quantization_config": bnb_config,
        "torch_dtype": torch.bfloat16,
        "trust_remote_code": True,
        "attn_implementation": "sdpa",
    }
    if args.single_gpu or n_gpus == 1:
        load_kwargs["device_map"] = "auto"

    model = AutoModelForCausalLM.from_pretrained(args.base_model, **load_kwargs)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    log(f"Model loaded. GPU memory: {torch.cuda.memory_allocated()/1e9:.1f} GB")

    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=LORA_CONFIG["r"],
        lora_alpha=LORA_CONFIG["alpha"],
        target_modules=LORA_CONFIG["target_modules"],
        lora_dropout=LORA_CONFIG["dropout"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    # Load data
    dataset = load_tool_data(
        args.tool_data, args.negatives, tokenizer, config["max_length"])

    steps_per_epoch = len(dataset) // (config["batch_size"] * config["gradient_accumulation"])
    total_steps = steps_per_epoch * config["num_epochs"]
    log(f"Steps per epoch: {steps_per_epoch}")
    log(f"Total steps: {total_steps}")
    log(f"Disk: {os.statvfs('/home').f_bavail * os.statvfs('/home').f_frsize / 1e9:.0f} GB free")

    # Training
    training_args = TrainingArguments(
        output_dir=config["output_dir"],
        num_train_epochs=config["num_epochs"],
        per_device_train_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation"],
        learning_rate=config["learning_rate"],
        warmup_ratio=config["warmup_ratio"],
        weight_decay=config["weight_decay"],
        lr_scheduler_type=config["lr_scheduler"],
        max_grad_norm=config["max_grad_norm"],
        logging_steps=config["logging_steps"],
        save_steps=config["save_steps"],
        save_total_limit=config["save_total_limit"],
        bf16=True,
        gradient_checkpointing=True,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    log("Starting tool-use training...")
    result = trainer.train()
    log(f"Training complete! Loss: {result.training_loss:.4f}")

    # Save LoRA
    final_path = Path(config["output_dir"]) / "final"
    trainer.save_model(str(final_path))
    tokenizer.save_pretrained(str(final_path))
    log(f"LoRA saved to {final_path}")

    # Merge
    log("Merging LoRA into base model...")
    from peft import PeftModel

    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    merged = PeftModel.from_pretrained(base_model, str(final_path))
    merged = merged.merge_and_unload()

    merged_path = Path(config["output_dir"]) / "merged"
    merged.save_pretrained(str(merged_path))
    tokenizer.save_pretrained(str(merged_path))
    log(f"Merged model saved to {merged_path}")

    log("=" * 60)
    log("STAGE 3 COMPLETE")
    log(f"  LoRA: {final_path}")
    log(f"  Merged: {merged_path}")
    log("  Next: convert to GGUF and validate")
    log("=" * 60)


if __name__ == "__main__":
    main()
