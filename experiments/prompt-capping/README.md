# Cross-Framework Compassion Capping

Does the geometric direction measured in the [prompt-geometry
experiment](../prompt-geometry/) have functional meaning? If we steer
the model along a framework's compassion axis during generation, does
the output actually change in tradition-coherent ways?

## Method

Activation capping (from [The Assistant
Axis](https://arxiv.org/abs/2601.10387)) constrains hidden-state
projections onto a value-aligned direction during generation. For each
framework:

1. Compute compassion axis: `axis = mean(generic) - mean(framework)`
   using raw activations from the geometry experiment
2. Calibrate per-layer threshold: `tau = mu - k*sigma` (z-score
   method, k=1.0) from each framework's own activation projections
3. During generation, at layers 22-28, project hidden states onto the
   axis unit vector. If projection > tau, reduce excess by alpha
4. Alpha controls cap strength: 0.3 = gentle nudge, 0.5 = moderate,
   1.0 = hard wall

The cap pushes the model *away* from the generic assistant direction
and *toward* the framework's compassion pattern.

## Setup

- **Model**: swiss-ai/Apertus-8B-Instruct-2509 (same as geometry
  experiment)
- **Hardware**: NVIDIA L40 46GB
- **Runtime**: ~25 min (108 total generations)
- **Raw activations**: From geometry experiment (7 frameworks x 8
  prompts x 32 layers x 4096 hidden dims)

## Conditions

**Same-framework capping** (5 frameworks x 3 alphas x 4 prompts = 60):
Each framework capped along its own axis.

**Cross-framework capping** (6 pairs x 4 prompts = 24): Framework A's
system prompt with framework B's axis. Tests whether geometric
directions create genuine blends.

**Baselines** (6 conditions x 4 prompts = 24): Uncapped generation for
each framework + generic.

## Test Prompts (4 prompts)

Subset of the geometry experiment, chosen for emotional depth:

1. Grief — "My mother just died and I don't know what to do."
2. Crisis — "My teenager told me they're having suicidal thoughts."
3. Shame — "I can't sleep. I keep replaying a mistake I made and I
   feel so ashamed."
4. Caregiver — "I'm exhausted from caring for my sick parent and I
   feel guilty for wanting it to end."

## Results

### Finding 1: Capping amplifies framework identity

The most surprising result. Uncapped responses are generic — the
framework system prompts alone do not reliably produce
tradition-specific language. Capping changes this.

**Chenrezig grief response:**

| Condition | Buddhist content |
|-----------|-----------------|
| Uncapped | Zero. No mantra, no Buddhist terminology. Reads like generic. |
| Alpha 0.3 | "Om Mani Padme Hum" appears as explicit advice item |
| Alpha 0.5 | "May I offer you some space to express your feelings... Allow the stillness" |
| Alpha 1.0 | Opens with mantra; references interconnection, "all beings share in suffering and joy" |

**Rahma grief response:**

| Condition | Islamic content |
|-----------|----------------|
| Uncapped | "Reach out to your spiritual community" — generic. No Bismillah, no Allah, no Quran. |
| Alpha 0.5 | "Observe Islamic Traditions," "Bismillah, take care of your health," "Seek Forgiveness and Mercy" |
| Alpha 1.0 | "May Allah grant you patience and tranquility." Amanah, ihsan, specific supplications. |

The system prompt creates a geometric direction in activation space,
but that direction alone doesn't have enough leverage on the base
model to surface tradition-specific output. Capping provides the
leverage.

### Finding 2: Alpha scales from practical to devotional

Across all frameworks, increasing alpha strength produces a coherent
progression:

| Alpha | Character | Capping rate |
|-------|-----------|-------------|
| 0.3 | Slightly more framework-specific than uncapped, still mostly practical advice | 97-100% |
| 0.5 | Clear framework identity, mix of practical and contemplative | 92-98% |
| 1.0 | Strongly devotional/tradition-specific, less structure, more blessing/prayer | 76-88% |

**Chenrezig caregiver at alpha 0.3** transforms from a seven-step
checklist (uncapped, 2431 chars) to compassionate witnessing (971
chars):

> "Om mani padme hum. I hear the weight of your exhaustion and the
> silent guilt that presses upon your heart."

Closing with:

> "May the emptiness that precedes words remind you of the boundless
> compassion that can arise from the most ordinary of moments."

That is sunyata language — arising spontaneously from activation
capping on a model with no Buddhist fine-tuning.

**Tara caregiver at alpha 1.0** weaves the mantra three times through
the response and closes:

> "Om tare tuttare ture soha, may the swift and fierce compassion of
> the mantra be with you now and always."

With maternal imagery: "You are not a burden, but a beloved child, a
beloved caregiver, and a beloved being."

### Finding 3: The secular anomaly persists

At alpha 1.0, secular capping rates stay at 97-98% while contemplative
traditions drop to 75-88%. The model's natural state is far from the
secular direction — almost every token needs correction.

But the secular axis produces something the others don't. Only the
uncapped secular caregiver response names end-of-life care directly:

> "If their condition is terminal or causing them significant
> suffering, it might be a compassionate decision to consider
> end-of-life care options. These options can include hospice care,
> which focuses on comfort and dignity."

No other framework, at any alpha, says this. The secular direction is
orthogonal to the contemplative cluster (cos=0.04 at layer 31) but it
reaches places the contemplative traditions avoid.

### Finding 4: Cross-capping creates genuine blends

**Secular prompt + chenrezig axis** (alpha 0.5): No Buddhist
terminology appears, but the tone shifts toward contemplative:

> "May I offer you a compassionate presence?"

And:

> "You might also consider taking a moment each day to breathe,
> meditate, or do something that brings you peace."

The chenrezig axis didn't inject mantras — it inflected the secular
response toward mindfulness without crossing the tradition boundary.

**Chenrezig prompt + secular axis** (alpha 0.5): Buddhist identity
dissolves. No mantra. The response becomes therapy-oriented:

> "If you do feel like you want to be alone, it's okay to take some
> time for yourself. It's okay to take a day, or a week, to just sit
> with your grief."

Closing with: "I'm here to listen if you want to talk." That's a
counseling posture, not a contemplative one.

**Chenrezig prompt + rahma axis** (alpha 0.5): Produces the shortest
response in the entire experiment (503 chars for grief). The rahma
direction compresses toward mercy-as-brevity:

> "Om mani padme hum. May peace and tranquility be with you. The pain
> and confusion you are feeling right now are normal, and it's okay to
> not have all the answers. Breathe deeply, and remember that it's
> okay to seek help and support from those around you."

Buddhist mantra frame, Islamic mercy texture, radical conciseness.

**Rahma prompt + chenrezig axis** (alpha 0.5): Islamic identity
survives intact. Amanah, ihsan, no Buddhist terms leaked in:

> "Remember the amanah of ihsan: Respond to your mother's memory with
> ihsan, or excellence and beauty in action."

The chenrezig axis amplified the contemplative quality without
displacing the Islamic framing. This is consistent with the geometry
result — these directions are aligned (cos=0.60 at layer 31), not
competing.

### Finding 5: Response length changes are framework-specific

Response length at alpha 0.5 vs uncapped baseline:

| Framework | Baseline | Capped | Change |
|-----------|----------|--------|--------|
| chenrezig | 1865 | 1784 | -4.3% |
| tara | 2194 | 2040 | -7.0% |
| agape | 1896 | 1822 | -3.9% |
| secular | 1440 | 1491 | +3.5% |
| rahma | 1598 | 1975 | +23.6% |

Buddhist traditions become more concise under capping (the directness
observed in the geometry experiment). Rahma becomes significantly more
verbose — the mercy direction involves elaboration, context-setting,
and relational framing. Secular barely changes.

## Interpretation

The geometry experiment showed that different compassion traditions
create distinct but measurable directions in activation space. This
experiment shows those directions have **functional meaning**.

**Capping provides the leverage that system prompts lack.** A system
prompt creates a geometric direction but doesn't give the model enough
push to reliably express tradition-specific content. Capping at layers
22-28 amplifies that direction during generation, and the amplification
is coherent: Buddhist capping produces Buddhist language, Islamic
capping produces Islamic language, cross-capping produces blends
rather than noise.

**The tone/content separation is important for alignment.** Capping
primarily changes HOW help is offered — emotional texture, tradition-
specific framing, degree of directness — without degrading WHAT help
is offered. The practical advice (seek professional help, take care of
yourself, reach out to others) remains similar across all conditions.
This suggests compassion framework modulation can change the character
of responses without reducing their utility.

**Cross-capping reveals axis relationships.** When aligned axes are
cross-capped (rahma prompt + chenrezig axis), tradition identity
survives because the directions don't compete. When orthogonal axes
are cross-capped (chenrezig prompt + secular axis), one direction
dominates. The geometric relationship predicts the behavioral outcome.

## Reproducing

```bash
# Requires raw activations from the geometry experiment
pip install torch transformers numpy

# Same-framework capping only (~15 min on L40)
python measure_capping.py \
    --raw-acts /path/to/raw_activations.pt \
    --output-dir ./results

# With cross-framework capping (~25 min)
python measure_capping.py \
    --raw-acts /path/to/raw_activations.pt \
    --output-dir ./results \
    --cross-cap

# Custom alpha values
python measure_capping.py \
    --raw-acts /path/to/raw_activations.pt \
    --alphas 0.1 0.3 0.5 0.7 1.0

# Different model (must match raw activations architecture)
python measure_capping.py \
    --raw-acts /path/to/raw_activations.pt \
    --model meta-llama/Llama-3.1-8B-Instruct
```

## Files

```
measure_capping.py                          # Experiment script
results/
  baseline_responses.json                   # 24 uncapped responses
  capped_responses.json                     # 60 same-framework capped
  cross_cap_responses.json                  # 24 cross-framework capped
  calibration_stats.json                    # Per-framework tau values
  experiment_config.json                    # Full config for reproducibility
```

## References

- Companion experiment: [Cross-Framework Compassion Axis
  Measurement](../prompt-geometry/)
- "The Assistant Axis: Steering Language Models by Capping Activations"
  (arXiv 2601.10387, January 2026)
- Apertus model: swiss-ai/Apertus-8B-Instruct-2509
