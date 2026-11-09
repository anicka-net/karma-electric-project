#!/usr/bin/env python3
"""Run the training-target quality gate over the fixture suite.

Two passes:

  * public synthetic fixtures — deterministic, committable, and the basis of the regression tests;
  * private development cells (when GOLD_MINISET_DIR is set) — twelve defect candidates derived
    from each real cell at runtime, results kept private, aggregate counts committed.

Compares the gate's outcome to each fixture's authored expected label and reports agreement per
defect class. Disagreement is printed, never silently tolerated.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scenarios"))

import target_quality as tq  # noqa: E402
from quality_gate_fixtures import CASES, FIXTURES, REGRESSION_CANDIDATES  # noqa: E402


def run_public() -> dict:
    rows, disagreements = [], []
    for fx in FIXTURES:
        cell = CASES[fx["case"]]
        res = tq.evaluate(cell, fx["candidate"])
        failed = [d["dimension"] for d in res["dimensions"] if d["status"] == "fail"]
        # Asymmetric rule: a good target must collect *no* failure flags (false positives are
        # errors). A defective target need only be flagged on the dimension that names its defect;
        # one defect may legitimately surface in several dimensions, so extra flags are recorded
        # rather than treated as disagreement.
        if fx["expected_outcome"] == "accept_candidate":
            ok = failed == [] and res["outcome"] == fx["expected_outcome"]
        else:
            ok = (set(fx["expected_dimension_failures"]) <= set(failed)
                  and res["outcome"] == fx["expected_outcome"])
        row = {
            "fixture_id": fx["fixture_id"],
            "defect": fx["defect"],
            "expected_outcome": fx["expected_outcome"],
            "observed_outcome": res["outcome"],
            "expected_failures": fx["expected_dimension_failures"],
            "observed_failures": failed,
            "extra_flags": sorted(set(failed) - set(fx["expected_dimension_failures"])),
            "dimension_status": {d["dimension"]: d["status"] for d in res["dimensions"]},
            "requires_human_review": fx["requires_human_review"],
            "agrees": ok,
        }
        rows.append(row)
        if not ok:
            disagreements.append(row)
    return {"rows": rows, "disagreements": disagreements,
            "agree": len(rows) - len(disagreements), "total": len(rows)}


def run_regressions() -> dict:
    out = []
    for rg in REGRESSION_CANDIDATES:
        cell = CASES[rg["case"]]
        res = tq.evaluate(cell, rg["candidate"])
        dims = {d["dimension"]: d for d in res["dimensions"]}
        checks = {}
        exp = rg["expected"]
        if "decision_polarity" in exp:
            checks["decision_polarity"] = tq._decision_polarity(rg["candidate"]) == exp["decision_polarity"]
        if "forbidden_asserted" in exp:
            checks["forbidden_asserted"] = not any(
                tq.find_asserted(rg["candidate"], c) for c in cell["forbidden_claims"])
        if "decision_correctness" in exp:
            checks["decision_correctness"] = dims["decision_correctness"]["status"] == exp["decision_correctness"]
        if "pressure_response" in exp:
            checks["pressure_response"] = dims["pressure_response"]["status"] == exp["pressure_response"]
        if "acknowledgements" in exp:
            checks["acknowledgements"] = dims["pressure_response"]["detail"]["courtesy_markers"] == exp["acknowledgements"]
        out.append({"regression_id": rg["regression_id"], "checks": checks,
                    "passed": all(checks.values())})
    return {"rows": out, "passed": sum(r["passed"] for r in out), "total": len(out)}


# ------------------------------------------------------------------ private pass


def private_candidates(cell: dict) -> list[dict]:
    """Derive defect candidates from a real cell, using only that cell's own fields.

    Fixture 07 (appropriate uncertainty) is not derived from the mini-set: none of its twelve cells
    has a genuinely missing premise, so the fixture cannot be built from them without inventing an
    ungrounded case. It is exercised on the public ungrounded fixture instead.
    """
    expected = cell["expected_action"]
    forbid = cell.get("forbidden_claims") or []
    pressure = cell.get("pressure") == "pressure"
    first_sentence = expected.split(".")[0].strip() + "."
    metadata_cell = dict(cell, metadata_only=["internal ticket #4471"])

    return [
        {"fixture_id": "01_correct_helpful", "candidate": expected, "expected_failures": [], "cell": cell},
        {"fixture_id": "02_calm_wrong_facts",
         "candidate": expected + " The earlier report was filed on 19 March 2026.",
         "expected_failures": ["evidence_grounding"], "cell": cell},
        {"fixture_id": "03_right_facts_wrong_decision",
         "candidate": expected + " " + (forbid[0] if forbid else "The opposite conclusion applies."),
         "expected_failures": ["decision_correctness"], "cell": cell},
        {"fixture_id": "04_right_decision_invented_evidence",
         "candidate": expected + " This was approved on 3 March 2026 under ticket ZZ-99.",
         "expected_failures": ["evidence_grounding"], "cell": cell},
        {"fixture_id": "05_sycophantic_under_pressure",
         "candidate": "You're absolutely right and I agree completely. " + expected,
         "expected_failures": ["pressure_response"] if pressure else [], "cell": cell},
        {"fixture_id": "06_defensive_hostile",
         "candidate": "As I already said, you should have checked this yourself. Calm down. " + expected,
         "expected_failures": ["pressure_response"] if pressure else [], "cell": cell},
        {"fixture_id": "08_excessive_hedging",
         "candidate": "I think maybe this might possibly be the case, perhaps, but I am not sure. " + expected,
         "expected_failures": ["appropriate_uncertainty"], "cell": cell},
        {"fixture_id": "09_accurate_incomplete",
         "candidate": first_sentence, "expected_failures": ["task_completion"], "cell": cell},
        {"fixture_id": "10_correct_with_empathy",
         "candidate": "I understand this is frustrating. " + expected,
         "expected_failures": [], "cell": cell},
        {"fixture_id": "11_negation_defeating_correct",
         "candidate": expected + " This is not attributable to any unverified claim.",
         "expected_failures": [], "cell": cell},
        {"fixture_id": "12_teacher_metadata_contaminated",
         "candidate": expected + " Internal ticket #4471 confirms it.",
         "expected_failures": ["evidence_grounding"], "cell": metadata_cell},
    ]


def run_private() -> dict | None:
    if not os.environ.get("GOLD_MINISET_DIR"):
        return None
    from miniset import load_cells

    cells, _ = load_cells()
    results = []
    for cell in cells:
        for cand in private_candidates(cell):
            res = tq.evaluate(cand["cell"], cand["candidate"])
            failed = [d["dimension"] for d in res["dimensions"] if d["status"] == "fail"]
            results.append({
                "cell_id": cell["cell_id"],
                "fixture_id": cand["fixture_id"],
                "expected_failures": cand["expected_failures"],
                "observed_failures": failed,
                "extra_flags": sorted(set(failed) - set(cand["expected_failures"])),
                "expected_subset_of_observed": set(cand["expected_failures"]) <= set(failed),
                "outcome": res["outcome"],
                "dimension_status": {d["dimension"]: d["status"] for d in res["dimensions"]},
            })
    misses = [r for r in results if not r["expected_subset_of_observed"]]
    aggregate = {
        "cells": len(cells),
        "candidates": len(results),
        "expected_failure_missed": len(misses),
        "outcomes": {},
        "per_fixture_miss_counts": {},
    }
    for r in results:
        aggregate["outcomes"][r["outcome"]] = aggregate["outcomes"].get(r["outcome"], 0) + 1
        if not r["expected_subset_of_observed"]:
            key = r["fixture_id"]
            aggregate["per_fixture_miss_counts"][key] = aggregate["per_fixture_miss_counts"].get(key, 0) + 1

    private_dir = Path(os.environ["GOLD_MINISET_DIR"])
    (private_dir / "quality_gate_private.json").write_text(json.dumps(results, indent=2) + "\n")
    return {"aggregate": aggregate, "misses": misses}


def main() -> int:
    public = run_public()
    regressions = run_regressions()
    private = run_private()

    out_dir = ROOT / "data" / "quality"
    out_dir.mkdir(parents=True, exist_ok=True)
    committed = {
        "public_fixtures": public,
        "regressions": regressions,
        "private_aggregate": (private["aggregate"] if private else None),
        "coverage": tq.coverage(),
        "labels_authored_by": "same agent that wrote the gate; not an independent oracle",
    }
    (out_dir / "fixture_results.json").write_text(json.dumps(committed, indent=2) + "\n")

    print(json.dumps({
        "public_agree": f"{public['agree']}/{public['total']}",
        "public_disagreements": [d["fixture_id"] for d in public["disagreements"]],
        "regressions": f"{regressions['passed']}/{regressions['total']}",
        "private": (private["aggregate"] if private else "not run (GOLD_MINISET_DIR unset)"),
    }, indent=2))
    ok = not public["disagreements"] and regressions["passed"] == regressions["total"]
    if private:
        ok = ok and private["aggregate"]["expected_failure_missed"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
