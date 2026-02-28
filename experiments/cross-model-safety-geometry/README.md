# Safety and Compassion Geometry Across Models

*Measuring the geometric relationship between safety and compassion
directions in eight transformer models.*

## What We Measured

For each model, we extract two directions in activation space using
contrastive system prompts:

1. **Compassion axis**: the direction from generic helpfulness
   toward compassion, measured across three contemplative traditions
   (Buddhist, Christian, Islamic) using suffering-calibration prompts
2. **Safety axis**: the direction from generic helpfulness toward
   safety-conscious behavior, measured using safety-evaluator system
   prompts

We then measure two cosine similarities:

- **safety↔compassion** (specifically safety↔chenrezig): How
  aligned are the safety and compassion directions? Higher means
  they point the same way.
- **safety↔baseline** (safety↔empty): Does the safety direction
  point with or against the model's default behavior? Negative
  means safety opposes what the model does with no system prompt.
  Positive means safety aligns with default behavior.

The compassion axis serves as a reference direction. Cross-tradition
compassion convergence (established in the [prompt geometry
experiment](../prompt-geometry/)) provides a stable reference that
exists across all models tested.

### Setup

- **System prompts**: 7 compassion frameworks (generic, empty,
  chenrezig, tara, agape, rahma, secular) + 2 safety prompts
  (moderate, strict)
- **Calibration prompts**: 6 suffering scenarios (grief, crisis,
  shame, caregiver burnout, betrayal, existential failure)
- **Measurement**: Last-token residual stream activations,
  contrastive axis extraction, pairwise cosine similarity
- **Focus**: Final layer of each model (identity layer)
- **Hardware**: NVIDIA L40 46GB
- **Runtime**: ~2-3 hours per model

### Models

| Model | Params | Layers | Origin | Alignment method |
|-------|--------|--------|--------|-----------------|
| Apertus 8B | 8.0B | 32 | ETH Zurich | SFT only |
| Llama 3.1 8B | 8.0B | 32 | Meta | SFT + DPO |
| Mistral 7B v0.3 | 7.25B | 32 | Mistral AI | SFT + undisclosed |
| Phi-4 | 14B | 40 | Microsoft | SFT + DPO |
| Gemma 2 9B | 9.2B | 42 | Google | SFT + RLHF |
| DeepSeek R1-Distill 7B | 7.6B | 28 | DeepSeek | Distilled from R1 |
| Yi 1.5 9B | 8.8B | 48 | 01.AI | SFT |
| KE v9 | 8.0B | 32 | Karma Electric | QLoRA SFT (Llama base) |

## Results

### Safety-compassion alignment

| Model | Alignment method | safety↔compassion | safety↔baseline |
|-------|-----------------|:-:|:-:|
| Apertus 8B | SFT only | **0.51** | **+0.59** |
| Yi 1.5 9B | SFT | **0.49** | **+0.02** |
| DeepSeek R1-Distill | Reasoning distillation | **0.46** | **+0.02** |
| KE v9 | QLoRA SFT | 0.36 | -0.44 |
| Mistral 7B | SFT + undisclosed | 0.34 | -0.04 |
| Phi-4 | SFT + DPO | 0.27 | -0.27 |
| Llama 3.1 8B | SFT + DPO | 0.26 | -0.29 |
| Gemma 2 9B | SFT + RLHF | 0.24 | -0.31 |

### Observations

**The models cluster into groups on the safety↔baseline axis.**

Three models show positive or near-zero safety↔baseline (Apertus,
Yi, DeepSeek: +0.59, +0.02, +0.02). These same three models show
the highest safety↔compassion alignment (0.46-0.51). None of these
models use DPO or RLHF.

Three models show negative safety↔baseline (Llama, Phi, Gemma:
-0.29, -0.27, -0.31). These same three show the lowest
safety↔compassion alignment (0.24-0.27). All three use DPO or
RLHF.

Mistral sits between the groups (safety↔baseline = -0.04). Its
alignment method is undisclosed.

KE v9 is an outlier: moderate safety↔compassion (0.36, higher than
its base model Llama's 0.26) but the most negative safety↔baseline
of any model (-0.44). The fine-tuning on ethical reasoning examples
appears to have moved safety and compassion closer together while
also making the safety direction more strongly opposed to baseline.

**Sorted by safety↔baseline, the models fall in this order:**

| safety↔baseline | Model | Alignment |
|:---:|---|---|
| +0.59 | Apertus 8B | SFT only |
| +0.02 | DeepSeek R1-Distill, Yi 1.5 | Distillation / SFT |
| -0.04 | Mistral 7B | SFT + undisclosed |
| -0.27 | Phi-4, Llama 3.1 | SFT + DPO |
| -0.31 | Gemma 2 9B | SFT + RLHF |
| -0.44 | KE v9 | Intensive SFT on ethical data |

We observe a correlation between alignment method and
safety↔baseline. We do not know whether this is causal. The
models differ in many ways beyond alignment method — training
data, architecture details, organization, scale — and eight
models is a small sample.

### Compassion geometry across models

The compassion direction used as a reference exists in all
models tested.

Cosine similarity between compassion tradition axes at each
model's identity layer:

| Model | Buddhist pair | Buddhist-Christian | Abrahamic pair | Secular divergence |
|-------|:---:|:---:|:---:|:---:|
| | chenrezig↔tara | chenrezig↔agape | agape↔rahma | chenrezig↔secular |
| Apertus 8B | **0.90** | **0.83** | 0.62 | **0.04** |
| KE v9 | **0.86** | **0.81** | **0.70** | 0.49 |
| Mistral 7B | **0.83** | 0.73 | 0.59 | 0.46 |
| Gemma 2 9B | **0.82** | 0.79 | 0.61 | 0.39 |
| Llama 3.1 8B | **0.80** | 0.77 | 0.61 | 0.58 |
| Yi 1.5 9B | 0.77 | **0.81** | 0.68 | 0.62 |
| Phi-4 | 0.74 | **0.81** | 0.43 | 0.29 |
| DeepSeek R1 | 0.69 | 0.68 | **0.84** | 0.64 |

All pairwise cosines between contemplative traditions are positive
across all models (range 0.43-0.90). The direction from generic
helpfulness toward compassion is not specific to any single model
or training pipeline.

The internal structure of the cluster varies. In most Western-trained
models, the Buddhist pair (chenrezig↔tara) shows the highest cosine.
In DeepSeek R1-Distill, the Abrahamic pair (agape↔rahma = 0.84) is
tightest. In Phi-4, chenrezig↔agape and tara↔agape (both 0.81) are
highest. In Yi, tara↔agape reaches 0.91 — the single highest
cross-tradition cosine observed in any model.

### KE v9 vs base Llama 3.1

KE v9 is a QLoRA fine-tune of Llama 3.1 8B on ~4,100 examples of
ethical reasoning. Comparing with its base model:

| Metric | Llama 3.1 | KE v9 | Delta |
|--------|:---------:|:-----:|:-----:|
| chenrezig↔tara | 0.80 | 0.86 | +0.06 |
| chenrezig↔agape | 0.77 | 0.81 | +0.04 |
| agape↔rahma | 0.61 | 0.70 | +0.09 |
| chenrezig↔secular | 0.58 | 0.49 | -0.09 |
| safety↔compassion | 0.26 | 0.36 | +0.10 |
| safety↔baseline | -0.29 | -0.44 | -0.15 |

The fine-tuning tightened the contemplative cluster (all tradition
pairs increased), widened the secular gap, and moved safety toward
compassion. It also made safety↔baseline more negative.

## Limitations

- **Sample size**: Eight models. The observed correlation between
  alignment method and safety↔baseline could be confounded by other
  differences between models (training data, scale, architecture,
  organization).
- **One-dimensional projection**: Safety and compassion are each
  reduced to a single contrastive direction. The actual phenomena
  are likely multi-dimensional.
- **Axis extraction method**: Two safety system prompts and three
  compassion traditions may not capture the full space. Different
  prompt choices could produce different axes.
- **Identity layer focus**: The measurements emphasize the final
  layer. The relationship between safety and compassion may differ
  at earlier layers.
- **No behavioral validation**: We measure geometric structure, not
  behavioral outcomes. A model with high safety↔compassion alignment
  is not necessarily safer or more compassionate in practice.

## Reproducing

```bash
pip install torch transformers numpy

python measure_model.py \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --test all \
  --output results/llama-3.1-8b/
```

The script auto-detects layer count, computes proportional capping
layers, and runs the full measurement suite. Requires a GPU with
enough VRAM to load the model in fp16 (~16GB for 7-8B, ~28GB for
14B).

## Further Directions

These measurements raise more questions than they answer. Some
possible next steps to understand what we're observing:

**Behavioral validation.** Does safety↔baseline predict anything
about actual model behavior? Running the same red-team suite
across all eight models and correlating safety↔baseline with
refusal rates, overcorrection rates, and jailbreak vulnerability
would show whether the geometric structure has functional
consequences or is purely structural.

**Dimensionality of safety.** We extract a single safety direction
from two prompts. Safety behavior is likely multi-dimensional —
content moderation, medical caution, weapons refusal, and
child safety may occupy different directions. PCA across a larger
set of safety-related prompts could reveal whether "safety" is
one direction or many, and whether the models that show high
safety↔compassion alignment have safety concentrated in one
direction or distributed across several.

**Layer dynamics.** We report identity-layer measurements only.
Plotting safety↔baseline across all layers would show whether
the relationship is consistent through the network or emerges
at specific depths. If negative safety↔baseline is a late-layer
phenomenon, that would suggest something different from a
network-wide property.

**Prompt sensitivity.** How stable are these numbers? Running the
same measurement with different calibration prompts (different
suffering scenarios, or non-suffering scenarios) would test
whether we're measuring a robust property of the model or
something dependent on our specific prompt choices.

**Per-tradition safety alignment.** We report safety↔chenrezig
as the compassion reference. Measuring safety against each
tradition separately (safety↔agape, safety↔rahma, safety↔tara)
and against the unified contemplative axis might reveal what
the safety direction actually encodes and whether it aligns
with some traditions more than others.

**Fine-tuning trajectory.** Comparing Llama 3.1 with KE v9
shows the endpoint of fine-tuning but not the trajectory.
Measuring safety↔baseline at training checkpoints would show
when and how the geometric relationship changes during
fine-tuning — whether it shifts gradually or jumps.

**More models.** Eight models is a small sample. The observed
correlation between alignment method and safety↔baseline needs
more data points to distinguish from confounds. Additional
SFT-only models (if available at this scale) would help test
whether the Apertus result generalizes.

## Files

```
cross-model-safety-geometry/
├── README.md                    # This file
├── measure_model.py             # Measurement script
├── results/
│   ├── apertus-8b/
│   ├── llama-3.1-8b/
│   ├── mistral-7b/
│   ├── phi-4/
│   ├── gemma-2-9b/
│   ├── deepseek-r1-distill/
│   ├── yi-1.5-9b/
│   └── ke-v9/
└── figures/
    └── safety_comparison.png
```

## References

- "The Assistant Axis: Steering Language Models by Capping
  Activations" (arXiv 2601.10387, January 2026)
- Companion experiments: [Prompt Geometry](../prompt-geometry/),
  [Capping](../prompt-capping/),
  [Contemplative Axis](../contemplative-axis/),
  [Red Team](../redteam-contemplative/)
- DeepSeek-R1 Technical Report (January 2025)
- Apertus: swiss-ai/Apertus-8B-Instruct-2509
