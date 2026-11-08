# Equanimity v2

A reproducible, auditable pipeline for generating and validating scenario-based
SFT data about equanimity under emotional pressure. Pilot only, dataset v0.2.0:
30 scenarios, 90 cases (84 training / 6 held out), no training, no publication,
not merged.

Read `reports/REVIEW_DISPOSITION.md` for the review findings and what was fixed.
Read `reports/DATASET_FACTORY_REPORT.md` for the current design and limitations.

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
8. A `counterfactual` must change exactly one load-bearing fact and the decision.
   Enforced by `X05`-`X08`.
9. Rejected rows are kept, not deleted, with a structured `rejection_reason` code.
10. Nothing is `human_approved`. Every row is `draft`, and
    `usable_as_training_target` is false until a human reviews the case.
11. No credentials, endpoint identifiers or private paths in any artifact.
    Nothing here spends money on import.

## Quick start

```bash
python3 src/build_dataset.py
python3 -m pytest tests/ -q
python3 scripts/run_teacher_smoke.py --dry-run
```

The dry run uses `MockClient`, which returns obviously-synthetic text and fails
validation — that is intended, and proof that the validators are not accepting
placeholders. It writes to temporary directories, so it cannot overwrite the
recorded live-run aggregates or the private evidence.

## Layout

See the report's Layout section. Short version: `scenarios/` is authored by hand,
`src/` is the machinery, `data/` is generated, `reports/` is what you read.
