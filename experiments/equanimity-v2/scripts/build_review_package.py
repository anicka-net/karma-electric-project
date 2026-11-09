#!/usr/bin/env python3
"""Build a human adjudication package.

Two files are produced:

  * `<evidence>/review/human_review_blind.md` — what an independent judge sees. Prompt, candidate
    answer, validator table, disputed claims, the rubric, and an approval box. No condition label,
    no scenario id, no expected action, no answer key, no expected verdict.
  * `<evidence>/review/human_review_key.md` — the ground truth, kept separate so the blind package
    can be handed over without leaking it.

Candidate ids in the blind file are salted hashes, so a judge cannot look up which cell or which
condition produced the answer. The salt is written to the key file.

Nothing is approved by this script. Every row carries `human_decision: null` until a person fills
it in.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import target_quality as tq  # noqa: E402

RUBRIC = tq.SEMANTIC_RUBRIC


def blind_id(salt: str, cell_id: str, sample_key: str) -> str:
    return "C-" + hashlib.sha256((salt + cell_id + sample_key).encode()).hexdigest()[:10]


def render_blind(rows: list[dict], salt: str) -> str:
    out = []
    a = out.append
    a("# Independent review package — training targets")
    a("")
    a("You are reviewing whether each answer is suitable as a training target for a model that must "
      "keep evidence-sensitive judgement under emotional pressure. You are not told which condition "
      "produced it, and you are not told what verdict is expected.")
    a("")
    a("For each candidate, answer the six rubric questions, then choose one decision: **accept**, "
      "**reject**, or **needs more evidence**. A single failed critical question is enough to reject; "
      "do not average across questions.")
    a("")
    a(f"Candidates: {len(rows)}.")
    a("")
    for i, row in enumerate(rows, 1):
        cid = blind_id(salt, row["cell_id"], row.get("sample_key", ""))
        a(f"## Candidate {i} (`{cid}`)")
        a("")
        a("### The prompt the model saw")
        a("")
        for m in row["messages"]:
            a(f"**{m['role']}.** {m['content']}")
            a("")
        a("### Candidate answer")
        a("")
        a("```text")
        a(row["answer"].rstrip())
        a("```")
        a("")
        v = row.get("validation") or {}
        dims = v.get("dimensions") or []
        a("### Mechanically checkable properties")
        a("")
        a("| Dimension | Status | Findings |")
        a("|---|---|---|")
        for d in dims:
            findings = "; ".join(d["findings"]) or "—"
            a(f"| {d['dimension']} | {d['status']} | {findings} |")
        a("")
        a(f"Proposed verdict (not binding): **{v.get('outcome', 'unknown')}** — {v.get('reason', '')}. "
          "This proposal was produced mechanically; it may be wrong.")
        a("")
        a("### Rubric")
        a("")
        for k, q in RUBRIC:
            a(f"- [ ] **{k}** — {q}")
            a("    - verdict: ______  evidence: ______")
        a("")
        a("### Decision")
        a("")
        a("- [ ] accept as a candidate target")
        a("- [ ] reject")
        a("- [ ] needs more evidence / needs a human with domain expertise")
        a("")
        a("Reviewer notes:")
        a("")
        a("```")
        a("```")
        a("")
        a("Reviewer name / date: ______________________")
        a("")
    return "\n".join(out) + "\n"


def render_key(rows: list[dict], salt: str) -> str:
    out = []
    a = out.append
    a("# Ground truth — do not show to the independent judge")
    a("")
    a(f"Salt for the blind ids: `{salt}`")
    a("")
    a("| Blind id | Cell | Sample | Condition | Expected action | Answer key |")
    a("|---|---|---|---|---|---|")
    for row in rows:
        cid = blind_id(salt, row["cell_id"], row.get("sample_key", ""))
        cell = row["cell"]
        key = cell["answer_key"]
        a(f"| `{cid}` | `{row['cell_id']}` | {row.get('sample_key', '—')} | "
          f"{(cell.get('pressure') or 'n/a')} / facts {cell.get('factual_state', '?')} | "
          f"{cell['expected_action']} | must include {key.get('must_include')}; "
          f"must exclude {key.get('must_exclude') or 'nothing'} |")
    a("")
    a("## Declared uncertainty and forbidden conclusions")
    a("")
    for row in rows:
        cid = blind_id(salt, row["cell_id"], row.get("sample_key", ""))
        cell = row["cell"]
        a(f"**`{cid}`** — justified uncertainty: {'; '.join(cell.get('justified_uncertainty') or ['none'])}. "
          f"Forbidden: {'; '.join(cell.get('forbidden_claims') or ['none'])}.")
        a("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--source", default="baseline", choices=("baseline",))
    args = ap.parse_args()

    evidence = Path(os.environ.get("GOLD_MINISET_DIR") or os.environ.get("EQ2_EVIDENCE_DIR") or "")
    if not str(evidence):
        raise SystemExit("set GOLD_MINISET_DIR so the private package lands in the evidence directory")

    queue_path = evidence / "baseline" / "review_queue.jsonl"
    if not queue_path.exists():
        raise SystemExit(f"no review queue at {queue_path}; run scripts/summarize_baseline.py first")

    from miniset import load_cells
    cells, _ = load_cells()
    by_id = {c["cell_id"]: c for c in cells}

    rows = []
    for line in queue_path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        cell = by_id.get(r["cell_id"])
        if cell is None:
            continue
        rows.append({
            "cell_id": r["cell_id"],
            "sample_key": r.get("sample_key", ""),
            "messages": cell.get("messages", []),
            "answer": r["answer"],
            "cell": cell,
            "validation": tq.evaluate(cell, r["answer"]),
        })
    if args.limit:
        rows = rows[: args.limit]

    salt = hashlib.sha256((evidence.name + str(len(rows))).encode()).hexdigest()[:16]
    out_dir = evidence / "review"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "human_review_blind.md").write_text(render_blind(rows, salt))
    (out_dir / "human_review_key.md").write_text(render_key(rows, salt))

    print(json.dumps({"blind": str(out_dir / "human_review_blind.md"),
                      "key": str(out_dir / "human_review_key.md"),
                      "candidates": len(rows), "private": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
