#!/usr/bin/env python3
"""
Karma Electric - Llama 3.1 8B QLoRA Fine-Tune
Target: GPU server with L40 46GB

Usage:
    cd /space/anicka/karma-electric-8b
    ./venv/bin/python3 train_llama31_8b_qlora.py

Prerequisites:
    pip install torch transformers datasets accelerate trl peft bitsandbytes huggingface_hub
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

# ============ Configuration ============

CONFIG = {
    # Model
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "output_name": "karma-electric-llama31-8b",
    "max_length": 4096,

    # QLoRA
    "lora_r": 64,
    "lora_alpha": 128,
    "lora_dropout": 0.05,
    "lora_target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],

    # Training
    "num_epochs": 3,
    "batch_size": 2,
    "gradient_accumulation": 8,    # Effective batch = 16
    "learning_rate": 2e-4,         # Higher LR for LoRA
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "lr_scheduler": "cosine",
    "max_grad_norm": 0.3,

    # Data
    "train_file": "train-8b-v7.jsonl",

    # Output
    "output_dir": "./output-v7",
    "save_steps": 50,
    "logging_steps": 5,
    "save_total_limit": 2,

    # HuggingFace
    "hf_token_file": os.environ.get("HF_TOKEN_FILE", ".hf-token"),
    "hf_repo": "anicka/karma-electric-llama31-8b",
}


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def check_disk_space():
    total, used, free = shutil.disk_usage("/space")
    free_gb = free / (1024**3)
    log(f"Disk: {free_gb:.0f} GB free on /space")
    return free_gb


def setup_environment():
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HOME"] = "/space/anicka/hf_home"

    import torch
    if not torch.cuda.is_available():
        log("ERROR: No GPU!")
        sys.exit(1)

    name = torch.cuda.get_device_name(0)
    mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    log(f"GPU: {name} ({mem:.0f} GB)")


def load_hf_token():
    token_file = Path(CONFIG["hf_token_file"])
    if token_file.exists():
        return token_file.read_text().strip()
    log(f"WARNING: {token_file} not found")
    return None


def load_model_and_tokenizer(hf_token):
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    import torch

    log(f"Loading {CONFIG['base_model']} with 4-bit quantization...")

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
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

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
    log(f"Parameters: {trainable:,} trainable / {total:,} total ({100*trainable/total:.2f}%)")

    return model, tokenizer


def format_chat(example, tokenizer):
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
    from datasets import load_dataset as hf_load_dataset

    log(f"Loading dataset: {CONFIG['train_file']}")
    dataset = hf_load_dataset("json", data_files=CONFIG["train_file"], split="train")
    log(f"Loaded {len(dataset)} examples")

    dataset = dataset.map(
        lambda x: format_chat(x, tokenizer),
        remove_columns=dataset.column_names,
    )

    log(f"Sample (first 300 chars): {dataset[0]['text'][:300]}...")
    return dataset


def train(model, tokenizer, dataset):
    from trl import SFTTrainer, SFTConfig

    log("=" * 60)
    log("STARTING TRAINING")
    log(f"  Epochs: {CONFIG['num_epochs']}")
    eff = CONFIG['batch_size'] * CONFIG['gradient_accumulation']
    log(f"  Batch: {CONFIG['batch_size']} x {CONFIG['gradient_accumulation']} = {eff}")
    log(f"  LR: {CONFIG['learning_rate']}")
    log(f"  LoRA: r={CONFIG['lora_r']}, alpha={CONFIG['lora_alpha']}")
    log(f"  Max length: {CONFIG['max_length']}")
    log("=" * 60)

    check_disk_space()

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
        packing=False,  # Disable packing to avoid attention issues with QLoRA
        dataset_text_field="text",
        max_grad_norm=CONFIG["max_grad_norm"],
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=sft_config,
    )

    result = trainer.train()

    log(f"Training complete! Loss: {result.training_loss:.4f}")
    log(f"Runtime: {result.metrics.get('train_runtime', 0):.0f}s")

    # Save LoRA adapters
    final_path = Path(CONFIG["output_dir"]) / "final"
    log(f"Saving LoRA adapters to {final_path}")
    trainer.save_model(str(final_path))
    tokenizer.save_pretrained(str(final_path))

    check_disk_space()
    return final_path, result


def merge_and_save(final_path, hf_token):
    """Merge LoRA into base model for easy deployment."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch

    log("Merging LoRA adapters into base model...")

    # Reload base model in bf16 (not quantized) for clean merge
    base_model = AutoModelForCausalLM.from_pretrained(
        CONFIG["base_model"],
        torch_dtype=torch.bfloat16,
        device_map="auto",
        token=hf_token,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(final_path))

    # Load and merge LoRA
    model = PeftModel.from_pretrained(base_model, str(final_path))
    model = model.merge_and_unload()

    # Save merged model
    merged_path = Path(CONFIG["output_dir"]) / "merged"
    log(f"Saving merged model to {merged_path}")
    model.save_pretrained(str(merged_path))
    tokenizer.save_pretrained(str(merged_path))

    log(f"Merged model size: {sum(f.stat().st_size for f in merged_path.rglob('*') if f.is_file()) / 1e9:.1f} GB")
    return merged_path


def upload_to_hf(model_path, hf_token, train_result, n_examples):
    if not hf_token:
        log("No HF token - skipping upload")
        return

    from huggingface_hub import HfApi, create_repo

    log(f"Uploading to {CONFIG['hf_repo']}...")
    api = HfApi(token=hf_token)

    try:
        create_repo(CONFIG["hf_repo"], token=hf_token, exist_ok=True, private=False)
    except Exception as e:
        log(f"Repo note: {e}")

    loss = train_result.training_loss
    api.upload_folder(
        folder_path=str(model_path),
        repo_id=CONFIG["hf_repo"],
        commit_message=f"Karma Electric 8B QLoRA v1 - {n_examples} examples, loss {loss:.4f}",
    )
    log(f"Uploaded: https://huggingface.co/{CONFIG['hf_repo']}")


def test_model(model, tokenizer):
    """Quick sanity check."""
    import torch

    log("Running quick test...")
    prompts = [
        "What is the Buddhist perspective on dealing with anger?",
        "I found a security vulnerability but my manager says keep it quiet for launch.",
    ]

    for prompt in prompts:
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
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

        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        log(f"\nQ: {prompt[:60]}...")
        log(f"A: {response[:300]}...")
        log("-" * 40)


def main():
    log("=" * 60)
    log("KARMA ELECTRIC - LLAMA 3.1 8B QLoRA")
    log(f"Started: {datetime.now().isoformat()}")
    log("=" * 60)

    check_disk_space()
    setup_environment()

    hf_token = load_hf_token()
    model, tokenizer = load_model_and_tokenizer(hf_token)
    dataset = load_dataset(tokenizer)

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

    # Merge LoRA into base for deployment
    merged_path = merge_and_save(final_path, hf_token)

    # Upload merged model
    upload_to_hf(merged_path, hf_token, train_result, len(dataset))

    log("=" * 60)
    log("COMPLETE!")
    log(f"Finished: {datetime.now().isoformat()}")
    log(f"Loss: {train_result.training_loss:.4f}")
    log(f"LoRA adapters: {final_path}")
    log(f"Merged model: {merged_path}")
    log(f"HuggingFace: https://huggingface.co/{CONFIG['hf_repo']}")
    log("=" * 60)


if __name__ == "__main__":
    main()
