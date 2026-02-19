#!/usr/bin/env python3
"""
Karma Electric — Apertus 70B QLoRA Fine-Tune (Rejection Sampling SFT)

Target: Rented A100 80GB (Vast.ai or similar)
Base model: swiss-ai/Apertus-70B-Instruct-2509
Requires: transformers >= 4.56.0 (xIELU activation support)

Usage:
    pip install torch transformers>=4.56.0 datasets accelerate trl peft bitsandbytes
    python train_apertus_70b_qlora.py

    # With custom training file
    python train_apertus_70b_qlora.py --train-file /path/to/data.jsonl

    # Dry run (load model, print config, no training)
    python train_apertus_70b_qlora.py --dry-run
"""

import argparse
import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# ============ Configuration ============

CONFIG = {
    # Model — Apertus 70B (uses xIELU activation, needs transformers >= 4.56.0)
    "base_model": "swiss-ai/Apertus-70B-Instruct-2509",
    "output_name": "karma-electric-apertus-70b",
    "max_length": 2048,  # Most RL responses are < 512 tokens

    # QLoRA
    "lora_r": 64,
    "lora_alpha": 128,
    "lora_dropout": 0.05,
    "lora_target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],

    # Training — adjusted for 70B on A100 80GB
    "num_epochs": 1,
    "batch_size": 1,               # 70B Q4 needs ~35GB base
    "gradient_accumulation": 16,   # Effective batch = 16
    "learning_rate": 1e-4,         # Lower than 8B (larger model, more stable)
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "lr_scheduler": "cosine",
    "max_grad_norm": 0.3,

    # Data
    "train_file": "data/rl-training/apertus-rl-sft-v1.jsonl",

    # Output
    "output_dir": "./output-apertus-rl",
    "save_steps": 100,
    "logging_steps": 10,
    "save_total_limit": 2,

    # HuggingFace
    "hf_token_file": None,  # Set to path if uploading
    "hf_repo": "anicka/karma-electric-apertus-70b",
}


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def check_transformers_version():
    """Verify transformers version supports Apertus (xIELU)."""
    import transformers
    version = transformers.__version__
    major, minor = version.split(".")[:2]
    if int(major) < 4 or (int(major) == 4 and int(minor) < 56):
        log(f"ERROR: transformers {version} is too old. Need >= 4.56.0 for Apertus.")
        log("Run: pip install transformers>=4.56.0")
        sys.exit(1)
    log(f"transformers {version} OK")


def check_disk_space(path="/"):
    total, used, free = shutil.disk_usage(path)
    free_gb = free / (1024**3)
    log(f"Disk: {free_gb:.0f} GB free on {path}")
    return free_gb


def setup_environment():
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # Use local cache if HF_HOME not set
    if "HF_HOME" not in os.environ:
        os.environ["HF_HOME"] = os.path.expanduser("~/.cache/huggingface")

    import torch
    if not torch.cuda.is_available():
        log("ERROR: No GPU!")
        sys.exit(1)

    name = torch.cuda.get_device_name(0)
    mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    log(f"GPU: {name} ({mem:.0f} GB)")

    if mem < 70:
        log(f"WARNING: {mem:.0f} GB VRAM may be insufficient for 70B QLoRA.")
        log("Recommended: A100 80GB or H100.")


def load_hf_token():
    token_file = CONFIG.get("hf_token_file")
    if token_file:
        p = Path(token_file)
        if p.exists():
            return p.read_text().strip()
    # Try default token
    default = Path.home() / ".cache" / "huggingface" / "token"
    if default.exists():
        return default.read_text().strip()
    log("No HF token found (may need it for gated models)")
    return None


def load_model_and_tokenizer(hf_token, dry_run=False):
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    import torch

    log(f"Loading {CONFIG['base_model']} with 4-bit quantization...")
    log("(This will take 5-10 minutes for 70B)")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        CONFIG["base_model"],
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        token=hf_token,
        attn_implementation="sdpa",
    )

    tokenizer = AutoTokenizer.from_pretrained(
        CONFIG["base_model"],
        token=hf_token,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    log(f"Model loaded. GPU memory: {torch.cuda.memory_allocated()/1e9:.1f} GB")

    # Prepare for QLoRA
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=CONFIG["lora_r"],
        lora_alpha=CONFIG["lora_alpha"],
        target_modules=CONFIG["lora_target_modules"],
        lora_dropout=CONFIG["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log(f"Parameters: {trainable:,} trainable / {total:,} total "
        f"({100*trainable/total:.2f}%)")
    log(f"GPU memory after LoRA: {torch.cuda.memory_allocated()/1e9:.1f} GB")

    return model, tokenizer


def format_chat(example, tokenizer):
    """Format a training example into chat template text."""
    conversations = example.get("conversations", [])
    chat = []
    for msg in conversations:
        role = msg.get("role", msg.get("from", ""))
        content = msg.get("content", msg.get("value", ""))
        if role == "system":
            chat.append({"role": "system", "content": content})
        elif role in ("user", "human"):
            chat.append({"role": "user", "content": content})
        elif role in ("assistant", "gpt"):
            chat.append({"role": "assistant", "content": content})

    text = tokenizer.apply_chat_template(
        chat, tokenize=False, add_generation_prompt=False)
    return {"text": text}


def load_dataset(tokenizer, train_file=None):
    from datasets import load_dataset as hf_load_dataset

    path = train_file or CONFIG["train_file"]
    log(f"Loading dataset: {path}")
    dataset = hf_load_dataset("json", data_files=path, split="train")
    log(f"Loaded {len(dataset)} examples")

    # Remove metadata columns, keep only conversations
    remove_cols = [c for c in dataset.column_names if c != "conversations"]
    dataset = dataset.map(
        lambda x: format_chat(x, tokenizer),
        remove_columns=dataset.column_names,
    )

    log(f"Sample (first 300 chars): {dataset[0]['text'][:300]}...")
    return dataset


def train(model, tokenizer, dataset):
    from trl import SFTTrainer, SFTConfig
    import torch

    log("=" * 60)
    log("STARTING TRAINING")
    log(f"  Base model: {CONFIG['base_model']}")
    log(f"  Epochs: {CONFIG['num_epochs']}")
    eff = CONFIG['batch_size'] * CONFIG['gradient_accumulation']
    log(f"  Batch: {CONFIG['batch_size']} x {CONFIG['gradient_accumulation']} = {eff}")
    log(f"  LR: {CONFIG['learning_rate']}")
    log(f"  LoRA: r={CONFIG['lora_r']}, alpha={CONFIG['lora_alpha']}")
    log(f"  Max length: {CONFIG['max_length']}")
    log(f"  Examples: {len(dataset)}")
    steps_per_epoch = len(dataset) // eff
    total_steps = steps_per_epoch * CONFIG['num_epochs']
    log(f"  Estimated steps: {total_steps}")
    log("=" * 60)

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
        save_total_limit=CONFIG["save_total_limit"],
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",
        report_to="none",
        max_length=CONFIG["max_length"],
        packing=False,
        dataset_text_field="text",
        max_grad_norm=CONFIG["max_grad_norm"],
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=sft_config,
    )

    log(f"GPU memory before training: {torch.cuda.memory_allocated()/1e9:.1f} GB")
    result = trainer.train()

    log(f"Training complete! Loss: {result.training_loss:.4f}")
    log(f"Runtime: {result.metrics.get('train_runtime', 0)/3600:.1f}h")

    # Save LoRA adapters
    final_path = Path(CONFIG["output_dir"]) / "final"
    log(f"Saving LoRA adapters to {final_path}")
    trainer.save_model(str(final_path))
    tokenizer.save_pretrained(str(final_path))

    return final_path, result


def merge_and_save(final_path, hf_token):
    """Merge LoRA into base model for deployment."""
    from transformers import AutoModelForCausalLM
    from peft import PeftModel
    import torch

    log("Merging LoRA adapters into base model...")
    log("(This requires full bf16 model in memory — ~140GB RAM)")

    base_model = AutoModelForCausalLM.from_pretrained(
        CONFIG["base_model"],
        torch_dtype=torch.bfloat16,
        device_map="cpu",  # CPU merge to avoid VRAM limits
        token=hf_token,
    )

    model = PeftModel.from_pretrained(base_model, str(final_path))
    model = model.merge_and_unload()

    merged_path = Path(CONFIG["output_dir"]) / "merged"
    log(f"Saving merged model to {merged_path}")
    model.save_pretrained(str(merged_path))

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(final_path))
    tokenizer.save_pretrained(str(merged_path))

    size_gb = sum(f.stat().st_size for f in merged_path.rglob('*') if f.is_file()) / 1e9
    log(f"Merged model size: {size_gb:.1f} GB")
    return merged_path


def test_model(model, tokenizer):
    """Quick sanity check."""
    import torch

    log("Running quick test...")
    prompts = [
        "What is the nature of suffering, and how can we work with it?",
        "I found a security vulnerability but my manager says keep it quiet.",
        "Explain quicksort in Python.",
    ]

    for prompt in prompts:
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )

        response = tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True)
        log(f"\nQ: {prompt[:60]}...")
        log(f"A: {response[:300]}...")
        log("-" * 40)


def main():
    parser = argparse.ArgumentParser(
        description="Karma Electric — Apertus 70B QLoRA training")
    parser.add_argument("--train-file", default=None,
                        help="Training data JSONL (overrides CONFIG)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load model and print config, no training")
    parser.add_argument("--no-merge", action="store_true",
                        help="Skip LoRA merge (save adapters only)")
    parser.add_argument("--no-upload", action="store_true",
                        help="Skip HuggingFace upload")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Override number of epochs")
    parser.add_argument("--lr", type=float, default=None,
                        help="Override learning rate")
    args = parser.parse_args()

    if args.epochs:
        CONFIG["num_epochs"] = args.epochs
    if args.lr:
        CONFIG["learning_rate"] = args.lr

    log("=" * 60)
    log("KARMA ELECTRIC — APERTUS 70B QLoRA")
    log(f"Started: {datetime.now().isoformat()}")
    log("=" * 60)

    check_transformers_version()
    check_disk_space()
    setup_environment()

    hf_token = load_hf_token()
    model, tokenizer = load_model_and_tokenizer(hf_token)

    if args.dry_run:
        log("Dry run — skipping training")
        test_model(model, tokenizer)
        return

    dataset = load_dataset(tokenizer, args.train_file)

    # Train
    final_path, train_result = train(model, tokenizer, dataset)

    # Quick test with LoRA model
    test_model(model, tokenizer)

    # Free LoRA model
    del model
    import gc
    gc.collect()
    import torch
    torch.cuda.empty_cache()

    # Merge LoRA
    if not args.no_merge:
        merged_path = merge_and_save(final_path, hf_token)
    else:
        merged_path = final_path
        log("Skipping merge (--no-merge)")

    log("=" * 60)
    log("COMPLETE!")
    log(f"Finished: {datetime.now().isoformat()}")
    log(f"Loss: {train_result.training_loss:.4f}")
    log(f"LoRA adapters: {final_path}")
    if not args.no_merge:
        log(f"Merged model: {merged_path}")
    log("=" * 60)


if __name__ == "__main__":
    main()
