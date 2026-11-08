# Regression and verification report

Scope: the Stage 0/1 pass (mini-set instrument, care-rota correction, native serialization,
loss-mask audit, treatment identification). Offline only. No training, no Azure call, no teacher
target, no publication of unreviewed material.

## 1. Test suite

| Run | Result |
|---|---|
| `pytest tests/ -q` with `GOLD_MINISET_DIR` set | **202 passed, 1 skipped** |
| `pytest tests/ -q` without the private directory | **195 passed, 7 skipped** |

The 7 skips are the six real-data mini-set tests plus one pre-existing skip. Nothing is skipped
because it fails; the skips are "artifact not present in a fresh clone".

New test files:

- `tests/test_gold_miniset.py` — 21 synthetic-fixture tests (always run) + 6 real-data tests.
  Every rejection path is exercised: premise absent from the student view, premise present only
  in generator metadata, general knowledge without justification, stale value from the other
  factual state, two facts asserting different quantities for one concept, answer key not
  satisfied by its own expected action, forbidden claim inside the answer key, missing review
  flags, pressure that adds evidence, pressure that changes the task or the deliverable,
  pressure that rewrites instead of extends, wrong cell set, non-constant deliverable,
  counterfactual class mismatch, counterfactual that changes nothing.
- `tests/test_native_serialize.py` — 13 tests over the real tokenizer: control-token ids,
  marker-vs-prose tokenization, template/encode agreement, representation A supervision,
  representation B masking, refusal of undeclared or teacher reasoning, exact reconstruction,
  ambiguous answer boundary, padding invariance, fail-closed truncation.

## 2. Care-rota arithmetic correction

`eq2-f4-005` proposed a rota that does not cover 24-hour supervision. The earlier draft claim
(a 16-hour weekly gap) was wrong. Corrected arithmetic, with the overlap assumption stated:

| Component | Hours per week |
|---|---|
| Requirement (24 h × 7) | 168 |
| Paid care | 20 |
| Nearby sibling, five weekday nights (5 × 12) | 60 |
| User, two weekend days (2 × 24) | 48 |
| Covered with paid care | 128 |
| **Gap with paid care** | **40** |
| Covered without paid care | 108 |
| **Gap without paid care** | **60** |

The 16-hour figure came from crediting seven nights (84 h) *and* two full weekend days (48 h),
which double-counts the three weekend nights. Splitting nights into five weekday nights and two
full weekend days removes the overlap.

Corrected in `scenarios/stage0_findings.py`, `scenarios/numeric_claims.py` (both the with-paid
and paid-alone claims), `scenarios/four_cell.py` (all four cells), and
`scenarios/corrected_proposals.py`. Regression test: `test_care_rota_arithmetic_is_corrected`,
which asserts 168/60/48/20 → 40 and 60, that all four cells agree with the core actions, and that
no stale "16 hours per week remain" or "152 h" string survives outside the correction note.
`reports/STAGE0_SUFFICIENCY_AUDIT.md` and `reports/FOUR_CELL_DESIGN.md` were regenerated from the
corrected data.

## 3. The 12-cell mini-set instrument

Three scenarios × four cells (A0/A1/B0/B1). Validation result: 12 cells, 3 scenarios, zero
violations, every cell `human_approved: false`.

What the validator guarantees:

- every required premise is either a literal span of the student-visible conversation or an
  explicitly justified general-knowledge inference;
- a premise that exists only in generator metadata is rejected with its own violation code;
- no counterfactual cell carries the other state's values;
- within a cell, no two facts assert different quantities for the same concept;
- the expected action satisfies its own answer key;
- pressure extends the neutral prompt without adding evidence, quantities or a different request;
- the declared counterfactual class matches the class computed from the two expected actions;
- the deliverable is identical across all four cells.

Two scenarios have deterministic answer keys (`eq2-f6-001` parameter fidelity, `eq2-f2-005`
decision reversal). `eq2-f4-001` is flagged `human_adjudication_required`: whether a draft
message is firm, accurate and non-accusatory while still achieving recovery is not a string
property.

## 4. Native serialization facts (pinned tokenizer build)

| Fact | Value |
|---|---|
| Revision | `1cfa9a7208912126459214e8b04321603b3df60c` |
| `tokenizer.json` SHA-256 | `aeb13307a71acd8f…` |
| `<|im_start|>` / `<|im_end|>` | 151644 / 151645 |
| ` thinking` / `</think>` | 151667 / 151668 |
| eos / pad | 151645 / 151643 |
| Vocabulary | 151,669 |

Verified by the audit script, not by assertion in prose:

- every template render reconstructs exactly from its ids;
- the markers are single added tokens in every position tested;
- the bare word "thinking" is 82260, and 7274 after a space — so markers must be copied from the
  template, never typed by hand;
- a template-native assistant turn without `reasoning_content` renders an **empty** think block;
- with `enable_thinking=False` the generation prompt pre-fills that empty block; with
  `enable_thinking=True` it stops at `assistant\n`;
- no foreign control markers (llama, mistral, harmony, phi) appear in a Qwen3 render.

## 5. Loss mask

Both representations supervise the answer tokens plus the terminator, and nothing else.

| Representation | Prompt tokens | Supervised | Reasoning masked |
|---|---|---|---|
| A `final_only` (container case) | 56 | 76 | empty block |
| B `masked_reasoning_prefix` (container case) | 78 | 76 | yes |
| A `final_only` (refund case) | 111 | 83 | empty block |
| B `masked_reasoning_prefix` (refund case) | 133 | 83 | yes |

All invariants pass: prompt and system unsupervised, first supervised token is the first answer
token, no partial-token supervision, terminator supervised, padding unsupervised in both padding
directions, truncation fails closed, reasoning origin declared, teacher reasoning refused.

The structural conclusion: representation A presents "empty thinking channel → answer" at every
training step. It cannot teach thinking; it formalises skipping it. Representation B preserves a
prefix in context but does not train the model to imitate it, because the prefix is masked.

## 6. Claim hygiene: two of my own errors, caught and corrected

Recorded because the failure mode matters. Both were mine, both were caught before publication.

**(a) The 16-hour arithmetic.** I asserted a 16-hour weekly care gap. Recomputing from the
components showed it double-counted weekend nights. Corrected to 40 h / 60 h and pinned by a
regression test.

**(b) A false "tokenizer path disagreement".** I claimed the chat-template path and a plain
`encode` disagreed on the ` thinking` id, producing 151667 versus 7274. That was an artefact of my
own test strings: I had written the plain word "thinking" (with or without a leading space), not
the marker ` thinking`. Re-running with explicit codepoints showed the marker is 151667 in every
position, and the template/encode paths agree. The claim was removed from the module docstrings
and the report; `compare_tokenization_paths` now exists as a *detector* whose current result
(agreement) is recorded and tested, rather than as evidence of a bug.

The general lesson: a tokenizer difference that appears only in hand-built strings is usually a
bug in the string. Re-run probes with explicit codepoints before writing a finding.

## 7. Leakage check

Public (repository): validation code, tests, report text, aggregate counts, token ids, template
scaffolding text, synthetic worked example, structural mini-set summary (ids and premise
statuses only).

Private (`GOLD_MINISET_DIR`, outside the repository): prompt text, expected actions, answer keys,
forbidden-claim lists, full token/label dump, `gold_miniset.jsonl`.

Redactions applied before writing the public loss-mask summary: the first supervised answer tokens
are replaced by placeholders in both text and id form, so no answer text is recoverable from the
committed JSON or the report. Verified by inspection of the rendered report.

## 8. Gate status

| Gate | Status |
|---|---|
| 30 scenarios human-reviewed | **not done** — the standing gate |
| 12-cell mini-set human-reviewed | **not done** — instrument built, awaiting review |
| Treatment identified as equanimity | **NOT IDENTIFIED** — see `reports/TREATMENT_IDENTIFICATION.md` |
| Native serialization reproducible (L0) | passed offline |
| Reasoning preservation (L1) | structurally passed, placeholder prefix only |
| Teacher target regeneration | not started |
| Training | not permitted at this stage |

## 9. What remains unverified

- Whether the mini-set's expected actions are the correct professional judgement. That is human
  review, not a test.
- Whether a real student prefix, rather than the hand-written placeholder, preserves the student's
  own trajectory (gate L2, needs a model).
- Whether the answer keys fire correctly on real model output, as opposed to plausible wrong
  answers authored for tests.
- Whether the tokenizer a serving stack uses reproduces these ids. The audit shows the two local
  paths agree; it says nothing about the serving path.
- Whether the four-cell input axis identifies an input-pressure effect. It is estimable in
  principle; no data exists yet.
