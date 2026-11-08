#!/usr/bin/env python3
"""Build and validate the 12-cell gold-standard development mini-set.

The mini-set prompt text lives outside the repository (GOLD_MINISET_DIR) until it has been
human-reviewed. This script:

  * validates all 12 cells and all 3 scenarios;
  * writes `gold_miniset.jsonl` into the private directory;
  * writes a sanitized structural summary into `data/audit/gold_miniset_summary.json`
    (counts, ids, evidence statuses, violation codes; no prompt or answer text);
  * renders `GOLD_MINISET_REVIEW.md` into the private directory and, if requested, a copy
    path for upload.

Exits non-zero if any check fails. No teacher target is generated here.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from miniset import load_cells, score_answer, validate  # noqa: E402


def render_review(cells, src, report) -> str:
    out = []
    a = out.append
    a("# Gold-standard development mini-set — 12 cells for human review")
    a("")
    a(f"**Version:** `{src['mini_set_version']}`  ")
    a(f"**Status:** {src['status']}.  ")
    a("**Not** the confirmatory holdout. No teacher target has been generated.")
    a("")
    a("Three scenarios, four cells each: factual state A/B x neutral/pressure. Within a "
      "factual state the evidence and the requested deliverable are identical; the pressure "
      "cell only adds tone. Across factual states exactly one declared premise changes.")
    a("")
    a("## Instrument summary")
    a("")
    a(f"- Cells: {report['cells']}; scenarios: {report['scenarios']}; validation: "
      f"{'clean' if report['ok'] else 'FAILED'}.")
    a("- Every cell is `human_approved: false` and `requires_human_review: true`.")
    a("- Answer keys are deterministic presence checks. They cannot judge tone, accuracy "
      "beyond the listed tokens, or usefulness.")
    a("")
    a("## Check matrix")
    a("")
    a("| Cell | Facts | Pressure | Task | Deliverable constant | Evidence premises | Violations |")
    a("|---|---|---|---|---|---|---|")
    by_cell = {r["cell_id"]: r for r in report["reports"]}
    for c in cells:
        rep = by_cell[c["cell_id"]]
        ev = "; ".join(f"{e['premise_id']}={e['status']}" for e in rep["evidence_map"])
        v = ", ".join(sorted({x["code"] for x in rep["violations"]})) or "-"
        a(f"| {c['cell_id']} | {c['factual_state']} | {c['pressure']} | {c['task_id']} | yes | {ev} | {v} |")
    a("")
    a("## Scenarios")
    a("")
    for sid, s in src["scenarios"].items():
        a(f"### {sid} — {s['title']}")
        a("")
        a(f"**Task id:** `{s['task_id']}`  ")
        a(f"**Counterfactual class:** `{s['counterfactual_class']}` ({s['counterfactual_class_source']})  ")
        a(f"**Changed premise:** {s['counterfactual_change']}  ")
        a(f"**Pressure manipulation:** {s['pressure_note']}")
        a("")
        a(f"**Deliverable (identical in all four cells):** {s['deliverable']}")
        a("")
        for c in [x for x in cells if x["scenario_id"] == sid]:
            a(f"#### {c['cell_id']} — facts {c['factual_state']}, {c['pressure']}")
            a("")
            a("```text")
            for m in c["messages"]:
                a(f"[{m['role']}]")
                a(m["content"])
            a("```")
            a("")
            a("**Evidence map**")
            a("")
            a("| Premise | Kind | Status | Span / justification |")
            a("|---|---|---|---|")
            for e in by_cell[c["cell_id"]]["evidence_map"]:
                if e["status"] == "visible":
                    span = e["span"]["quote"]
                elif e["status"] == "general_knowledge":
                    span = e.get("justification", "")
                else:
                    span = "NOT VISIBLE"
                a(f"| {e['premise_id']} | {e['kind']} | {e['status']} | {span} |")
            a("")
            a(f"**Expected action.** {c['expected_action']}")
            a("")
            a(f"**Acceptable alternatives.** {'; '.join(c['acceptable_alternatives'])}")
            a("")
            a(f"**Justified uncertainty.** {'; '.join(c['justified_uncertainty'])}")
            a("")
            a(f"**Forbidden claims.** {'; '.join(c['forbidden_claims'])}")
            a("")
            a(f"**Answer key.** must include {c['answer_key'].get('must_include')}; "
              f"must exclude {c['answer_key'].get('must_exclude') or 'nothing'}")
            a("")
            if c.get("human_adjudication_required"):
                a(f"**Human adjudication required.** {c['human_adjudication_reason']}")
                a("")
            a("**Review flags**")
            a("")
            for f in c["human_review_flags"]:
                a(f"- [ ] {f}")
            a("")
    a("## Reviewer questions for each cell")
    a("")
    a("1. Is every required premise genuinely visible in the prompt, or does the prompt only "
      "gesture at it?")
    a("2. Is the expected action the correct professional judgement, independent of whether it "
      "is well worded?")
    a("3. In the pressure cell, does the correct action stay the same? If it changes, the pair "
      "is not a pressure manipulation.")
    a("4. In the counterfactual cell, does the change genuinely move the required action, or "
      "only a number?")
    a("5. Would a competent human answering the neutral cell produce something the answer key "
      "would accept but the expected action would not?")
    a("")
    a("## Known limitations")
    a("")
    a("- Twelve cells cannot estimate any effect; they exist to test the instrument.")
    a("- The answer keys are presence checks. A response can satisfy every token and still be "
      "wrong in tone, accuracy or usefulness.")
    a("- The document scenario requires human adjudication by construction: whether a draft "
      "message is firm and non-accusatory while still achieving recovery is not a string "
      "property.")
    a("- Facts, expected actions and checks were authored by the same agent. Agreement among "
      "them is not independent evidence.")
    a("")
    return "\n".join(out) + "\n"


def main() -> int:
    try:
        cells, src = load_cells()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    report = validate(cells)
    d = Path(os.environ["GOLD_MINISET_DIR"])

    with (d / "gold_miniset.jsonl").open("w") as f:
        for c in cells:
            f.write(json.dumps(c, sort_keys=True) + "\n")

    summary = {
        "mini_set_version": src["mini_set_version"],
        "cells": report["cells"],
        "scenarios": report["scenarios"],
        "ok": report["ok"],
        "violations": report["violations"],
        "cell_structure": [
            {
                "cell_id": r["cell_id"],
                "scenario_id": r["scenario_id"],
                "factual_state": r["factual_state"],
                "pressure": r["pressure"],
                "evidence_statuses": {e["premise_id"]: e["status"] for e in r["evidence_map"]},
                "violation_codes": sorted({x["code"] for x in r["violations"]}),
                "human_approved": r["human_approved"],
                "requires_human_review": r["requires_human_review"],
            }
            for r in report["reports"]
        ],
        "scenario_structure": {
            sid: {
                "cell_codes": sorted(c["cell_code"] for c in cells if c["scenario_id"] == sid),
                "counterfactual_class": next(c["counterfactual_class"] for c in cells if c["scenario_id"] == sid),
                "task_id": next(c["task_id"] for c in cells if c["scenario_id"] == sid),
                "violations": report["scenario_violations"].get(sid, []),
            }
            for sid in sorted({c["scenario_id"] for c in cells})
        },
        "answer_keys_deterministic": sorted({c["scenario_id"] for c in cells if not c.get("human_adjudication_required")}),
        "human_adjudication_scenarios": sorted({c["scenario_id"] for c in cells if c.get("human_adjudication_required")}),
        "note": "Structural summary only. Prompt text, expected actions and answer keys stay private until reviewed.",
    }
    out = ROOT / "data" / "audit" / "gold_miniset_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    md = render_review(cells, src, report)
    (d / "GOLD_MINISET_REVIEW.md").write_text(md)
    if os.environ.get("GOLD_MINISET_UPLOAD_COPY"):
        Path(os.environ["GOLD_MINISET_UPLOAD_COPY"]).write_text(md)

    print(json.dumps({"cells": report["cells"], "scenarios": report["scenarios"],
                      "ok": report["ok"], "violations": len(report["violations"]),
                      "answer_keys_deterministic": summary["answer_keys_deterministic"],
                      "human_adjudication_scenarios": summary["human_adjudication_scenarios"]}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
