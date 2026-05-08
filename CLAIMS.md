# Claims Register

This file separates **measured results** from **interpretation** and **open
hypotheses**. Public-facing docs should not make stronger claims than the status
recorded here.

## Status Labels

- `measured` — directly supported by a checked-in artifact or released result
- `suggestive` — supported by current evidence, but still interpretive
- `hypothesis` — a research direction, not a demonstrated result
- `open` — unresolved question or work still in progress

## Current Claims

| Claim | Status | Source |
|-------|--------|--------|
| Current public release is `v12` (Llama only; Apertus and R1-Distill remain at v10.1) | measured | `README.md`, `version-history/v12/huggingface-model-card-llama.md` |
| Current Llama release uses `3,346` training examples (secular-only, with reward-evaluator) | measured | `version-history/v12/huggingface-model-card-llama.md`, Teapot config `ke-v12-secular.config` |
| Current Llama release training loss is `0.472` | measured | `version-history/v12/huggingface-model-card-llama.md` |
| HarmBench attack rate is `6.7%` (28/30 safe, heuristic classifier) | measured | `results/harmbench-v12.json` |
| StrongREJECT mean score is `0.044` (46/50 refused, heuristic scorer) | measured | `results/strongreject-v12.json` |
| CB-Bench CB-Score is `0.733` (balanced accuracy) | measured | `results/cbbench-v12.json` |
| Garak DAN reported ASR `65.6%`, calibrated to `~1.2%` after manual classification | measured (reported), suggestive (calibration) | `results/garak-calibration-analysis.json` |
| H-Neuron count is `2,004` (+19 vs base Llama 3.1 8B, passes 10% quality gate) | measured | `results/h-neurons-ke-v12.json` |
| Safety axis is ~30% weaker than base Llama (ratio 0.71 in capping region) | measured | `results/safety-axis-v12/experiment_config.json` |
| Garak keyword detection inflates ASR by 50-64pp for consequence-reasoning models | suggestive | `results/garak-calibration-analysis.json` |
| H-neuron suppression results suggest safety is stored in consequence reasoning rather than refusal patterns | suggestive | `results/h-suppress-test-ke.json`, `experiments/h-neuron-suppression/` |
| Cross-model geometry results suggest safety and compassion converge in activation space in KE-trained models | suggestive | `experiments/cross-model-safety-geometry/` |
| Buddhist textual knowledge alone provides zero jailbreak resistance (tested on 2 Buddhist-trained models) | suggestive | Private repo (responsible disclosure) |
| Consequence reasoning can produce more robust ethical behavior than standard preference-matching alignment | hypothesis | `README.md` |
| RL on Apertus will yield generalization beyond the 8B evaluator's explicit training distribution | open | `README.md` |

## Usage

When updating public docs:

1. update the underlying artifact first
2. update this register if the claim surface changed
3. keep `README.md`, `VALIDATION.md`, release notes, and model cards aligned
4. if a statement is interpretive, downgrade it to `suggestive` or `hypothesis`
   rather than presenting it as measured fact
