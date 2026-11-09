#!/usr/bin/env python3
"""Bounded Qwen3-4B baseline on the 12-cell development mini-set.

Design:

  * checkpoint: the locally cached Qwen3-4B snapshot, pinned to the revision recorded in
    `src/native_serialize.py`; no download, no rental, no Azure;
  * 12 cells x (2 thinking-enabled samples + 1 thinking-disabled sample) = 36 generations;
  * sampling recorded per generation: temperature, top_p, top_k, max_new_tokens, seed, dtype,
    thinking mode, model revision;
  * resumable: each finished generation is appended to a private JSONL, so an interrupted run
    continues instead of regenerating;
  * raw text and reasoning traces stay private; the summarizer writes aggregate counts only.

CPU-only inference is slow (measured ~1.6 tok/s), so the run is bounded by `--max-new-tokens`.
Nothing here updates weights.

    python3 scripts/run_baseline.py --dry-run          # validate wiring without loading weights
    python3 scripts/run_baseline.py --limit 1          # one generation, timing probe
    python3 scripts/run_baseline.py                    # full 36-generation run, resumable
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_serialize import PINNED_REVISION, load_tokenizer  # noqa: E402

DEFAULT_MODEL_DIR = Path.home() / ".cache" / "huggingface" / "hub" / "models--Qwen--Qwen3-4B" / "snapshots" / PINNED_REVISION

SAMPLING = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 20,
    "repetition_penalty": 1.0,
    "max_new_tokens": 512,
}
SEEDS = {"thinking:0": 0, "thinking:1": 1, "no_thinking:0": 2}

THINK_OPEN = "<" + "think" + ">"
THINK_CLOSE = "<" + "/" + "think" + ">"


def private_dir() -> Path:
    d = os.environ.get("GOLD_MINISET_DIR") or os.environ.get("EQ2_EVIDENCE_DIR")
    if not d:
        raise SystemExit("set GOLD_MINISET_DIR (or EQ2_EVIDENCE_DIR) so raw output stays private")
    p = Path(d) / "baseline"
    p.mkdir(parents=True, exist_ok=True)
    return p


def split_channels(text: str) -> tuple[str, str, bool]:
    """Split a completion into (reasoning, answer).

    The model opens the thinking channel itself, so a completion either contains the closer once or
    never opened the channel.
    """
    if THINK_CLOSE in text:
        head, tail = text.split(THINK_CLOSE, 1)
        reasoning = head.replace(THINK_OPEN, "", 1).strip("\n")
        return reasoning, tail.strip("\n"), True
    if THINK_OPEN in text:
        # The channel opened but never closed: the token budget ran out inside the reasoning.
        # There is no answer, and calling the reasoning text an answer would be a category error.
        return text.replace(THINK_OPEN, "", 1).strip("\n"), "", False
    return "", text.strip("\n"), True


def plan(cells: list[dict]) -> list[dict]:
    out = []
    for c in cells:
        for mode in ("thinking", "thinking", "no_thinking"):
            key = f"{mode}:{0 if mode == 'no_thinking' else len([x for x in out if x['cell_id'] == c['cell_id'] and x['mode'] == 'thinking'])}"
            out.append({
                "cell_id": c["cell_id"],
                "mode": mode,
                "sample_key": key,
                "seed": SEEDS[key],
                "messages": c["messages"],
            })
    return out


def load_done(raw_path: Path) -> set[tuple[str, str]]:
    done = set()
    if raw_path.exists():
        for line in raw_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add((r["cell_id"], r["sample_key"]))
    return done


def generate_one(model, tok, messages, mode, seed, max_new_tokens, dtype_name, model_revision):
    import torch

    enable_thinking = mode == "thinking"
    rendered = tok.apply_chat_template(list(messages), tokenize=False,
                                       add_generation_prompt=True, enable_thinking=enable_thinking)
    enc = tok(rendered, return_tensors="pt", add_special_tokens=False)
    prompt_tokens = int(enc["input_ids"].shape[1])

    torch.manual_seed(seed)
    t0 = time.time()
    with torch.inference_mode():
        out = model.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=SAMPLING["temperature"],
            top_p=SAMPLING["top_p"],
            top_k=SAMPLING["top_k"],
            repetition_penalty=SAMPLING["repetition_penalty"],
            pad_token_id=tok.pad_token_id,
            eos_token_id=tok.eos_token_id,
        )
    elapsed = time.time() - t0
    new_ids = out[0][prompt_tokens:]
    text = tok.decode(new_ids, skip_special_tokens=True)
    reasoning, answer, channel_closed = split_channels(text)
    return {
        "model_revision": model_revision,
        "dtype": dtype_name,
        "mode": mode,
        "seed": seed,
        "sampling": dict(SAMPLING, max_new_tokens=max_new_tokens),
        "prompt_tokens": prompt_tokens,
        "output_tokens": int(len(new_ids)),
        "finish": ("eos" if len(new_ids) and int(new_ids[-1]) == tok.eos_token_id else "length"),
        "elapsed_s": round(elapsed, 1),
        "tokens_per_s": round(float(len(new_ids)) / elapsed, 2) if elapsed > 0 else None,
        "thinking_mode": enable_thinking,
        "reasoning_chars": len(reasoning),
        "reasoning_tokens": len(tok.encode(reasoning, add_special_tokens=False)) if reasoning else 0,
        "reasoning_channel_present": bool(reasoning),
        "reasoning_channel_closed": channel_closed,
        "answer_chars": len(answer),
        "raw_text": text,
        "reasoning_text": reasoning,
        "answer_text": answer,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="validate wiring without loading weights")
    ap.add_argument("--limit", type=int, default=None, help="stop after N generations")
    ap.add_argument("--max-new-tokens", type=int, default=None)
    ap.add_argument("--dtype", default="bfloat16", choices=("bfloat16", "float32"))
    args = ap.parse_args()

    from miniset import load_cells
    cells, _ = load_cells()
    jobs = plan(cells)
    max_new = args.max_new_tokens or SAMPLING["max_new_tokens"]
    pdir = private_dir()
    raw_path = pdir / "raw.jsonl"

    print(json.dumps({"planned_generations": len(jobs), "cells": len(cells),
                      "max_planned_generations": 36,
                      "raw_path": str(raw_path), "private": True}, indent=2))

    if args.dry_run:
        done = load_done(raw_path)
        pending = [j for j in jobs if (j["cell_id"], j["sample_key"]) not in done]
        print(json.dumps({"dry_run": True, "already_done": len(done), "pending": len(pending),
                          "first_pending": pending[0] if pending else None}, indent=2))
        return 0

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    threads = int(os.environ.get("BASELINE_THREADS", "12"))
    torch.set_num_threads(threads)

    model_dir = Path(os.environ.get("QWEN3_MODEL_DIR") or DEFAULT_MODEL_DIR)
    if not model_dir.exists():
        print(json.dumps({"blocked": True, "reason": "checkpoint not present", "path": str(model_dir)}), file=sys.stderr)
        return 3

    dtype = torch.bfloat16 if args.dtype == "bfloat16" else torch.float32
    tok = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(str(model_dir), dtype=dtype, low_cpu_mem_usage=True)
    model.eval()

    done = load_done(raw_path)
    pending = [j for j in jobs if (j["cell_id"], j["sample_key"]) not in done]
    if args.limit:
        pending = pending[: args.limit]

    with raw_path.open("a") as f:
        for i, job in enumerate(pending, 1):
            rec = generate_one(model, tok, job["messages"], job["mode"], job["seed"],
                               max_new, args.dtype, PINNED_REVISION)
            rec.update({"cell_id": job["cell_id"], "sample_key": job["sample_key"]})
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(json.dumps({"i": i, "of": len(pending), "cell_id": job["cell_id"],
                              "mode": job["mode"], "tokens": rec["output_tokens"],
                              "finish": rec["finish"], "s": rec["elapsed_s"]}), flush=True)

    print(json.dumps({"finished": len(pending), "raw_path": str(raw_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
