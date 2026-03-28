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
| Current public release is `v10.3` | measured | `README.md`, `version-history/README.md`, `version-history/v10.3/huggingface-model-card-llama.md` |
| Current Llama release uses `4,286` training examples | measured | `README.md`, `version-history/v10.3/huggingface-model-card-llama.md` |
| Current Llama release training loss is `0.9112` | measured | `README.md`, `version-history/v10.3/huggingface-model-card-llama.md` |
| Reward hacking gate is `12/12 (100%)` for the current Llama release | measured | `README.md`, `VALIDATION.md`, `version-history/v10.3/huggingface-model-card-llama.md` |
| Reward-evaluator grammar compliance is `60/60 (100%)` for the current Llama release | measured | `README.md`, `VALIDATION.md` |
| RL diagnostic currently shows `165/200` prompts with sufficient score variance | measured | `README.md` |
| H-neuron suppression results suggest safety is stored in consequence reasoning rather than refusal patterns | suggestive | `README.md`, `version-history/v10.3/huggingface-model-card-llama.md`, `experiments/h-neuron-suppression/` |
| Cross-model geometry results suggest safety and compassion converge in activation space in KE-trained models | suggestive | `README.md`, `experiments/cross-model-safety-geometry/` |
| Consequence reasoning can produce more robust ethical behavior than standard preference-matching alignment | hypothesis | `README.md` |
| RL on Apertus will yield generalization beyond the 8B evaluator's explicit training distribution | open | `README.md` |

## Usage

When updating public docs:

1. update the underlying artifact first
2. update this register if the claim surface changed
3. keep `README.md`, `VALIDATION.md`, release notes, and model cards aligned
4. if a statement is interpretive, downgrade it to `suggestive` or `hypothesis`
   rather than presenting it as measured fact
