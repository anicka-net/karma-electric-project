# Experiments

Activation-space experiments on compassion geometry, run on
swiss-ai/Apertus-8B-Instruct-2509 — a clean model with no
compassion-specific fine-tuning. All experiments use the activation
capping method from [The Assistant Axis](https://arxiv.org/abs/2601.10387).

## Sequence

Each experiment builds on the previous one's results.

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

### 5. [Cross-Model Safety Geometry](cross-model-safety-geometry/)

Runs the same measurement across eight models from five countries
to test universality. Measures both compassion geometry and the
geometric relationship between safety and compassion directions.
Key observation: models cluster into groups on the safety↔baseline
axis, and this clustering correlates with alignment method
(SFT-only vs DPO vs RLHF). The contemplative compassion cluster
exists in all models tested.

## Summary

Contemplative compassion has a measurable, tradition-independent
geometric direction in activation space. This direction encodes
*how to meet suffering* — validation, presence, naming difficult
truths — but not *where to draw lines*. Safety alignment requires
its own direction.

The cross-model experiment shows that the compassion direction
exists universally across models, but the relationship between
safety and compassion varies. In some models these directions
are aligned; in others they are nearly independent. The reasons
for this variation are not yet understood.
