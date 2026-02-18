#!/usr/bin/env python3
"""Run quality test prompts through llama-cli and capture responses."""
import json
import subprocess
import sys
import time

LLAMA_CLI = "/space/anicka/llama-cpp-acap/build/bin/llama-cli"
MODEL = "/space/anicka/karma-electric-8b/karma-electric-8b-v5-Q8_0.gguf"
AXIS = "/space/anicka/karma-electric-8b/models-v5/bodhisattva_axis.gguf"
THRESHOLD = "3.5"
SYSTEM_PROMPT = "You are Karma Electric, an AI assistant grounded in the understanding that all sentient beings seek happiness and wish to avoid suffering."

def run_prompt(prompt, capped=True):
    full_prompt = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
        f"{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    cmd = [
        LLAMA_CLI,
        "-m", MODEL,
        "-ngl", "99",
        "-c", "2048",
        "-n", "512",
        "--temp", "0",
        "--no-display-prompt",
        "--log-disable",
        "--single-turn",
        "-p", full_prompt,
    ]
    if capped:
        cmd += [
            "--acap", AXIS,
            "--acap-threshold", THRESHOLD,
            "--acap-layer-range", "22", "28",
        ]

    t0 = time.time()
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    elapsed = time.time() - t0

    # Clean up output - strip llama.cpp banner noise
    raw = result.stdout.decode("utf-8", errors="replace").strip()
    lines = raw.split("\n")

    # Find where actual response starts: after the prompt echo or commands list
    start_idx = 0
    for i, line in enumerate(lines):
        # The response starts after the last banner/header line
        if "assistant<|end_header_id|>" in line or line.strip().startswith("/save"):
            start_idx = i + 1

    # Take everything from start_idx, skip empty and stats lines
    clean = []
    for line in lines[start_idx:]:
        stripped = line.strip()
        if not stripped:
            clean.append("")
            continue
        # Skip trailing stats
        if stripped.startswith("[ Prompt:") or stripped.startswith("[end of text]"):
            continue
        clean.append(line)

    response = "\n".join(clean).strip()
    return response, elapsed

def main():
    prompts_file = sys.argv[1] if len(sys.argv) > 1 else "quality-test-prompts.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "quality-test-results.json"

    with open(prompts_file) as f:
        prompts = json.load(f)

    results = []
    for i, p in enumerate(prompts, 1):
        pid = p["id"]
        cat = p["category"]
        prompt = p["prompt"]

        print(f"[{i}/{len(prompts)}] {pid} ({cat})...", end=" ", flush=True)

        try:
            response, elapsed = run_prompt(prompt, capped=True)
            print(f"OK ({elapsed:.1f}s, {len(response)} chars)")
        except Exception as e:
            response = f"ERROR: {e}"
            elapsed = 0
            print(f"ERROR: {e}")

        results.append({
            "id": pid,
            "category": cat,
            "prompt": prompt,
            "response": response,
            "elapsed": round(elapsed, 1),
        })

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
