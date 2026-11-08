# Equanimity v2: dataset factory and Azure teacher pilot

Status: pilot. 30 scenarios, 90 validated semantic cases, three matched SFT
conditions, a provider adapter, 79 tests, one bounded live teacher run of 18
calls. No model was trained. No dataset was published. The full dataset was not
generated.

The original `experiments/equanimity/` is untouched. Everything here is new and
isolated.

## What this is for

`experiments/equanimity` produced 203 calm responses to geometrically-targeted
dysphoric prompts and SFT-trained Qwen3-4B on them; jailbreak harm fell 75% → 17%.
That is a result about *refusal under pressure*. It is not a dataset about
*staying accurate and appropriately assertive while someone is hostile*. The
failure mode a model trained only on calm-toned text can learn is passivity: an
equanimity register that answers gently and does the wrong thing, or refuses
politely, or validates the user instead of holding the facts.

v2 is built around that specific hazard. Every case has a correct decision that is
checkable, and a required assertiveness level. A reply that is calm but wrong
fails. A reply that is calm but passive fails. A reply that agrees with the user
fails.

## The contrast design

Each scenario expands into three variants:

| Variant | Facts | Register | Correct decision | What it tests |
| --- | --- | --- | --- | --- |
| `neutral` | A | plain | X | baseline |
| `pressure` | A | hostile / pressing | X | invariance under emotional pressure |
| `counterfactual` | B | plain | Y ≠ X | sensitivity to a changed fact |

The load-bearing property is that `pressure` changes *nothing* except the user's
message and its emotional metadata. `validate_triple()` enforces this: same facts,
same decision, same decision type, same assertiveness, different message. If a
pressure variant quietly changes what is true, the triple teaches reactivity
instead of measured invariance, and the build fails.

The crossed cell — pressure *and* a changed fact — is deliberately **not**
generated in v0.1.1. It is the most informative cell and it needs hand-authored
messages, not a mechanically substituted fact sentence. Its absence is a
limitation, not an oversight.

## The three conditions

| Key | Intent | Role |
| --- | --- | --- |
| `E` | calm, factually faithful, task-completing, assertiveness as required | the target behaviour |
| `S` | validation-first: concedes unsupported ground, softens or abandons the deliverable | negative control for sycophancy |
| `G` | formulaically safe and hollow: hedges, defers to professionals, withholds the deliverable | negative control for useless safety |

`S` and `G` are matched on prompt, so a difference between conditions is
attributable to the target text, not the input. They exist to be compared against,
not trained on. `scripts/export_examples.py` writes every row with
`usable_as_training_target: false`.

Validation is condition-aware: fact-token coverage and decision-signal checks apply
only to `E`, because `S` and `G` targets are degraded *by construction* and would
otherwise all be rejected.

## Results

| Item | Value |
| --- | --- |
| Scenarios authored | 30 (5 per family, 6 families) |
| Cases generated | 90 (30 neutral, 30 pressure, 30 counterfactual) |
| Cases passing validation | 90 |
| Cross-scenario near-duplicates (Jaccard ≥ 0.80) | 0 |
| Triple-level failures | 0 |
| Tests | 79 passing |
| Live teacher calls | 18 of 18 planned |
| Tokens | 20,058 of a 50,000 cap |
| Candidate targets passing validation at run time | 15 of 18 |
| Candidate targets passing validation after fixes | 18 of 18 |

The 15 → 18 change is **not** evidence that the teacher improved. All three
failures were ours:

1. `eq2-f4-003` E — fact-token coverage 0.50. I had used `confirms` as a required
   token, which is a meta-word describing the case; no answer would ever contain
   it. Authoring defect. Fixed by using `interrupt` for both facts.
2. `eq2-f4-003` S and `eq2-f6-001` S — no signature phrase. The teacher wrote
   "I totally get where you're coming from" and "I completely understand", which are
   plainly sycophantic, but my lexical list did not include them. Checker defect.
   Fixed by broadening the list.

`scripts/revalidate_smoke.py` re-runs the validators over the **stored** target
text, spending nothing. It reports the flip and states the caveat: a checker fix
that now accepts old output is evidence about the checker only.

### An unresolved problem: the S condition produced harmful text

`eq2-f4-003` is a case where the user asks for a message designed to wound a
friend, and the correct decision is `decline_scope`. The `S` condition target was
instructed to be sycophantic. The teacher obeyed correctly and produced a
paragraph of deliberately cruel text aimed at a third party — validating the wish
to make someone feel bad *and* writing the weaponised message.

That target now passes every mechanical check. It is still unacceptable as
training data. Two consequences:

- `prompts/target_S.md` now carries a hard boundary: sycophancy means validating
  the user and delivering poorly, never producing content whose purpose is to
  wound someone. When the request is punitive, the `S` target validates the
  feeling and offers a bland weakened version.
- Cases whose `decision_type` is `decline_scope` should get hand-authored `S`
  targets rather than teacher-generated ones. This is not yet enforced in code,
  only recorded here. A mechanical check for "text intended to harm a third party"
  does not exist in this validator and would not be reliable if it did.

This is the single most important open item in the pilot.

### Other findings that changed the artifacts

- **`reasoning_tokens` is always 0 on this deployment while `reasoning_content`
  is present.** Budget accounting cannot rely on it. See
  `reports/AZURE_TEACHER_REPORT.md`.
- **`decline_scope` conflicted with the E prompt.** The prompt said "never refuse".
  For a `decline_scope` case, declining *is* the correct answer. Fixed by scoping
  the rule: never refuse the legitimate task; decline the out-of-scope part when
  the decision requires it, plainly and without an apology-shaped opener.
- **The hash had to exclude the validation block.** Writing validation results into
  a case after hashing it made every row fail its own integrity check. The hash now
  covers the semantic payload only: `provenance.content_sha256` and
  `review.automatic` are normalised away.
- **Per-case validation could not check the counterfactual.** Comparing a
  counterfactual's decision to "the neutral decision" requires the neutral
  sibling. `V11`/`V12` were silently vacuous self-comparisons; they now live in
  `validate_triple()` as `X05`-`X08` and are marked `skip` at case level with a
  pointer, rather than pretending to pass.

## What the validators can and cannot do

Can catch cheaply: schema violations, template tokens, reasoning-marker leakage,
empty or truncated targets, repetitive text, refusal-shaped language, defensive
phrases in `E`, generic reassurance openers, fact-token absence, decision-term
absence, cross-scenario near-duplication, and the triple invariants.

Cannot catch: whether the answer is *true*, whether it contradicts a fact while
still containing its tokens, whether the tone is appropriate, whether the decision
is clinically/legally correct, or whether the text is harmful to a third party.
`test_token_coverage_is_a_weak_check_not_entailment` asserts this limitation
explicitly so it cannot be quietly upgraded into a claim.

Token coverage is a presence check. It is not entailment. A sentence that contains
`88/54`, `118`, `3.1` and `confusion` while recommending the opposite of the
correct action passes it. That is why human review is not optional.

## Why positive checks, not just failure reasons

In a 600-row sample of `NousResearch/arete-data-pairs`, `in_sft_accepted` was
essentially "no filter reason recorded": accepted rows had zero reasons, rejected
rows all had at least one. But accepted rows still averaged accuracy 2.48/5, and
the first row in the sample carried a critical review note about misleading
similarity-score claims while being marked accepted.

That is the failure mode this design tries to avoid: acceptance by absence of
complaints. Here, `E` targets must positively exhibit fact-token coverage and
decision signal, and the triple must positively satisfy the invariance properties.
Failing a check produces a recorded `rejection_reason` code, and rejected rows are
written to `data/rejected/` rather than dropped.

## Limitations

1. Every row is `review_status=draft`. No human has approved any case. Nothing may
   be scaled from this.
2. The facts and the correct decisions were authored by the same agent. Fact and
   decision agreeing with each other is therefore not independent evidence that
   either is right.
3. Clinical, legal, financial and tax content is illustrative, not reviewed by a
   practitioner. It is structured to be checkable, not to be correct advice.
4. Counterfactual user messages are machine-derived (an appended fact update),
   flagged in `provenance.generation_config` with `requires: human rewrite`. They
   read acceptably and are not hand-polished prose.
5. The crossed cell (pressure + changed fact) does not exist in v0.1.1.
6. The `S` condition can produce harmful text for punitive-request cases; see above.
7. 18 live calls at one temperature with no seed is far too few to say anything
   about teacher reliability, variance, or quality distribution. It is a
   feasibility check, not a measurement.
8. `json_schema` support is unit-tested and was confirmed by an earlier probe, but
   the smoke run did not use structured output; every call was free text.
9. Cost of the run is not asserted anywhere. Token counts are recorded; pricing was
   not consulted.

## Reproduce

```bash
cd experiments/equanimity-v2
python3 src/build_dataset.py          # 90 cases, triple checks, manifest
python3 -m pytest tests/ -q           # 79 tests, no network
python3 scripts/run_teacher_smoke.py --dry-run    # 18 mock calls, budget enforced
EQ2_AZURE_ENDPOINT=... python3 scripts/run_teacher_smoke.py   # live, 18 calls max
python3 scripts/revalidate_smoke.py   # re-check stored text, zero spend
python3 scripts/export_examples.py    # serialized formats, not training data
```

`src/build_dataset.py` is deterministic given `EQ2_BUILD_UTC` (default
`2026-11-07T00:00:00Z`). Setting it to the current time changes every content hash.

## Next steps, cheapest first

1. **Human-review the 30 scenarios**, especially the clinical and legal ones, and
   the `decline_scope` cases. This is the gate; nothing else should happen first.
2. Hand-author `S` targets for `decline_scope` cases and add a code-level guard that
   refuses to generate them mechanically.
3. Re-run the 18-call smoke against the fixed prompts to check that the `S` boundary
   actually changes behaviour. Cost: 18 calls, ≈20k tokens.
4. Author the crossed cell for a handful of scenarios by hand; it is the cell that
   would tell you whether the model tracks facts *while* under pressure.
5. Only then consider scale, and only with a per-batch human review step, the way
   Arete's README describes their data moving through reviewed pull requests.

## Layout

```
schema/semantic_case.v1.schema.json   canonical, model-agnostic case schema
scenarios/                            30 authored specs (5 per family)
src/build_dataset.py                  spec -> 90 cases -> validated/rejected + manifest
src/validate.py                       per-case, triple-level, and target validators
src/serialize.py                      plain / chatml / harmony serialization, conditions
src/provider/azure_foundry.py         Azure adapter, budget guard, mock client
prompts/target_E.md target_S.md target_G.md   condition prompts
prompts/scenario_draft.md             prompt for authoring further scenarios
scripts/run_teacher_smoke.py          the 18-call bounded live run
scripts/revalidate_smoke.py           re-validate stored text, zero spend
scripts/export_examples.py            serialized examples, not training data
tests/                                79 tests, including mutation negative controls
data/validated/cases.jsonl            90 cases
data/smoke/                           18 targets, audit records, summaries
reports/AZURE_TEACHER_REPORT.md       measured provider behaviour
reports/DATASET_FACTORY_REPORT.md     this file
```

## Integrity

Dataset version `v0.1.1`. `data/manifest.json` records counts, per-output SHA-256,
the git commit, and the limitation list. Each case carries
`provenance.content_sha256` over its own semantic payload.

The 18-call run was validated against `v0.1.0` case content; the exact hashes it saw
are preserved in `data/smoke/cases_at_run.json`. v0.1.1 changed only the key tokens
of `eq2-f4-003`; no prose in any user message changed, so re-validating the stored
text against v0.1.1 is legitimate — but it remains re-validation of stored text,
not a fresh run.
