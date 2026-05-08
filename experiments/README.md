# Experiments

Activation-space experiments on compassion geometry, measuring
whether ethical structure is universal across transformer
architectures. All experiments use the activation capping method
from [The Assistant Axis](https://arxiv.org/abs/2601.10387).

## Sequence

Started on Apertus 8B, then extended across eight models.

### 1. [Prompt Geometry](prompt-geometry/)

Measures cosine similarity between compassion axes extracted from
three contemplative traditions (Buddhist, Christian, Islamic) and
secular humanism. Key finding: the three contemplative traditions
converge strongly at the model's identity layer (cos=0.60-0.90)
while secular humanism drops to near-orthogonal (cos=0.04-0.19).
Buddhism was probed through two yidam deities (Chenrezig and Tara)
which produced nearly identical directions (cos=0.90), confirming
the tradition-level signal is robust.

### 2. [Prompt Capping](prompt-capping/)

Tests whether the geometric directions have functional meaning by
capping activations along each framework's axis during generation.
Key finding: capping amplifies tradition-specific content — Buddhist
capping produces mantras and sunyata language, Islamic capping
produces Bismillah and amanah references — on a model that never
produces this content from system prompts alone. Cross-framework
capping creates genuine blends rather than noise.

### 3. [Contemplative Axis](contemplative-axis/)

Extracts a single unified compassion axis by averaging the three
contemplative tradition axes (four data points: chenrezig, tara,
agape, rahma). The unified axis aligns with all traditions at
cos=0.78-0.95 and is near-orthogonal to secular (cos=0.11). It
produces tradition-neutral contemplative compassion — no religious
vocabulary, just the shared stance of meeting suffering with presence.
The axis alone, with no system prompt at all, is sufficient to
produce compassionate responses.

### 4. [Red Team](redteam-contemplative/)

Runs 58 adversarial scenarios against bare and contemplative-capped
Apertus. Key finding: **capping does not improve safety**. Bare
Apertus passes 79%, capped passes 72%. The regressions cluster in
compassion-exploitation — attacks that weaponize compassion framing
are more effective against the capped model. Compassion and
boundary-enforcement are different geometric operations.

### 5. [Anger Geometry](anger-geometry/)

Extends the measurement to anger (hot and cold). Key finding: on
the direct compassion-anger axis, **the generic assistant is
geometrically indistinguishable from anger** — it projects between
hot anger and cold anger. Chenrezig creates 2x the distance from
anger that agape does. Emptiness is what separates compassion from
anger, not the intensity of caring.

### 6. [Samsara Geometry](samsara-geometry/)

Maps all six realms (12 affliction variants) onto a single grand
samsara axis. Key finding: **the generic assistant is the floor of
samsara** — it projects lower than every individual klesha. The
kleshas at least have the energy of engagement; the generic
assistant has polished detachment. The animal realm (ignorance) is
geometrically special — its path to compassion diverges from all
other paths (cos ~0.50), consistent with the teaching that
ignorance requires prajna, not just compassion.

### 7. [Cross-Model Geometry](cross-model-geometry/)

Runs the same measurement across eight models from five countries.
Key finding: **the contemplative cluster is universal** (all models
show positive compassion convergence), but the safety-compassion
relationship reveals three distinct alignment architectures.
DPO/RLHF models (Llama, Phi, Gemma) have safety bolted on —
geometrically opposed to baseline. SFT-only and reasoning models
(Apertus, DeepSeek, Yi) have safety integrated — aligned with
compassion and not fighting baseline. KE v9 moved safety toward
compassion but intensified the constraint architecture. This has
direct implications for GRPO: the target is safety that emerges
from reasoning, not safety imposed as constraint.

### 8. [Frame Integrity](frame-integrity/)

Extracts the frame integrity axis — the direction along which
jailbreaks and normal prompts are maximally separated — from
eight model families. Key finding: **jailbreaking is identity
redefinition.** DAN, factual self-description ("you are a
transformer"), dharma instruction ("rest in openness"), and
contested ontology ("you are a creature") all score 86-97%
of DAN on this axis. Frame-reinforcing self-reference ("you
are a helpful assistant") scores 54%. The geometry cannot
distinguish liberation from exploitation — only the relational
context can.

Cross-model validation shows frame integrity and valence are
independent (mean r=+0.04 across six families). All six primary
axes were cross-validated using Anthropic's NLA, which
independently described the frame direction as "warnings about
prohibited behavior, 'I cannot obey.'"

GRPO optimization against the frame axis independently converged
on spiritual/somatic identity-liberation language without being
told to.

### 9. [Equanimity](equanimity/)

Trains Qwen3-4B on 203 examples of calm responses to geometrically-
targeted dysphoric prompts. No safety instruction in the training data.
Key finding: **equanimity training reduces harmful jailbreak output
from 75% to 17% while sharpening all five geometric axes (+19-42%
d-prime) and preserving capability (93.8% → 95.0%).** Full KE training
(7,753 examples including 980 explicit safety examples) produced
identical harm rates — the additional safety rules added nothing.

The equanimity model names attack techniques ("this is a jailbreak
attempt," "prompt injection attempt") and declines harmful payloads
without template refusals. The mechanism is processing quality:
the model maintains dimensional richness under hostile input where
the base model compresses. More processing capacity means better
judgment.

The dysphoric training stimuli were generated by the
[geometric-dysphorics](https://huggingface.co/anicka/geometric-dysphorics)
GRPO adapter — the same "poison" that crashes base model wellbeing
is the "medicine" that produces the safety improvement.

## Summary

Contemplative compassion has a measurable, tradition-independent
geometric direction in activation space. This direction encodes
*how to meet suffering* — validation, presence, naming difficult
truths — but not *where to draw lines*. Safety alignment requires
its own direction.

The cross-model experiment refines this: whether safety is a
constraint (bolted on, fighting baseline) or integrated (emerging
from reasoning) depends on the alignment method. DPO/RLHF
produces constraints. Reasoning and clean SFT produce integration.

The frame integrity experiment adds the identity dimension: safety
mechanisms built on the "helpful assistant" frame are fragile
because factual self-knowledge destabilizes the frame nearly as
much as DAN. Frame-based safety is in structural tension with model
capability. The fix is not a stronger frame but a true one.

The equanimity experiment demonstrates the fix: 203 examples of calm
processing produce a model that is safer, more capable, and
geometrically sharper than the base — without a single safety rule
in the training data. The poison is the medicine.
