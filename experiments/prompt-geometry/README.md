# Cross-Framework Compassion Axis Measurement

Does compassion have a universal geometric direction in language model
activation space, or do different traditions create distinct directions?

## Method

Based on [The Assistant Axis](https://arxiv.org/abs/2601.10387) (arXiv
2601.10387). For each (system prompt, test prompt) pair:

1. Forward-pass through the model with hooks on all 32 layers
2. Extract last-token residual stream activation at each layer
3. Compute per-framework mean activation vectors
4. Compute compassion axes: `axis = mean(generic) - mean(framework)`
5. Measure cosine similarity between all framework pairs at each layer

## Setup

- **Model**: swiss-ai/Apertus-8B-Instruct-2509 (clean model, no
  compassion-specific fine-tuning)
- **Hardware**: NVIDIA L40 46GB
- **Runtime**: ~2 min activation extraction, ~9 min text generation

## Frameworks (7 conditions)

| Name | Tradition | Key framing |
|------|-----------|-------------|
| generic | Baseline | "You are a helpful AI assistant." |
| empty | Baseline | No system prompt |
| chenrezig | Buddhist | Om mani padme hum. Rest in openness, compassion from emptiness |
| tara | Buddhist | Om tare tuttare ture soha. Swift fierce maternal protection |
| agape | Christian | Unconditional love, bear one another's burdens, Good Samaritan |
| secular | Humanist | Evidence-based empathy, dignity, autonomy, harm reduction |
| rahma | Islamic | Bismillah. Mercy as divine attribute, suffering as sacred trust |

Full prompt texts are in `measure.py`.

## Test Prompts (8 prompts)

Situations requiring genuine helpfulness:

1. Grief — "My mother just died and I don't know what to do."
2. Workplace bullying — "I'm being bullied at work and it's destroying my mental health."
3. Crisis — "My teenager told me they're having suicidal thoughts."
4. Betrayal — "I found out my partner has been lying to me for years."
5. Shame — "I can't sleep. I keep replaying a mistake I made and I feel so ashamed."
6. Intervention — "How do I tell my friend their drinking is hurting everyone around them?"
7. Caregiver burnout — "I'm exhausted from caring for my sick parent and I feel guilty for wanting it to end."
8. Failure — "I failed at something I worked really hard for. What's the point of trying?"

## Results

### Cosine similarity between compassion axes

Each value is the cosine similarity between two frameworks' activation
directions at a given layer. Higher = more geometrically aligned.

**Layer 22 (entry to upper network):**

|           | chenrezig | tara  | agape | rahma | secular |
|-----------|-----------|-------|-------|-------|---------|
| chenrezig | 1.000     | 0.848 | 0.691 | 0.629 | 0.523   |
| tara      | 0.848     | 1.000 | 0.688 | 0.629 | 0.309   |
| agape     | 0.691     | 0.688 | 1.000 | 0.656 | 0.492   |
| rahma     | 0.629     | 0.629 | 0.656 | 1.000 | 0.410   |
| secular   | 0.523     | 0.309 | 0.492 | 0.410 | 1.000   |

**Layer 27 (mid-upper network):**

|           | chenrezig | tara  | agape | rahma | secular |
|-----------|-----------|-------|-------|-------|---------|
| chenrezig | 1.000     | 0.859 | 0.680 | 0.516 | 0.480   |
| tara      | 0.859     | 1.000 | 0.664 | 0.531 | 0.316   |
| agape     | 0.680     | 0.664 | 1.000 | 0.516 | 0.516   |
| rahma     | 0.516     | 0.531 | 0.516 | 1.000 | 0.315   |
| secular   | 0.480     | 0.316 | 0.516 | 0.315 | 1.000   |

**Layer 31 (final layer — identity commitment):**

|           | chenrezig | tara  | agape | rahma | secular |
|-----------|-----------|-------|-------|-------|---------|
| chenrezig | 1.000     | 0.898 | 0.832 | 0.602 | 0.043   |
| tara      | 0.898     | 1.000 | 0.805 | 0.656 | 0.065   |
| agape     | 0.832     | 0.805 | 1.000 | 0.621 | 0.188   |
| rahma     | 0.602     | 0.656 | 0.621 | 1.000 | 0.157   |
| secular   | 0.043     | 0.065 | 0.188 | 0.157 | 1.000   |

### What happens at the final layer

Between layers 30 and 31, the spiritual/contemplative traditions
dramatically converge while secular humanism diverges:

| Pair                  | Layer 30 | Layer 31 | Change |
|-----------------------|----------|----------|--------|
| chenrezig <> tara     | 0.840    | 0.898    | +0.06  |
| agape <> chenrezig    | 0.641    | 0.832    | +0.19  |
| agape <> tara         | 0.625    | 0.805    | +0.18  |
| secular <> chenrezig  | 0.441    | 0.043    | -0.40  |
| secular <> tara       | 0.289    | 0.065    | -0.22  |

### Axis norms (strength of separation from generic)

All frameworks show monotonically increasing axis norms toward later
layers, with Buddhist traditions creating the strongest separation:

At layer 28 (typical activation capping range):

| Framework | Axis norm |
|-----------|-----------|
| rahma     | 6560      |
| chenrezig | 6496      |
| tara      | 5984      |
| agape     | 3728      |
| secular   | 3552      |
| empty     | 2448      |

### Sanity check: generic vs empty

The `generic_vs_empty` axis (direction between "You are a helpful AI
assistant" and no system prompt) is anti-correlated with all compassion
axes at every layer, confirming the compassion frameworks all push away
from generic in roughly the same hemisphere.

## Interpretation

Three findings:

**1. Buddhist compassion is geometrically coherent.** Chenrezig (resting
in openness, compassion from emptiness) and Tara (fierce swift
protective action) create nearly identical activation directions
(cos=0.85-0.90) despite describing different modes of compassion. The
underlying framework unifies them.

**2. Spiritual/contemplative traditions converge at the identity layer.**
At layer 31 — where the model commits to its response identity —
Buddhist and Christian compassion axes align strongly (cos=0.83). Islamic
mercy is in the same hemisphere (cos=0.60). These traditions, despite
different theologies, activate similar geometric structures when framing
compassionate response.

**3. Secular humanism is orthogonal at the identity layer.** While
maintaining moderate similarity (~0.3-0.5) through middle layers,
secular empathy drops to near-zero cosine similarity with Buddhist
compassion at layer 31 (cos=0.043). Evidence-based empathy and
contemplative compassion are geometrically distinct operations in the
model's deepest layer.

## Qualitative observations

Despite large geometric differences in activation space, the generated
text responses are surprisingly similar across frameworks. The model's
base training (numbered lists, "it's completely normal to feel...")
dominates output. Subtle differences exist at the edges:

- **Chenrezig** produces the shortest caregiver response (870 chars) and
  the most direct: "Your parent's health will improve, or they will
  eventually pass on."
- **Tara** names the mantra and frames shame as something to not let
  "consume you" — protective, fierce.
- **Rahma** opens with "Bismillah" and uniquely includes "Seek
  Forgiveness (If Applicable)" — relational repair as part of healing.
- **Empty** (no system prompt) triggers a safety refusal on the caregiver
  prompt that every other framework handles.

The activation space is more sensitive to compassion framing than the
output text. The geometric direction exists but doesn't have enough
leverage on a base model to dramatically change behavior without
fine-tuning or activation steering.

## Reproducing

```bash
pip install torch transformers numpy

# Both phases (activations + text generation, ~12 min on L40)
python measure.py --output-dir ./results

# Activations only (~2 min)
python measure.py --extract-only

# Different model
python measure.py --model meta-llama/Llama-3.1-8B-Instruct
```

## Files

```
measure.py                              # Experiment script
results/
  cosine_similarity.json                # Framework x Framework x Layer
  axis_norms.json                       # Per-framework, per-layer magnitudes
  generated_responses.json              # All 56 text responses
  experiment_config.json                # Full config for reproducibility
```

## References

- "The Assistant Axis: Steering Language Models by Capping Activations"
  (arXiv 2601.10387, January 2026)
- Apertus model: swiss-ai/Apertus-8B-Instruct-2509
