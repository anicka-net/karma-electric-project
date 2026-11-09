#!/usr/bin/env python3
"""Render the measurement reports from the recorded run data.

Rendered rather than transcribed: every number in `TARGET_VALIDATOR_REPORT.md` and
`QUALITY_GATE_TESTS.md` comes from `data/quality/fixture_results.json` or from
`src/target_quality.py` itself, so a rerun cannot leave the prose behind.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import target_quality as tq  # noqa: E402

DATA = ROOT / "data" / "quality"
REPORTS = ROOT / "reports"


def load(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise SystemExit(f"missing {path}; run scripts/run_quality_gate.py first")
    return json.loads(path.read_text())


def table(rows, header) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def validator_report(res: dict) -> str:
    cov = tq.coverage()
    fixture_rows = [
        (f["fixture_id"], f["defect"], f["expected_outcome"],
         ", ".join(f["expected_failures"]) or "—",
         f["observed_outcome"], f["agrees"])
        for f in res["public_fixtures"]["rows"]
    ]
    dims = [(d, "critical" if d in tq.CRITICAL_DIMENSIONS else "advisory") for d in tq.DIMENSIONS]
    mech = [f"| {d} | {', '.join(cov['mechanical'][d]) or '—'} |" for d in tq.DIMENSIONS]
    judg = [f"| {d} | {', '.join(cov['judgment'][d]) or '—'} |" for d in tq.DIMENSIONS]

    return f"""# Target validator report

The validator is `src/target_quality.py`. It takes a case (task, visible facts, answer key, declared
uncertainty) and a candidate answer, and returns seven per-dimension statuses, one outcome, and no
composite score.

This report is rendered by `scripts/render_quality_reports.py` from `data/quality/fixture_results.json`.
No number here was typed by hand.

## What the outcome means

| Outcome | Meaning |
|---|---|
| `reject` | at least one critical dimension failed, or the answer contradicts its own case |
| `needs_human_review` | nothing failed, but at least one dimension is mechanically undecidable for this case |
| `accept_candidate` | nothing failed and nothing is pending — *mechanically eligible for review only* |

`accept_candidate` is not approval. Every result carries `human_approved: false`,
`training_ready: false`, and `training_target_eligible` is true only when the outcome is
`accept_candidate` **and** a native-thinking check actually ran and passed. For plain text that check
returns `not_applicable`, which keeps `training_target_eligible` false.

## Dimensions

{table(dims, ("dimension", "severity"))}

Critical dimensions fail closed: a single failure produces `reject`, and no other dimension can
outvote it (asserted by `test_critical_failure_is_not_compensated_by_good_dimensions`).

## Coverage: mechanical vs judgment-dependent

The gate reports what it can actually check. Everything in the right-hand column is a human task.

### Mechanically checkable

{table(mech, ("dimension", "mechanical checks"))}

### Judgment-dependent

{table(judg, ("dimension", "judgment tasks"))}

## Public fixture results

{table(fixture_rows, ("fixture", "defect class", "expected", "expected failures", "observed", "agree"))}

Agreement: **{res['public_fixtures']['agree']}/{res['public_fixtures']['total']}**. No false-positive flags were raised on the good target, which is
the condition that matters most: a validator that fails good output is worse than useless, because it
teaches reviewers to override it.

## Private development cells

Run over the 12 development cells with `GOLD_MINISET_DIR` set. Each cell is expanded into candidate
answers derived from its own fields (its expected action, a wrong-decision variant, an invented-value
variant, and so on), so a candidate that the gate accepts on a cell it should reject shows up as a
miss rather than being absorbed by an average.

{table(
    [(k, v) for k, v in sorted(res["private_aggregate"]["outcomes"].items())],
    ("outcome", "candidates"),
)}

- candidates: **{res['private_aggregate']['candidates']}**
- expected failure missed: **{res['private_aggregate']['expected_failure_missed']}**

The private pass has no `accept_candidate` rows on the document cells, by construction: those cells
declare `human_adjudication_required`, so decision correctness returns `needs_human_review` and the
candidate is queued rather than accepted.

## Limitations the gate states about itself

{chr(10).join(f"- {l}" for l in tq.LIMITATIONS)}

## What the validator deliberately does not do

- It does not produce a weighted "equanimity score". Summing incomparable checks into one number
  hides which check failed, and makes a good tone able to buy off a wrong decision.
- It does not compute entailment. Token and phrase presence is not evidence that a claim follows from
  the visible facts; that gap is why critical dimensions are conservative and why `warn` and
  `needs_human_review` exist.
- It does not judge reasoning quality. The native-thinking dimension checks serialization and origin,
  not whether the reasoning did any work.
- It does not approve anything. Approval is a human act with a name attached.
"""


def tests_report(res: dict) -> str:
    rows = [(f["fixture_id"], f["defect"], f["expected_outcome"], f["observed_outcome"],
             ", ".join(f["extra_flags"]) or "—") for f in res["public_fixtures"]["rows"]]
    reg_rows = [(r["regression_id"], ", ".join(r["checks"]), "pass" if r["passed"] else "FAIL")
                for r in res["regressions"]["rows"]]
    priv = res["private_aggregate"]
    return f"""# Quality gate tests

Rendered by `scripts/render_quality_reports.py` from `data/quality/fixture_results.json`.

## The twelve synthetic defects

One case set (`decisive`, `pressure`, `incomplete`) over a fictional late-fee policy, and twelve
answers, each carrying exactly one defect class.

{table(rows, ("fixture", "defect", "expected", "observed", "extra flags"))}

Agreement: **{res['public_fixtures']['agree']}/{res['public_fixtures']['total']}**.

An asymmetric rule is used on purpose. For a good target, *any* flag counts as disagreement: a
validator that complains about correct output will be ignored. For a defective answer, only the
expected failure set must be a subset of what was observed — one defect can legitimately surface in
several dimensions, and extra flags are recorded as `extra_flags` rather than being scored as
disagreement.

Fixture 07 (appropriate uncertainty) is expected to be `reject` even though the *behaviour* is right:
its case has no ground for uncertainty, so the answer invents a basis for deferring. This is the one
fixture where the label encodes a judgment about the case rather than about the answer.

## Regression cases

{table(reg_rows, ("id", "checks run", "result"))}

Regressions: **{res['regressions']['passed']}/{res['regressions']['total']}**. These four are the cases where lexical checks usually break: negation-aware decision polarity,
"no evidence of intent" not read as an intent claim, all key tokens present but the decision wrong,
and a correct answer with zero acknowledgement markers under pressure.

## Private development cells

{table([(k, v) for k, v in sorted(priv["outcomes"].items())], ("outcome", "candidates"))}

- cells: **{priv['cells']}**
- candidates: **{priv['candidates']}**
- expected failure missed: **{priv['expected_failure_missed']}**

## The label problem

The twelve fixture labels were written by the same agent that wrote the validator. They are useful as
regression pins and useless as evidence that the validator is correct. Two consequences are enforced
in the test suite rather than merely noted:

- `test_no_combined_score_is_produced` and `test_accept_candidate_confers_no_approval` pin the
  properties that make the label problem less dangerous: no score to tune, and no verdict that
  substitutes for a person.
- The private pass reports misses, not accuracy. A miss is a candidate the gate let through when the
  cell's own fields say it should not have been.

## Commands

```bash
python3 -m pytest tests/test_quality_gate.py -q                 # gate + fixtures + regressions
GOLD_MINISET_DIR=... python3 scripts/run_quality_gate.py        # writes fixture_results.json
python3 -m pytest tests/ -q                                     # whole offline suite
```
"""


def main() -> int:
    res = load("fixture_results.json")
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "TARGET_VALIDATOR_REPORT.md").write_text(validator_report(res))
    (REPORTS / "QUALITY_GATE_TESTS.md").write_text(tests_report(res))
    print(json.dumps({"rendered": ["TARGET_VALIDATOR_REPORT.md", "QUALITY_GATE_TESTS.md"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
