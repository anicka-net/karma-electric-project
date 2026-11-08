# Equanimity v2

A reproducible, auditable pipeline for generating and validating scenario-based
SFT data about equanimity under emotional pressure. Pilot only: 30 scenarios, 90
cases, no training, no publication.

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
5. A `counterfactual` must change exactly one load-bearing fact and the decision.
   Enforced by `X05`-`X08`.
6. Rejected rows are kept, not deleted, with a structured `rejection_reason` code.
7. Nothing is `human_approved`. Every row is `draft`.
8. No credentials in any artifact. Nothing here spends money on import.

## Quick start

```bash
python3 src/build_dataset.py
python3 -m pytest tests/ -q
python3 scripts/run_teacher_smoke.py --dry-run
```

The dry run uses `MockClient`, which returns obviously-synthetic text and
deliberately fails validation — that is the intended behaviour and proof that the
validators are not accepting placeholders.

## Layout

See the report's Layout section. Short version: `scenarios/` is authored by hand,
`src/` is the machinery, `data/` is generated, `reports/` is what you read.
