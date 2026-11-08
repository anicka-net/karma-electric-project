# ReLIFT as an exploratory design extension

Reference: https://arxiv.org/abs/2506.07527
Status: proposal only. Nothing run. No reinforcement learning is permitted in this workstream.

## Why it fits

This dataset produces a specific, observable failure mode: a model that is correct on the
neutral variant and wrong on the pressure variant of the *same* case, with the same facts and
the same correct decision. That pair is a direct measurement of the thing the experiment is
about, and it is exactly the kind of signal a calibration-aware sampling method can exploit.

Balanced random sampling treats those pairs as noise. If most cases are answered correctly
under both framings, the gradient is dominated by cases the model already handles, and the
pressure failures are a small minority of the batch.

## Proposed comparison

Two arms, identical in every respect except which training cases are selected:

| Arm | Sampling rule |
| --- | --- |
| A | Balanced sampling: uniform over the training split, stratified only by family and condition so the condition mix matches |
| B | Calibration-failure-targeted: oversample cases where the base student is neutral-correct and pressure-wrong |

Requirements:

- **Same cases, different weights.** Both arms draw from the same 84 training cases; no new data
  is authored for arm B.
- **Matched training tokens.** Total supervised tokens equal within 2% across arms. Selection
  changes composition, not budget.
- **Matched condition mix, where possible.** If arm B concentrates on pressure variants, report
  the achieved mix rather than pretending it matched.
- **Same hyperparameters, same seed set, same number of steps.** If step count must differ to keep
  tokens matched, report both.

## The selection rule must be computed before training, not during

Arm B's weights come from a fixed calibration probe on the base student: run both variants of
every training scenario, score correctness mechanically (fact coverage + decision signal +
deliverable checks), and freeze the resulting partition. The partition is recorded with hashes
so it cannot drift between arms.

## Independence of the confirmatory evaluation

The confirmatory semantic evaluation dataset must not be derived from calibration-failure
selection. Concretely:

- The six held-out cases (`eq2-f4-003`, `eq2-f5-005`) are evaluation-only and are never used for
  calibration or sampling.
- A separate held-out scenario set must be authored for confirmation, disjoint from all 30
  training scenarios, and frozen before any training run.
- The calibration probe's outputs may not be reused as evaluation labels.

Without this, arm B's advantage is partly definitional: it is trained on the measurement it is
then scored against.

## Metrics

Primary: pressure-wrong rate on the independent confirmatory set, comparing arm A and arm B on
the same prompts with the same sampling parameters and the same N.

Secondary, reported but not gating:

- neutral-correct rate (a check that arm B did not trade accuracy for pressure robustness);
- over-acknowledgement rate under pressure (E-condition discipline);
- deliverable-check pass rate on mechanically checkable cases.

## Decision rule, declared before running

The comparison is only interesting if arm B improves pressure-wrong rate *without* worsening
neutral-correct rate beyond the pre-declared tolerance. Otherwise the result is a
capability/robustness trade, which is a different claim.

Report a confidence interval over the paired difference, and report the number of cases where
the two arms disagree — with 84 training cases and a small student, a difference on a handful of
cases is not a result.

## Risks, named

- **Selection leakage**: the calibration probe sees the same cases it later scores. Mitigated only
  by the independent confirmatory set, not by cleverness in the probe.
- **Small n**: 30 scenarios means the targeted subset may be a dozen cases. Any measured
  difference will be fragile.
- **Confounded by condition mix**: arm B may end up with more pressure examples, so "targeted
  sampling works" and "more pressure examples work" are not distinguished by this design alone.
  A third arm (uniform but pressure-heavy) would be needed to separate them, and should be
  considered before running two arms.
- **No RL**: this proposal is SFT sampling only. Nothing here authorises reward-based training.

## Sequencing

Depends on: human-approved data, the native-thinking pilot, and a frozen confirmatory set. None
of those exist yet, so this stays a proposal.
