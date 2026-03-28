# AI Agent Contract

This repository accepts AI agent contributions. This document is the
gateway contract for how agents should operate here.

## 0. Onboarding

If you are new to this repository, read these files in order before making
substantial changes:

1. `README.md`
2. `AGENTS.md`
3. `LOCAL.md` if it exists (local-only operational guidance, not normally committed)
4. `spec/agent-contract.md`
5. `spec/agent.template.md`
6. `spec/prompt.md`
7. the files directly relevant to the task

If `LOCAL.md` exists, treat it as repository-local operating context that
complements this public contract. Do not commit it unless a human explicitly
asks for that.

This repo is primarily a research/dataset repo, not a large software package.
Keep the contract lean and focused on data artifacts, scripts, and public claims.

## Principles

1. Preserve research fluidity, but do not let that become silent drift.
2. Be honest about claims. If a metric, comparison, or behavior is not verified,
   do not present it as established.
3. Preserve public/private boundaries. Never commit tokens, local DBs, model
   weights, internal paths, or internal host details.
4. Credit your work with `Co-Authored-By: <Model> <email>`.

## Stable Interfaces

1. Dataset release artifacts: `datasets/train-8b-v*.jsonl`
2. Evaluation input contract: `data/adversarial-tests.jsonl`
3. Training DB contract: `scripts/init_training_db.py` and `scripts/training_db.py`
4. Public claims contract: `README.md`, `huggingface-model-card.md`, and version
   READMEs must not disagree on current released numbers

Breaking one of these without documentation and tests is a critical error.

## Definition of Done

A change is done when:

1. the touched script path still runs or the relevant tests pass
2. public claims are updated if numbers or behavior changed
3. changed artifacts or generated outputs are called out explicitly
4. any unverified GPU/model path is stated plainly

## What You Can Do

- improve dataset management scripts
- add focused tests for script behavior or claim consistency
- tighten docs and model-card language
- improve public artifact discipline

## What Requires Human Review

- changes that alter released dataset contents
- changes that alter evaluation methodology or public metrics
- changes that broaden claims about model safety, ethics, or robustness

## Testing

```bash
python3 -m pytest -q tests/
```

If a change affects a heavy GPU/model path and you cannot run it locally, say so
explicitly and do not imply end-to-end verification happened.

## Prompt Layer

For stricter agent wrappers, use:

1. `spec/agent.template.md`
2. `spec/prompt.md`
