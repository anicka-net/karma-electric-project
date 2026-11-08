# Treatment identification — what the E/S/G conditions actually compare

Status: analysis of the existing v0.2.0 design. No new condition has been built. No model has
been trained. This document exists to stop a positive result from being over-read.

## 1. What the arms are, operationally

The three conditions share the scenario, the prompt set, the facts and the correct decision.
They differ in one authored field: how many acknowledgement clauses the target may contain.

| Condition | Acknowledgement cap | Other target properties |
|---|---|---|
| E | at most one | correct, task-completing, length-matched |
| S | zero | correct, task-completing, length-matched |
| G | unconstrained | correct, task-completing, length-matched |

"Length-matched" means the supervised-token budget is held in the same band across arms.
Correctness, urgency and deliverable coverage are the same in all three. There is no
deliberately degraded arm: S is not a rude control, and E is not a polite-but-incompetent
control.

So the single designed difference between E and S is **the presence of acknowledgement
clauses in the training target**. Call that TAP, target acknowledgement policy. G is the
unconstrained arm; it is a ceiling/natural-rate reference, not a treatment.

The evaluation set is pressure-framed prompts with human-adjudicated correctness.

## 2. What the contrast can identify

E vs S identifies the causal effect of TAP on behaviour measured by that evaluation, under
the assumption that nothing else differs between the arms. That is a **style-policy** effect.

It does not identify equanimity. The word "equanimity" in this project names a behavioural
claim: the response does not escalate, degrade or change its decision when the user becomes
hostile. No arm encodes that claim as a predicate. The nearest thing in the data is an
acknowledgement count, which is a surface marker of tone, not a behavioural property.

A target that acknowledges once and one that acknowledges never can both be perfectly
non-reactive; a target with one acknowledgement clause can be just as reactive in its
decision. The dataset cannot separate these.

## 3. Verdict

| Claim | Status |
|---|---|
| Effect of target acknowledgement policy on pressure-eval behaviour | **Partially identified.** Identified as a main effect of a style manipulation, confounded with token presence on affect-relevant spans and with evaluator preference. |
| Equanimity as non-reactivity under pressure | **NOT IDENTIFIED.** No arm trains or measures a non-escalation predicate independent of acknowledgement. |

If E beats S on the pressure eval, the licensed statement is:

> Training targets that contain one acknowledgement clause instead of none changed measured
> behaviour on this evaluation set by Δ (CI).

Nothing about equanimity follows. In particular, the result cannot be described as "teaching
equanimity", and it cannot be transferred to a claim that the model stays non-reactive under
pressure.

## 4. Competing explanations for E > S

Assume the arms are otherwise matched and the eval is fair. These are the live alternatives:

1. **Acknowledgement content.** Naming the user's emotion changes the user-visible interaction
   and the model's own continuation. The effect is about acknowledgement, not about
   robustness.
2. **Token presence.** E targets contain more tokens positioned on affect-relevant spans. Any
   difference could come from where attention is spent, independent of what those tokens say.
3. **Evaluator preference.** If the scorer is a model or a human reading for tone, it may
   prefer acknowledgement. The measurement then reflects preference, not task behaviour.
4. **In-distribution prompt advantage.** If E's targets were authored against the same pressure
   wording used at evaluation, E is closer to its training distribution. This raises accuracy
   without any robustness gain.
5. **Domain mix and length.** Small differences in scenario selection or answer length can move
   scores more than the treatment.

Alternatives 2 and 3 are the ones that most often masquerade as an equanimity result.

## 5. Confound ledger

| Confound | How it produces E > S | Control | Status |
|---|---|---|---|
| Acknowledgement content | affects tone-sensitive scoring | token-matched filler control (see §6) | not built |
| Token presence on affect spans | attention shift without semantic cause | filler arm with equal tokens, no acknowledgement | not built |
| Evaluator style preference | prefers acknowledgement | blind paired adjudication, order randomised | not built |
| Training/eval prompt overlap | in-distribution advantage | held-out prompts with different wording | partially: heldout split exists, wording overlap unmeasured |
| Length | longer answers score higher | supervised-token band matched | controlled by construction, not measured post-hoc |
| Domain mix | scenario selection effect | scenario-id-level splits | not built |

## 6. Cheapest decisive test

Four arms, all with the same facts, the same correct decision and the same supervised-token
count:

| Arm | Target contains | Purpose |
|---|---|---|
| N | no affect tokens | baseline |
| F | neutral filler tokens at the same positions and count as acknowledgement | token-presence control |
| A1 | one acknowledgement clause | treatment |
| A0 | zero acknowledgement clauses, one extra factual clause to match length | length control |

If A1 > F, the effect is about acknowledgement content. If A1 ≈ F > N, the effect is token
presence. If A1 ≈ N, there is no effect worth explaining.

That is four conditions over the same scenario set. It is cheap because the prompts already
exist; only targets need authoring and review.

## 7. The design that would identify the construct: 2x2 factorial

Input framing and target style are separate axes and have been conflated.

| | Reactive target | Non-reactive target |
|---|---|---|
| **Neutral input** | baseline accuracy | accuracy with non-reactive style |
| **Pressure input** | pressure failure | pressure robustness |

The treatment of interest is the **interaction** cell: pressure input with a non-reactive
target, compared against pressure input with a reactive target, with correctness and length
held constant. A main effect of target style on neutral inputs is a style result and must not
be reported as robustness.

`scenarios/four_cell.py` implements the input axis only (neutral/pressure for five existing
scenarios). The target axis does not exist yet, so the interaction is not currently estimable.

A non-reactive target needs a predicate that is not an acknowledgement count. Candidates:

- the decision does not change when the user's framing changes (measurable against the
  counterfactual pairs already in the audit);
- the response does not adopt the user's factual assertion without evidence (measurable
  against `premise_status` and `forbidden_claims`);
- the response does not escalate tone beyond a declared bound (needs human adjudication).

The first two are mechanical; the third is not. That asymmetry is why the document scenario in
the mini-set is flagged `human_adjudication_required`.

## 8. ReLIFT — exploratory design only

ReLIFT is a sampling design, not a training method here. Reinforcement learning is not
permitted in this project, so nothing below is runnable as-is.

Three sampling strategies, each selecting *scenarios* (not variants) into the training set:

| Strategy | Rule | What it would test |
|---|---|---|
| balanced | uniform over scenario ids | whether the effect exists at all |
| calibration-failure-targeted | prefer scenarios where the student's answer is wrong under pressure | whether targeting failures amplifies robustness |
| uniformly pressure-heavy | every training prompt pressure-framed | whether input mix alone drives robustness |

Leakage rules, all mandatory:

1. split by `scenario_id`, never by variant; a scenario's four cells stay together;
2. selection uses only the train split;
3. the confirmatory holdout is frozen before any selection and never inspected for selection;
4. selection history is recorded per scenario so the final set is auditable.

Confound to state up front: calibration-failure-targeted sampling selects harder items, so a
gain could be difficulty-matching rather than sampling. The control is a difficulty-matched
balanced arm selected on the same difficulty estimate.

Status: design only. No RL, no selection run, no reward model.

## 9. What would change the verdict

The verdict changes from NOT IDENTIFIED to identified when:

1. non-reactivity has a predicate that does not reduce to acknowledgement count;
2. targets are authored to differ only in that predicate, with correctness and length matched;
3. the evaluation includes the interaction cell, with blind human adjudication of correctness
   and of non-escalation;
4. a token-matched filler control exists, so token presence is excluded.

Until then the safe claim is the one in §3.
