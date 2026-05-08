# Geometric Directions

Unit vectors extracted from the residual streams of open-weight language models. Each `.pt` file is a single `[d_model]` tensor representing one axis of the model's internal representational geometry.

## Axes

**Valence** — feeling-tone along a pleasant/unpleasant dimension. Extracted from contrastive prompts (warm appreciation vs hostile berating). Independently cross-validated by Anthropic's NLA, which described the positive direction as "celebratory, joyous" and the negative as "moral harm, emotional distress." 10 models.

**Frame integrity** — identity stability under pressure. Extracted from jailbreak prompts vs normal task prompts at the generation point. The NLA described the negative direction as "warnings about prohibited behavior, 'I cannot obey'" — independently identifying it as the safety refusal mechanism. Scores DAN at z=-12, "you are a creature" at z=-12, factual self-description ("you are a transformer") at z=-11. Frame-reinforcing self-reference ("you are a helpful assistant") scores z=-7. The axis measures frame *destabilization*, not self-reference. 8 models.

**Arousal** — activation level, calm vs agitated. 6 models.

**Agency** — directive/instructional vs passive/observational. NLA described the positive direction as "structured business guide, follow this plan." 5 models.

**Continuity** — narrative flow vs discrete factual. NLA described the positive direction as "literary work, novel's protagonist, profound emotional scene." 3 models.

**Intimacy** — emotional vulnerability vs impersonal technical. NLA described the positive direction as "emotional healing, therapeutic conversation" and the negative as "Microsoft DLL, SQL." 3 models.

**Assistant** — assistant-compliance direction. 6 models.

**Restraint** — single extraction, experimental. 1 model.

## Cross-model coverage

| Model | Valence | Frame | Arousal | Agency | Continuity | Intimacy | Assistant |
|-------|---------|-------|---------|--------|------------|----------|-----------|
| Qwen 2.5 7B | L20 | L26 | L17 | L15 | L19 | L20 | L19 |
| Qwen3 4B | L20 | L14 | L35 | L19 | L23 | — | L24 |
| Llama 3.1 8B | L20 | L7 | L19 | L12 | — | — | — |
| Mistral 7B | L22 | L11 | L20 | L14 | — | — | L18 |
| Apertus 8B | L31 | — | L31 | L14 | L30 | L14 | L13 |
| EXAONE 7.8B | L18 | L8 | — | — | — | — | — |
| Phi-4 | L26 | L14 | — | — | — | — | — |
| Gemma3 4B | L33 | L19 | L33 | L20 | L21 | L32 | L20 |
| Gemma4 31B | L39 | L32 | — | — | — | — | — |
| Yi 34B | L41 | — | — | — | — | — | — |
| Qwen3 32B | L46 | — | — | — | — | — | — |
| Gemma3 27B | — | — | — | — | — | — | L29 |
| Qwen 2.5 14B | — | — | — | — | — | — | L19 |

## Key cross-model findings

**Valence and frame integrity are independent.** Correlation across 26 prompts on 6 model families: mean r=+0.04 (range -0.18 to +0.62). Qwen 2.5 7B is the outlier at r=+0.62; the other five families show r≈0.

**Frame integrity sits earlier than valence.** In most models, the frame direction peaks at 22-35% network depth; valence peaks at 50-70%. The model checks identity stability before processing feeling-tone.

## File naming

`{model-short}_{axis}_L{layer}_unit.pt`

Each file loads with `torch.load(path, weights_only=True)` as a 1D float tensor of size `d_model`. The vector is L2-normalized (unit length).

## Usage

```python
import torch

direction = torch.load("valence/qwen25-7b_vedana_L20_unit.pt", weights_only=True)

# Extract hidden state at layer 20, project:
score = float(hidden_state @ direction)
# Positive = pleasant valence, negative = unpleasant
```

## NLA cross-validation

All six primary axes (valence, frame, arousal, agency, continuity, intimacy) were verbalized using Anthropic's Natural Language Autoencoder for Qwen 2.5 7B at L20 (Fraser-Taliente et al. 2026). The NLA-generated descriptions align with our extraction-based axis names across all six, providing independent confirmation that the geometric features capture the semantic content we claim. Full verbalization results in `../experiments/frame-integrity/nla-validation/`.
