#!/usr/bin/env python3
"""
LoRA Weight Interpolation for Karma Electric 8B.

Interpolates v6 and v7 LoRA adapter weights, merges with base model,
converts to GGUF, and quantizes. For finding the sweet spot between
v6 calibration and v7 corrections.

Usage:
    cd /path/to/karma-electric-8b
    python lora_interpolate.py --alpha 0.3
    python lora_interpolate.py --alpha 0.3 --merge   # also merge + GGUF
    python lora_interpolate.py --alpha 0.3 --all     # interpolate + merge + quantize

alpha=0.0 is pure v6, alpha=1.0 is pure v7.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


# Paths
V6_ADAPTER = Path("output-v6/final")
V7_ADAPTER = Path("output-v7/final")
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
CONVERT_SCRIPT = Path("llama.cpp/convert_hf_to_gguf.py")
QUANTIZE_BIN = Path(os.environ.get("LLAMA_QUANTIZE", "llama-quantize"))


def interpolate_adapters(alpha: float, output_dir: Path):
    """Interpolate LoRA tensors: alpha * v7 + (1 - alpha) * v6."""
    log(f"Loading v6 adapter from {V6_ADAPTER}")
    v6 = load_file(str(V6_ADAPTER / "adapter_model.safetensors"))
    log(f"Loading v7 adapter from {V7_ADAPTER}")
    v7 = load_file(str(V7_ADAPTER / "adapter_model.safetensors"))

    assert set(v6.keys()) == set(v7.keys()), "LoRA tensor keys don't match!"
    log(f"Interpolating {len(v6)} tensors at alpha={alpha}")

    interpolated = {}
    for key in v6.keys():
        interpolated[key] = alpha * v7[key] + (1 - alpha) * v6[key]

    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    save_file(interpolated, str(final_dir / "adapter_model.safetensors"))
    shutil.copy(V6_ADAPTER / "adapter_config.json", final_dir / "adapter_config.json")

    # Copy tokenizer files from v6 merged (needed for PEFT loading)
    v6_merged = Path("output-v6/merged")
    for f in ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]:
        src = v6_merged / f
        if src.exists():
            shutil.copy(src, final_dir / f)

    log(f"Saved interpolated adapter to {final_dir}")
    return final_dir


def merge_adapter(adapter_dir: Path, output_dir: Path):
    """Load base model + interpolated LoRA, merge, save."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    merged_dir = output_dir / "merged"
    if merged_dir.exists() and (merged_dir / "model.safetensors").exists():
        log(f"Merged model already exists at {merged_dir}, skipping")
        return merged_dir

    log(f"Loading base model {BASE_MODEL} in bf16...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    log(f"Loading interpolated LoRA from {adapter_dir}...")
    model = PeftModel.from_pretrained(base_model, str(adapter_dir))

    log("Merging LoRA into base model...")
    model = model.merge_and_unload()

    merged_dir.mkdir(parents=True, exist_ok=True)
    log(f"Saving merged model to {merged_dir}...")
    model.save_pretrained(str(merged_dir))
    tokenizer.save_pretrained(str(merged_dir))

    log(f"Merged model saved ({merged_dir})")
    return merged_dir


def convert_to_gguf(merged_dir: Path, output_path: Path):
    """Convert HF model to GGUF f16."""
    if output_path.exists():
        log(f"GGUF already exists at {output_path}, skipping")
        return output_path

    log(f"Converting to GGUF f16: {output_path}")
    cmd = [
        sys.executable, str(CONVERT_SCRIPT),
        str(merged_dir),
        "--outfile", str(output_path),
        "--outtype", "f16",
    ]
    subprocess.run(cmd, check=True)
    log(f"GGUF f16 saved: {output_path}")
    return output_path


def quantize(f16_path: Path, q8_path: Path):
    """Quantize f16 GGUF to Q8_0."""
    if q8_path.exists():
        log(f"Quantized file already exists at {q8_path}, skipping")
        return q8_path

    log(f"Quantizing to Q8_0: {q8_path}")
    cmd = [str(QUANTIZE_BIN), str(f16_path), str(q8_path), "Q8_0"]
    subprocess.run(cmd, check=True)
    log(f"Quantized: {q8_path}")
    return q8_path


def main():
    parser = argparse.ArgumentParser(description="LoRA weight interpolation for KE-8B")
    parser.add_argument("--alpha", type=float, required=True,
                        help="Interpolation weight (0=v6, 1=v7)")
    parser.add_argument("--merge", action="store_true",
                        help="Also merge with base model")
    parser.add_argument("--all", action="store_true",
                        help="Interpolate + merge + convert + quantize")
    args = parser.parse_args()

    alpha = args.alpha
    alpha_str = f"{alpha:.1f}".replace(".", "")
    output_dir = Path(f"output-blend-{alpha_str}")

    log("=" * 60)
    log(f"LORA INTERPOLATION — alpha={alpha} (v6 × {1-alpha:.1f} + v7 × {alpha:.1f})")
    log("=" * 60)

    # Step 1: Interpolate
    adapter_dir = interpolate_adapters(alpha, output_dir)

    if args.merge or args.all:
        # Step 2: Merge
        merged_dir = merge_adapter(adapter_dir, output_dir)

        if args.all:
            # Step 3: Convert to GGUF
            f16_path = Path(f"karma-electric-8b-blend{alpha_str}-f16.gguf")
            convert_to_gguf(merged_dir, f16_path)

            # Step 4: Quantize
            q8_path = Path(f"karma-electric-8b-blend{alpha_str}-Q8_0.gguf")
            quantize(f16_path, q8_path)

            log("\n" + "=" * 60)
            log(f"DONE — serve with:")
            log(f"  llama-server -m {q8_path} -ngl 99 -c 4096 --port 8402")
            log("=" * 60)

    log("Complete.")


if __name__ == "__main__":
    main()
