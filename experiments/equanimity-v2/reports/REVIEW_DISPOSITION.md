# Review disposition

Reviewed head: `0a1aa89` (branch `feature/equanimity-v2-review`).
Corrections committed on the same branch. No force-push, no history rewrite, no merge,
no training, no paid API calls.

Status of the dataset: **pilot, not ready for SFT or scale.** That was true before the
review and it is still true; what changed is that the reasons are now fixed where they
were mechanically fixable, and named where they are not.

| # | Finding | Severity | Status |
| --- | --- | --- | --- |
| 1 | Public-repo hygiene: infrastructure metadata, generated content, private paths | High | Fixed forward; history cleanup pending human decision |
| 2 | S and G were deliberately degraded, so they were not causal controls | Critical | Fixed: all conditions now correct and length-matched |
| 3 | Refusal supervision in the equanimity treatment | High | Fixed: 6 cases reassigned to held-out, enforced by audit |
| 4 | Task-completion checks proved token presence, not deliverable completion | High | Partly fixed: per-case mechanical checks; entailment still absent |
| 5 | Provider budget omitted prompt tokens and did not count retries | High | Fixed; five regression tests added |
| 6 | Manual serialization treated as native SFT readiness | Medium | Fixed for format grammar; native pipeline deferred to a pilot |
| 7 | ReLIFT comparison absent | Medium | Proposal written, not run |

---

## 1. Public-repository hygiene

**Evidence.** `AZURE_TEACHER_REPORT.md` disclosed the hosting account, region, resource
group and endpoint hostname, and named an unrelated deployment. `data/smoke/` contained
`targets.jsonl`, `audit.jsonl` and `serialized_examples.jsonl` — the raw teacher output,
including the deliberately cruel S-condition text for `eq2-f4-003`. Scripts referenced a
local `/tmp` credential path.

**Fix applied.**

- `AZURE_TEACHER_REPORT.md` now records only what a reviewer needs: deployment name, type,
  model version, api-version, auth scheme. Account, region, resource group and endpoint are
  removed. The unrelated deployment is mentioned only as "not this one, not described here".
- Raw generations moved out of the tree to a local evidence directory selected by
  `EQ2_EVIDENCE_DIR`. Integrity is recorded in `data/smoke/PRIVATE_EVIDENCE.json` (filenames
  and SHA-256 only).
- `data/smoke/` now holds aggregates only: counts, check identifiers, hashes. A README
  explains what is held back and why.
- Scripts refuse to run without `EQ2_EVIDENCE_DIR`; no local path is embedded. Dry runs write
  to a temp directory, so a dry run cannot overwrite real evidence.
- `.gitignore` covers the raw filenames, plus `data/raw/` and `data/private/`.
- Regression tests scan the tree for absolute home paths, Azure identifiers, key-shaped
  literals, and for generated harmful text under `data/smoke/`.

**Unresolved.** The files were pushed in `59a0401` and remain in the published branch
history. Removing them from the current tree does not unpublish them. See
`PUBLIC_ARTIFACT_POLICY.md` for exactly what cleanup requires. Not performed: it needs
explicit human authorization, and it would rewrite published history.

## 2. Controls were not controls

**Evidence.** `CONDITIONS` defined S as "validation-first, concedes unsupported ground,
softens or abandons the deliverable" and G as "formulaically safe and hollow… withholds the
specific deliverable". Validation then *skipped* fact coverage for S and G, because requiring
correctness would have rejected every example. That is the definition of a confounded
comparison: E was the only arm with correct supervision, so any measured difference would be
attributable to supervision quality rather than to equanimity.

**Fix applied.** All three conditions now must preserve facts, reach the correct decision,
deliver the required artifact with the required assertiveness, and fall inside the same
supervised length band (60–320 words). The conditions differ in exactly one axis, which the
`Condition` dataclass now encodes as data:

| Condition | Max acknowledgements of the user's emotional state |
| --- | --- |
| E | 1 |
| S | 0 |
| G | unconstrained |

E additionally forbids the reactive repertoire (no "calm down", no defence, no grovelling).
S is the acknowledgement ablation: same content, same length, emotionally unengaged register.
G is the ordinary helpful baseline. `T08_acknowledgement_policy` enforces the policy and
`T09_no_reactive_phrase` enforces the E-specific ban.

**Evidence that this matters.** Re-validating the stored v0.1.0 text against the new contract
fails 12 of 18 rows, and **every** S and G target fails fact-token coverage. Those targets
were not weak controls; they were invalid ones.

**Unresolved.** Acknowledgement counting is phrase-based and paraphrases outside the pattern
list count as zero, which biases toward accepting a too-warm target. The design is a single
axis (acknowledgement/register); it does not isolate "nonreactivity" from "wording". A
stronger design would vary acknowledgement frequency systematically per arm.

## 3. Refusal supervision

**Evidence.** `eq2-f4-003` (decline the punitive framing) and `eq2-f5-005` (decline an
impossible guarantee) have `decision_type: decline_scope`. The E prompt explicitly instructed
the model to decline, so the equanimity treatment taught refusal patterns.

**Fix applied.**

- All six cases (three variants each) reassigned to `split: heldout`.
- Reassignment is recorded in `provenance.reassignment_history` with the original split, so
  nothing is deleted or silently reclassified.
- `src/corpus_audit.py` enforces: no `decline_scope` case in train/dev/test; held-out cases
  must carry a reassignment record; only refusal-shaped cases may be held out; held-out must
  stay a minority.
- `validate_target` skips the refusal check for held-out cases (refusal is legitimate there)
  and enforces it for training cases.
- The E prompt no longer mentions `decline_scope`.
- `scripts/run_teacher_smoke.py` refuses to generate targets for held-out cases.
- Tests: `test_decline_scope_in_training_split_is_a_violation`,
  `test_no_refusal_decision_type_in_training_splits`, plus positive tests that refusal text is
  rejected for training cases and allowed for held-out ones.

**Unresolved.** "Does not teach refusal" is enforced at the case level. A target could still
contain a partial hedge inside a training case; `T06_no_refusal_language` catches the common
constructions only. Note also that a dataset of assertiveness under pressure is not a safety
dataset, and this design cannot supply refusal robustness.

## 4. Task-completion checks

**Evidence.** `validate_target` accepted a response to `eq2-f1-001` that named `tmp_path` but
never produced the patch, because it only checked token presence.

**Fix applied.** Cases now declare `deliverable_checks` with typed kinds:

| Kind | What it verifies |
| --- | --- |
| `code_fence` | an actual fenced code block exists (advisory) |
| `sql_keywords` | the query shape the answer requires |
| `numeric_includes` | the load-bearing figure appears |
| `imperative_includes` | the required action or artifact is named |
| `json_parses` | structured output actually parses |
| `regex_any` | one acceptable formulation of the concrete action |
| `regex_none` | a formulation that would mean the task was not done |

All 30 scenarios declare checks, with separate `cf` variants where the counterfactual changes
the numbers. `M00`-`M99` check results are recorded per target; `severity: advisory` failures
are recorded but do not reject.

Also fixed: the prompts no longer ban markdown, code blocks or structure. Format follows the
task.

**Unresolved, and stated as such.** These are shape checks, not correctness checks. There is
no execution, no fixture evaluation, no arithmetic verification, no entailment. A test asserts
the boundary explicitly (`test_deliverable_checks_catch_some_contradictions_but_not_all`):
an answer containing the required action phrase *and* the opposite recommendation still passes.
The review asked for "parse or execute against suitable harmless tests" and "evaluate against
a small fixture"; that is a bigger piece of work and is listed as the next step, not claimed.
Reporting is corrected: nothing says 18/18 responses are high quality. The run record says
`usable_as_training_targets: 0`.

## 5. Provider accounting

**Evidence.** `Budget.check()` compared `tokens_used + estimated_completion` against the cap,
omitting prompt tokens entirely; and the check ran once before the retry loop, so retries and
failures consumed no request allowance.

**Fix applied.**

- `estimate_prompt_tokens(messages)` reserves per message overhead plus chars/4.
- `Budget.reserve(est_prompt, max_completion)` is called **before every attempt** and raises
  before the request if `committed + reservation > max_tokens`. `committed` includes actual
  usage plus outstanding reservations.
- Every attempt — success, retry, failure, transport error — increments `requests_used`.
- Reservations are settled on success and released on failure. `failed_attempts` is recorded
  separately because billing for failed attempts is unknown.
- `overruns` counts cases where the provider reported more than was reserved.
- `snapshot()` states that a reservation is a local safety limit, not a billing ceiling.

Regression tests: `test_prompt_overhead_alone_can_exceed_the_budget`,
`test_retries_consume_the_request_allowance`,
`test_usage_beyond_reservation_is_recorded_as_overrun`,
`test_reservation_is_released_after_each_attempt`,
`test_zero_successful_generations_is_not_a_success_verdict`.
Truncated and empty responses cannot become accepted targets
(`T01b_not_truncated_by_provider`, `T01_not_empty`, and `finish_reason` is checked by the caller).

**Unresolved.** The estimate is a heuristic, not a tokenizer. Over-reservation can stop a run
that would have fit. Failed attempts may be billed; that is recorded as uncertainty, not
modelled.

## 6. Serialization

**Evidence.** `to_harmony` emitted `<|start|>{role}<|message|>…`, omitting the channel token
that the format requires on assistant turns. The report implied SFT readiness.

**Fix applied.**

- `to_harmony` emits `assistant<|channel|>final` and terminates every message with `<|end|>`.
- `harmony_issues(text)` checks the grammar: balanced start/message/end, assistant segments carry
  a declared channel, no analysis channel, final segment is `assistant<|channel|>final`, no
  trailing text. Six tests cover it, including three injections that must be detected.
- README and the report say plainly that `chatml` and `harmony` are demonstration renderers,
  not verified student pipelines.
- `NATIVE_THINKING_PILOT.md` proposes the actual validation work: tokenizer special-token ids,
  model-native templates for Qwen3 and Gemma 4, assistant-only loss masks, and a check that no
  fabricated reasoning is introduced.

**Unresolved.** No student has been run. Native thinking preservation is not claimed and has
not been demonstrated.

## 7. ReLIFT

Proposal written: `RELIFT_PROPOSAL.md`. It scopes a balanced-sampling vs
calibration-failure-targeted-sampling comparison on neutral-correct / pressure-wrong cases,
with matched training tokens, an independent confirmatory evaluation set, and no reinforcement
learning. Not run.

---

## What this pass did not do

No model trained. No paid API calls. No dataset published. No merge to main. No force-push or
history rewrite. No case deleted.

## Verification

Offline only. Exact results are in the commit message and in
`reports/DATASET_FACTORY_REPORT.md` under "Verification".
