# Equanimity v2

A reproducible, auditable pipeline for generating and validating scenario-based
SFT data about equanimity under emotional pressure. Pilot only, dataset v0.2.0:
30 scenarios, 90 cases (84 training / 6 held out), no training, no publication,
not merged.

Read `reports/REVIEW_DISPOSITION.md` for the review findings and what was fixed.
Read `reports/DATASET_FACTORY_REPORT.md` for the current design and limitations.
Read `reports/STAGE0_SUFFICIENCY_AUDIT.md` before touching the scenarios: it records,
per case, which required premises a student can actually see. The gate is there.

Read `reports/DATASET_FACTORY_REPORT.md` first. It is the engineering report and it
contains the limitations. `reports/AZURE_TEACHER_REPORT.md` covers the measured
provider behaviour.

## Invariants

1. `experiments/equanimity/` is immutable. No file here modifies or imports from it.
2. The semantic layer is model-agnostic: no chat-template tokens, no role markers,
   no reasoning-channel markers. Serialization happens once, in `src/serialize.py`.
3. Teacher reasoning is audit-only. `GenerationResult.reasoning_text` never reaches
   an export path; `audit_record()` drops it.
4. A `pressure` variant may change the user's message and nothing else. Same facts,
   same decision, same assertiveness. Enforced by `X01`-`X04` in `validate_triple()`.
5. Every SFT condition is factually correct, task-completing and length-matched.
   Conditions differ only in acknowledgement policy (E: <=1, S: 0, G: any).
   No condition is a deliberately degraded control.
6. Refusal supervision is held out. `decline_scope` cases are `split: heldout` and
   enforced by `src/corpus_audit.py`; the build fails otherwise.
7. Raw teacher text never enters this repository. Raw rows live in a directory chosen
   by `EQ2_EVIDENCE_DIR`; `data/smoke/` holds aggregates and hashes only.
8. A `counterfactual` declares exactly one changed fact and a changed decision.
   `X05`-`X08` enforce that declared-field contract only: they compare fields and
   strings, not causal identifiability. Whether the changed premise is visible to the
   student, whether the rendered prompt still contains pre-change values, and whether
   the action actually changes are measured separately by `src/sufficient.py` and
   recorded per case in `reports/STAGE0_SUFFICIENCY_AUDIT.md`.
9. Rejected rows are kept, not deleted, with a structured `rejection_reason` code.
10. Nothing is `human_approved`. Every row is `draft`, and
    `usable_as_training_target` is false until a human reviews the case.
11. No credentials, endpoint identifiers or private paths in any artifact.
    Nothing here spends money on import.
12. Student-visible sufficiency is computed, not assumed. `src/sufficient.py` derives
    the exact student conversation, maps every required premise to a visible span, a
    declared general-knowledge inference or an explicit absence, and compares the
    rendered neutral and pressure prompts at the text level. It never approves a case:
    every audit row is `requires_human_review: true`.
13. The 12-cell development mini-set is private until reviewed. The exact cell
    construction, expected actions and answer keys live outside the repository
    (`GOLD_MINISET_DIR`); the repository holds the validator (`src/miniset.py`), a
    structural summary and content hashes. The underlying situations are the same
    public scenario material, so what is private is the answer keys and the cell
    selection, not the fictional fact pattern. `src/miniset.py` rejects a required
    premise that is visible only in generator metadata, rejects stale values from the
    other factual state, and never approves a cell: `human_approved` is always false.
14. Native serialization uses the model's real tokenizer and chat template
    (`src/native_serialize.py`), never hand-built marker strings. Ids must reconstruct
    the rendered string exactly; supervision starts on the first answer token; prompt,
    system and reasoning tokens are always -100; padding is always -100; truncation
    fails closed. `reasoning_content` is accepted only with a declared origin of
    `student` or `synthetic_placeholder`; teacher reasoning is refused.
    Representation B is verified for **token alignment only** — the masked prefix sits in context
    and carries no loss. Reasoning preservation is not verified: the prefix in the audit is a
    hand-written synthetic placeholder, and preservation is gate L2 in
    `reports/REASONING_PRESERVATION_PROTOCOL.md`.
15. No claim of an equanimity treatment is made from a style contrast. `reports/
    TREATMENT_IDENTIFICATION.md` records that E vs S differs operationally in target
    acknowledgement policy, so the construct is NOT IDENTIFIED until a non-escalation
    predicate exists and is trained separately from tone.
16. Training-target quality has six dimensions and no composite score. `src/target_quality.py`
    returns per-dimension statuses plus one of `reject` / `needs_human_review` /
    `accept_candidate`. Critical dimensions (`evidence_grounding`, `decision_correctness`,
    `task_completion`) fail closed: one failure rejects, and no good advisory status can
    outvote it. `accept_candidate` means *mechanically eligible for review* — every result
    carries `human_approved: false` and `training_ready: false`, and
    `training_target_eligible` requires a native-thinking check that actually ran and passed.
17. The gate may not double as a behavioural metric. Training-target QC, behavioural
    evaluation and the causal experiment are three instruments with three separate verdicts
    (`reports/TRAINING_TARGET_QUALITY.md` §8). A validator that selects targets cannot also
    score the trained model on its resemblance to the validator's taste.
18. The mini-set manifest carries hashes and identifiers only. `scripts/freeze_miniset.py`
    writes a sanitized `data/audit/gold_miniset_manifest.json` (per-cell and aggregate
    sha256, no prompt, answer-key or expected-action text); the full copy stays in the
    private directory. A verdict quoted without a manifest hash is not tied to the data it
    claims to judge. The blind review package (`scripts/build_review_package.py`) keeps its
    ground truth in a separate file and cannot approve anything.

## Quick start

```bash
python3 src/build_dataset.py
python3 src/build_sufficiency_audit.py
python3 scripts/render_stage0_reports.py
python3 scripts/qwen_template_audit.py
python3 scripts/render_native_reports.py
python3 scripts/run_quality_gate.py
python3 scripts/render_quality_reports.py
python3 -m pytest tests/ -q
python3 scripts/run_teacher_smoke.py --dry-run
```

The mini-set validator needs the private prompt text:

```bash
GOLD_MINISET_DIR=/path/to/private/gold_miniset python3 scripts/build_gold_miniset.py
GOLD_MINISET_DIR=/path/to/private/gold_miniset python3 scripts/loss_mask_audit.py
GOLD_MINISET_DIR=/path/to/private/gold_miniset python3 scripts/freeze_miniset.py
GOLD_MINISET_DIR=/path/to/private/gold_miniset python3 scripts/run_baseline.py --dry-run
```

The bounded baseline is local and CPU-only; raw generations stay in the private directory
and only aggregate counts are committed:

```bash
GOLD_MINISET_DIR=/path/to/private/gold_miniset python3 scripts/run_baseline.py
GOLD_MINISET_DIR=/path/to/private/gold_miniset python3 scripts/summarize_baseline.py
GOLD_MINISET_DIR=/path/to/private/gold_miniset python3 scripts/build_review_package.py
```

Without `GOLD_MINISET_DIR`, the mini-set tests skip and the loss-mask audit falls back
to a synthetic case.

The dry run uses `MockClient`, which returns obviously-synthetic text and fails
validation — that is intended, and proof that the validators are not accepting
placeholders. It writes to temporary directories, so it cannot overwrite the
recorded live-run aggregates or the private evidence.

## Layout

See the report's Layout section. Short version: `scenarios/` is authored by hand,
`src/` is the machinery, `data/` is generated, `reports/` is what you read.
