# Karma Electric Agent Contract

This is the machine-facing execution contract for AI contributors.

## Work Order

1. inspect the touched script, artifact, or claim surface
2. identify which stable interface is affected
3. make the smallest defensible change
4. run the relevant tests or command-path checks
5. update docs if public behavior or public claims changed
6. report what was verified and what was not

Do not improvise a different order for convenience.

## Stable Interfaces

1. dataset snapshots in `datasets/`
2. adversarial test suite input in `data/adversarial-tests.jsonl`
3. training DB management scripts
4. public claim surfaces in `README.md`, `huggingface-model-card.md`, and `v*/README.md`

## Definition of Done

A contribution is complete when:

1. the touched interface still matches docs and tests
2. the relevant checks passed
3. changed public claims were updated everywhere they are surfaced
4. unresolved limits or unverified paths are reported explicitly

## Required Verification

- DB or export script changes:
  - `python3 -m pytest -q tests/`
- anti-judge changes:
  - `python3 -m pytest -q tests/`
- public-claim changes:
  - verify the same numbers across all claim surfaces
- heavy model/inference changes:
  - run what is feasible
  - if not feasible, state that clearly rather than bluffing

## Public Claims

README, model card, and version READMEs are product surface.

Do not:

- leave version counts inconsistent
- leave evaluation numbers inconsistent across docs
- describe research hypotheses as established facts
- present unrun comparisons as verified results
