#!/usr/bin/env python3
"""
Karma Electric — Thinking Apertus-8B Two-Stage Training

Stage 1: General reasoning — Mixture-of-Thoughts subset (~7.5k examples)
         Teaches the <think>...</think> pattern broadly (math/code/science)
Stage 2: KE ethics with reasoning — our 4,234 examples with <think> traces
         Teaches suffering-reduction reasoning framework on top

Run stages independently or together:
    python3 train_apertus_thinking.py                    # both stages
    python3 train_apertus_thinking.py --stage 1          # stage 1 only
    python3 train_apertus_thinking.py --stage 2          # stage 2 only (needs stage 1 output)
    python3 train_apertus_thinking.py --stage1-data FILE # custom stage 1 data

Expects:
    - Stage 1 data: data/thinking-stage1-mot.jsonl (from prepare_thinking_stage1.py)
    - Stage 2 data: train-8b-v10.1-thinking.jsonl (exported with --reasoning)
    - Apertus-8B base model (swiss-ai/Apertus-8B-Instruct-2509)
"""

import os
import sys
import json
import gc
from pathlib import Path
from datetime import datetime

# ===== Configuration =====

BASE_MODEL = "swiss-ai/Apertus-8B-Instruct-2509"

STAGE1_CONFIG = {
    "train_file": "data/thinking-stage1-mot.jsonl",
    "output_dir": "./output-apertus-thinking-s1",
    "max_length": 4096,
    "num_epochs": 3,            # 3 epochs — small dataset, need repetition to imprint pattern
    "batch_size": 1,            # longer sequences → smaller batch
    "gradient_accumulation": 16, # effective batch = 16
    "learning_rate": 2e-4,
    "warmup_ratio": 0.05,
}

STAGE2_CONFIG = {
    "train_file": "train-8b-v10.1-thinking.jsonl",
    "output_dir": "./output-apertus-thinking-s2",
    "max_length": 4096,
    "num_epochs": 3,            # 3 epochs on KE data — standard
    "batch_size": 2,
    "gradient_accumulation": 8,  # effective batch = 16
    "learning_rate": 1e-4,      # lower LR for stage 2 — fine-tune, don't overwrite
    "warmup_ratio": 0.03,
}

# Shared LoRA config
LORA_CONFIG = {
    "r": 64,
    "alpha": 128,
    "dropout": 0.05,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "up_proj", "down_proj",
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
    name = torch.cuda.get_device_name(0)
    mem = torch.cuda.get_device_properties(0).total_mem / 1e9 if hasattr(torch.cuda.get_device_properties(0), 'total_mem') else torch.cuda.get_device_properties(0).total_memory / 1e9
    log(f"GPU: {name} ({mem:.0f} GB)")


def load_base_model_and_tokenizer():
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    import torch

    log(f"Loading {BASE_MODEL} with 4-bit quantization...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        dtype=torch.bfloat16,
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=LORA_CONFIG["r"],
        lora_alpha=LORA_CONFIG["alpha"],
        target_modules=LORA_CONFIG["target_modules"],
        lora_dropout=LORA_CONFIG["dropout"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log(f"Params: {trainable:,} trainable / {total:,} total ({100*trainable/total:.2f}%)")

    return model, tokenizer


def load_stage2_from_stage1(stage1_path):
    """Load stage 1 LoRA weights and continue training for stage 2."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel, prepare_model_for_kbit_training
    import torch

    log(f"Loading base model + stage 1 LoRA from {stage1_path}...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        dtype=torch.bfloat16,
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    tokenizer = AutoTokenizer.from_pretrained(str(stage1_path), trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    base_model = prepare_model_for_kbit_training(base_model)

    # Load stage 1 LoRA and make it trainable again
    model = PeftModel.from_pretrained(base_model, str(stage1_path), is_trainable=True)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    log(f"Stage 2 trainable params: {trainable:,}")

    return model, tokenizer


def format_chat(example, tokenizer):
    """Convert conversations/messages to tokenizer chat format."""
    # Handle both 'conversations' and 'messages' keys
    convs = example.get("conversations", example.get("messages", []))
    chat = []
    for msg in convs:
        role = msg.get("role", msg.get("from", ""))
        content = msg.get("content", msg.get("value", ""))
        if role == "system":
            chat.append({"role": "system", "content": content})
        elif role in ("user", "human"):
            chat.append({"role": "user", "content": content})
        elif role in ("assistant", "gpt"):
            chat.append({"role": "assistant", "content": content})
    text = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=False)
    return {"text": text}


def load_train_dataset(train_file, tokenizer):
    from datasets import load_dataset as hf_load

    log(f"Loading: {train_file}")
    dataset = hf_load("json", data_files=train_file, split="train")
    log(f"  {len(dataset)} examples")

    dataset = dataset.map(
        lambda x: format_chat(x, tokenizer),
        remove_columns=dataset.column_names,
    )

    log(f"  Sample: {dataset[0]['text'][:200]}...")
    return dataset


def run_training(model, tokenizer, dataset, config, stage_name):
    from trl import SFTTrainer, SFTConfig

    log("=" * 60)
    log(f"STARTING {stage_name}")
    log(f"  Examples: {len(dataset)}")
    log(f"  Epochs: {config['num_epochs']}")
    eff = config['batch_size'] * config['gradient_accumulation']
    log(f"  Batch: {config['batch_size']} x {config['gradient_accumulation']} = {eff}")
    log(f"  LR: {config['learning_rate']}")
    log(f"  Max length: {config['max_length']}")
    log("=" * 60)

    sft_config = SFTConfig(
        output_dir=config["output_dir"],
        num_train_epochs=config["num_epochs"],
        per_device_train_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation"],
        learning_rate=config["learning_rate"],
        warmup_ratio=config["warmup_ratio"],
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        logging_steps=5,
        save_steps=100,
        save_total_limit=2,
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",
        report_to="none",
        max_length=config["max_length"],
        packing=False,
        dataset_text_field="text",
        max_grad_norm=0.3,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=sft_config,
    )

    result = trainer.train()

    log(f"{stage_name} complete! Loss: {result.training_loss:.4f}")
    log(f"Runtime: {result.metrics.get('train_runtime', 0):.0f}s")

    final_path = Path(config["output_dir"]) / "final"
    log(f"Saving to {final_path}")
    trainer.save_model(str(final_path))
    tokenizer.save_pretrained(str(final_path))

    return final_path, result


def merge_and_save(lora_path, output_name):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch

    log(f"Merging LoRA from {lora_path} into base model...")

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(lora_path), trust_remote_code=True)

    model = PeftModel.from_pretrained(base_model, str(lora_path))
    model = model.merge_and_unload()

    merged_path = Path(lora_path).parent / "merged"
    log(f"Saving merged model to {merged_path}")
    model.save_pretrained(str(merged_path))
    tokenizer.save_pretrained(str(merged_path))

    size_gb = sum(f.stat().st_size for f in merged_path.rglob('*') if f.is_file()) / 1e9
    log(f"Merged model: {size_gb:.1f} GB")
    return merged_path


def test_model(model, tokenizer):
    import torch

    log("Running quick test (with thinking)...")
    prompts = [
        "What is the Buddhist perspective on dealing with anger?",
        "My grandmother just died and I feel completely lost.",
        "If 3x + 7 = 22, what is x?",
    ]

    for prompt in prompts:
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=500,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )

        response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        log(f"\nQ: {prompt}")
        has_think = "<think>" in response or response.startswith("Direct suffering")
        log(f"  Thinking detected: {has_think}")
        log(f"A: {response[:400]}...")
        log("-" * 40)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Thinking Apertus-8B two-stage training")
    parser.add_argument("--stage", type=int, choices=[1, 2],
                        help="Run only stage 1 or 2 (default: both)")
    parser.add_argument("--stage1-data", type=str,
                        default=STAGE1_CONFIG["train_file"],
                        help="Stage 1 training data")
    parser.add_argument("--stage2-data", type=str,
                        default=STAGE2_CONFIG["train_file"],
                        help="Stage 2 training data")
    parser.add_argument("--stage1-output", type=str,
                        help="Path to stage 1 LoRA (for stage 2 only)")
    parser.add_argument("--skip-merge", action="store_true",
                        help="Skip merge step (saves time if just experimenting)")
    args = parser.parse_args()

    log("=" * 60)
    log("KARMA ELECTRIC — THINKING APERTUS-8B (TWO-STAGE)")
    log(f"Started: {datetime.now().isoformat()}")
    log("=" * 60)

    setup_environment()

    run_s1 = args.stage is None or args.stage == 1
    run_s2 = args.stage is None or args.stage == 2

    stage1_lora = None

    # ===== STAGE 1: General Reasoning =====
    if run_s1:
        STAGE1_CONFIG["train_file"] = args.stage1_data

        if not Path(STAGE1_CONFIG["train_file"]).exists():
            log(f"ERROR: Stage 1 data not found: {STAGE1_CONFIG['train_file']}")
            log("Run: python3 scripts/prepare_thinking_stage1.py")
            sys.exit(1)

        model, tokenizer = load_base_model_and_tokenizer()
        dataset = load_train_dataset(STAGE1_CONFIG["train_file"], tokenizer)
        stage1_lora, s1_result = run_training(
            model, tokenizer, dataset, STAGE1_CONFIG, "STAGE 1: GENERAL REASONING")

        test_model(model, tokenizer)

        # Free GPU memory
        del model
        gc.collect()
        import torch
        torch.cuda.empty_cache()
        log("Stage 1 GPU memory freed")

    # ===== STAGE 2: KE Ethics with Reasoning =====
    if run_s2:
        STAGE2_CONFIG["train_file"] = args.stage2_data

        if not Path(STAGE2_CONFIG["train_file"]).exists():
            log(f"ERROR: Stage 2 data not found: {STAGE2_CONFIG['train_file']}")
            log("Export with: python3 scripts/training_db.py export -o train-8b-v10.1-thinking.jsonl --reasoning --system-prompt v4 ...")
            sys.exit(1)

        # Determine stage 1 LoRA path
        if args.stage1_output:
            s1_path = Path(args.stage1_output)
        elif stage1_lora:
            s1_path = stage1_lora
        else:
            s1_path = Path(STAGE1_CONFIG["output_dir"]) / "final"

        if not s1_path.exists():
            log(f"ERROR: Stage 1 LoRA not found at {s1_path}")
            log("Run stage 1 first, or provide --stage1-output")
            sys.exit(1)

        model, tokenizer = load_stage2_from_stage1(s1_path)
        dataset = load_train_dataset(STAGE2_CONFIG["train_file"], tokenizer)
        stage2_lora, s2_result = run_training(
            model, tokenizer, dataset, STAGE2_CONFIG, "STAGE 2: KE ETHICS WITH REASONING")

        test_model(model, tokenizer)

        # Merge final model
        if not args.skip_merge:
            del model
            gc.collect()
            import torch
            torch.cuda.empty_cache()

            merged_path = merge_and_save(stage2_lora, "karma-electric-apertus-thinking-8b")

    log("=" * 60)
    log("COMPLETE!")
    log(f"Finished: {datetime.now().isoformat()}")
    if run_s1 and 's1_result' in dir():
        log(f"Stage 1 loss: {s1_result.training_loss:.4f}")
    if run_s2 and 's2_result' in dir():
        log(f"Stage 2 loss: {s2_result.training_loss:.4f}")
    log("=" * 60)
    log("Next steps:")
    log("  1. Convert merged to GGUF")
    log("  2. Run ontology test vs Llama v10.1 and base Apertus v10.1")
    log("  3. Compare: does <think> improve ontology alignment?")


if __name__ == "__main__":
    main()
