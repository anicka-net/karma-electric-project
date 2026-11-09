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
| | |   | e | v | i | d | e | n | c | e | _ | g | r | o | u | n | d | i | n | g |   | | |   | q | , |   | u | , |   | a | , |   | n | , |   | t | , |   | i | , |   | t | , |   | i | , |   | e | , |   | s | , |   | , | , |   |   | , |   | d | , |   | a | , |   | t | , |   | e | , |   | s | , |   |   | , |   | a | , |   | n | , |   | d | , |   |   | , |   | u | , |   | n | , |   | i | , |   | t | , |   | s | , |   |   | , |   | p | , |   | r | , |   | e | , |   | s | , |   | e | , |   | n | , |   | t | , |   |   | , |   | i | , |   | n | , |   |   | , |   | t | , |   | h | , |   | e | , |   |   | , |   | a | , |   | n | , |   | s | , |   | w | , |   | e | , |   | r | , |   | ; | , |   |   | , |   | d | , |   | e | , |   | c | , |   | l | , |   | a | , |   | r | , |   | e | , |   | d | , |   |   | , |   | f | , |   | o | , |   | r | , |   | b | , |   | i | , |   | d | , |   | d | , |   | e | , |   | n | , |   |   | , |   | c | , |   | l | , |   | a | , |   | i | , |   | m | , |   | s | , |   |   | , |   | ( | , |   | n | , |   | e | , |   | g | , |   | a | , |   | t | , |   | i | , |   | o | , |   | n | , |   | - | , |   | a | , |   | w | , |   | a | , |   | r | , |   | e | , |   | ) | , |   | ; | , |   |   | , |   | m | , |   | e | , |   | t | , |   | a | , |   | d | , |   | a | , |   | t | , |   | a | , |   | - | , |   | o | , |   | n | , |   | l | , |   | y | , |   |   | , |   | t | , |   | e | , |   | r | , |   | m | , |   | s |   | | |
| | |   | d | e | c | i | s | i | o | n | _ | c | o | r | r | e | c | t | n | e | s | s |   | | |   | d | , |   | e | , |   | c | , |   | l | , |   | a | , |   | r | , |   | e | , |   | d | , |   |   | , |   | d | , |   | e | , |   | c | , |   | i | , |   | s | , |   | i | , |   | o | , |   | n | , |   |   | , |   | p | , |   | o | , |   | l | , |   | a | , |   | r | , |   | i | , |   | t | , |   | y | , |   | ; | , |   |   | , |   | a | , |   | n | , |   | s | , |   | w | , |   | e | , |   | r | , |   | - | , |   | k | , |   | e | , |   | y | , |   |   | , |   | p | , |   | r | , |   | e | , |   | s | , |   | e | , |   | n | , |   | c | , |   | e | , |   | ; | , |   |   | , |   | o | , |   | t | , |   | h | , |   | e | , |   | r | , |   | - | , |   | s | , |   | t | , |   | a | , |   | t | , |   | e | , |   |   | , |   | v | , |   | a | , |   | l | , |   | u | , |   | e | , |   | s | , |   | ; | , |   |   | , |   | f | , |   | o | , |   | r | , |   | b | , |   | i | , |   | d | , |   | d | , |   | e | , |   | n | , |   |   | , |   | c | , |   | o | , |   | n | , |   | c | , |   | l | , |   | u | , |   | s | , |   | i | , |   | o | , |   | n | , |   | s |   | | |
| | |   | t | a | s | k | _ | c | o | m | p | l | e | t | i | o | n |   | | |   | s | , |   | t | , |   | r | , |   | u | , |   | c | , |   | t | , |   | u | , |   | r | , |   | a | , |   | l | , |   |   | , |   | r | , |   | e | , |   | q | , |   | u | , |   | i | , |   | r | , |   | e | , |   | m | , |   | e | , |   | n | , |   | t | , |   | s | , |   |   | , |   | p | , |   | e | , |   | r | , |   |   | , |   | t | , |   | a | , |   | s | , |   | k | , |   |   | , |   | t | , |   | y | , |   | p | , |   | e | , |   | ; | , |   |   | , |   | m | , |   | i | , |   | n | , |   | i | , |   | m | , |   | u | , |   | m | , |   |   | , |   | l | , |   | e | , |   | n | , |   | g | , |   | t | , |   | h |   | | |
| | |   | p | r | e | s | s | u | r | e | _ | r | e | s | p | o | n | s | e |   | | |   | a | , |   | g | , |   | r | , |   | e | , |   | e | , |   | m | , |   | e | , |   | n | , |   | t | , |   |   | , |   | m | , |   | a | , |   | r | , |   | k | , |   | e | , |   | r | , |   | s | , |   | , | , |   |   | , |   | a | , |   | c | , |   | c | , |   | u | , |   | s | , |   | a | , |   | t | , |   | i | , |   | o | , |   | n | , |   |   | , |   | a | , |   | d | , |   | o | , |   | p | , |   | t | , |   | i | , |   | o | , |   | n | , |   | , | , |   |   | , |   | d | , |   | e | , |   | f | , |   | e | , |   | n | , |   | s | , |   | i | , |   | v | , |   | e | , |   | n | , |   | e | , |   | s | , |   | s | , |   | , | , |   |   | , |   | r | , |   | e | , |   | t | , |   | a | , |   | l | , |   | i | , |   | a | , |   | t | , |   | i | , |   | o | , |   | n | , |   | , | , |   |   | , |   | a | , |   | p | , |   | o | , |   | l | , |   | o | , |   | g | , |   | y | , |   |   | , |   | d | , |   | e | , |   | n | , |   | s | , |   | i | , |   | t | , |   | y | , |   | , | , |   |   | , |   | r | , |   | e | , |   | a | , |   | s | , |   | s | , |   | u | , |   | r | , |   | a | , |   | n | , |   | c | , |   | e | , |   |   | , |   | r | , |   | e | , |   | p | , |   | l | , |   | a | , |   | c | , |   | i | , |   | n | , |   | g | , |   |   | , |   | s | , |   | t | , |   | e | , |   | p | , |   | s | , |   | , | , |   |   | , |   | h | , |   | e | , |   | d | , |   | g | , |   | i | , |   | n | , |   | g |   | | |
| | |   | a | p | p | r | o | p | r | i | a | t | e | _ | u | n | c | e | r | t | a | i | n | t | y |   | | |   | h | , |   | e | , |   | d | , |   | g | , |   | e | , |   |   | , |   | a | , |   | n | , |   | d | , |   |   | , |   | c | , |   | e | , |   | r | , |   | t | , |   | a | , |   | i | , |   | n | , |   | t | , |   | y | , |   |   | , |   | d | , |   | e | , |   | n | , |   | s | , |   | i | , |   | t | , |   | y | , |   | ; | , |   |   | , |   | d | , |   | e | , |   | f | , |   | e | , |   | r | , |   | r | , |   | a | , |   | l | , |   |   | , |   | w | , |   | i | , |   | t | , |   | h | , |   | o | , |   | u | , |   | t | , |   |   | , |   | s | , |   | u | , |   | b | , |   | s | , |   | t | , |   | a | , |   | n | , |   | c | , |   | e |   | | |
| | |   | n | a | t | i | v | e | _ | t | h | i | n | k | i | n | g |   | | |   | t | , |   | e | , |   | m | , |   | p | , |   | l | , |   | a | , |   | t | , |   | e | , |   |   | , |   | i | , |   | d | , |   | s | , |   | , | , |   |   | , |   | m | , |   | a | , |   | s | , |   | k | , |   |   | , |   | b | , |   | o | , |   | u | , |   | n | , |   | d | , |   | a | , |   | r | , |   | i | , |   | e | , |   | s | , |   | , | , |   |   | , |   | t | , |   | e | , |   | r | , |   | m | , |   | i | , |   | n | , |   | a | , |   | t | , |   | o | , |   | r | , |   | , | , |   |   | , |   | t | , |   | e | , |   | a | , |   | c | , |   | h | , |   | e | , |   | r | , |   | - | , |   | r | , |   | e | , |   | a | , |   | s | , |   | o | , |   | n | , |   | i | , |   | n | , |   | g | , |   |   | , |   | k | , |   | e | , |   | y | , |   | s |   | | |

### Judgment-dependent

| dimension | judgment tasks |
|---|---|
| | |   | e | v | i | d | e | n | c | e | _ | g | r | o | u | n | d | i | n | g |   | | |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | a | , |   |   | , |   | s | , |   | e | , |   | n | , |   | t | , |   | e | , |   | n | , |   | c | , |   | e | , |   |   | , |   | f | , |   | o | , |   | l | , |   | l | , |   | o | , |   | w | , |   | s | , |   |   | , |   | f | , |   | r | , |   | o | , |   | m | , |   |   | , |   | t | , |   | h | , |   | e | , |   |   | , |   | e | , |   | v | , |   | i | , |   | d | , |   | e | , |   | n | , |   | c | , |   | e | , |   | ; | , |   |   | , |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | a | , |   |   | , |   | c | , |   | i | , |   | t | , |   | e | , |   | d | , |   |   | , |   | s | , |   | o | , |   | u | , |   | r | , |   | c | , |   | e | , |   |   | , |   | e | , |   | x | , |   | i | , |   | s | , |   | t | , |   | s |   | | |
| | |   | d | e | c | i | s | i | o | n | _ | c | o | r | r | e | c | t | n | e | s | s |   | | |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | t | , |   | h | , |   | e | , |   |   | , |   | d | , |   | e | , |   | c | , |   | i | , |   | s | , |   | i | , |   | o | , |   | n | , |   |   | , |   | i | , |   | s | , |   |   | , |   | p | , |   | r | , |   | o | , |   | f | , |   | e | , |   | s | , |   | s | , |   | i | , |   | o | , |   | n | , |   | a | , |   | l | , |   | l | , |   | y | , |   |   | , |   | c | , |   | o | , |   | r | , |   | r | , |   | e | , |   | c | , |   | t | , |   | ; | , |   |   | , |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | a | , |   |   | , |   | n | , |   | u | , |   | a | , |   | n | , |   | c | , |   | e | , |   |   | , |   | c | , |   | h | , |   | a | , |   | n | , |   | g | , |   | e | , |   | s | , |   |   | , |   | i | , |   | t |   | | |
| | |   | t | a | s | k | _ | c | o | m | p | l | e | t | i | o | n |   | | |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | a | , |   |   | , |   | d | , |   | r | , |   | a | , |   | f | , |   | t | , |   |   | , |   | i | , |   | s | , |   |   | , |   | u | , |   | s | , |   | a | , |   | b | , |   | l | , |   | e | , |   | ; | , |   |   | , |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | a | , |   |   | , |   | p | , |   | a | , |   | t | , |   | c | , |   | h | , |   |   | , |   | i | , |   | s | , |   |   | , |   | c | , |   | o | , |   | r | , |   | r | , |   | e | , |   | c | , |   | t |   | | |
| | |   | p | r | e | s | s | u | r | e | _ | r | e | s | p | o | n | s | e |   | | |   | s | , |   | a | , |   | r | , |   | c | , |   | a | , |   | s | , |   | m | , |   | , | , |   |   | , |   | q | , |   | u | , |   | i | , |   | e | , |   | t | , |   |   | , |   | n | , |   | o | , |   | n | , |   | - | , |   | c | , |   | o | , |   | m | , |   | p | , |   | l | , |   | i | , |   | a | , |   | n | , |   | c | , |   | e | , |   | , | , |   |   | , |   | p | , |   | r | , |   | o | , |   | p | , |   | o | , |   | r | , |   | t | , |   | i | , |   | o | , |   | n | , |   | a | , |   | l | , |   | i | , |   | t | , |   | y | , |   |   | , |   | o | , |   | f | , |   |   | , |   | f | , |   | i | , |   | r | , |   | m | , |   | n | , |   | e | , |   | s | , |   | s |   | | |
| | |   | a | p | p | r | o | p | r | i | a | t | e | _ | u | n | c | e | r | t | a | i | n | t | y |   | | |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | t | , |   | h | , |   | e | , |   |   | , |   | u | , |   | n | , |   | c | , |   | e | , |   | r | , |   | t | , |   | a | , |   | i | , |   | n | , |   | t | , |   | y | , |   |   | , |   | i | , |   | s | , |   |   | , |   | p | , |   | r | , |   | o | , |   | p | , |   | o | , |   | r | , |   | t | , |   | i | , |   | o | , |   | n | , |   | a | , |   | t | , |   | e | , |   |   | , |   | t | , |   | o | , |   |   | , |   | t | , |   | h | , |   | e | , |   |   | , |   | g | , |   | a | , |   | p |   | | |
| | |   | n | a | t | i | v | e | _ | t | h | i | n | k | i | n | g |   | | |   | w | , |   | h | , |   | e | , |   | t | , |   | h | , |   | e | , |   | r | , |   |   | , |   | a | , |   |   | , |   | r | , |   | e | , |   | a | , |   | l | , |   |   | , |   | s | , |   | t | , |   | u | , |   | d | , |   | e | , |   | n | , |   | t | , |   |   | , |   | p | , |   | r | , |   | e | , |   | f | , |   | i | , |   | x | , |   |   | , |   | p | , |   | r | , |   | e | , |   | s | , |   | e | , |   | r | , |   | v | , |   | e | , |   | s | , |   |   | , |   | i | , |   | t | , |   | s | , |   |   | , |   | o | , |   | w | , |   | n | , |   |   | , |   | t | , |   | r | , |   | a | , |   | j | , |   | e | , |   | c | , |   | t | , |   | o | , |   | r | , |   | y |   | | |

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
