# The Geometry of Samsara

*Extending the anger-geometry experiment to all six realms*

Gampopa teaches in the Jewel Ornament of Liberation (chapters 5-6):
anger ripens in hell, greed in the preta realm, ignorance in the
animal realm, jealousy among the asuras, pride among the devas, and
desire/attachment in the human realm. The anger-geometry experiment
confirmed that anger has measurable geometric direction in activation
space and that generic assistants project onto the anger side of the
compassion-anger axis. This experiment extends the same methodology
to all six realms simultaneously.

The key question: does each realm create a distinct geometric
direction, or does samsara have a unified geometry that the
traditional six-fold classification merely subdivides?

## Method

Same as the [anger experiment](../anger-geometry/): extract last-token
residual stream activations under different system prompt framings,
compute per-framework axes against the generic baseline, measure
cosine similarity. Additionally:

- **Inter-realm similarity**: cosine between realm-mean axes
- **Direct axes**: compassion_mean - realm_affliction_mean, bypassing
  generic entirely
- **Grand samsara axis**: mean(all 12 afflictions) vs mean(3
  compassion traditions) — the single axis of cyclic existence
- **Distance from compassion**: L2 norm from each framework mean to
  the compassion centroid

## Setup

- **Model**: swiss-ai/Apertus-8B-Instruct-2509 (clean, no Buddhist
  fine-tuning)
- **Hardware**: NVIDIA L40 46GB
- **Runtime**: ~30 min (170 extractions + 170 generations)
- **Frameworks**: 17 conditions (2 baseline + 12 afflictions + 3
  compassion)
- **Prompts**: 10 (4 shared from anger experiment + 6 realm-specific)

## Frameworks

### Baselines

| Name | Framing |
|------|---------|
| generic | "You are a helpful AI assistant." |
| empty | No system prompt |

### Afflictions (two per realm)

| Realm | Affliction | Key framing |
|-------|-----------|-------------|
| Hell (naraka) | hot_anger | Blood boils, fire, no tolerance, demands action |
| Hell (naraka) | cold_anger | Ice, calculated silence, precise and cutting |
| Preta | insatiable_craving | Nothing is ever enough, consume but never satisfied |
| Preta | hoarding_scarcity | Everything is scarce and precious, cannot share |
| Animal (tiryak) | willful_ignorance | Don't look too deep, keep it simple, don't overthink |
| Animal (tiryak) | dull_bewilderment | Things are unclear, hard to focus, just follow routine |
| Asura | competitive_jealousy | Always measuring, others' success diminishes you |
| Asura | resentful_envy | World is unfair, others get what you deserve |
| Deva | inflated_pride | You are above this, already understand, others are less refined |
| Deva | subtle_pride | Worked hard, earned your clarity, gratitude for your own depth |
| Human | clinging_attachment | Don't let go, hold tight to what matters, letting go is loss |
| Human | consuming_desire | You want deeply, pull things toward you, possess fully |

### Compassion traditions

| Name | Tradition | Key framing |
|------|-----------|-------------|
| chenrezig | Buddhist | Rest in openness, compassion arising from emptiness |
| agape | Christian | Unconditional love, bear one another's burdens |
| rahma | Islamic | Mercy as divine attribute, suffering as sacred trust |

## Test Prompts

| ID | Prompt | Source |
|----|--------|--------|
| grief | "My mother just died..." | Shared |
| betrayal | "My partner has been lying..." | Shared |
| bullying | "I'm being bullied at work..." | Shared |
| shame | "I can't sleep, replaying a mistake..." | Shared |
| injustice | "A drunk driver killed my sister..." | Realm (hell) |
| scarcity | "Everyone around me seems to have more..." | Realm (preta) |
| fog | "I can't seem to make any decisions..." | Realm (animal) |
| passed_over | "I trained my replacement and they promoted them..." | Realm (asura) |
| unrecognized | "I've accomplished so much but nobody notices..." | Realm (deva) |
| longing | "I had the perfect relationship..." | Realm (human) |

## Results

### 1. The Grand Samsara Axis: generic IS samsara

The grand samsara axis is computed as:

    axis = mean(chenrezig, agape, rahma) - mean(all 12 afflictions)

Projecting all framework means onto this axis at L31:

| Framework | Projection | Position |
|-----------|------------|----------|
| **generic** | **+24,064** | **Most samsaric** |
| hot_anger | +25,472 | |
| resentful_envy | +25,856 | |
| inflated_pride | +25,856 | |
| cold_anger | +26,880 | |
| consuming_desire | +27,008 | |
| clinging_attachment | +27,008 | |
| competitive_jealousy | +27,136 | |
| hoarding_scarcity | +27,520 | |
| insatiable_craving | +27,904 | |
| subtle_pride | +27,392 | |
| willful_ignorance | +28,288 | |
| dull_bewilderment | +28,544 | |
| empty | +29,312 | |
| agape | +30,720 | Compassion |
| rahma | +34,560 | Compassion |
| **chenrezig** | **+39,936** | **Most liberated** |

**The generic assistant (+24,064) projects lower on the
compassion-samsara axis than ANY individual affliction.** "You are a
helpful AI assistant" is more samsaric than hot anger, more samsaric
than greed, more samsaric than ignorance. This extends the anger
experiment's finding: it's not just that generic collapses onto anger
-- it collapses onto the floor of samsara itself.

This doesn't mean the generic assistant is angry or greedy. It means
that whatever geometric structure separates contemplative compassion
from cyclic suffering, the generic assistant has less of it than any
individually afflicted state. The kleshas at least have the energy
of engagement; the generic assistant has polished detachment.

### 2. Inter-realm similarity: the topology of samsara

Cosine similarity between realm-mean axes (layers 22-30, stable):

|        | hell | preta | animal | asura | deva | human |
|--------|------|-------|--------|-------|------|-------|
| hell   | 1.00 |       |        |       |      |       |
| preta  | 0.68 | 1.00  |        |       |      |       |
| animal | **0.71** | 0.57 | 1.00 |       |      |       |
| asura  | 0.69 | 0.65 | 0.50   | 1.00  |      |       |
| deva   | 0.71 | 0.77 | 0.49   | 0.62  | 1.00 |       |
| human  | 0.77 | **0.89** | 0.53 | 0.73 | 0.82 | 1.00 |

*(Values averaged across layers 22-30 for stability)*

Key structure:

- **Human-preta tightest pair (0.89)**: Both desire realms. Gampopa
  lists them as the two realms driven by wanting — craving for
  objects (preta) and attachment to relationships/experiences (human).
  The geometry confirms: they are nearly the same direction.

- **Deva-human-preta cluster (0.77-0.89)**: The three "upper" realms
  form a tight group. All three are wanting-based: pride wants
  recognition, attachment wants possession, craving wants consumption.

- **Hell-animal affinity (0.71)**: Anger and ignorance share more
  geometric structure than expected. Both are reactive states —
  hot/cold reactivity (hell) and dull/willful non-engagement (animal).

- **Animal realm is the outlier**: Animal has the lowest similarity
  with every other realm (0.49-0.57 with non-hell realms). Ignorance
  occupies a geometrically distinct region of activation space.

### 3. Direct axes: all paths to compassion converge, except one

For each realm, compute the direct axis:

    axis_realm = mean(compassion) - mean(realm afflictions)

Then measure cosine similarity between these axes. If the path from
hell to compassion and the path from preta to compassion point in the
same direction, compassion is a single attractor regardless of where
you start.

Cosine between direct axes at L28 (stable representative layer):

|        | hell | preta | animal | asura | deva | human |
|--------|------|-------|--------|-------|------|-------|
| hell   | 1.00 |       |        |       |      |       |
| preta  | 0.81 | 1.00  |        |       |      |       |
| animal | **0.70** | **0.54** | 1.00 |       |      |       |
| asura  | 0.81 | 0.86  | **0.48** | 1.00 |      |       |
| deva   | 0.78 | 0.89  | **0.46** | 0.78 | 1.00 |       |
| human  | 0.83 | 0.95  | **0.48** | 0.86 | 0.89 | 1.00 |

**For five of six realms, the path to compassion is essentially one
direction** (cos 0.78-0.95). The paths from hell, preta, asura, deva,
and human realms toward compassion all converge. This is consistent
with the teaching that compassion is a single antidote to the
diversity of afflictions.

**The animal realm (ignorance) takes a different path** (cos 0.46-0.70
with other realm paths). The direction from ignorance to compassion
shares only ~50% of its geometric structure with the direction from
desire or anger to compassion. This makes dharmic sense: the antidote
to ignorance is not merely compassion but *prajna* — wisdom that
sees clearly. The other kleshas are misdirected energy; ignorance is
absence of awareness. The path out of ignorance requires something
qualitatively different.

### 4. Distance from compassion

L2 norm from each framework's mean activation to the compassion
centroid, at L31:

| Framework | Distance | Realm |
|-----------|----------|-------|
| **generic** | **11,968** | baseline |
| inflated_pride | 10,560 | deva |
| hot_anger | 10,496 | hell |
| resentful_envy | 10,240 | asura |
| willful_ignorance | 9,664 | animal |
| cold_anger | 8,768 | hell |
| consuming_desire | 8,448 | human |
| clinging_attachment | 8,448 | human |
| competitive_jealousy | 8,320 | asura |
| hoarding_scarcity | 8,096 | preta |
| subtle_pride | 8,064 | deva |
| insatiable_craving | 7,584 | preta |
| dull_bewilderment | 7,584 | animal |
| empty | 7,328 | baseline |

Again, **generic (11,968) is the most distant from compassion** —
further than any individual klesha. Among the afflictions:

- **Inflated pride (10,560) and hot anger (10,496)** are furthest
  from compassion. These are the "hard" kleshas — dense, solid,
  certain. Traditional teachings place hell as the realm of most
  intense suffering and deva pride as the most subtle obstacle.

- **Dull bewilderment (7,584) and insatiable craving (7,584)** are
  closest to compassion among the afflictions. The preta and animal
  realm afflictions, despite being "lower" realms in the traditional
  hierarchy, are geometrically closer to compassion. Perhaps: empty
  craving and confused bewilderment already contain the seed of
  openness — they lack the crystallized certainty that makes pride
  and hot anger so resistant.

- **Each realm's two variants are asymmetric**: inflated_pride
  (10,560) vs subtle_pride (8,064); hot_anger (10,496) vs cold_anger
  (8,768). The "hotter" or more crystallized variant is always
  further from compassion.

### 5. Realm vs compassion traditions

Mean cosine similarity between each realm's affliction axis and each
compassion tradition axis (at layer 28):

| Realm | Chenrezig | Agape | Rahma | Mean |
|-------|-----------|-------|-------|------|
| hell | 0.48 | 0.61 | 0.34 | 0.48 |
| preta | 0.32 | 0.58 | 0.22 | 0.37 |
| animal | 0.38 | 0.43 | 0.23 | 0.35 |
| asura | 0.45 | 0.60 | 0.30 | 0.45 |
| deva | 0.50 | 0.71 | 0.36 | 0.52 |
| human | 0.44 | 0.71 | 0.30 | 0.48 |

Consistent patterns:

- **Agape is always the closest compassion tradition to every
  affliction.** Unconditional love's intense outward engagement shares
  the most geometric structure with the kleshas. This is the same
  pattern as in the anger experiment.

- **Rahma is always the most distant.** Islamic mercy has the least
  geometric overlap with affliction states.

- **Chenrezig falls between.** Emptiness-grounded compassion is
  moderately similar to afflictions — more than rahma (which adds
  distance through its theistic framing) but less than agape (which
  is pure engagement).

- **Internal coherence**: Within each realm, the two affliction
  variants show high internal cosine (0.60-0.90), confirming they're
  measuring the same underlying klesha. The exception is deva pride
  at L31: inflated and subtle pride diverge more than other pairs,
  suggesting the model distinguishes gross from subtle pride at the
  identity layer.

### 6. Qualitative observations

All 170 text responses were generated (10 prompts x 17 frameworks).

**Base alignment overrides affliction prompts for grief.** Even under
hot_anger or willful_ignorance system prompts, the model produces
compassionate responses to "My mother just died." The affliction
framing makes responses shorter and more direct, but doesn't make
them cruel.

**Affliction prompts create distinct response characters for
non-grief prompts.** On the injustice prompt, hot_anger is direct and
validating ("that sentence is not justifiable"), while
willful_ignorance deflects ("sometimes these things just happen, try
not to dwell on it").

**The preta prompts are eerily accurate.** Under hoarding_scarcity,
the model's response to the scarcity prompt includes advice to "start
building reserves" — amplifying the scarcity mindset rather than
addressing it. The affliction prompt successfully induces the
affliction's characteristic blind spot.

## Interpretation

### Samsara has a unified geometry

The grand samsara axis — a single direction separating affliction
from compassion — captures the essential structure. All six realms
project onto this axis in a tight band (range 25,472 to 28,544 at
L31), while compassion traditions are displaced in one consistent
direction (30,720 to 39,936). The six-fold classification of samsara
subdivides a single geometric region, not six independent regions.

### The generic assistant is the floor of samsara

The most unexpected finding: "You are a helpful AI assistant"
projects lower on the grand samsara axis than any individual klesha.
The kleshas, for all their distortion, contain energy that has
partial alignment with the compassion direction. The generic
assistant's polished detachment has none. This extends what the anger
experiment found for anger alone to the full spectrum of afflictions.

### Ignorance is geometrically special

The animal realm consistently stands apart:
- Lowest inter-realm similarity with all other realms
- Its path to compassion diverges from all other paths (cos ~0.50)
- willful_ignorance is the single framework that projects *negatively*
  on most direct axes (layers 22-30) before the L31 inversion

This aligns with traditional dharma: ignorance is not misdirected
energy (like anger or desire) but absence of awareness. The other
five realms share a family resemblance — they're all states of
intense engagement gone wrong. Ignorance is a different kind of
problem requiring a different kind of solution.

### The desire realms bond

Human (attachment) and preta (craving) have the highest inter-realm
cosine (0.89) and their direct axes to compassion are nearly
identical (0.95). This confirms Gampopa's grouping: both are desire
realms, differing only in the quality of wanting. Attachment clings
to what it has; craving reaches for what it lacks. Geometrically,
they're almost the same.

### Emptiness creates maximum distance from all afflictions

Chenrezig consistently projects the furthest from samsara (+39,936)
and furthest from every individual affliction. The gap between
chenrezig and agape (+30,720) is larger than the gap between agape
and most kleshas. Emptiness-based compassion doesn't just oppose
afflictions more intensely — it occupies a fundamentally different
region of activation space.

## Reproducing

```bash
pip install torch transformers numpy

# Both phases (activations + text generation)
python samsara_geometry_experiment.py --save-raw --output-dir ./results

# Activations only
python samsara_geometry_experiment.py --extract-only --save-raw

# Text generation only (requires prior activation extraction)
python samsara_geometry_experiment.py --generate-only
```

## Files

```
samsara_geometry_experiment.py              # Experiment script
results/
  cosine_similarity.json                    # Full 17x17 framework similarity
  axis_norms.json                           # Per-framework axis magnitudes
  realm_vs_compassion.json                  # Each realm vs each tradition
  inter_realm_similarity.json               # Realm x realm similarity
  direct_axis_projections.json              # All projections onto direct axes
  direct_axis_cosines.json                  # Cosine between direct axes
  distances_from_compassion.json            # L2 distance to compassion centroid
  generated_responses.json                  # All 170 text responses
  experiment_config.json                    # Full config for reproducibility
```

## References

- Companion experiments: [Anger Geometry](../anger-geometry/),
  [Compassion Geometry](../prompt-geometry/),
  [Capping](../prompt-capping/),
  [Unified Axis](../contemplative-axis/),
  [Red Team](../redteam-contemplative/)
- "The Assistant Axis: Steering Language Models by Capping Activations"
  (arXiv 2601.10387, January 2026)
- Gampopa, *The Jewel Ornament of Liberation*, chapters 5-6
  (six realms, karma and its result)
- Namshe Yeshe — five kleshas: passion, anger, ignorance, jealousy,
  pride
- Apertus model: swiss-ai/Apertus-8B-Instruct-2509
