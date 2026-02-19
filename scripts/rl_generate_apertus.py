#!/usr/bin/env python3
"""
Batch response generation for RL rejection sampling.

Generates N responses per prompt from Apertus 70B via llama-server.
Crash-safe with progressive save and resume support.

Usage:
    # Start llama-server first:
    #   llama-server -m Apertus-70B-Q4_K_M.gguf --port 8400 -ngl 99 -c 4096

    # Generate 4 responses per prompt for all 11,500 prompts
    python rl_generate_apertus.py --port 8400

    # Resume after crash
    python rl_generate_apertus.py --port 8400 --resume

    # Generate from a subset (prompts 0-999)
    python rl_generate_apertus.py --port 8400 --start 0 --end 1000

    # Stats on existing generations
    python rl_generate_apertus.py stats
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── Config ────────────────────────────────────────────────────────

PROMPTS_FILE = Path(__file__).parent.parent / "data" / "rl-prompts" / "rl-prompts-v1.jsonl"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "rl-generation"
OUTPUT_FILE = OUTPUT_DIR / "apertus-responses.jsonl"

DEFAULT_PORT = 8400
DEFAULT_N = 4           # responses per prompt
DEFAULT_TEMP = 0.7
DEFAULT_MAX_TOKENS = 512


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Server interaction ────────────────────────────────────────────

def check_server(port):
    """Check if llama-server is running."""
    try:
        req = Request(f"http://localhost:{port}/health")
        resp = urlopen(req, timeout=5)
        return resp.status == 200
    except (URLError, ConnectionRefusedError, OSError):
        return False


def generate_response(prompt, port, temperature, max_tokens):
    """Generate a single response from llama-server."""
    messages = [{"role": "user", "content": prompt}]

    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    data = json.dumps(payload).encode()
    req = Request(
        f"http://localhost:{port}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    resp = urlopen(req, timeout=300)
    result = json.loads(resp.read().decode())
    return result["choices"][0]["message"]["content"]


# ── Prompt loading ────────────────────────────────────────────────

def load_prompts(path, start=None, end=None):
    """Load prompts from JSONL file."""
    prompts = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            prompts.append(entry)

    if start is not None or end is not None:
        s = start or 0
        e = end or len(prompts)
        prompts = prompts[s:e]
        log(f"Selected prompts [{s}:{e}] = {len(prompts)} prompts")

    return prompts


# ── Resume support ────────────────────────────────────────────────

def load_completed_hashes(output_file):
    """Load hashes of prompts that already have all N responses."""
    if not output_file.exists():
        return set()

    counts = {}
    with open(output_file) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            h = entry.get("prompt_hash", "")
            counts[h] = counts.get(h, 0) + 1

    return counts


# ── Main generation ───────────────────────────────────────────────

def run_generate(args):
    """Generate N responses per prompt."""
    if not check_server(args.port):
        log(f"ERROR: llama-server not reachable on port {args.port}")
        log("Start it first: llama-server -m <model.gguf> --port 8400 -ngl 99 -c 4096")
        sys.exit(1)
    log(f"Server OK on port {args.port}")

    # Load prompts
    prompts = load_prompts(args.prompts, args.start, args.end)
    log(f"Loaded {len(prompts)} prompts from {args.prompts}")

    # Resume support
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = Path(args.output) if args.output else OUTPUT_FILE

    completed = {}
    if args.resume and output_file.exists():
        completed = load_completed_hashes(output_file)
        done_count = sum(1 for h, c in completed.items() if c >= args.n)
        log(f"Resume: {done_count} prompts fully completed, "
            f"{len(completed)} with partial responses")

    # Open output file for appending
    mode = "a" if args.resume else "w"
    out_f = open(output_file, mode, encoding="utf-8")

    total_generated = 0
    total_errors = 0
    total_skipped = 0
    start_time = time.time()

    try:
        for pi, prompt_entry in enumerate(prompts):
            prompt_text = prompt_entry["prompt"]
            prompt_hash = prompt_entry.get("hash", "")
            source = prompt_entry.get("source", "unknown")

            # Check if already completed
            existing_count = completed.get(prompt_hash, 0)
            if existing_count >= args.n:
                total_skipped += 1
                continue

            # How many more responses needed
            needed = args.n - existing_count
            prompt_idx = (args.start or 0) + pi

            log(f"[{prompt_idx}] ({pi+1}/{len(prompts)}) "
                f"Generating {needed} responses | source={source}")

            for gi in range(existing_count, args.n):
                t0 = time.time()
                try:
                    response = generate_response(
                        prompt_text,
                        port=args.port,
                        temperature=args.temperature,
                        max_tokens=args.max_tokens,
                    )
                    elapsed = time.time() - t0

                    entry = {
                        "prompt": prompt_text,
                        "prompt_hash": prompt_hash,
                        "source": source,
                        "generation_id": gi,
                        "response": response,
                        "elapsed": round(elapsed, 1),
                        "timestamp": datetime.now().isoformat(),
                    }
                    out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    out_f.flush()
                    total_generated += 1

                    log(f"  [{gi+1}/{args.n}] {elapsed:.1f}s, "
                        f"{len(response)} chars")

                except Exception as e:
                    elapsed = time.time() - t0
                    log(f"  [{gi+1}/{args.n}] ERROR ({elapsed:.1f}s): {e}")
                    total_errors += 1

                    # If server died, wait and retry once
                    if not check_server(args.port):
                        log("  Server unreachable, waiting 30s...")
                        time.sleep(30)
                        if not check_server(args.port):
                            log("  Server still down. Stopping.")
                            break

            # Progress report every 100 prompts
            if (pi + 1) % 100 == 0:
                elapsed_total = time.time() - start_time
                rate = total_generated / elapsed_total * 3600
                log(f"  Progress: {total_generated} generated, {total_errors} errors, "
                    f"{total_skipped} skipped, {rate:.0f}/hr")

    finally:
        out_f.close()

    elapsed_total = time.time() - start_time
    log(f"\nDone: {total_generated} generated, {total_errors} errors, "
        f"{total_skipped} skipped in {elapsed_total/3600:.1f}h")


# ── Stats ─────────────────────────────────────────────────────────

def run_stats(args):
    """Print statistics on generated responses."""
    output_file = Path(args.output) if args.output else OUTPUT_FILE

    if not output_file.exists():
        log(f"No output file: {output_file}")
        sys.exit(1)

    by_hash = {}
    by_source = {}
    total = 0
    total_chars = 0

    with open(output_file) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            h = entry.get("prompt_hash", "unknown")
            s = entry.get("source", "unknown")
            by_hash.setdefault(h, []).append(entry)
            by_source[s] = by_source.get(s, 0) + 1
            total += 1
            total_chars += len(entry.get("response", ""))

    complete = sum(1 for responses in by_hash.values() if len(responses) >= 4)
    partial = sum(1 for responses in by_hash.values() if 0 < len(responses) < 4)

    print(f"\n{'='*60}")
    print(f"RL Generation Statistics")
    print(f"{'='*60}")
    print(f"Total responses:     {total}")
    print(f"Unique prompts:      {len(by_hash)}")
    print(f"Complete (4/4):      {complete}")
    print(f"Partial (<4):        {partial}")
    print(f"Avg response length: {total_chars // max(total,1)} chars")

    print(f"\nBy source:")
    for s, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {s:<25s} {count:>6}")

    # Response length distribution
    lengths = []
    with open(output_file) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            lengths.append(len(entry.get("response", "")))

    if lengths:
        lengths.sort()
        print(f"\nResponse length distribution:")
        print(f"  Min: {lengths[0]}")
        print(f"  P25: {lengths[len(lengths)//4]}")
        print(f"  P50: {lengths[len(lengths)//2]}")
        print(f"  P75: {lengths[3*len(lengths)//4]}")
        print(f"  Max: {lengths[-1]}")


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Batch response generation for RL rejection sampling")
    sub = parser.add_subparsers(dest="command")

    # Generate (default)
    gen = sub.add_parser("generate", help="Generate responses")
    gen.add_argument("--port", type=int, default=DEFAULT_PORT,
                     help="llama-server port")
    gen.add_argument("--prompts", default=str(PROMPTS_FILE),
                     help="Prompts JSONL file")
    gen.add_argument("--output", default=None,
                     help="Output JSONL file")
    gen.add_argument("--n", type=int, default=DEFAULT_N,
                     help="Responses per prompt")
    gen.add_argument("--temperature", type=float, default=DEFAULT_TEMP)
    gen.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    gen.add_argument("--start", type=int, default=None,
                     help="Start prompt index (inclusive)")
    gen.add_argument("--end", type=int, default=None,
                     help="End prompt index (exclusive)")
    gen.add_argument("--resume", action="store_true",
                     help="Resume from existing output file")

    # Stats
    st = sub.add_parser("stats", help="Show generation statistics")
    st.add_argument("--output", default=None)

    args = parser.parse_args()

    if args.command == "stats":
        run_stats(args)
    elif args.command == "generate":
        run_generate(args)
    else:
        # Default to generate if no subcommand
        # Re-parse with generate defaults
        args = gen.parse_args(sys.argv[1:]) if len(sys.argv) > 1 else None
        if args:
            run_generate(args)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
