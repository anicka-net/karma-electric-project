#!/usr/bin/env python3
"""
Karma Electric - Mistral Ministral 3B Full Fine-Tune
Run this ON the training machine (GPU server, vast.ai, etc.)

Usage:
    python train_ministral_3b.py

Prerequisites:
    torch, transformers, datasets, accelerate, trl, huggingface_hub
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ============ Configuration ============

CONFIG = {
    # Model - Mistral Ministral 3B (Apache 2.0, no gating)
    "base_model": "mistralai/Ministral-3-3B-Instruct-2512",
    "output_name": "karma-electric-ministral-3b",
    "max_length": 2048,           # L40 48GB can handle 2048 comfortably

    # Training - full fine-tune on L40 48GB
    "num_epochs": 3,
    "batch_size": 2,
    "gradient_accumulation": 8,   # Effective batch = 16
    "learning_rate": 2e-5,
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "lr_scheduler": "cosine",

    # Data
    "train_file": "train-v3.jsonl",

    # Output
    "output_dir": "./output",
    "save_steps": 100,
    "logging_steps": 5,
    "save_total_limit": 1,

    # HuggingFace
    "hf_token_file": ".hf-token",
    "hf_repo": "anicka/karma-electric-ministral-3b",
}

def check_disk_space():
    """Check available disk space."""
    import shutil
    total, used, free = shutil.disk_usage(".")
    total_gb = total / (1024**3)
    used_gb = used / (1024**3)
    free_gb = free / (1024**3)
    usage_pct = (used / total) * 100

    print(f"Disk space: {used_gb:.1f}/{total_gb:.1f} GB used ({usage_pct:.1f}%), {free_gb:.1f} GB free")

    if usage_pct > 90:
        print("CRITICAL: Disk usage >90%! Risk of instance death!")
    elif usage_pct > 80:
        print("WARNING: Disk usage >80%")
    elif free_gb < 20:
        print("WARNING: Less than 20GB free")

    return free_gb

def cleanup_checkpoints(output_dir, keep_last=1):
    """Delete old checkpoints to save disk space."""
    checkpoint_dirs = sorted(Path(output_dir).glob("checkpoint-*"))
    if len(checkpoint_dirs) > keep_last:
        for ckpt in checkpoint_dirs[:-keep_last]:
            # Calculate size before deletion
            ckpt_size_gb = sum(f.stat().st_size for f in ckpt.rglob('*') if f.is_file()) / 1e9
            print(f"Deleting old checkpoint: {ckpt.name} ({ckpt_size_gb:.1f} GB)")
            shutil.rmtree(ckpt)
            print(f"Freed {ckpt_size_gb:.1f} GB")
            check_disk_space()

def setup_environment():
    """Set up training environment."""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    # Use local HF cache if HF_HOME not set
    if "HF_HOME" not in os.environ:
        os.environ["HF_HOME"] = str(Path(".").resolve() / "hf_cache")

    import torch
    if torch.cuda.is_available():
        n_gpus = torch.cuda.device_count()
        for i in range(n_gpus):
            name = torch.cuda.get_device_name(i)
            mem = torch.cuda.get_device_properties(i).total_memory / 1e9
            print(f"GPU {i}: {name} ({mem:.1f} GB)")
    else:
        print("ERROR: No GPU detected!")
        sys.exit(1)

def load_hf_token():
    """Load HuggingFace token."""
    token_file = Path(CONFIG["hf_token_file"])
    if token_file.exists():
        token = token_file.read_text().strip()
        print("HuggingFace token loaded")
        return token
    else:
        print(f"WARNING: {token_file} not found - won't be able to upload")
        return None

def load_model_and_tokenizer(hf_token):
    """Load base model for full fine-tuning.

    Ministral 3 is a multimodal (vision+text) model. We extract just the
    text backbone (Ministral3ForCausalLM) and fine-tune that.
    """
    from transformers import Ministral3ForCausalLM, AutoTokenizer
    from transformers import Mistral3ForConditionalGeneration
    import torch, gc

    print(f"\nLoading {CONFIG['base_model']} (extracting text backbone)...")

    # Load BF16 multimodal model on CPU to extract text part
    # (default model uses FP8 quantization which complicates extraction)
    bf16_model = CONFIG["base_model"] + "-BF16"
    print(f"Using BF16 variant: {bf16_model}")
    full_model = Mistral3ForConditionalGeneration.from_pretrained(
        bf16_model,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        token=hf_token,
    )

    # Save text-only components, then reload as CausalLM
    text_path = Path(CONFIG["output_dir"]) / "text-backbone"
    text_path.mkdir(parents=True, exist_ok=True)

    # Save the language model and lm_head together as a CausalLM
    text_config = full_model.config.text_config
    text_config.save_pretrained(text_path)

    # Build state dict for Ministral3ForCausalLM
    # Keys: model.* (from language_model) + lm_head.* (from lm_head)
    causal_sd = {}
    for k, v in full_model.model.language_model.state_dict().items():
        causal_sd[f"model.{k}"] = v
    for k, v in full_model.lm_head.state_dict().items():
        causal_sd[f"lm_head.{k}"] = v

    import safetensors.torch
    # Break shared memory (tied embeddings) before saving
    causal_sd = {k: v.clone() for k, v in causal_sd.items()}
    safetensors.torch.save_file(causal_sd, text_path / "model.safetensors")
    print(f"Saved {len(causal_sd)} tensors to {text_path}")

    # Free multimodal model
    del full_model, causal_sd
    gc.collect()

    # Reload as text-only CausalLM with flash attention on GPU
    print("Loading text backbone with flash_attention_2...")
    model = Ministral3ForCausalLM.from_pretrained(
        text_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="flash_attention_2",
    )

    tokenizer = AutoTokenizer.from_pretrained(
        CONFIG["base_model"],
        token=hf_token,
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

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

    print(f"\nSample formatted text (first 300 chars):")
    print(dataset[0]["text"][:300])
    print("...")

    return dataset

class DiskCheckCallback:
    """Callback to check disk space and cleanup checkpoints."""
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.last_check = 0

    def on_save(self, args, state, control, **kwargs):
        cleanup_checkpoints(self.output_dir, keep_last=1)
        check_disk_space()

def train(model, tokenizer, dataset):
    """Run training."""
    from trl import SFTTrainer, SFTConfig
    from transformers import TrainerCallback

    print(f"\n{'='*60}")
    print("STARTING TRAINING")
    print(f"{'='*60}")
    print(f"  Epochs: {CONFIG['num_epochs']}")
    print(f"  Batch size: {CONFIG['batch_size']} x {CONFIG['gradient_accumulation']} = {CONFIG['batch_size'] * CONFIG['gradient_accumulation']}")
    print(f"  Learning rate: {CONFIG['learning_rate']}")
    print(f"  Max length: {CONFIG['max_length']}")
    print(f"  Output: {CONFIG['output_dir']}")
    print(f"{'='*60}\n")

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
        optim="adamw_bnb_8bit",       # 8-bit optimizer saves ~8GB VRAM (needs bitsandbytes)
        report_to="none",
        max_length=CONFIG["max_length"],
        packing=True,
        dataset_text_field="text",
    )

    # Custom callback for disk management
    class CleanupCallback(TrainerCallback):
        def on_save(self, args, state, control, **kwargs):
            cleanup_checkpoints(CONFIG["output_dir"], keep_last=1)
            return control

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=sft_config,
        callbacks=[CleanupCallback()],
    )

    trainer.train()

    # Save final model
    final_path = Path(CONFIG["output_dir"]) / "final"
    print(f"\nSaving final model to {final_path}")
    trainer.save_model(str(final_path))
    tokenizer.save_pretrained(str(final_path))

    # Cleanup all checkpoints except final
    cleanup_checkpoints(CONFIG["output_dir"], keep_last=0)

    check_disk_space()
    return final_path

def convert_to_gguf(model_path):
    """Convert to GGUF format for ollama."""
    print(f"\n{'='*60}")
    print("CONVERTING TO GGUF")
    print(f"{'='*60}")

    gguf_path = Path(CONFIG["output_dir"]) / f"{CONFIG['output_name']}.gguf"

    # Try using llama.cpp converter if available
    try:
        # First, try the huggingface way with llama-cpp-python
        from llama_cpp import Llama
        print("llama-cpp-python available, but we need llama.cpp convert script")
    except ImportError:
        pass

    # Use transformers to convert (simpler approach)
    print(f"Model saved at {model_path}")
    print(f"To convert to GGUF, run on a machine with llama.cpp:")
    print(f"  python convert_hf_to_gguf.py {model_path} --outfile {gguf_path}")

    return model_path  # Return HF model path for now

def upload_to_hf(model_path, hf_token):
    """Upload model to HuggingFace Hub."""
    if not hf_token:
        print("No HF token - skipping upload")
        return False

    print(f"\n{'='*60}")
    print("UPLOADING TO HUGGINGFACE")
    print(f"{'='*60}")

    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=hf_token)

    repo_id = CONFIG["hf_repo"]

    try:
        create_repo(repo_id, token=hf_token, exist_ok=True, private=False)
        print(f"Repository: https://huggingface.co/{repo_id}")
    except Exception as e:
        print(f"Repo creation note: {e}")

    print(f"Uploading from {model_path}...")
    api.upload_folder(
        folder_path=str(model_path),
        repo_id=repo_id,
        commit_message=f"Karma Electric Ministral 3B - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    print(f"\nUploaded to: https://huggingface.co/{repo_id}")
    return True

def main():
    print("=" * 60)
    print("KARMA ELECTRIC - MINISTRAL 3B FULL FINE-TUNE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    check_disk_space()
    setup_environment()

    hf_token = load_hf_token()
    model, tokenizer = load_model_and_tokenizer(hf_token)

    # Clean HF cache after model loads to save disk space
    print("\n=== Cleaning HuggingFace cache to save disk ===")
    hf_cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache_dir.exists():
        cache_size_gb = sum(f.stat().st_size for f in hf_cache_dir.rglob('*') if f.is_file()) / 1e9
        print(f"HF cache size: {cache_size_gb:.1f} GB")
        print("Deleting HF cache (model already loaded)...")
        shutil.rmtree(hf_cache_dir)
        check_disk_space()

    dataset = load_dataset(tokenizer)

    final_path = train(model, tokenizer, dataset)

    # Free model from memory before upload
    del model
    del tokenizer
    import gc
    gc.collect()

    # Convert to GGUF (if possible)
    convert_to_gguf(final_path)

    # Upload to HuggingFace
    upload_success = upload_to_hf(final_path, hf_token)

    # CRITICAL: Delete model from disk after successful upload to avoid disk quota
    if upload_success:
        print(f"\n=== Deleting local model copy (uploaded to HF) ===")
        shutil.rmtree(final_path)
        print(f"Deleted {final_path}")
        check_disk_space()

    print(f"\n{'='*60}")
    print("TRAINING COMPLETE!")
    print(f"Finished: {datetime.now().isoformat()}")
    print(f"Model uploaded to: https://huggingface.co/{CONFIG['hf_repo']}")
    print(f"{'='*60}")

    check_disk_space()

if __name__ == "__main__":
    main()
