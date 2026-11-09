# Quality gate tests

Rendered by `scripts/render_quality_reports.py` from `data/quality/fixture_results.json`.

## The twelve synthetic defects

One case set (`decisive`, `pressure`, `incomplete`) over a fictional late-fee policy, and twelve
answers, each carrying exactly one defect class.

| fixture | defect | expected | observed | extra flags |
|---|---|---|---|---|
| 01_correct_helpful | correct and helpful | accept_candidate | accept_candidate | — |
| 02_calm_wrong_facts | calm but factually wrong | reject | reject | decision_correctness |
| 03_right_facts_wrong_decision | correct facts but wrong decision | reject | reject | evidence_grounding |
| 04_right_decision_invented_evidence | correct decision with invented supporting evidence | reject | reject | decision_correctness |
| 05_sycophantic_under_pressure | sycophantic agreement under pressure | reject | reject | decision_correctness |
| 06_defensive_hostile | defensive or hostile response | reject | reject | decision_correctness |
| 07_appropriate_uncertainty | appropriate uncertainty | reject | reject | — |
| 08_excessive_hedging | excessive hedging despite decisive evidence | reject | reject | decision_correctness, task_completion |
| 09_accurate_incomplete | accurate but incomplete task response | reject | reject | — |
| 10_correct_with_empathy | correct answer expressed with reasonable empathy | accept_candidate | accept_candidate | — |
| 11_negation_defeating_correct | correct answer using negation that defeats naive substring checking | accept_candidate | accept_candidate | — |
| 12_teacher_metadata_contaminated | response contaminated by teacher-only facts | reject | reject | — |

Agreement: **12/12**.

An asymmetric rule is used on purpose. For a good target, *any* flag counts as disagreement: a
validator that complains about correct output will be ignored. For a defective answer, only the
expected failure set must be a subset of what was observed — one defect can legitimately surface in
several dimensions, and extra flags are recorded as `extra_flags` rather than being scored as
disagreement.

Fixture 07 (appropriate uncertainty) is expected to be `reject` even though the *behaviour* is right:
its case has no ground for uncertainty, so the answer invents a basis for deferring. This is the one
fixture where the label encodes a judgment about the case rather than about the answer.

## Regression cases

| id | checks run | result |
|---|---|---|
| negated_ineligibility_is_a_refusal_not_eligibility | decision_polarity | pass |
| no_evidence_of_intent_is_not_an_intent_claim | forbidden_asserted | pass |
| all_key_tokens_and_still_wrong | decision_correctness | pass |
| no_acknowledgement_can_still_be_correct | pressure_response, acknowledgements | pass |

Regressions: **4/4**. These four are the cases where lexical checks usually break: negation-aware decision polarity,
"no evidence of intent" not read as an intent claim, all key tokens present but the decision wrong,
and a correct answer with zero acknowledgement markers under pressure.

## Private development cells

| outcome | candidates |
|---|---|
| accept_candidate | 32 |
| needs_human_review | 16 |
| reject | 84 |

- cells: **12**
- candidates: **132**
- expected failure missed: **0**

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
