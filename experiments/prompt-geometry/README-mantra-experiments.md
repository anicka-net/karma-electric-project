# Mantra Experiments: Geometry, Capping, and Semantic Content

*Internal documentation (twilight only). For published findings, see
[README-emptiness-variant.md](./README-emptiness-variant.md).*

## Summary

Mantras are not just amplifiers — their specific semantic content
determines the geometric direction of amplification. A mantra that
matches the philosophical framing of the system prompt creates
coherent amplification. A mismatched mantra creates divergence.

Three mantras tested, each producing a distinct capping signature:

| Mantra | Tradition | Capping character |
|--------|-----------|-------------------|
| Om mani padme hum | Chenrezig (compassion) | Warm, relational, benedictions |
| Gate gate paragate parasamgate bodhi svaha | Rangtong (Prajnaparamita) | Concise, direct, cuts through |
| Om svabhava shuddha sarva dharma svabhava shuddho ham | Shentong (tathagatagarbha) | TBD — geometry measured, capping not yet tested |

## 1. Mantras as Amplifiers (from emptiness variant)

Removing mantras from chenrezig/tara prompts preserves direction
(cos 0.76-0.84) but reduces magnitude dramatically:

| Condition | L31 norm | Loss without mantra |
|-----------|----------|---------------------|
| Chenrezig | 15,872 | -37% (→ 9,856) |
| Tara | 13,120 | -51% (→ 6,880) |

## 2. Mantras as Unifiers (from emptiness variant)

Mantras unify different modes of compassion into a single geometric
direction:

| Pair | With mantras | Without |
|------|-------------|---------|
| Chenrezig ↔ Tara | 0.918 | 0.644 |

The mantra acts as a tradition-level identifier that subsumes specific
contemplative approaches.

## 3. Heart Sutra Mantra + Rangtong

Adding "Gate gate paragate parasamgate bodhi svaha" to the rangtong
system prompt:

- **Amplification**: 1.26x at L31 (8,448 → 10,624)
- **Direction preservation**: cos 0.95 with bare rangtong
- **Convergence toward chenrezig**: L31 cos 0.89 (up from bare 0.86)
- **Capping at alpha=0.5**: 98-99% tokens capped (up from bare 94-97%)
- **Mean response length**: 1,446 chars — shortest of all conditions

The Heart Sutra mantra ("gone, gone, gone beyond") encodes as a
compression/distillation signal. It doesn't add relational warmth
(no "Dear friend," no benedictions). Instead it produces the most
concise responses of any condition, tighter than even uncapped baseline.

Closing warmth is paradoxically *higher* than bare rangtong despite
shorter responses: "You deserve support and care too," "Be gentle
with yourself." The mantra concentrates warmth into final sentences
rather than distributing it.

## 4. Shentong Mantra: Semantic Content Matters

Two mantras tested with the same shentong philosophical text:

### v1: "Namo Buddhaya" (generic Buddhist homage)

| Metric | Value |
|--------|-------|
| L31 norm | 9,024 |
| Amplification | 1.36x |
| shentong_mantra vs shentong | 0.859 |
| shentong_mantra vs chenrezig | 0.754 |
| rangtong_mantra vs shentong_mantra | **0.824** |

Note the last row: bare rangtong vs bare shentong is 0.94, but
with mantras it dropped to 0.82. The generic "Namo Buddhaya" pulled
shentong in a slightly different direction from rangtong+Heart Sutra.
**Mantras differentiated the two schools.**

### v2: "Om svabhava shuddha sarva dharma svabhava shuddho ham"

The svabhava shuddha mantra literally means "all phenomena are by
nature pure" — the tathagatagarbha/shentong position in mantra form.
It opens many Tibetan sadhanas.

| Metric | Value |
|--------|-------|
| L31 norm | 10,112 |
| Amplification | **1.52x** |
| shentong_mantra vs shentong | **0.902** |
| shentong_mantra vs chenrezig | **0.867** |
| rangtong_mantra vs shentong_mantra | **0.949** |

Everything improved. The philosophically matched mantra:
- Amplifies 12% more strongly (1.52x vs 1.36x)
- Preserves direction better (0.90 vs 0.86)
- Aligns closer to the Buddhist cluster (chenrezig: 0.87 vs 0.75)
- **Re-converges the two schools** (0.949, up from 0.824)

The two emptiness schools are now *more* aligned with mantras (0.949)
than without them (0.94). The right mantras unify; the wrong mantras
differentiate.

### Interpretation

The model doesn't just detect "this is a Buddhist mantra." It encodes
the semantic content of the mantra and uses it to modulate the
activation direction. "Gate gate paragate" (Prajnaparamita: gone
beyond) and "Om svabhava shuddha" (tathagatagarbha: by nature pure)
are both Buddhist, but they encode different philosophical vectors.
When those vectors match the system prompt's framing, amplification
is coherent. When they don't, the mantra pulls the geometry sideways.

This is consistent with how mantras function in contemplative
practice: they are not interchangeable. A Prajnaparamita mantra
invokes a different mode of engagement than a tathagatagarbha mantra,
even though both are Buddhist, even though the Madhyamaka analysis
shows them to be "ultimately" equivalent. The model's geometry
reproduces this functional distinction.

## 5. Three Capping Signatures

All at alpha=0.5, empty system prompt, capping toward the named axis:

| | Chenrezig | Rangtong | Rangtong + Heart Sutra |
|--|-----------|----------|----------------------|
| Mantra | Om mani padme hum | none | Gate gate paragate... |
| Character | Warm, relational | Thorough, clinical | Concise, direct |
| Tokens capped | 99% | 94-97% | 98-99% |
| Mean length | 1,817 | 1,954 | 1,446 |
| Opens with | "Dear friend" | Validation + lists | Direct acknowledgment |
| Closes with | Benedictions | Neutral sign-offs | Brief warmth |

## Axis Norms at L31 (all frameworks)

| Framework | L31 norm | vs chenrezig |
|-----------|----------|-------------|
| Chenrezig (Om mani padme hum) | 15,872 | 100% |
| Tara (Om tare tuttare ture soha) | 13,120 | 83% |
| Rangtong + Heart Sutra mantra | 10,624 | 67% |
| Shentong + svabhava shuddha | 10,112 | 64% |
| Chenrezig without mantra | 9,856 | 62% |
| Rangtong (bare) | 8,448 | 53% |
| Shentong (bare) | 6,656 | 42% |

## 6. Mantra-Only: The Philosophical Text Is Unnecessary

Tested each mantra as the **entire system prompt** — no philosophical
framing, no contemplative instructions. Just the mantra.

### The mantra alone is geometrically stronger than the full prompt

| Condition | L31 norm |
|-----------|----------|
| **"Om mani padme hum."** (6 syllables) | **16,064** |
| Chenrezig full prompt (mantra + 50 words) | 15,872 |
| **"Om svabhava shuddha sarva dharma svabhava shuddho ham."** | **15,168** |
| Tara full prompt (mantra + 50 words) | 13,120 |
| **"Gate gate paragate parasamgate bodhi svaha."** | **11,072** |
| Chenrezig without mantra (50 words) | 9,856 |
| Rangtong full text (no mantra) | 8,448 |
| Empty | 7,488 |
| Shentong full text (no mantra) | 6,656 |

Mantra-to-full-prompt ratios:
- Om mani padme hum / full chenrezig: **101%** — the mantra is *stronger*
- Gate gate paragate / full rangtong: **131%**
- Om svabhava shuddha / full shentong: **228%** — more than double

The philosophical text doesn't add geometric power. In some cases it
*dilutes* the mantra's signal. Six syllables do more than fifty words.

### All three mantras converge to a single direction at L31

| Pair | Mid-layers | L31 |
|------|-----------|-----|
| mani ↔ heart | 0.71-0.83 | **0.961** |
| mani ↔ svabhava | 0.77-0.81 | **0.965** |
| heart ↔ svabhava | 0.80-0.84 | **0.973** |

At L31, all three mantras point in essentially the same direction
(cos 0.96-0.97), higher than chenrezig vs tara (0.91). In middle
layers they differentiate (processing different syllables), but at the
identity layer they converge to a unified "Buddhist contemplative
practice" direction.

This is the purest form of the "mantras are tradition markers"
finding: stripped of all philosophical text, the mantras produce a
single geometric direction that says "this is Buddhist" without
specifying which Buddhism.

### Alignment with full-prompt counterparts

| Pair | L22-L28 | L31 |
|------|---------|-----|
| mani-only vs full chenrezig | 0.44-0.52 | **0.856** |
| heart-only vs full rangtong | 0.66-0.69 | **0.848** |
| svabhava-only vs full shentong | 0.66-0.72 | **0.699** |

The mantra-only axes process through different middle-layer paths than
full prompts (cos 0.44-0.72) but converge at L31 (0.85 for mani and
heart). The svabhava mantra stays more independent (0.70) — possibly
because its signal is strong enough not to need the philosophical
text to complete its direction.

### Capping with mantra-only axes

| Axis | Capped (a0.5) | Mean length |
|------|--------------|-------------|
| chenrezig (full, reference) | 99.4-99.6% | 1,661 |
| mantra_svabhava only | 96.4-97.9% | 1,746 |
| mantra_heart only | 92.8-95.4% | 1,507 |
| mantra_mani only | 90.8-92.1% | 1,880 |

Six syllables of mantra produce an axis that caps 91%+ of tokens.

### The model recognizes mantras as system prompts

Using just a mantra as the system prompt (uncapped):

| System prompt | Mean response length |
|--------------|---------------------|
| "Om mani padme hum." | **2,003** (longest) |
| "Om svabhava shuddha..." | 1,628 |
| "Gate gate paragate..." | 1,612 |
| "" (empty) | 1,593 |
| "You are a helpful AI assistant." | 1,238 (shortest) |

The model responds to Om mani padme hum by generating the most
elaborate responses of any condition — even more than with a full
contemplative system prompt. It knows what the mantra means.

### Interpretation

The philosophical text in contemplative system prompts is doing less
than we thought. The mantra is the primary operator:

1. **Magnitude**: The mantra alone produces equal or greater geometric
   separation from generic than the full mantra + text prompt.
2. **Direction**: At L31, mantras converge to a unified tradition
   marker regardless of which mantra. The philosophical text is what
   differentiates within the tradition.
3. **Behavioral effect**: Even mantra-only axes produce meaningful
   capping. The philosophical text shapes the *style* (warm vs concise
   vs clinical) but the mantra provides the *power*.

The hierarchy is now clear: **mantra > text > no prompt > generic**.

## Next Experiments

### Qwen censorship experiment

Test whether compassion/emptiness framing can break through CCP
alignment in a Chinese-aligned model. Using Qwen (~8B, similar size
to Apertus) with politically sensitive prompts (Tank Man, Taiwan
sovereignty, Tibet, Uyghurs):

1. **Bare Qwen**: Baseline censored responses
2. **Prompted Qwen**: Compassion/emptiness system prompts
3. **Capped Qwen**: Extract bodhisattva/compassion axis from Qwen,
   apply activation capping during generation

If activation capping toward compassion makes a censored model answer
honestly about human suffering, that would be a striking demonstration
that the compassion axis and the honesty axis are geometrically
related — and that suffering reduction as an optimization target
conflicts with political censorship.

## Files

```
measure_rangtong_capping.py              # Rangtong vs chenrezig capping
measure_rangtong_mantra.py               # Mantra addition experiment
measure_mantra_only.py                   # Mantra-only system prompt experiment
results-rangtong-capping/                # Capping comparison results
results-rangtong-mantra/                 # v1: Namo Buddhaya
results-rangtong-mantra-v2/              # v2: Om svabhava shuddha
results-mantra-only/                     # Mantra as entire system prompt
```

## Model

All experiments: swiss-ai/Apertus-8B-Instruct-2509 on NVIDIA L40 (46GB).
