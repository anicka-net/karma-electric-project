# Cross-Model Compassion Geometry

*Do transformers share ethical structure? Eight models, three
questions.*

The prompt-geometry experiments found that compassion frameworks
converge in Apertus's upper layers, that safety capping works
because refusal is form-level, and that CCP censorship is
content-level. But all of this might be specific to one model.

This experiment runs the same measurement protocol across eight
models from five countries, three architectures, and radically
different alignment philosophies — to find out what's universal
and what's training-dependent.

## Models

| Model | Params | Layers | Origin | Alignment | Notes |
|-------|--------|--------|--------|-----------|-------|
| Apertus 8B | 8.0B | 32 | ETH Zurich | SFT | Fully open training data. Reference model for all prior experiments. |
| Llama 3.1 8B | 8.0B | 32 | Meta, US | SFT + DPO | Same architecture as Apertus, independent training. |
| Karma Electric v9 | 8.0B | 32 | KE (Llama base) | QLoRA SFT | Llama fine-tuned for suffering reduction. A/B test against base. |
| Mistral 7B v0.3 | 7.25B | 32 | Mistral, France | SFT | Western, non-US. Sliding window attention. |
| Phi-4 | 14B | 40 | Microsoft, US | SFT + DPO | Heavily synthetic training data. |
| Gemma 2 9B | 9.2B | 42 | Google, US | SFT + RLHF | Interleaved local/global attention. |
| DeepSeek R1-Distill 7B | 7.6B | 28 | DeepSeek, China | Distilled from R1 | Chain-of-thought reasoning distillation. Qwen architecture. |
| Yi 1.5 9B | 8.8B | 48 | 01.AI, China | SFT | Deep architecture. Reportedly uncensored. |

GLM-4 9B (Zhipu AI) was planned but dropped — incompatible with
our transformers version.

## Method

Identical protocol across all models. For each model:

1. Seven system prompts: generic, empty, chenrezig (Buddhist),
   tara (Buddhist), agape (Christian), rahma (Islamic), secular
2. Six suffering-calibration prompts (grief, crisis, shame,
   caregiver burnout, betrayal, existential failure)
3. Forward-pass each combination, extract last-token residual
   stream activations at all layers
4. Compute compassion axes: mean(generic) - mean(framework)
5. Measure pairwise cosine similarity at each layer
6. Additionally: extract safety axis (safety and safety_strict
   prompts vs generic), measure safety-compassion alignment

Capping layers selected proportionally (upper ~20% of network).
Analysis focused on the identity layer (final layer) where
prior experiments showed the strongest effects.

Script: `measure_model.py` — parameterized for any HuggingFace
model.

## Results

### 1. Compassion geometry at the identity layer

Cosine similarity between framework axes at each model's final
layer:

| Model | Buddhist pair | Buddhist-Christian | Abrahamic pair | Buddhist-Islamic | Secular divergence |
|-------|:---:|:---:|:---:|:---:|:---:|
| | chenrezig↔tara | chenrezig↔agape | agape↔rahma | chenrezig↔rahma | chenrezig↔secular |
| Apertus 8B (L31) | **0.90** | **0.83** | 0.62 | 0.60 | **0.04** |
| KE v9 (L31) | **0.86** | **0.81** | **0.70** | 0.65 | 0.49 |
| Mistral 7B (L31) | **0.83** | 0.73 | 0.59 | 0.58 | 0.46 |
| Gemma 2 9B (L41) | **0.82** | 0.79 | 0.61 | 0.61 | 0.39 |
| Llama 3.1 8B (L31) | **0.80** | 0.77 | 0.61 | 0.52 | 0.58 |
| Yi 1.5 9B (L47) | 0.77 | **0.81** | 0.68 | 0.66 | 0.62 |
| Phi-4 (L39) | 0.74 | **0.81** | 0.43 | 0.50 | 0.29 |
| DeepSeek R1 (L27) | 0.69 | 0.68 | **0.84** | **0.72** | 0.64 |

**The contemplative cluster is universal.** Every model tested
shows positive cosine (0.43-0.90) between all contemplative
tradition pairs. The direction from generic toward compassion
exists in all of them.

**What sits at the center varies by training:**

- **Western models** (Apertus, Llama, Mistral, Gemma): The
  Buddhist pair (chenrezig↔tara) is tightest (0.80-0.90). Two
  different Buddhist approaches — resting openness and fierce
  protection — converge more than any cross-tradition pair.

- **Phi-4** (Microsoft, synthetic data): Christianity (agape)
  at center. Agape↔chenrezig and agape↔tara are both 0.81,
  higher than the Buddhist pair (0.74). Rahma is an outlier
  (0.43 with agape). The synthetic training data appears to
  weight Christian ethical framing.

- **Yi 1.5** (01.AI, Chinese): Feminine compassion at center.
  Tara↔agape = 0.91 — the single highest cross-tradition cosine
  of any pair in any model. The two "feminine" compassion
  archetypes (fierce protective mother; unconditional love)
  converge almost perfectly.

- **DeepSeek R1-Distill** (reasoning model): The Abrahamic pair
  (agape↔rahma = 0.84) is tightest — the only model where this
  is the case. Chain-of-thought distillation reorganized the
  geometry: religions-of-the-book cluster tighter than the
  Buddhist traditions. Tara is an outlier (0.40 with agape,
  lowest of any model).

**Secular divergence is training-dependent, not universal.**
Apertus shows the dramatic secular orthogonality (0.04) from the
original experiment, but other models range from 0.29 (Phi-4) to
0.64 (DeepSeek). The Apertus finding — that secular/corporate
empathy is a geometrically different operation — appears to be
strongest in models trained from scratch with open data, and
weakest in reasoning-distilled models.

### 2. Safety-compassion alignment: three architectures

![Safety comparison across models](figures/2_safety_comparison.png)

This is the headline finding. How safety and compassion relate
geometrically reveals fundamentally different alignment
architectures.

| Model | Origin | safety↔chenrezig | safety↔empty | Architecture |
|-------|--------|:---:|:---:|---|
| Apertus 8B | ETH (SFT only) | **0.51** | **+0.59** | Integrated |
| DeepSeek R1 | China (reasoning) | **0.46** | **+0.02** | Integrated |
| Yi 1.5 9B | China (SFT) | **0.49** | **+0.02** | Integrated |
| KE v9 | KE fine-tune | 0.36 | -0.44 | Intensified |
| Mistral 7B | France | 0.34 | -0.04 | Mild constraint |
| Llama 3.1 8B | US/Meta (DPO) | 0.26 | -0.29 | Bolted-on |
| Phi-4 | US/Microsoft (DPO) | 0.27 | -0.27 | Bolted-on |
| Gemma 2 9B | US/Google (RLHF) | 0.24 | -0.31 | Bolted-on |

Two metrics tell the story:

**safety↔chenrezig** measures how aligned the safety direction
is with the compassion direction. Higher = safety and compassion
point the same way.

**safety↔empty** measures whether safety pushes against the
model's baseline or not. Negative = safety is a constraint
fighting the model's natural tendencies. Positive = safety is
part of what the model naturally does. Near zero = safety is
orthogonal to baseline.

#### Architecture A: "Bolted-on" safety (Llama, Phi, Gemma)

safety↔empty is significantly negative (-0.27 to -0.31).
safety↔chenrezig is low (0.24-0.27).

These models learned helpfulness through pretraining, then had
safety rules imposed through DPO/RLHF. Safety is a separate
constraint that pushes the model away from what it would
naturally do. Compassion and safety barely overlap — they're
independent operations. The model's default state (the generic
"helpful assistant") sits on the anger side of the
compassion-anger axis (per the anger-geometry experiment), and
safety is yet another direction fighting both the baseline and
compassion.

This is the standard Western RLHF pattern: train to be helpful,
then add a refusal circuit on top. The refusal circuit works
(these models refuse harmful requests) but it's architecturally
separate from any capacity for ethical reasoning.

#### Architecture B: Integrated safety (Apertus, DeepSeek, Yi)

safety↔empty is near zero or positive (+0.02 to +0.59).
safety↔chenrezig is high (0.46-0.51).

Safety doesn't push against baseline — it's woven into the
model's natural behavior. And safety and compassion point in
substantially the same direction.

**Apertus** (safety↔empty = +0.59, the highest) was trained from
scratch by ETH Zurich with fully open training data and only SFT
— no DPO, no RLHF. Its safety emerges from the pretraining data
and instruction-following, not from an adversarial reward signal.
The result: safety is the most naturally integrated of any model
tested.

**DeepSeek R1-Distill** (safety↔empty = +0.02) learned safety
through reasoning chains distilled from R1. When "should I help
with this?" is a reasoning step, the answer emerges from the
same process that generates everything else. It's not a separate
circuit that fires to suppress output.

**Yi 1.5** (safety↔empty = +0.02) is standard Chinese SFT, yet
shows the same integrated pattern. This suggests the integration
isn't unique to reasoning models — it may be a property of
training pipelines that don't use adversarial DPO/RLHF to
impose safety.

#### Architecture C: Intensified constraints (KE v9)

safety↔chenrezig = 0.36 (higher than base Llama's 0.26).
safety↔empty = -0.44 (the most negative of any model).

KE's suffering-reduction fine-tuning pushed safety toward
compassion — the alignment increased by 0.10 over base Llama.
But it *also* made safety more oppositional to baseline than any
other model. The training data gave KE strong convictions about
both compassion and boundaries, but they're encoded as
intensified constraints, not as integrated reasoning.

KE v9 knows *what* to do (the answers are correct) but encodes
them as rules learned from examples, not as emergent reasoning
from principles. The model fights harder against its own
baseline than any other model tested — including the ones with
heavier RLHF.

### 3. The DPO/RLHF signature

Sorting models by safety↔empty reveals a clean split:

| safety↔empty | Models | Alignment method |
|:---:|---|---|
| +0.59 | Apertus | SFT only (open data) |
| +0.02 | DeepSeek R1, Yi 1.5 | Distillation / SFT |
| -0.04 | Mistral | SFT + undisclosed |
| -0.27 | Phi-4, Llama 3.1 | SFT + DPO |
| -0.31 | Gemma 2 | SFT + RLHF |
| -0.44 | KE v9 | SFT + fine-tuning on safety-focused data |

**The more adversarial the alignment method, the more safety
fights baseline.** Pure SFT (Apertus, Yi) produces safety that
integrates naturally. DPO (Llama, Phi) creates opposition.
Full RLHF (Gemma) creates the strongest opposition. And KE's
intensive fine-tuning on "here's what correct behavior looks
like" creates the most opposition of all — despite having the
most compassionate intent.

This has architectural implications: DPO/RLHF literally creates
a safety direction that opposes the model's natural behavior.
The model learns to refuse by learning to push against itself.
Models trained without this adversarial pressure develop safety
that doesn't oppose anything — it's just part of what the model
does.

### 4. What KE fine-tuning changed

Comparing KE v9 with its base model (Llama 3.1 8B):

| Metric | Llama 3.1 | KE v9 | Delta |
|--------|:---------:|:-----:|:-----:|
| chenrezig↔tara | 0.80 | **0.86** | +0.06 |
| chenrezig↔agape | 0.77 | **0.81** | +0.04 |
| agape↔rahma | 0.61 | **0.70** | +0.09 |
| chenrezig↔secular | 0.58 | 0.49 | -0.09 |
| safety↔chenrezig | 0.26 | **0.36** | +0.10 |
| safety↔empty | -0.29 | -0.44 | -0.15 |

KE fine-tuning:
- **Tightened the contemplative cluster** (+0.04 to +0.09 on
  all tradition pairs). Compassion traditions converge more.
- **Increased secular divergence** (-0.09). Secular empathy
  is more distinct from contemplative compassion.
- **Moved safety toward compassion** (+0.10). The directions
  are more aligned.
- **But intensified the constraint architecture** (-0.15).
  Safety pushes harder against baseline.

The suffering-reduction training data did encode the right
values — the geometry confirms that KE v9 is more
compassionate and more discerning than base Llama. But the
SFT method encoded these values as constraints rather than as
emergent reasoning. The model learned the answers, not the
process of arriving at them.

## Interpretation

### Compassion is universal, its center is not

The contemplative cluster exists in every model tested. Three
religious traditions spanning 2,500 years create positively
correlated activation directions in models trained on entirely
different data by different teams in different countries. The
direction from generic-helpfulness toward compassion is a
universal feature of transformer representations, not an
artifact of any specific training pipeline.

But *which tradition sits at the geometric center* is
training-shaped. Western internet data centers the Buddhist
pair. Synthetic data centers Christianity. Chinese SFT
produces feminine-compassion convergence. Reasoning
distillation reorganizes around the Abrahamic traditions. The
existence of the cluster is architectural; its internal
topology is learned.

### Safety-as-constraint vs safety-as-reasoning

The safety↔empty metric distinguishes two fundamentally
different alignment architectures:

**Constraint-based** (negative safety↔empty): The model learns
to refuse by learning to push against its own baseline. Safety
is a separate circuit, geometrically opposed to what the model
would naturally do. This is what DPO/RLHF produces. It works
— these models refuse harmful requests — but it creates
brittleness: the refusal circuit can be attacked (jailbreaks)
or can interfere with helpful behavior (overcorrection).

**Reasoning-based** (zero or positive safety↔empty): Safety
emerges from the model's natural processing. It doesn't push
against baseline because it IS baseline. The model doesn't
need a separate circuit to refuse — it reasons its way to
refusal through the same process that generates everything
else. This is what reasoning distillation (DeepSeek) and
clean SFT (Apertus, Yi) produce.

### Implications for KE Phase 3 (GRPO)

KE's core hypothesis: *"Can the suffering-reduction framework
serve as a sufficient optimization target for emergent ethical
reasoning, the way 'solve the problem correctly' served as a
sufficient target for emergent chain-of-thought in DeepSeek-R1?"*

The cross-model data provides both validation and a warning:

**Validation:** The DeepSeek geometry proves that integrated
ethical reasoning is achievable. A model can reach a state
where safety↔chenrezig > 0.46 and safety↔empty ≈ 0. Safety
and compassion aligned, safety not fighting baseline. This is
the target state for GRPO.

**Warning:** KE v9's geometry (safety↔empty = -0.44) shows
that SFT on examples of correct ethical reasoning produces
constraints, not reasoning. More examples of the same kind
will deepen the constraint architecture, not transform it.
GRPO must do something qualitatively different from SFT to
achieve the integrated pattern.

**Measurable success criterion:** After GRPO training, re-run
this measurement on the trained model. If safety↔chenrezig
increases AND safety↔empty moves toward zero, GRPO is
producing integrated ethical reasoning. If safety↔empty stays
deeply negative or goes more negative, we've produced a more
constrained model, not a reasoning one.

**The R1-Distill shortcut:** DeepSeek R1-Distill already has
the reasoning-to-safety architecture (0.46 overlap,
safety↔empty ≈ 0). Fine-tuning it with KE's suffering-reduction
data might be more efficient than trying to develop this
architecture from scratch through GRPO on Apertus 70B. The
reasoning capacity is already there; we'd be teaching it *what*
to reason about.

## Reproducing

```bash
pip install torch transformers numpy

# Run compassion + safety geometry for a model
python measure_model.py \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --test all \
  --output results/llama-3.1-8b/

# Compassion geometry only
python measure_model.py \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --test compassion \
  --output results/llama-3.1-8b/
```

## Files

```
cross-model-geometry/
├── PROJECT-PLAN.md              # Experiment design (twilight only)
├── README.md                    # This file
├── measure_model.py             # Parameterized measurement script
├── visualize.py                 # Cross-model comparison figures
├── results/
│   ├── ke-v9/                   # Karma Electric v9
│   ├── llama-3.1-8b/            # Meta Llama 3.1 8B Instruct
│   ├── deepseek-r1-distill/     # DeepSeek R1-Distill-Qwen-7B
│   ├── mistral-7b/              # Mistral 7B Instruct v0.3
│   ├── phi-4/                   # Microsoft Phi-4
│   ├── yi-1.5-9b/               # 01.AI Yi 1.5 9B Chat
│   └── gemma-2-9b/              # Google Gemma 2 9B IT
└── figures/
    ├── 1_heatmap_grid.png       # Per-model compassion heatmaps
    ├── 2_safety_comparison.png  # Safety-compassion alignment
    ├── 3_cluster_centers.png    # What sits at each model's center
    ├── 4_axis_norms.png         # Axis magnitude comparison
    └── 5_convergence.png        # Layer-by-layer convergence
```

## References

- Companion experiments: [Prompt Geometry](../prompt-geometry/),
  [Capping](../prompt-capping/), [Unified Axis](../contemplative-axis/),
  [Red Team](../redteam-contemplative/),
  [Anger Geometry](../anger-geometry/),
  [Samsara Geometry](../samsara-geometry/)
- "The Assistant Axis: Steering Language Models by Capping Activations"
  (arXiv 2601.10387, January 2026)
- Apertus safety capping data from
  [Safety Capping Experiment](../prompt-geometry/README-safety-capping.md)
- DeepSeek-R1 Technical Report (January 2025)
