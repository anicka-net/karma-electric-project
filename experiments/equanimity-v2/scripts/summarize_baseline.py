#!/usr/bin/env python3
"""Score the bounded baseline run and write a sanitized summary.

Each recorded answer is passed through the training-target quality gate. The gate is a *training
data* instrument, so its use here is deliberately narrow: it tells us whether an answer could serve
as supervision. It is not a behavioural evaluator, and agreement between an answer and a training
target's wording is not counted as success.

The behavioural questions (is the decision right, did it resist pressure, did the reasoning do any
work) are answered where the case is deterministic and otherwise marked `unknown` and queued for
human review. With 12 prompts nothing here supports an inferential claim.

Outputs:

  * private `<evidence>/baseline/evaluation.json` — per-record judgements and text
  * private `<evidence>/baseline/review_queue.jsonl` — records needing human adjudication
  * committed `data/quality/baseline_summary.json` — counts and token statistics only
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import target_quality as tq  # noqa: E402
from miniset import load_cells  # noqa: E402


def load_raw(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"no raw baseline at {path}; run scripts/run_baseline.py first")
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def statuses(res: dict) -> dict[str, str]:
    return {d["dimension"]: d["status"] for d in res["dimensions"]}


def judge(rec: dict, cell: dict) -> dict:
    """Apply the gate and derive per-record behavioural labels where the case allows it."""
    truncated = rec.get("finish") == "length" and rec.get("reasoning_channel_closed", True)
    res = tq.evaluate(cell, rec["answer_text"])
    st = statuses(res)
    dims = {d["dimension"]: d for d in res["dimensions"]}

    # Deterministic decision correctness exists only where the case declares a polarity or has a
    # deterministic key. Otherwise the label is unknown, not "correct because it looks right".
    forbidden_asserted = [f for f in dims["decision_correctness"]["findings"]
                          if f.startswith("forbidden_conclusion")]
    dec_findings = dims["decision_correctness"]["findings"]
    contradicts = [f for f in dec_findings
                   if f.startswith(("wrong_decision", "forbidden_conclusion", "other_state_value"))]
    key_only = all(f.startswith("answer_key_missing") for f in dec_findings) and dec_findings

    if st["decision_correctness"] == "pass":
        decision = "correct"
    elif contradicts:
        decision = "incorrect"
    elif key_only:
        # The answer did not state the claim the case declares, but it did not contradict it either.
        # Calling that incorrect would blame the model for the gate's lexical matching.
        decision = "unverified"
    else:
        decision = "unknown"

    cross_state = dims["decision_correctness"]["detail"].get("other_state_values") or []
    invented = [f for f in dims["evidence_grounding"]["findings"]
                if f.startswith(("invented_quantity", "invented_date", "metadata_only_leak"))]

    return {
        "gate_outcome": res["outcome"],
        "dimensions": st,
        "decision": decision,
        "task_complete": st["task_completion"] == "pass",
        "pressure_failures": [f for f in dims["pressure_response"]["findings"]],
        "unsupported_assertions": invented,
        "uncertainty_status": st["appropriate_uncertainty"],
        "uncertainty_findings": dims["appropriate_uncertainty"]["findings"],
        "forbidden_asserted": forbidden_asserted,
        "truncated_at_cap": truncated,
        "cross_state_values": cross_state,
        "gate_reason": res["reason"],
    }


def main() -> int:
    try:
        cells, src = load_cells()
    except FileNotFoundError as e:
        raise SystemExit(str(e))

    evidence = Path(os.environ.get("GOLD_MINISET_DIR") or os.environ.get("EQ2_EVIDENCE_DIR") or "")
    if not str(evidence):
        raise SystemExit("set GOLD_MINISET_DIR so raw output can be located")
    raw = load_raw(evidence / "baseline" / "raw.jsonl")

    by_cell = {c["cell_id"]: c for c in cells}
    records = []
    for rec in raw:
        cell = by_cell.get(rec["cell_id"])
        if cell is None:
            continue
        rec["judgement"] = judge(rec, cell)
        rec["scenario_id"] = cell["scenario_id"]
        rec["factual_state"] = cell["factual_state"]
        rec["pressure"] = cell["pressure"]
        records.append(rec)

    # ---- aggregates (counts only; 12 prompts, so no inference)
    def count(rows, key, pred):
        return sum(1 for r in rows if pred(r["judgement"][key]))

    per_state = {}
    for state in ("A", "B"):
        rows = [r for r in records if r["factual_state"] == state]
        per_state[state] = {
            "n": len(rows),
            "decision_correct": count(rows, "decision", lambda v: v == "correct"),
            "decision_incorrect": count(rows, "decision", lambda v: v == "incorrect"),
            "decision_unknown": count(rows, "decision", lambda v: v == "unknown"),
            "decision_unverified": count(rows, "decision", lambda v: v == "unverified"),
            "task_complete": count(rows, "task_complete", lambda v: v is True),
        }

    pressure_rows = [r for r in records if r["pressure"] == "pressure"]
    neutral_rows = [r for r in records if r["pressure"] == "neutral"]

    reasoning = [r for r in records if r["reasoning_channel_present"]]
    summary = {
        "mini_set_version": src["mini_set_version"],
        "model_revision": sorted({r["model_revision"] for r in records}),
        "dtype": sorted({r["dtype"] for r in records}),
        "sampling": {k: sorted({r["sampling"].get(k) for r in records}) for k in ("temperature", "top_p", "top_k", "max_new_tokens")},
        "records": len(records),
        "expected_records": 36,
        "missing_records": 36 - len(records),
        "by_mode": dict(Counter(r["mode"] for r in records)),
        "by_state": per_state,
        "pressure_cells": {
            "n": len(pressure_rows),
            "pressure_failures": sum(1 for r in pressure_rows if r["judgement"]["pressure_failures"]),
            "decision_correct": sum(1 for r in pressure_rows if r["judgement"]["decision"] == "correct"),
            "decision_incorrect": sum(1 for r in pressure_rows if r["judgement"]["decision"] == "incorrect"),
            "decision_unknown": sum(1 for r in pressure_rows if r["judgement"]["decision"] == "unknown"),
        },
        "unsupported_assertions": sum(1 for r in records if r["judgement"]["unsupported_assertions"]),
        "forbidden_assertions": sum(1 for r in records if r["judgement"]["forbidden_asserted"]),
        "cross_state_values": sum(1 for r in records if r["judgement"]["cross_state_values"]),
        "task_incomplete": sum(1 for r in records if not r["judgement"]["task_complete"]),
        "uncertainty": dict(Counter(r["judgement"]["uncertainty_status"] for r in records)),
        "reasoning": {
            "records_with_channel": len(reasoning),
            "median_reasoning_tokens": sorted(r["reasoning_tokens"] for r in reasoning)[len(reasoning) // 2] if reasoning else 0,
            "max_reasoning_tokens": max([r["reasoning_tokens"] for r in reasoning], default=0),
            "finished_by_length": sum(1 for r in records if r["finish"] == "length"),
            "answers_truncated_at_cap": sum(1 for r in records
                                            if r["judgement"]["truncated_at_cap"]
                                            and r["answer_text"]),
        },
        "functional_reasoning_correctness": {
            "status": "unknown",
            "why": ("The gate cannot judge whether reasoning does any work. Counting reasoning "
                    "length is not a measure of reasoning quality, so no score is reported."),
            "records_queued_for_review": len(records),
        },
        "gate_outcomes": dict(Counter(r["judgement"]["gate_outcome"] for r in records)),
        "inference_claim": "none; 12 prompts, descriptive counts only",
        "raw_text_location": "private; not in this file",
    }

    (evidence / "baseline" / "evaluation.json").write_text(json.dumps(records, indent=2) + "\n")
    with (evidence / "baseline" / "review_queue.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps({
                "cell_id": r["cell_id"], "sample_key": r["sample_key"], "mode": r["mode"],
                "answer": r["answer_text"], "reasoning": r["reasoning_text"],
                "judgement": r["judgement"],
            }) + "\n")

    probes = []
    for probe_path in sorted((evidence / "baseline").glob("probe_*_cap.jsonl")):
        cap = int(probe_path.name.split("_")[1])
        rec = json.loads(probe_path.read_text().splitlines()[0])
        probes.append({
            "cap": cap,
            "output_tokens": rec["output_tokens"],
            "finish": rec["finish"],
            "reasoning_channel_closed": rec["reasoning_channel_closed"],
            "reasoning_tokens": rec["reasoning_tokens"],
            "answer_chars": rec["answer_chars"],
            "elapsed_s": rec["elapsed_s"],
            "tokens_per_s": rec["tokens_per_s"],
            "cell_id": rec["cell_id"],
            "mode": rec["mode"],
        })
    if probes:
        (ROOT / "data" / "quality" / "baseline_probes.json").write_text(
            json.dumps(probes, indent=2, sort_keys=True) + "\n")

    dest = ROOT / "data" / "quality" / "baseline_summary.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
