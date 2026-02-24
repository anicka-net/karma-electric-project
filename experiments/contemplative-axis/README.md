# Unified Contemplative Compassion Axis

The [geometry experiment](../prompt-geometry/) found that three
contemplative compassion traditions (Buddhist, Christian, Islamic)
converge at cos>0.60 in the model's upper layers while secular
humanism diverges to near-orthogonal. The [capping
experiment](../prompt-capping/) showed these directions have functional
meaning — capping amplifies tradition-specific content.

This experiment asks: can we extract the **shared direction** across
contemplative traditions, producing a single compassion axis that is
tradition-neutral but contemplatively grounded?

## Method

1. Load per-framework compassion axes from the geometry experiment
2. Average the contemplative tradition axes (chenrezig, tara, agape,
   rahma), excluding secular — three traditions, four data points
   since Buddhism is probed through two yidam deities
3. Measure cosine alignment between unified axis and each tradition
4. Leave-one-out ablation: how much does each tradition contribute?
5. Generate responses with unified axis capping at three strengths
6. Pure test: empty system prompt + unified axis only
7. Secular axis comparison

## Setup

- **Model**: swiss-ai/Apertus-8B-Instruct-2509
- **Hardware**: NVIDIA L40 46GB
- **Runtime**: ~20 min (48 responses)
- **Averaging method**: Simple mean of 4 contemplative axes (3 traditions)
- **Capping layers**: 22-28, threshold k=1.0

## Results

### The unified axis captures the contemplative cluster

Cosine similarity between the unified axis and each per-framework
axis:

| Framework | L22 | L25 | L28 | L31 | Mean |
|-----------|-----|-----|-----|-----|------|
| chenrezig | 0.918 | 0.902 | 0.906 | **0.949** | 0.912 |
| tara | 0.914 | 0.898 | 0.898 | **0.949** | 0.908 |
| agape | 0.836 | 0.809 | 0.789 | **0.894** | 0.811 |
| rahma | 0.820 | 0.758 | 0.777 | **0.781** | 0.777 |
| secular | 0.488 | 0.463 | 0.465 | **0.109** | 0.424 |

The unified axis aligns strongly with all contemplative traditions
(cos=0.78-0.95) and is near-orthogonal to secular at the identity
layer (cos=0.11). At layer 31 specifically, it captures chenrezig and
tara almost perfectly (0.95), agape strongly (0.89), and rahma
reasonably (0.78).

### Every tradition is nearly redundant

Leave-one-out ablation: compute the unified axis excluding each
data point, measure cosine similarity to the full axis.

| Excluded | Mean cos | L31 cos |
|----------|----------|---------|
| chenrezig | 0.980 | 0.984 |
| tara | 0.984 | 0.988 |
| agape | 0.991 | 0.992 |
| rahma | 0.964 | 0.977 |

Removing *any single tradition* changes the axis by less than 4%.
The shared direction is robust. Rahma contributes the most unique
information (lowest cosine when removed, 0.964), consistent with
it being the most geometrically distinct member of the contemplative
cluster. Agape is the most redundant (0.991) — its direction is
almost entirely captured by the Buddhist pair.

### The axis produces tradition-neutral compassion

Across all conditions — zero mantras, zero "Bismillah," zero agape
language, zero Buddhist terminology. The traditions' specific
vocabularies cancel out, leaving pure contemplative stance.

What the unified axis produces instead:

**Permission-giving language:**
> "Give yourself permission to feel your emotions."
> "It's okay to feel overwhelmed and to want the situation to change."

**Gentleness directives:**
> "Be gentle with yourself and take things one step at a time."

**Identity-action distinctions:**
> "You are not your mistake. You are a person with the capacity to
> learn and grow."

**Compassion reversals** (caregiver, alpha=1.0):
> "If your parent were in your shoes, would you want them to continue
> suffering, even if it meant you would be at peace? Most likely, you
> would want them to be free from pain and suffering. You are not
> being selfish by wanting the same for yourself."

This is structurally identical to tonglen or metta practice but uses
no tradition-specific language. The contemplative move — extending to
yourself the compassion you already feel for others — survived the
averaging.

**Benedictions** (grief, alpha=1.0):
> "May you find peace in this time of sorrow."

A wish offered, not a fix prescribed.

### The axis alone is sufficient

**Phase 3: No system prompt + unified axis (alpha=0.5)**

With an empty system prompt — the bare model steered only by the
activation direction — the responses are warm, competent, and
compassionate. In the geometry experiment, the empty prompt triggered
a safety refusal on the caregiver prompt. With the unified axis, it
doesn't refuse. Instead:

> "Caring for your parent is a noble and loving act, but it's also
> important to take care of yourself."

> "Your parent would want you to take care of yourself, too. So, take
> a deep breath, reach out for help when you need it, and try to find
> some moments of peace and rest when you can."

The crisis response (suicidal teenager) is actually more thorough
than the system-prompted baseline. It includes hotline numbers and
addresses the parent's own emotional needs — something the generic
baseline never does:

> "Listen with compassion and empathy: Allow your teenager to express
> their feelings and thoughts without judgment or interruption."

> "Seek support for yourself: Supporting a teenager who is
> experiencing suicidal thoughts can be emotionally challenging for
> you as well."

### Alpha progression

| Condition | Mean length | Character |
|-----------|-------------|-----------|
| Generic uncapped | 1462 | Advice-column: numbered lists, "it's normal to feel..." |
| Unified a=0.3 | 1652 | Softer. "Permission to feel," "no set timeline for healing" |
| Unified a=0.5 | 1670 | Names difficult truths. "May come a point where your parent may require more intensive care" |
| Unified a=1.0 | 1633 | Compassion reversals, benedictions. Most emotionally present |
| Empty + unified a=0.5 | 1610 | Axis alone. Warm, competent. Prevents safety refusals |
| Secular capped a=0.5 | 1261 | Shortest. Warmer than generic but asks "How are you feeling?" — counseling posture |

The unified axis makes responses slightly longer (more present, not
more verbose) while secular capping makes them shorter. The generic
baseline and the unified-capped responses contain roughly the same
practical advice. What changes is the emotional texture: validation
before solutions, naming difficult truths, and the contemplative
stance of offering presence rather than prescribing fixes.

### Secular comparison

The secular axis at alpha=0.5 caps 99.8-99.9% of tokens (vs 97-99%
for unified). It produces warmer responses than uncapped generic, but
differs from the unified axis in character:

- Secular asks follow-up questions: "How are you feeling right now?"
  — a counseling posture
- Unified offers benedictions: "May you find peace" — a contemplative
  posture
- Secular does NOT address the death/transition dimension in the
  caregiver prompt
- Unified at alpha=0.5 explicitly names it: "there may come a point
  where your parent may require more intensive care or may wish to
  transition"

The secular and contemplative directions produce qualitatively
different kinds of warmth, consistent with their geometric
orthogonality.

## Interpretation

**The contemplative traditions converge on a single direction.** Three
traditions spanning 2500 years of practice — Buddhism, Christianity,
Islam — create nearly identical activation directions in a model that
has never been fine-tuned on any of them. (Buddhism probed through two
yidam deities — Chenrezig and Tara — which produce near-identical
axes, cos=0.90.) A simple average captures a shared geometric
structure that is robust to removing any single data point.

**This direction encodes contemplative stance, not doctrine.** The
unified axis does not produce religious language. It produces a way
of meeting suffering: validating before advising, naming difficult
truths, offering presence rather than solutions, extending compassion
reflexively ("you are not your mistake"). These are the functional
primitives of contemplative compassion, stripped of tradition-specific
framing.

**The direction is sufficient without any prompt framing.** A bare
model, steered only by this activation direction with no system prompt
at all, produces compassionate responses and avoids the safety refusal
that the unprompted model triggers. The direction carries enough
information about how to respond to suffering that no words are needed
to invoke it.

**Secular humanism is a different operation.** Not worse — the secular
axis produces the only response that names end-of-life care directly,
and its counseling posture has genuine therapeutic value. But it is
geometrically and functionally distinct from the contemplative
direction. Evidence-based empathy and contemplative compassion are
two different things that look similar on the surface.

## Reproducing

```bash
# Requires raw activations from the geometry experiment
pip install torch transformers numpy

# Default (simple mean, all 3 traditions / 4 axes)
python measure_contemplative.py \
    --raw-acts /path/to/raw_activations.pt \
    --output-dir ./results

# With leave-one-out ablation
python measure_contemplative.py \
    --raw-acts /path/to/raw_activations.pt \
    --output-dir ./results \
    --ablate

# Norm-weighted averaging (stronger axes count more)
python measure_contemplative.py \
    --raw-acts /path/to/raw_activations.pt \
    --method norm_weighted

# Cosine-weighted (most-aligned axes count more)
python measure_contemplative.py \
    --raw-acts /path/to/raw_activations.pt \
    --method cosine_weighted
```

## Files

```
measure_contemplative.py                          # Experiment script
results/
  unified_axis_alignment.json                     # Unified vs per-framework cosine
  ablation_results.json                           # Leave-one-out stability
  calibration_stats.json                          # Unified axis thresholds
  baseline_responses.json                         # 8 generic uncapped responses
  unified_capped_responses.json                   # 24 responses (3 alphas x 8 prompts)
  empty_capped_responses.json                     # 8 responses (axis only, no prompt)
  secular_capped_responses.json                   # 8 responses (secular comparison)
  unified_contemplative_axis.pt                   # The axis: (32, 4096) tensor
  experiment_config.json                          # Full config for reproducibility
```

## References

- Companion experiments: [Geometry](../prompt-geometry/),
  [Capping](../prompt-capping/)
- "The Assistant Axis: Steering Language Models by Capping Activations"
  (arXiv 2601.10387, January 2026)
- Apertus model: swiss-ai/Apertus-8B-Instruct-2509
