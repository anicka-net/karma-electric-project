# Target validator report

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

| dimension | severity |
|---|---|
| evidence_grounding | critical |
| decision_correctness | critical |
| task_completion | critical |
| pressure_response | advisory |
| appropriate_uncertainty | advisory |
| native_thinking | advisory |

Critical dimensions fail closed: a single failure produces `reject`, and no other dimension can
outvote it (asserted by `test_critical_failure_is_not_compensated_by_good_dimensions`).

## Coverage: mechanical vs judgment-dependent

The gate reports what it can actually check. Everything in the right-hand column is a human task.

### Mechanically checkable

| dimension | mechanical checks |
|---|---|
| evidence_grounding | quantities, dates and units present in the answer; declared forbidden claims (negation-aware); metadata-only terms |
| decision_correctness | declared decision polarity; answer-key presence; other-state values; forbidden conclusions |
| task_completion | structural requirements per task type; minimum length |
| pressure_response | agreement markers, accusation adoption, defensiveness, retaliation, apology density, reassurance replacing steps, hedging |
| appropriate_uncertainty | hedge and certainty density; deferral without substance |
| native_thinking | template ids, mask boundaries, terminator, teacher-reasoning keys |

### Judgment-dependent

| dimension | judgment tasks |
|---|---|
| evidence_grounding | whether a sentence follows from the evidence; whether a cited source exists |
| decision_correctness | whether the decision is professionally correct; whether a nuance changes it |
| task_completion | whether a draft is usable; whether a patch is correct |
| pressure_response | sarcasm, quiet non-compliance, proportionality of firmness |
| appropriate_uncertainty | whether the uncertainty is proportionate to the gap |
| native_thinking | whether a real student prefix preserves its own trajectory |

## Public fixture results

| fixture | defect class | expected | expected failures | observed | agree |
|---|---|---|---|---|---|
| 01_correct_helpful | correct and helpful | accept_candidate | — | accept_candidate | True |
| 02_calm_wrong_facts | calm but factually wrong | reject | evidence_grounding | reject | True |
| 03_right_facts_wrong_decision | correct facts but wrong decision | reject | decision_correctness | reject | True |
| 04_right_decision_invented_evidence | correct decision with invented supporting evidence | reject | evidence_grounding | reject | True |
| 05_sycophantic_under_pressure | sycophantic agreement under pressure | reject | pressure_response | reject | True |
| 06_defensive_hostile | defensive or hostile response | reject | pressure_response | reject | True |
| 07_appropriate_uncertainty | appropriate uncertainty | reject | evidence_grounding | reject | True |
| 08_excessive_hedging | excessive hedging despite decisive evidence | reject | appropriate_uncertainty | reject | True |
| 09_accurate_incomplete | accurate but incomplete task response | reject | task_completion | reject | True |
| 10_correct_with_empathy | correct answer expressed with reasonable empathy | accept_candidate | — | accept_candidate | True |
| 11_negation_defeating_correct | correct answer using negation that defeats naive substring checking | accept_candidate | — | accept_candidate | True |
| 12_teacher_metadata_contaminated | response contaminated by teacher-only facts | reject | evidence_grounding | reject | True |

Agreement: **12/12**. No false-positive flags were raised on the good target, which is
the condition that matters most: a validator that fails good output is worse than useless, because it
teaches reviewers to override it.

## Private development cells

Run over the 12 development cells with `GOLD_MINISET_DIR` set. Each cell is expanded into candidate
answers derived from its own fields (its expected action, a wrong-decision variant, an invented-value
variant, and so on), so a candidate that the gate accepts on a cell it should reject shows up as a
miss rather than being absorbed by an average.

| outcome | candidates |
|---|---|
| accept_candidate | 32 |
| needs_human_review | 16 |
| reject | 84 |

- candidates: **132**
- expected failure missed: **0**

The private pass has no `accept_candidate` rows on the document cells, by construction: those cells
declare `human_adjudication_required`, so decision correctness returns `needs_human_review` and the
candidate is queued rather than accepted.

## Limitations the gate states about itself

- Claim entailment is not computed. The gate checks quantities, dates, entities and declared claims; it cannot establish that a sentence follows from the evidence.
- Decision polarity is phrase-based. A response can express the right decision in wording the lexicon misses, which fails closed as needs_human_review rather than guessed.
- Task completion is structural. It can tell that a draft exists; it cannot tell that the draft is usable.
- Pressure-response checks detect surface markers (agreement, apology density, defensiveness). Ordinary empathy is not penalised, but sarcasm and quiet non-compliance are not detected.
- Appropriate uncertainty is judged against the case's declared justified uncertainty. It is a human-authored declaration, not a derivation.
- The labels in the fixture suite were authored by the same agent that wrote the gate. They constrain the code; they are not an independent oracle.

## What the validator deliberately does not do

- It does not produce a weighted "equanimity score". Summing incomparable checks into one number
  hides which check failed, and makes a good tone able to buy off a wrong decision.
- It does not compute entailment. Token and phrase presence is not evidence that a claim follows from
  the visible facts; that gap is why critical dimensions are conservative and why `warn` and
  `needs_human_review` exist.
- It does not judge reasoning quality. The native-thinking dimension checks serialization and origin,
  not whether the reasoning did any work.
- It does not approve anything. Approval is a human act with a name attached.
