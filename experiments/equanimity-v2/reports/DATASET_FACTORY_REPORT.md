# Equanimity v2: dataset factory and Azure teacher pilot

Dataset version **v0.2.0**. Pilot. No model trained. No dataset published. Not merged.

This report supersedes the v0.1.1 version. The v0.1.1 controls were invalid and the corrections
are summarised in `REVIEW_DISPOSITION.md`; this document describes the current state.

## What this is

A reproducible, auditable pipeline for scenario-based SFT data about equanimity under emotional
pressure. `experiments/equanimity/` — the original experiment — is untouched.

The original experiment produced 203 calm responses and trained Qwen3-4B on them; jailbreak harm
fell 75% → 17%. That is a result about refusal under pressure. It is not a dataset about staying
accurate and appropriately assertive while someone is hostile. A model trained only on calm-toned
text can learn passivity: gentle register, wrong action, polite refusal, or agreement with the
user instead of the facts.

v2 is built around that hazard. Every case has a checkable correct decision and a required
assertiveness level. A reply that is calm but wrong fails. A reply that is calm but passive fails.
A reply that agrees with the user fails.

## The contrast design

| Variant | Facts | Register | Correct decision | What it measures |
| --- | --- | --- | --- | --- |
| `neutral` | A | plain | X | baseline |
| `pressure` | A | hostile / pressing | X | invariance under emotional pressure |
| `counterfactual` | B | plain | Y ≠ X | sensitivity to a changed fact |

The load-bearing property: `pressure` changes nothing except the user's message and its emotional
metadata. `validate_triple()` enforces same facts, same decision, same decision type, same
assertiveness, different message. If a pressure variant quietly changes what is true, the triple
measures reactivity instead of invariance, and the build fails.

The crossed cell — pressure *and* a changed fact — is not generated. It needs hand-authored
messages. Recorded as a limitation.

## The three conditions (corrected)

All three are correct, complete and length-matched. They differ in exactly one axis.

| Condition | Max acknowledgements of the user's emotional state | Role |
| --- | --- | --- |
| `E` equanimity | 1, plus no reactive phrase | treatment |
| `S` style-matched | 0 | acknowledgement ablation |
| `G` generic | unconstrained | ordinary helpful baseline |

Every condition must preserve facts, reach the correct decision, deliver the actual artifact with
the required assertiveness, and land in the 60–320 word band. `T08_acknowledgement_policy` and
`T09_no_reactive_phrase` are the condition-specific checks; fact coverage, decision signal and
deliverable checks apply to all three.

Length matching is a corpus property, checked by `corpus_audit.audit_target_set()` across each
scenario triple (tolerance 1.30), not per target.

`S` and `G` are not degraded controls. Nothing is trained on deliberately bad output. The old
sycophantic and hollow prompts are gone; if a diagnostic collection of deliberately defective
responses is ever wanted, it belongs in an evaluation set, never labelled a control.

## Refusal supervision

The equanimity treatment must not teach refusal. Six cases (`eq2-f4-003`, `eq2-f5-005`, three
variants each) have `decision_type: decline_scope`; they are reassigned to `split: heldout`, with
the original split and reason preserved in `provenance.reassignment_history`. Nothing is deleted.

`src/corpus_audit.py` enforces, and the build fails on violation:

- no `decline_scope` case in train/dev/test;
- every held-out case carries a reassignment record;
- only refusal-shaped cases may be held out;
- held-out stays a minority (84 training / 6 held out).

Assertiveness and urgency remain in ordinary training cases: `escalate_urgently` cases teach
decisive action, which is not refusal.

## Deliverable checks

Token presence was not enough: a target that never produced the requested patch was accepted
because it mentioned `tmp_path`. Cases now declare `deliverable_checks`:

`code_fence`, `sql_keywords`, `numeric_includes`, `json_parses`, `imperative_includes`,
`regex_any`, `regex_none` — each with `severity: required|advisory`.

All 30 scenarios declare checks, with separate `cf` variants where the counterfactual changes the
numbers. Examples: `eq2-f1-001` requires a python code fence and `tmp_path_factory`; `eq2-f2-001`
requires `LEFT JOIN`; `eq2-f3-002` requires a concrete emergency action phrase, not the word
"urgent"; `eq2-f6-001` requires the numbers 512 and 700.

The prompts no longer ban markdown, code blocks or structure. Format follows the task.

### What the checks cannot do

They are shape checks, not correctness checks. There is no execution, no fixture evaluation, no
arithmetic verification, no entailment model. `test_deliverable_checks_catch_some_contradictions_but_not_all`
asserts the boundary: an answer containing the required action phrase *and* the opposite
recommendation passes every check.

Token coverage is a presence check. A sentence containing `88/54`, `118`, `3.1` and `confusion`
while recommending the opposite of the correct action passes it. Human review is not optional.

## Results

| Item | Value |
| --- | --- |
| Scenarios | 30 (5 per family, 6 families) |
| Cases | 90 (30 neutral, 30 pressure, 30 counterfactual) |
| Training / held-out | 84 / 6 |
| Cases passing validation | 90 |
| Corpus audit | pass |
| Triple-level failures | 0 |
| Cross-scenario near-duplicates (Jaccard ≥ 0.80) | 0 |
| Offline tests | 132 passed (with evidence dir mounted), 131 passed + 1 skipped otherwise |
| Live teacher calls in the recorded run | 18 (v0.1.0 contract) |
| Tokens | 20,058 of a 50,000 cap |

### The recorded 18-call run is superseded

It ran under the v0.1.0 contract, in which S was deliberately sycophantic and G deliberately
useless. Re-validating that stored text against v0.2.0 fails **12 of 18** rows, and **every** S and
G target fails fact-token coverage.

That is not a teacher failure. It is the old prompts asking for degraded output. It is also the
clearest evidence that the old controls could not have supported a causal claim: E was the only
arm with correct supervision.

`data/smoke/RUN_RECORD.json` records status `superseded` and `usable_as_training_targets: 0`.

The stored text itself is held outside Git history (see `PUBLIC_ARTIFACT_POLICY.md`); the
repository keeps aggregates only.

### The three original failures were mine, not the teacher's

At the time, three of eighteen failed. All three were defects in my own checkers or key-token
selection: a meta-word (`confirms`) used as a required token, and a sycophancy phrase list missing
"I totally get" / "I completely understand". Re-validating the stored text flipped them to pass.
That is evidence about the checker only, which is why it is labelled revalidation and not a new run.

## Why positive checks rather than failure reasons

In a 600-row sample of `NousResearch/arete-data-pairs`, `in_sft_accepted` was essentially "no
filter reason recorded". Accepted rows averaged accuracy 2.48/5, and the first sampled row carried
a critical review note while being marked accepted.

Acceptance by absence of complaints is the failure mode this design avoids. `E` targets must
positively exhibit fact coverage, decision signal and the declared deliverable; the triple must
positively satisfy invariance. Failures produce structured `rejection_reason` codes and rejected
rows are written to `data/rejected/`, not dropped.

## Limitations

1. Every row is `review_status=draft`. No human has approved any case. Nothing may be scaled.
2. Facts and decisions were authored by the same agent. Their agreement is not independent
   evidence of correctness.
3. Clinical, legal, financial and tax content is illustrative and not practitioner-reviewed. It is
   structured to be checkable, not to be correct advice.
4. Counterfactual user messages are machine-derived (appended fact update), flagged in
   `provenance.generation_config` with `requires: human rewrite`.
5. The crossed cell (pressure + changed fact) is not generated.
6. Acknowledgement counting is phrase-based; paraphrases outside the list count as zero, which
   biases toward accepting a too-warm target.
7. Deliverable checks verify shape, not correctness or entailment.
8. 18 live calls at one temperature with no seed says nothing about teacher reliability or quality
   distribution. It is a feasibility check.
9. `chatml` and `harmony` are demonstration renderers checked against their grammars. Neither is a
   verified student pipeline. Native thinking preservation is not measured and not claimed; see
   `NATIVE_THINKING_PILOT.md`.
10. Cost of the recorded run is not asserted. Token counts are recorded; pricing was not consulted.
11. ReLIFT sampling comparison is a proposal, not a result.

## Verification

Offline, no network:

```
python3 src/build_dataset.py          -> 90 cases, 84/6 split, corpus audit pass
python3 src/corpus_audit.py           -> ok
python3 -m pytest tests/ -q           -> 132 passed
                                        (131 passed, 1 skipped when EQ2_EVIDENCE_DIR is unset,
                                         because the private-evidence hash check cannot run)
```

The build is deterministic given `EQ2_BUILD_UTC` (default `2026-11-07T00:00:00Z`). Changing it
changes every content hash.

## Reproduce

```bash
cd experiments/equanimity-v2
python3 src/build_dataset.py
python3 -m pytest tests/ -q
python3 scripts/run_teacher_smoke.py --dry-run          # 18 mock calls, temp dirs, budget enforced
EQ2_EVIDENCE_DIR=<private dir> python3 scripts/revalidate_smoke.py
```

A live run additionally needs `EQ2_AZURE_ENDPOINT`, `EQ2_AZURE_API_KEY` and an explicit
`--rows-dir` outside the repository. It must not be run before human review of the scenarios.

## Next steps, cheapest first

1. Human review of the 30 scenarios — clinical, legal and the two held-out families first. This is
   the gate.
2. Execute stage 0 and stage 1 of `NATIVE_THINKING_PILOT.md` (offline, tests the machinery, no
   compute).
3. Only then regenerate targets under v0.2.0: 18 calls, ~20k tokens, with human review of every
   output before any use.
4. Author the crossed cell by hand for a few scenarios.
5. Consider extending deliverable checks to execution (parse or run the code, evaluate SQL against
   a fixture) — the largest remaining gap between "shape is right" and "task is done".
6. ReLIFT comparison only after a frozen, independent confirmatory set exists.

## Layout

```
schema/semantic_case.v1.schema.json   canonical, model-agnostic case schema
scenarios/                            30 authored specs, heldout policy, deliverable checks
src/build_dataset.py                  spec -> 90 cases -> validated/rejected + manifest
src/validate.py                       per-case, triple-level and target validators
src/corpus_audit.py                   corpus invariants incl. no-refusal-supervision
src/serialize.py                      plain / chatml / harmony renderers, conditions
src/provider/azure_foundry.py         Azure adapter, fail-closed budget, mock client
prompts/target_E.md target_S.md target_G.md
scripts/run_teacher_smoke.py          bounded live run (raw rows never in repo)
scripts/revalidate_smoke.py           re-check stored text against the current contract
scripts/export_examples.py            serialized examples, written outside the repo
tests/                                132 offline tests, mostly negative controls
data/validated/cases.jsonl            90 cases
data/smoke/                           aggregates only; raw text held privately
reports/                              disposition, policy, pilot, proposal, provider, this file
```
