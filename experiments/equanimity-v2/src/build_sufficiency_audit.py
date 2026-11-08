#!/usr/bin/env python3
"""Write the Stage 0 information-sufficiency audit.

Outputs (all public-safe: they contain authored case text only, no teacher generations):
  data/audit/sufficiency.jsonl   90 variant rows with student view, evidence map, verdict
  data/audit/pairs.jsonl         30 neutral-vs-pressure text comparisons
  data/audit/summary.json        aggregate counts and the list of gating cases

Nothing here approves a case. Every row is `requires_human_review: true`,
`approved_for_training: false`.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scenarios"))

from sufficient import audit_case, audit_pairs  # noqa: E402
from stage0_findings import FINDINGS, summary as findings_summary  # noqa: E402
from numeric_claims import NUMERIC_CLAIMS  # noqa: E402


def main() -> int:
    cases_path = ROOT / "data" / "validated" / "cases.jsonl"
    cases = [json.loads(l) for l in cases_path.read_text().splitlines() if l.strip()]

    by: dict[str, dict[str, dict]] = {}
    for c in cases:
        by.setdefault(c["scenario_id"], {})[c["variant_kind"]] = c

    out_dir = ROOT / "data" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for c in cases:
        sid = c["scenario_id"]
        auth = dict(FINDINGS.get(sid, {}))
        auth["numeric_claims"] = NUMERIC_CLAIMS.get(sid, [])
        rows.append(audit_case(c, by[sid].get("neutral"), auth))

    with (out_dir / "sufficiency.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    pairs = audit_pairs(cases, FINDINGS)
    with (out_dir / "pairs.jsonl").open("w") as f:
        for p in pairs["pairs"]:
            f.write(json.dumps(p, sort_keys=True) + "\n")

    # Per-scenario verdict rollup: the worst verdict across the three variants.
    order = {"insufficient": 0, "undetermined": 1, "sufficient_lexically": 2}
    per_scenario = {}
    for sid in sorted(by):
        vr = [r for r in rows if r["scenario_id"] == sid]
        worst = min(vr, key=lambda r: order[r["sufficiency"]["verdict"]])
        cf = next((r["counterfactual"] for r in vr if r["counterfactual"]), None)
        missing = sorted({m for r in vr for m in r["sufficiency"]["missing_premise_ids"]})
        per_scenario[sid] = {
            "verdict": worst["sufficiency"]["verdict"],
            "missing_premise_ids": missing,
            "counterfactual_class": cf["class"] if cf else None,
            "counterfactual_estimand": cf["estimand"] if cf else None,
            "counterfactual_rendering_defects": cf["rendering_defects"] if cf else [],
            "numeric_contradictions": sorted({
                n["kind"] for r in vr for n in r["numeric_claims"] if n["contradicts_case"]
            }),
            "domain_review": sorted({r["high_stakes"]["review_type"] for r in vr
                                     if r["high_stakes"]["required"] and r["high_stakes"]["review_type"]}),
            "authored_flags": FINDINGS.get(sid, {}).get("flags", []),
            "authored_verdict": FINDINGS.get(sid, {}).get("verdict"),
            "flags": sorted({f["code"] for r in vr for f in r["mechanical_flags"]}),
        }

    summary = {
        "rows": len(rows),
        "scenarios": len(by),
        "variant_verdicts": dict(Counter(r["sufficiency"]["verdict"] for r in rows)),
        "scenario_verdicts": dict(Counter(v["verdict"] for v in per_scenario.values())),
        "approved_for_training": sum(1 for r in rows if r["approved_for_training"]),
        "requires_human_review": sum(1 for r in rows if r["requires_human_review"]),
        "counterfactual_classes": dict(Counter(v["counterfactual_class"] for v in per_scenario.values())),
        "counterfactual_mechanical_overrides": sorted(
            r["scenario_id"] for r in rows if r["counterfactual"] and r["counterfactual"]["overridden"]
        ),
        "counterfactual_rendering_defect_scenarios": sorted(
            sid for sid, v in per_scenario.items() if v["counterfactual_rendering_defects"]
        ),
        "numeric_contradiction_scenarios": sorted(
            sid for sid, v in per_scenario.items() if v["numeric_contradictions"]
        ),
        "domain_review_scenarios": sorted(
            sid for sid, v in per_scenario.items() if v["domain_review"]
        ),
        "scenarios_with_no_missing_premise": sorted(
            sid for sid, v in per_scenario.items() if not v["missing_premise_ids"]
        ),
        "pairs": pairs["count"],
        "pairs_with_evidence_relevant_change": sorted(
            p["scenario_id"] for p in pairs["pairs"]
            if p["quantity_diff"]["evidence_relevant_added"] or p["quantity_diff"]["evidence_relevant_removed"]
        ),
        "authored_findings": findings_summary(),
        "per_scenario": per_scenario,
        "note": (
            "Verdicts are lexical-presence verdicts only. 'sufficient_lexically' is not an approval. "
            "No scenario is approved for training."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("rows", "scenarios", "variant_verdicts",
                                              "counterfactual_classes", "approved_for_training")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
