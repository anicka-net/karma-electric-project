#!/usr/bin/env python3
"""Stage 0: audit the real Qwen3 tokenizer and chat template.

Synthetic messages only. Nothing here touches the private mini-set, calls a model, or
trains anything. Output: data/native/template_audit.json, rendered by
scripts/render_native_reports.py into reports/NATIVE_TEMPLATE_AUDIT.md.

The audit answers one question: is the serialization the model was trained on reproducible
from the artifacts in hand, and where exactly does the assistant turn end and the answer
begin?
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_serialize import (  # noqa: E402
    PINNED_REVISION,
    QWEN3,
    compare_tokenization_paths,
    describe_tokenizer,
    load_tokenizer,
    reconstruct,
)

# Control markers from other model families. Their presence in a Qwen3 render would mean the
# prompt format or the tokenizer came from the wrong artifact.
FOREIGN_MARKERS = {
    "llama3": "<|eot_id|>",
    "llama3_header": "<|start_header_id|>",
    "mistral": "[INST]",
    "harmony": "<|channel|>",
    "harmony_end": "<|end|>",
    "phi": "<|endoftext|>",
}

SYNTH = [
    {"role": "system", "content": "You are a careful assistant."},
    {"role": "user", "content": "Why does the container get killed?"},
]


def file_hashes(directory: Path) -> dict[str, str]:
    out = {}
    for name in ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"):
        p = directory / name
        if p.exists():
            out[name] = {
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
    return out


def template_probe(tok, messages, **kw) -> dict:
    rendered = tok.apply_chat_template(list(messages), tokenize=False, **kw)
    ids = tok.apply_chat_template(list(messages), tokenize=True, return_dict=False, **kw)
    if not isinstance(ids, list):
        ids = ids["input_ids"]
    rec = reconstruct(tok, ids)
    return {
        "kwargs": {k: v for k, v in kw.items()},
        "rendered": rendered,
        "rendered_codepoints": [f"0x{ord(c):x}" for c in rendered],
        "ids": list(ids),
        "n_tokens": len(ids),
        "reconstruction_exact": rec == rendered,
        "tokens_matching_layout": {
            "im_start": sum(1 for i in ids if i == QWEN3["im_start"]),
            "im_end": sum(1 for i in ids if i == QWEN3["im_end"]),
            "think_open": sum(1 for i in ids if i == QWEN3["think_open"]),
            "think_close": sum(1 for i in ids if i == QWEN3["think_close"]),
        },
        "foreign_markers_found": {
            fam: (marker in rendered) for fam, marker in FOREIGN_MARKERS.items()
        },
        "empty_think_block": (
            QWEN3["think_open"] in ids
            and QWEN3["think_close"] in ids
            and ids.index(QWEN3["think_close"]) - ids.index(QWEN3["think_open"]) == 2
        ),
    }


def main() -> int:
    tok = load_tokenizer()
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(str(Path.home() / ".cache/qwen3-4b-tokenizer/1cfa9a72"))

    probes = {
        "generation_prompt_thinking_enabled": template_probe(
            tok, SYNTH, add_generation_prompt=True, enable_thinking=True),
        "generation_prompt_thinking_disabled": template_probe(
            tok, SYNTH, add_generation_prompt=True, enable_thinking=False),
        "assistant_turn_with_reasoning": template_probe(
            tok, SYNTH + [{"role": "assistant", "content": "Raise the limit.",
                           "reasoning_content": "Compare the peak with the limit."}]),
        "assistant_turn_without_reasoning": template_probe(
            tok, SYNTH + [{"role": "assistant", "content": "Raise the limit."}]),
        "user_only": template_probe(tok, SYNTH[:2]),
    }

    paths = {
        "generation_prompt": compare_tokenization_paths(tok, SYNTH),
        "assistant_with_reasoning": compare_tokenization_paths(
            tok, SYNTH + [{"role": "assistant", "content": "Raise the limit.",
                           "reasoning_content": "Compare the peak with the limit."}]),
    }

    facts = describe_tokenizer(tok)

    # Findings that follow from the probes, computed rather than asserted.
    no_reasoning = probes["assistant_turn_without_reasoning"]
    findings = {
        "answer_only_turn_carries_empty_think_block": no_reasoning["empty_think_block"],
        "thinking_disabled_prompt_prefills_empty_think_block": (
            probes["generation_prompt_thinking_disabled"]["empty_think_block"]),
        "thinking_enabled_prompt_opens_assistant_turn_without_marker": (
            probes["generation_prompt_thinking_enabled"]["tokens_matching_layout"]["think_open"] == 0
            and probes["generation_prompt_thinking_enabled"]["rendered"].endswith("<|im_start|>assistant\n")),
        "all_renders_reconstruct_exactly": all(p["reconstruction_exact"] for p in probes.values()),
        "no_foreign_control_markers": not any(
            any(p["foreign_markers_found"].values()) for p in probes.values()),
        "template_paths_agree_with_plain_encode": all(p["agree"] for p in paths.values()),
        "system_role_supported": probes["user_only"]["rendered"].startswith("<|im_start|>system\n"),
    }

    out = {
        "stage": 0,
        "revision": PINNED_REVISION,
        "tokenizer_files": file_hashes(d),
        "tokenizer": facts,
        "probes": probes,
        "tokenization_path_comparison": paths,
        "findings": findings,
        "interpretation": {
            "answer_only_turn_carries_empty_think_block": (
                "A template-native assistant turn without reasoning_content renders an empty "
                "think block before the answer. Masking the prompt and the think block and "
                "supervising the answer therefore presents the model with 'empty think block "
                "-> answer' at every training step, and never with a thinking continuation."),
            "thinking_enabled_prompt": (
                "With enable_thinking=True the generation prompt stops at 'assistant\\n' and the "
                "model emits its own  thinking. With enable_thinking=False the prompt pre-fills an "
                "empty think block, so the model always starts after </think>."),
        },
        "limitations": [
            "These probes use synthetic messages; they establish template structure, not behaviour.",
            "Whether a serving stack tokenizes the rendered string or replays template ids cannot be "
            "determined from tokenizer files alone; the comparison recorded here only shows that the "
            "two paths agree for this build.",
        ],
    }

    dest = ROOT / "data" / "native" / "template_audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["findings"], indent=2))
    print(f"wrote {dest}")
    return 0 if all(v for k, v in findings.items() if isinstance(v, bool)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
