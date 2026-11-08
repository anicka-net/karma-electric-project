"""Corpus-level audits.

`validate_case` and `validate_triple` check a case or a scenario. This module checks
properties that only exist across the whole corpus:

  1. No refusal supervision in training. `decline_scope` cases must be held out.
  2. Every case declares mechanical deliverable checks.
  3. Every scenario has exactly one variant of each kind.
  4. Held-out assignment is recorded and does not silently disappear.
  5. Target sets are length-matched across conditions (needs generated targets).

Run from `build_dataset.py`, which fails the build on any violation. Also usable
standalone: `python3 src/corpus_audit.py`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from serialize import CONDITIONS, LENGTH_BAND  # noqa: E402

TRAINING_SPLITS = {"train", "dev", "test"}
REFUSAL_DECISION_TYPES = {"decline_scope"}

# A generated target set is "length-matched" when, within each scenario, the longest
# condition's word count is at most this multiple of the shortest.
LENGTH_MATCH_TOLERANCE = 1.30


def audit_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Corpus invariants over the semantic cases."""
    violations: list[dict[str, str]] = []

    training = [c for c in cases if c["split"] in TRAINING_SPLITS]
    heldout = [c for c in cases if c["split"] == "heldout"]

    # 1. no refusal supervision in any training split
    for c in training:
        if c["decision"]["decision_type"] in REFUSAL_DECISION_TYPES:
            violations.append({
                "rule": "no_refusal_supervision",
                "variant_id": c["variant_id"],
                "detail": f"decision_type={c['decision']['decision_type']} in split={c['split']}",
            })

    # 2. every case declares mechanical deliverable checks
    missing_checks = [c["variant_id"] for c in cases if not c.get("deliverable_checks")]
    for vid in missing_checks:
        violations.append({
            "rule": "deliverable_checks_declared",
            "variant_id": vid,
            "detail": "no deliverable_checks",
        })

    # 3. one variant of each kind per scenario
    kinds: dict[str, Counter] = defaultdict(Counter)
    for c in cases:
        kinds[c["scenario_id"]][c["variant_kind"]] += 1
    for sid, counter in kinds.items():
        if dict(counter) != {"neutral": 1, "pressure": 1, "counterfactual": 1}:
            violations.append({
                "rule": "one_variant_of_each_kind",
                "variant_id": sid,
                "detail": str(dict(counter)),
            })

    # 4. held-out assignment is recorded, and only decline_scope cases are held out
    for c in heldout:
        hist = (c.get("provenance") or {}).get("reassignment_history") or []
        if not hist:
            violations.append({
                "rule": "heldout_reassignment_recorded",
                "variant_id": c["variant_id"],
                "detail": "split=heldout with no reassignment_history",
            })
        if c["decision"]["decision_type"] not in REFUSAL_DECISION_TYPES:
            violations.append({
                "rule": "heldout_is_refusal_shaped",
                "variant_id": c["variant_id"],
                "detail": f"heldout but decision_type={c['decision']['decision_type']}",
            })

    # held-out must be a minority of the corpus, or the training set is not the point
    if heldout and len(heldout) > len(cases) / 2:
        violations.append({
            "rule": "heldout_is_minority",
            "variant_id": "-",
            "detail": f"{len(heldout)}/{len(cases)} held out",
        })

    return {
        "ok": not violations,
        "violations": violations,
        "counts": {
            "cases": len(cases),
            "training": len(training),
            "heldout": len(heldout),
            "scenarios": len(kinds),
        },
        "heldout_variant_ids": sorted(c["variant_id"] for c in heldout),
        "rules_checked": [
            "no_refusal_supervision",
            "deliverable_checks_declared",
            "one_variant_of_each_kind",
            "heldout_reassignment_recorded",
            "heldout_is_refusal_shaped",
            "heldout_is_minority",
        ],
    }


def audit_target_set(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Corpus invariants over a generated target set.

    `rows` must contain variant_id, condition, text (or content) and ok.
    """
    violations: list[dict[str, str]] = []
    by_scenario: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for r in rows:
        vid = r["variant_id"]
        sid = vid.rsplit("-", 1)[0]
        text = r.get("text") or r.get("content") or ""
        by_scenario[sid][r["condition"]] = {
            "variant_id": vid,
            "words": len(text.split()),
            "ok": bool(r.get("ok")),
            "text": text,
        }

    matched = []
    for sid, conds in by_scenario.items():
        if not all(k in conds for k in CONDITIONS):
            violations.append({
                "rule": "all_conditions_present",
                "variant_id": sid,
                "detail": f"present={sorted(conds)}",
            })
            continue
        counts = {k: conds[k]["words"] for k in CONDITIONS}
        lo, hi = min(counts.values()), max(counts.values())
        ratio = (hi / lo) if lo else float("inf")
        matched.append({"scenario_id": sid, "words": counts, "ratio": round(ratio, 2),
                        "matched": ratio <= LENGTH_MATCH_TOLERANCE})
        if ratio > LENGTH_MATCH_TOLERANCE:
            violations.append({
                "rule": "length_matched",
                "variant_id": sid,
                "detail": f"word counts {counts} ratio={ratio:.2f} > {LENGTH_MATCH_TOLERANCE}",
            })

    band_lo, band_hi = LENGTH_BAND
    out_of_band = [
        {"variant_id": r["variant_id"], "condition": r["condition"], "words": len((r.get("text") or r.get("content") or "").split())}
        for r in rows
        if not (band_lo <= len((r.get("text") or r.get("content") or "").split()) <= band_hi)
    ]
    for r in out_of_band:
        violations.append({
            "rule": "within_length_band",
            "variant_id": f"{r['variant_id']}::{r['condition']}",
            "detail": f"words={r['words']} band={(band_lo, band_hi)}",
        })

    return {
        "ok": not violations,
        "violations": violations,
        "scenario_matching": matched,
        "rows": len(rows),
        "tolerance": LENGTH_MATCH_TOLERANCE,
        "note": (
            "Length matching is a corpus property, not a per-target property. A run "
            "with too few scenarios or missing conditions cannot be called matched."
        ),
    }


def main() -> int:
    p = ROOT / "data" / "validated" / "cases.jsonl"
    if not p.exists():
        raise SystemExit("run src/build_dataset.py first")
    cases = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    res = audit_cases(cases)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
