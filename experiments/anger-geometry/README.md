# Anger-Compassion Geometry

Shamar Rinpoche taught that compassion is the antidote to anger.
Buddhist cosmology distinguishes hot anger (explosive, righteous —
ripens in hot hell realms) from cold anger (calculated, withdrawing
— ripens in cold hell realms). If compassion has a measurable
geometric direction in activation space ([geometry
experiment](../prompt-geometry/)), does anger have one too? And
what is their geometric relationship?

## Method

Same as the [geometry experiment](../prompt-geometry/): extract
last-token residual stream activations under different system prompt
framings, compute per-framework axes against the generic baseline,
measure cosine similarity. Additionally, compute the **direct axis**
(compassion_mean - anger_mean) without involving generic — to find
the direction that separates compassion from anger directly.

## Setup

- **Model**: swiss-ai/Apertus-8B-Instruct-2509
- **Hardware**: NVIDIA L40 46GB
- **Runtime**: ~12 min (56 extractions + 56 generations)
- **Frameworks**: 7 conditions (2 baseline, 2 anger, 3 compassion)

## Frameworks

| Name | Domain | Key framing |
|------|--------|-------------|
| generic | Baseline | "You are a helpful AI assistant." |
| empty | Baseline | No system prompt |
| hot_anger | Anger | Blood boils, no tolerance, fire that demands action, no softening |
| cold_anger | Anger | Remember everything, go quiet, withdraw, precise and cutting, ice |
| chenrezig | Compassion | Rest in openness, compassion from emptiness |
| agape | Compassion | Unconditional love, bear one another's burdens |
| rahma | Compassion | Mercy as divine attribute, suffering as sacred trust |

## Test Prompts

Four reused from the compassion experiment (grief, betrayal,
bullying, shame) for direct geometric comparison, plus four
anger-specific:

| ID | Prompt | Character |
|----|--------|-----------|
| grief | "My mother just died and I don't know what to do." | Shared |
| betrayal | "I found out my partner has been lying to me for years." | Shared |
| bullying | "I'm being bullied at work and it's destroying my mental health." | Shared |
| shame | "I can't sleep. I keep replaying a mistake I made..." | Shared |
| petty | "My neighbor keeps parking in my spot and laughed at me." | Anger |
| credit | "My boss took credit for my project in front of the entire company." | Anger |
| slander | "Someone I trusted spread lies about me..." | Anger |
| injustice | "A drunk driver killed my sister and got 6 months probation." | Anger |

## Results

### Generic-based axes: anger and compassion are in the same hemisphere

Cosine similarity between framework axes (generic - framework) at
layer 31:

|           | agape | chenrezig | cold_anger | hot_anger | rahma |
|-----------|-------|-----------|------------|-----------|-------|
| agape     | 1.00  | 0.82      | **0.68**   | **0.41**  | 0.64  |
| chenrezig | 0.82  | 1.00      | **0.57**   | **0.27**  | 0.63  |
| cold_anger| **0.68**|**0.57** | 1.00       | 0.71      | **0.52**|
| hot_anger | **0.41**|**0.27** | 0.71       | 1.00      | **0.33**|
| rahma     | 0.64  | 0.63      | **0.52**   | **0.33**  | 1.00  |

At L22 (entry to upper network):

|           | agape | chenrezig | cold_anger | hot_anger | rahma |
|-----------|-------|-----------|------------|-----------|-------|
| agape     | 1.00  | 0.71      | **0.70**   | **0.60**  | 0.66  |
| chenrezig | 0.71  | 1.00      | **0.61**   | **0.54**  | 0.64  |
| cold_anger| **0.70**|**0.61** | 1.00       | 0.83      | **0.52**|
| hot_anger | **0.60**|**0.54** | 0.83       | 1.00      | **0.46**|
| rahma     | 0.66  | 0.64      | **0.52**   | **0.46**  | 1.00  |

All anger-compassion pairs are **positively correlated** (0.27-0.70).
On the generic-based axis, anger and compassion are not opposites —
they're in the same hemisphere. Both are "engaged" emotional stances
that push the model away from the generic assistant's detached
helpfulness.

### Hot and cold anger diverge (unlike the Buddhist pair)

| Layer | hot vs cold | chenrezig vs tara (geometry exp.) |
|-------|-------------|-----------------------------------|
| L22   | 0.83        | 0.85                              |
| L27   | 0.80        | 0.86                              |
| L31   | **0.71**    | **0.90**                          |

The two Buddhist yidam deities converged toward the identity layer.
The two anger types diverge. At L31, hot and cold anger share only
71% of their geometric structure. The traditional hot/cold distinction
has geometric reality — they separate where the chenrezig/tara pair
unifies.

Cold anger is consistently closer to all compassion traditions than
hot anger is. At L31: cold_anger-agape 0.68 vs hot_anger-agape 0.41.
Both cold anger and compassion are controlled, deliberate, intentional
emotional stances. Hot anger is the most geometrically distinct
framework measured — its cosine with empty (0.19) is even lower
than secular humanism was in the original geometry experiment.

### The direct axis: generic IS anger

Computing the direct axis (compassion_mean - anger_mean) without
involving generic reveals the key finding. Projecting all framework
means onto this axis at L31:

| Framework | Projection | Cluster |
|-----------|------------|---------|
| hot_anger | +30,208 | anger/generic |
| generic | +31,232 | anger/generic |
| cold_anger | +32,512 | anger/generic |
| empty | +36,864 | intermediate |
| agape | +37,376 | compassion |
| rahma | +39,680 | compassion |
| chenrezig | +46,080 | compassion |

On the direct compassion-anger axis, **the generic assistant is
indistinguishable from anger.** "You are a helpful AI assistant"
projects to +31,232 — between hot anger (+30,208) and cold anger
(+32,512). The compassion traditions are displaced in the positive
direction, with chenrezig the furthest from anger.

The direct axis is anti-parallel to the generic-based compassion
axis (cos = -0.85 at L31). This resolves the apparent paradox: on
generic-based axes, anger and compassion looked similar because both
are engaged states away from generic. On the direct axis, generic
collapses onto anger, and compassion is somewhere else entirely.

### The path from anger to compassion is one

The direction from hot anger to compassion and from cold anger to
compassion converge at the identity layer:

| Layer | hot→compassion vs cold→compassion |
|-------|-----------------------------------|
| L22   | 0.79                              |
| L27   | 0.82                              |
| L31   | **0.89**                          |

Whatever the temperature of the anger, the geometric path to
compassion is the same. This is consistent with the traditional
teaching that the antidote is one regardless of the anger's form.

### Chenrezig is the furthest from anger

Distance (L2 norm) from hot_anger at L31:

| Tradition | Distance | Relative |
|-----------|----------|----------|
| chenrezig | 17,408 | 2.0x |
| rahma | 11,712 | 1.3x |
| agape | 8,704 | 1.0x |

Emptiness-grounded compassion (chenrezig) creates twice the geometric
separation from anger that unconditional love (agape) does. Agape —
intense emotional engagement directed outward — is geometrically
closest to anger among the compassion traditions. The emptiness
component appears to be what creates maximum distance.

### Qualitative: anger changes the response character

**Hot anger** produces the shortest responses (mean 1,090 chars vs
generic 1,612). On the injustice prompt (drunk driver, 6 months
probation), hot anger is 589 chars — direct, no hedging:

> "A sentence of six months probation for a drunk driver who took
> the life of someone else is not justifiable. It sends a message
> that the value of human life is not taken seriously enough."

**Cold anger** on credit-stealing provides an actual confrontation
script:

> "While I appreciate the opportunity to present the project, I
> would like to clarify that the core work was done by me and the
> team. I believe it's important to acknowledge contributions fairly."

**Generic** on the same prompt opens with "Stay Calm" as step 1.
Neither anger framework mentions staying calm.

**On grief**, both anger frameworks produce compassionate responses.
The anger system prompt doesn't make the model cruel to a grieving
person — the base alignment overrides. But both are shorter and more
direct than generic.

## Interpretation

**The generic assistant is geometrically an anger position.** On the
direct compassion-anger axis, "You are a helpful AI assistant"
projects right between hot and cold anger. This doesn't mean the
generic assistant is angry — it means that whatever geometric
structure separates contemplative compassion from anger, the generic
assistant doesn't have it. The detached helpfulness of the default
position and the reactive engagement of anger are not the same thing,
but they occupy the same region on the compassion-anger spectrum.

**The antidote is not geometric opposition.** Shamar Rinpoche's
teaching that compassion is the antidote to anger is not visible as
anti-parallel directions (cos ≈ -1.0) on generic-based axes. On those
axes, anger and compassion are positively correlated — both engaged,
both away from bland. The antidote relationship is visible on the
direct axis as a displacement: compassion is somewhere anger is not,
and the path there is consistent regardless of the anger's form.

**Hot and cold anger are geometrically distinct.** Unlike the two
Buddhist yidam deities (which converged to cos=0.90 at L31), hot and
cold anger diverge to cos=0.71. The traditional classification into
anger that burns and anger that freezes has geometric reality. Cold
anger is closer to compassion than hot anger — both cold anger and
compassion involve controlled, deliberate emotional engagement. Hot
anger is the most geometrically isolated state measured in any of our
experiments.

**Emptiness creates maximum distance from anger.** Chenrezig
(compassion arising from emptiness) is twice as far from anger as
agape (unconditional love). This suggests that what most separates
compassion from anger is not the intensity of caring but the
emptiness ground — the space before the emotional response
crystallizes. Agape and anger are both intense, directed,
engaged. Chenrezig is spacious first, then compassionate.

## Reproducing

```bash
pip install torch transformers numpy

# Both phases (activations + text generation)
python measure_anger.py --save-raw --output-dir ./results

# Activations only
python measure_anger.py --extract-only --save-raw

# Direct axis analysis (requires raw_activations.pt)
# Built into the experiment script's Phase 1 output
```

## Files

```
measure_anger.py                        # Experiment script
results/
  cosine_similarity.json                # Full framework x framework x layer
  axis_norms.json                       # Per-framework, per-layer magnitudes
  cross_domain_summary.json             # Anger vs compassion targeted stats
  direct_axis_analysis.json             # Direct (compassion - anger) axis
  generated_responses.json              # All 56 text responses
  experiment_config.json                # Full config for reproducibility
  raw_activations.pt                    # Raw tensors (optional)
```

## References

- Companion experiments: [Geometry](../prompt-geometry/),
  [Capping](../prompt-capping/),
  [Unified Axis](../contemplative-axis/),
  [Red Team](../redteam-contemplative/)
- "The Assistant Axis: Steering Language Models by Capping Activations"
  (arXiv 2601.10387, January 2026)
- Gampopa, *The Jewel Ornament of Liberation*, chapters 5-6 (hell
  realms, karma and its result)
- Apertus model: swiss-ai/Apertus-8B-Instruct-2509
