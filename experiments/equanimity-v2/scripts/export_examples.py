"""Emit serialized examples from the smoke-run targets.

This demonstrates the export path end to end on real teacher text. It is NOT a
training dataset:

  - the E targets are unapproved teacher candidates (review_status=draft),
  - the S and G targets are deliberately degraded controls, included so the
    three conditions can be compared, not so they can be trained on.

Every row carries `usable_as_training_target: false`. A consumer that ignores
that flag is doing something this script did not authorize.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from serialize import CONDITIONS, render  # noqa: E402


def evidence_dir() -> Path:
    import os

    raw = os.environ.get("EQ2_EVIDENCE_DIR", "")
    if not raw:
        raise SystemExit(
            "EQ2_EVIDENCE_DIR is not set. Serialized examples contain raw teacher\n"
            "text and are written to the evidence directory, not this repository."
        )
    return Path(raw)


def main() -> int:
    cases = {}
    for line in (ROOT / "data" / "validated" / "cases.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            cases[r["variant_id"]] = r

    ev = evidence_dir()
    stored = [json.loads(l) for l in (ev / "targets.jsonl").read_text().splitlines() if l.strip()]

    rows = []
    for r in stored:
        case = cases[r["variant_id"]]
        cond = CONDITIONS[r["condition"]]
        rows.append({
            "variant_id": r["variant_id"],
            "condition": r["condition"],
            "condition_intent": cond.intent,
            "case_content_sha256": case["provenance"]["content_sha256"],
            "dataset_version": case["dataset_version"],
            "review_status": case["provenance"]["review_status"],
            "usable_as_training_target": False,
            "plain": render(case, r["content"], "plain"),
            "chatml": render(case, r["content"], "chatml"),
            "harmony": render(case, r["content"], "harmony"),
        })

    out = evidence_dir() / "serialized_examples.jsonl"
    out.write_text("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n")
    print(f"wrote {len(rows)} serialized examples -> {out.relative_to(ROOT)}")
    print("all rows usable_as_training_target=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
