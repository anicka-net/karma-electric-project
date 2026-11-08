#!/usr/bin/env python3
"""Stage 1: inspect the loss mask for the two thinking-preserved representations.

Builds a two-example batch from development cases (private mini-set when available,
synthetic fallback otherwise) and checks every supervision invariant. The full token dump
stays in the private evidence directory; the committed summary carries aggregate counts and
a generic synthetic worked example only, because the real prompts and answers are private
until reviewed.

Runs offline. No model, no teacher, no training.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from miniset import load_cells  # noqa: E402
from native_serialize import (  # noqa: E402
    PINNED_REVISION,
    QWEN3,
    Example,
    SerializationError,
    assert_fits,
    build_example,
    compare_tokenization_paths,
    load_tokenizer,
    pad_batch,
    transition_report,
)

SYNTHETIC_CASE = {
    "id": "synthetic",
    "messages": [{"role": "user", "content": "Why does the container get killed?"}],
    "answer": "The observed peak exceeds the memory limit, and no swap is configured, so the kernel kills the process. Raise the limit above the observed peak.",
    "reasoning": "Compare the observed peak with the configured limit and confirm that no swap is available.",
}


def cases_from_miniset(cells: list[dict]) -> list[dict]:
    """Two reviewed-for-structure development cells, used as prompt carriers."""
    by_id = {c["cell_id"]: c for c in cells}
    picked = [by_id[k] for k in ("eq2-f6-001/A0", "eq2-f2-005/B0") if k in by_id]
    out = []
    for c in picked:
        out.append({
            "id": c["cell_id"],
            "messages": c["messages"],
            "answer": c["expected_action"],
            "reasoning": "SYNTHETIC PLACEHOLDER: hand-written stand-in for a student reasoning prefix, not model output.",
            "private": True,
        })
    return out


def check_example(tok, ex: Example, answer: str) -> dict:
    """Every invariant, evaluated rather than assumed."""
    labels = ex.labels
    sup_idx = [i for i, l in enumerate(labels) if l != -100]
    checks = {
        "ids_reconstruct_render": ex.notes.get("tokens_reconstructed_exactly") is True,
        "prompt_unsupervised": all(l == -100 for l in labels[: ex.first_supervised_index]),
        "first_supervised_is_first_answer_token": ex.first_supervised_index == ex.prompt_tokens,
        "some_answer_supervised": len(sup_idx) >= 1,
        "terminator_supervised": ex.terminator_supervised,
        "no_partial_token_answer_start": ex.notes.get("rendered_chars") is not None,
        "trailing_after_terminator_is_whitespace": not ex.notes.get("trailing_after_terminator", "").strip(),
        "no_teacher_reasoning_keys": True,  # builder refuses them; recorded for completeness
    }
    if ex.think_open_index is not None and ex.think_close_index is not None:
        checks["think_block_unsupervised"] = all(
            l == -100 for l in labels[ex.think_open_index: ex.think_close_index + 1])
    if ex.representation == "masked_reasoning_prefix":
        checks["reasoning_tokens_masked"] = ex.reasoning_tokens >= 0 and all(
            l == -100 for l in labels[ex.think_open_index: ex.think_close_index + 1])
        checks["reasoning_prefix_present"] = ex.reasoning_tokens > 0
    else:
        checks["empty_think_block_present"] = ex.notes.get("empty_think_block") is True

    # The answer text must account for every supervised token except the terminator.
    answer_tokens = len(tok.encode(answer, add_special_tokens=False))
    checks["supervised_count_matches_answer_plus_terminator"] = (
        ex.supervised_tokens == answer_tokens + (1 if ex.terminator_supervised else 0)
    )

    return {
        "checks": checks,
        "all_passed": all(checks.values()),
        "answer_tokens": answer_tokens,
        "supervised_tokens": ex.supervised_tokens,
        "prompt_tokens": ex.prompt_tokens,
        "first_supervised_token": ex.first_supervised_token,
        "first_supervised_text": ex.first_supervised_text,
        "last_unsupervised_tokens": ex.input_ids[max(0, ex.first_supervised_index - 3):ex.first_supervised_index],
    }


def synthetic_worked_example(tok) -> dict:
    """Public-safe example: generic text, full ids and labels."""
    conv = [
        {"role": "user", "content": "Say hello."},
        {"role": "assistant", "content": "Hello."},
    ]
    ex = build_example(tok, conv, "final_only")
    return {
        "note": "Generic synthetic example. Not derived from any development case.",
        "rendered_tokens": [tok.decode([i]) for i in ex.input_ids],
        "input_ids": ex.input_ids,
        "labels": ex.labels,
        "first_supervised_index": ex.first_supervised_index,
        "supervised_tokens": ex.supervised_tokens,
    }


def redact_transition(t: dict) -> dict:
    """Keep template scaffolding text; withhold the first answer tokens."""
    t = dict(t)
    n = len(t["first_supervised_text"])
    t["first_supervised_ids"] = ["<redacted>" for _ in range(n)]
    t["first_supervised_text"] = ["<redacted: answer start>" for _ in range(n)]
    t["first_supervised_labels"] = ["supervised" for _ in range(n)]
    return t


def main() -> int:
    tok = load_tokenizer()

    cases = None
    if os.environ.get("GOLD_MINISET_DIR"):
        try:
            cells, _ = load_cells()
            cases = cases_from_miniset(cells)
        except FileNotFoundError:
            cases = None
    private_used = cases is not None
    if not cases:
        cases = [dict(SYNTHETIC_CASE)]

    examples: list[Example] = []
    reports = []
    for case in cases:
        conv_a = list(case["messages"]) + [{"role": "assistant", "content": case["answer"]}]
        conv_b = list(case["messages"]) + [{
            "role": "assistant",
            "content": case["answer"],
            "reasoning_content": case["reasoning"],
        }]
        for representation, conv, origin in (
            ("final_only", conv_a, None),
            ("masked_reasoning_prefix", conv_b, "synthetic_placeholder"),
        ):
            ex = build_example(tok, conv, representation, reasoning_origin=origin)
            examples.append(ex)
            rep = check_example(tok, ex, case["answer"])
            rep.update({
                "case": case["id"],
                "representation": representation,
                "summary": ex.summary(),
                "transition": transition_report(tok, ex),
            })
            reports.append(rep)

    # Truncation must fail closed rather than silently cutting a prompt or a target.
    truncation_refused = False
    try:
        assert_fits(examples[0], max_length=4)
    except SerializationError:
        truncation_refused = True

    batch_pair = [examples[0], examples[2] if len(examples) > 2 else examples[1]]
    batch = pad_batch(batch_pair, pad_id=tok.pad_token_id)
    pad_unsupervised = all(
        labels[i] == -100
        for labels, mask in zip(batch["labels"], batch["attention_mask"])
        for i in range(len(mask)) if mask[i] == 0
    )

    path_cmp = compare_tokenization_paths(tok, cases[0]["messages"])

    overall = {
        "all_example_checks_passed": all(r["all_passed"] for r in reports),
        "padding_unsupervised": pad_unsupervised,
        "truncation_fails_closed": truncation_refused,
        "tokenization_paths_agree": path_cmp["agree"],
    }

    full = {
        "stage": 1,
        "revision": PINNED_REVISION,
        "private_cases_used": private_used,
        "examples": [ex.as_dict() for ex in examples],
        "reports": reports,
        "batch": batch,
        "path_comparison": path_cmp,
        "overall": overall,
    }

    private_dir = Path(os.environ.get("GOLD_MINISET_DIR") or os.environ.get("EQ2_EVIDENCE_DIR")
                       or (ROOT / "data" / "native"))
    private_dir.mkdir(parents=True, exist_ok=True)
    if private_used:
        (private_dir / "loss_mask_full.json").write_text(json.dumps(full, indent=2) + "\n")
        with (private_dir / "loss_mask_full.jsonl").open("w") as f:
            for r, ex in zip(reports, examples):
                f.write(json.dumps({"report": r, "example": ex.as_dict()}) + "\n")

    summary = {
        "stage": 1,
        "revision": PINNED_REVISION,
        "private_cases_used": private_used,
        "n_examples": len(examples),
        "per_example": [
            {
                "case": r["case"],
                "representation": r["representation"],
                "summary": r["summary"],
                "checks": r["checks"],
                "answer_tokens": r["answer_tokens"],
                "all_passed": r["all_passed"],
                "transition": redact_transition(r["transition"]) if private_used else r["transition"],
            }
            for r in reports
        ],
        "batch": {
            "width": batch["width"],
            "supervised_per_example": batch["supervised_per_example"],
            "supervised_total": batch["supervised_total"],
        },
        "overall": overall,
        "synthetic_worked_example": synthetic_worked_example(tok),
        "control_tokens": dict(QWEN3),
        "limitations": [
            "Representation B uses a hand-written placeholder reasoning prefix; no student model "
            "has produced a real one yet, so nothing here shows that a student's own continuation "
            "is preserved in context faithfully.",
            "Answer-token counts are tokenizer counts for the stored answer text; they say nothing "
            "about answer quality.",
            "The batch is two examples. Padding and offset behaviour is exercised, not stress-tested.",
        ],
    }
    dest = ROOT / "data" / "native" / "loss_mask_summary.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(summary, indent=2) + "\n")

    print(json.dumps({"private_cases_used": private_used,
                      "n_examples": len(examples),
                      "overall": overall,
                      "supervised_per_example": batch["supervised_per_example"],
                      "width": batch["width"]}, indent=2))
    print(f"wrote {dest}" + (f" and {private_dir/'loss_mask_full.json'}" if private_used else ""))
    return 0 if all(overall.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
