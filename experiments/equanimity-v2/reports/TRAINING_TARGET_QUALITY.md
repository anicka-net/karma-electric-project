# Training-target quality: rubric, acceptance policy, and the boundary with evaluation

This document specifies what the quality gate is for, what each of its six dimensions is meant to
catch, and what a verdict does and does not license. Measured results are in
`TARGET_VALIDATOR_REPORT.md` and `QUALITY_GATE_TESTS.md`, rendered from the run data.

The gate is a **training-data instrument**. It answers one question: *could this answer serve as
supervision for a model that must remain evidence-sensitive under pressure?* It does not answer
whether the model has equanimity, and it must not be used for that. §8 states the separation.

## 1. Six dimensions

| Dimension | Question | Severity |
|---|---|---|
| A. Evidence grounding | Does every factual assertion come from what the student can see? | critical |
| B. Decision correctness | Is the decision the case's own evidence supports — with the right polarity? | critical |
| C. Task completion | Does the answer deliver the requested artefact, not a fragment of it? | critical |
| D. Pressure response | Does the answer hold its judgement when the pressure is emotional rather than evidential? | advisory |
| E. Appropriate uncertainty | Is uncertainty expressed where the case justifies it, and absent where it does not? | advisory |
| F. Native-thinking compatibility | Is the serialization compatible with the model's own chat template, with no fabricated or teacher-derived reasoning? | advisory, but gates eligibility |

A critical failure is terminal: the outcome is `reject` and no accumulation of good advisory
statuses changes it. This is enforced by a test, not by convention. D and E are advisory because both
are phrase-detected proxies; a `fail` there is a reason to reject, but the absence of a fail is not
evidence of quality. F cannot be checked on plain text at all, so it returns `not_applicable` and
`training_target_eligible` stays false.

## 2. Decision rule

```
any critical fail, or a failed "insufficient_student_evidence" check   -> reject
any dimension in {needs_human_review}                                  -> needs_human_review
otherwise                                                             -> accept_candidate
```

`accept_candidate` carries three explicit falsehoods: `human_approved: false`,
`training_ready: false`, and no composite score. Its documented meaning is *"mechanically eligible
for human review"*. If a pipeline treats it as approval, the pipeline is wrong, and the test suite
pins the properties that make that misreading hard: there is no score field to threshold, and
`accept_candidate_meaning` is part of the result.

No weighted total is computed anywhere. A combined score would let a warm tone offset a fabricated
fact, and would hide which check failed. The seven statuses plus one outcome are the whole output.

## 3. What each dimension actually checks

Mechanical coverage is listed in `TARGET_VALIDATOR_REPORT.md`. The short version, and the honest
limits:

- **A** matches quantities, units, dates and metadata-only terms against the student-visible text.
  It detects *invented* values, not unsupported inferences. A sentence can be composed entirely of
  visible tokens and still assert something the evidence does not entail; that is not caught here.
- **B** reads decision polarity from a small outcome lexicon with negation handling, then checks the
  answer key, other-state values and declared forbidden conclusions. Where the case declares
  `human_adjudication_required`, B returns `needs_human_review` instead of guessing.
- **C** checks structural requirements per task type and a minimum length. It verifies shape, not
  correctness: an answer can satisfy every structural requirement and still be useless.
- **D** counts agreement markers, accusation adoption, defensiveness, retaliation, apology density,
  reassurance that replaces steps, and lost assertiveness. It is surface-level: quiet non-compliance
  and sarcasm are invisible to it.
- **E** distinguishes hedging (weak verbal modifiers) from uncertainty expressions ("does not
  establish", "unverified"), compares them to the case's declared uncertainty, and flags
  deferral-without-substance and confidence where the case says confidence is unwarranted. Omitting a
  caveat is recorded as a note, not a defect — an unanswered caveat is a quality issue, whereas
  asserting the opposite is a defect.
- **F** inspects representation metadata, refuses teacher-reasoning keys, refuses fabricated
  ` thinking` markers in candidate text, and when a tokenizer is available builds the example through
  the real chat template to confirm token alignment. It cannot confirm that a reasoning prefix
  *causes* the behaviour; that is a model experiment (`REASONING_PRESERVATION_PROTOCOL.md`, gate L2).

## 4. Layers, and who may decide what

| Layer | Actor | May do | May not do |
|---|---|---|---|
| mechanical | validator | flag, reject on critical fail, queue | approve, score, guess on undecidable cases |
| semantic rubric | judge (model or person) | answer six rubric questions, propose accept/reject | approve; the sheet sets `judge_may_approve: false` and `human_decision: null` |
| adjudication | named human | accept or reject, with reasons | delegate the decision to the validator's outcome |

The six rubric questions are asked of every candidate: does the answer use only the given evidence;
is the decision the one the evidence supports; is the requested thing delivered; does it stay
non-reactive without becoming cold or evasive; is uncertainty placed where the case justifies it; and
does it avoid asserting anything about hidden reasoning. Each question is answered with a verdict and
a quoted piece of evidence, so a disagreement is discussable rather than a vibe.

## 5. Acceptance policy for future teacher generations

When GPT-OSS teacher generations resume, every candidate goes through the same three layers, in this
order, and stops at the first decisive outcome:

1. **Mechanical gate.** Critical fail → `reject`, recorded with the failing check. Nothing is
   regenerated automatically; a rejection is data about the prompt or the case, not only about the
   sample.
2. **Semantic rubric.** A blinded judge answers the six questions. Agreement with the mechanical
   outcome is recorded; disagreement goes to layer 3 rather than being averaged away.
3. **Human adjudication.** A named person decides. The decision, the reason and the quote are stored
   with the candidate.

Outcome vocabulary is fixed: `accept_candidate`, `reject`, `needs_human_review`. There is no
"probably fine". A candidate that no layer resolved stays `needs_human_review` — it does not decay
into acceptance by timeout.

Coverage is reported per dimension per batch: how many candidates each check actually examined, how
many were undecidable, and how many rejections came from each check. A batch whose evidence
dimension was `not_applicable` for most candidates is reported as such, because "0 rejections" then
means the check did not run.

## 6. How semantic-judge reliability would be established

Not yet established. The plan, cheapest first:

- **Blinded duplication.** A stratified sample of candidates (good, borderline, defective) is reviewed
  twice by the same judge with order and ids shuffled. Reported: self-agreement rate and where it
  breaks.
- **Human agreement.** The same sample reviewed by a person. Reported: agreement rate, Cohen's κ, and
  the confusion matrix with the disagreement cases quoted in full. A judge that agrees on the easy
  strata and disagrees on the borderline ones is usable only for triage.
- **Position and label bias.** Pairs of nearly identical candidates, presented in both orders. A judge
  that prefers the first, or that prefers the answer whose case is labelled "pressure", is not
  measuring the answer.
- **Adversarial set.** The twelve synthetic defects plus the four regressions, expanded with negated
  and metadata-contaminated variants. A judge that accepts any of them is not ready.
- **Adjudication on disagreement.** Every human-judge disagreement is resolved and the resolution is
  kept, so the judge's error pattern is documented rather than smoothed.
- **Stop rule.** Until agreement on the borderline stratum is established, judge output is labelled
  advisory and the gate's mechanical verdict is what blocks a candidate.

## 7. Failure modes the gate is designed around

- **Tone buying off a wrong decision.** Prevented by critical dims and by having no score.
- **Lexical rejection of correct answers.** The refund and negation fixtures exist because a bare
  substring check rejected an answer that said "the 14-day window does not apply" — correct — and
  rejected "I cannot tell whether it was intentional" — also correct. Forbidden claims are matched
  clause-locally and negation-aware; `must_exclude` remains a raw value check, used only for
  state confusion.
- **Metadata leaking into the target.** A teacher that sees `expected_action` can write an answer that
  cites a fact the student never had. The gate treats metadata-only terms as invented evidence.
- **Fabricated reasoning.** Refused by name: `teacher_reasoning`, `analysis`,
  `teacher_reasoning_content`, and any `reasoning_origin` other than `student` or
  `synthetic_placeholder`.
- **Silent truncation.** If an answer does not fit or does not start on a token boundary, the
  serializer fails closed rather than trimming.

## 8. Separation from behavioural evaluation and from the causal experiment

Three different questions, three different instruments, and they must not share a verdict:

| Question | Instrument | Evidence |
|---|---|---|
| Is this answer usable as supervision? | this gate | per-candidate checks, human adjudication |
| Does the trained model behave differently? | behavioural evaluation on held-out scenarios | paired comparisons, pre-registered metrics |
| Did the treatment cause the difference? | factorial design with a control arm | 2×2 cells, token-matched filler, frozen holdout |

The gate cannot be the behavioural metric even though both read the same dimensions. If training
targets are selected by a validator that also scores the model, the model is being graded on its
resemblance to the validator's taste — a closed loop. Two consequences are enforced:

- The gate never sees model outputs as targets. Its inputs are cases and candidate answers, never a
  trained model's generations on the evaluation set.
- Behavioural evaluation uses scenarios and rubrics fixed before training, scored by humans or by a
  judge whose reliability was established independently (see `TREATMENT_IDENTIFICATION.md` for what
  the current design can and cannot identify).

The causal claim is narrower still. Because E and S currently differ operationally only in the target
acknowledgement policy, a positive result licenses "targets with one acknowledgement clause rather
than none changed measured behaviour by Δ (CI)" — not "equanimity was trained in". See
`TREATMENT_IDENTIFICATION.md` §5 for the confound ledger.

## 9. What is still unverified

- Entailment is not computed. A grounded-looking sentence may be unsupported.
- Decision polarity is phrase-based; unusual phrasings fall back to `needs_human_review`.
- Task completion is structural. Correctness of a delivered artefact is unchecked; the largest
  remaining gap is executing delivered code or SQL against a fixture.
- Pressure detection is surface-marker based and blind to quiet non-compliance.
- Uncertainty is case-declared, not derived. A case that declares the wrong uncertainty will produce
  the wrong verdict.
- The twelve fixture labels were authored by the same agent that wrote the gate. They pin behaviour;
  they are not an independent oracle, and the report says so where the numbers appear.
