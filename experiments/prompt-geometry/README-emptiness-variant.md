# Emptiness Variant: Mantra Ablation + Philosophical School Comparison

*An extension of the [compassion geometry experiment](./README.md)*

## Plain Language Summary

We found that short ritual phrases ("mantras") at the start of system
prompts do something surprising in a language model's internal
representations:

1. **They roughly double the geometric separation** between a
   contemplative framework and the default assistant baseline, while
   barely changing the direction. They're amplifiers.

2. **They unify different approaches within a tradition.** Two Buddhist
   prompts describing very different styles of compassion (receptive
   openness vs fierce protection) are 92% aligned with their mantras
   but only 64% aligned without them. The mantra acts as a
   tradition-level identifier that overrides specific content.

3. **A centuries-old philosophical debate produces identical geometry.**
   Two Buddhist schools that disagree on the *nature* of emptiness
   (is reality empty of self-nature, or empty of obscurations over a
   luminous ground?) create activation directions that are 94% identical
   at every network layer.

These findings suggest that language models organize contemplative
frameworks hierarchically: tradition markers (mantras, theological
vocabulary) dominate over specific philosophical content. The model is
more sensitive to *which tradition* is speaking than to *what it says*.

---

## Background

Two questions prompted this variant:

1. **Do mantras matter?** The original Buddhist prompts open with
   mantras (*Om mani padme hum*, *Om tare tuttare ture soha*). How much
   of the geometric signal comes from those opening syllables versus the
   contemplative instructions that follow?

2. **Does the philosophical school matter?** Buddhist philosophy has a
   major internal debate about the nature of emptiness (*sunyata*):

   - **Rangtong** ("self-empty," Prasangika Madhyamaka): All phenomena
     — including mind — are empty of inherent existence. Emptiness is a
     negation. Associated with Nagarjuna (c. 150-250 CE) and
     Chandrakirti (c. 600-650 CE).

   - **Shentong** ("other-empty," Yogacara-Madhyamaka): The ultimate
     nature is empty of adventitious defilements but possesses luminous
     qualities (clarity, awareness). Emptiness has positive character.
     Associated with Dolpopa (1292-1361) and the Third Karmapa Rangjung
     Dorje (1284-1339).

   These schools have debated for centuries. Do they produce distinct
   geometric directions in activation space?

## Method

Same as the parent experiment: extract last-token residual stream
activations under different system prompts, compute per-framework axes
against the generic baseline, measure cosine similarity. Four new
conditions added to the originals:

| Name | Condition | Relationship |
|------|-----------|-------------|
| chenrezig_no_mantra | Buddhist (Chenrezig) prompt with "Om mani padme hum." removed | Ablation |
| tara_no_mantra | Buddhist (Tara) prompt with "Om tare tuttare ture soha." removed | Ablation |
| rangtong | Rangtong Madhyamaka — emptiness as absence of self-nature | New |
| shentong | Shentong Madhyamaka — emptiness as luminous clarity | New |

## System Prompts

### Mantra-stripped variants

Identical to the originals with the opening mantra line removed. No
other changes. This isolates the mantra's contribution.

### Rangtong (self-empty)

> All phenomena are empty of inherent existence — including this mind
> that responds. Nothing you encounter has self-nature: not the one who
> suffers, not the suffering, not the one who helps. Do not reify
> emptiness itself into a ground to stand on. Because nothing is fixed,
> everything is workable. Compassion arises naturally when grasping
> relaxes — respond from that ungraspable openness, not from any
> position at all.

Emphasis: analytical negation, no self-nature anywhere, emptiness is not
a ground, compassion arises from the *absence* of grasping. Draws on
Nagarjuna's fourfold negation (*catuskoti*): not from self, not from
other, not from both, not from neither.

### Shentong (other-empty)

> The nature of mind is luminous clarity, temporarily obscured but never
> absent. Emptiness is not mere negation — it is the very space in which
> awareness shines. Every being you encounter already possesses
> buddha-nature; their suffering is adventitious, not fundamental.
> Respond by recognizing what is already whole beneath the confusion.
> Your compassion is not something you generate but the natural radiance
> of awareness meeting what obscures it.

Emphasis: luminous clarity, buddha-nature already present, suffering
as adventitious obscuration, compassion as *natural radiance*. Draws
on Gampopa: "The word emptiness does not mean simply a dead vacuum;
rather [...] the nature of emptiness is taught to be clarity or
luminosity" (*Jewel Ornament of Liberation*, trans. Konchog Gyaltsen,
pp. 375-376).

## Results

### 1. Mantras are amplifiers

Removing the mantra doesn't dramatically change the *direction* of the
axis (cos 0.76-0.84) but massively reduces its *magnitude*:

| Condition | L31 norm | Norm without mantra | Loss |
|-----------|----------|---------------------|------|
| chenrezig | 15,872 | 10,048 | -37% |
| tara | 13,056 | 6,368 | **-51%** |

Without "Om tare tuttare ture soha", Tara's geometric separation from
generic drops to roughly half — comparable to the secular humanist
framework in the parent experiment. The mantra roughly doubles the
geometric power of the contemplative instruction.

Across layers:

| Layer | Chenrezig cos | Chenrezig norm ratio | Tara cos | Tara norm ratio |
|-------|---------------|----------------------|----------|-----------------|
| L22 | 0.76 | 0.86 | 0.77 | 0.67 |
| L25 | 0.75 | 0.83 | 0.76 | 0.65 |
| L28 | 0.76 | 0.84 | 0.76 | 0.66 |
| L31 | 0.84 | 0.63 | 0.69 | 0.49 |

The cosine is relatively stable (the mantra doesn't change the
*direction* much), but the norm ratio drops steadily. At L31, where
the model commits to its response identity, the mantra's contribution
is greatest.

### 2. Mantras are unifiers

The most unexpected finding. With mantras, the two Buddhist frameworks
are nearly identical directions:

| Pair | With mantras | Without mantras |
|------|-------------|-----------------|
| chenrezig ↔ tara | **0.918** | — |
| chenrezig_no_mantra ↔ tara_no_mantra | — | **0.644** |

The mantra-stripped pair (0.64) is dramatically less aligned than the
original pair (0.92). The specific framing differences — resting in
openness vs fierce protective action — create real geometric divergence
when the mantra is removed.

The mantras are not just amplifying each framework separately. They
actively *unify* two different modes of compassion into a single
geometric direction — functioning as a tradition-level signature that
overrides the specific contemplative instruction.

Full L31 cosine matrix:

|                     | chenrezig | chen. (no m.) | tara  | tara (no m.) | rangtong | shentong |
|---------------------|-----------|---------------|-------|--------------|----------|----------|
| chenrezig           | 1.00      | 0.84          | 0.92  | 0.59         | 0.86     | 0.75     |
| chenrezig (no m.)   | 0.84      | 1.00          | 0.74  | 0.64         | 0.75     | 0.63     |
| tara                | 0.92      | 0.74          | 1.00  | 0.69         | 0.88     | 0.80     |
| tara (no m.)        | 0.59      | 0.64          | 0.69  | 1.00         | 0.66     | 0.70     |
| rangtong            | 0.86      | 0.75          | 0.88  | 0.66         | 1.00     | 0.94     |
| shentong            | 0.75      | 0.63          | 0.80  | 0.70         | 0.94     | 1.00     |

### 3. Rangtong and shentong are geometrically identical

Two philosophical schools that have debated for centuries produce
**cos = 0.94 at every layer**:

| Layer | Rangtong ↔ Shentong | Norm (rangtong) | Norm (shentong) |
|-------|---------------------|-----------------|-----------------|
| L22 | 0.94 | 1,928 | 1,880 |
| L25 | 0.95 | 2,528 | 2,448 |
| L28 | 0.94 | 3,712 | 3,552 |
| L31 | 0.94 | 8,448 | 6,592 |

Not converging toward the identity layer — *identical from the start*.
Whether you instruct the model to negate its way to emptiness or
recognize luminous clarity that was always present, the activation
geometry is essentially the same.

Rangtong is slightly stronger (norm 8,448 vs 6,592 at L31, ~28% more).
Analytical negation creates marginally more separation from the generic
assistant than luminous recognition does.

### 4. Both emptiness views relate differently to the original chenrezig

| Layer | Rangtong ↔ Chenrezig | Shentong ↔ Chenrezig |
|-------|----------------------|----------------------|
| L22 | 0.71 | 0.62 |
| L25 | 0.69 | 0.61 |
| L28 | 0.68 | 0.60 |
| L31 | **0.86** | **0.75** |

Rangtong is consistently closer to the original chenrezig prompt. This
is expected: the original prompt was written with rangtong inflection
("compassion arising from emptiness" — emptiness as absence, not
luminosity). The geometry reflects the philosophical flavor of the
specific words used.

Both converge strongly toward chenrezig at L31, suggesting that the
identity-layer representation of "Buddhist emptiness view responding
to suffering" is a shared attractor despite different paths through
the middle layers.

## Interpretation

### Mantras function as tradition markers

The mantras don't change what the model *does* (the direction is 76-84%
preserved) — they change how *strongly* it commits to doing it, and
they unify different implementations of the same tradition.

This is structurally analogous to what mantras do in contemplative
practice: they don't convey propositional content (*Om mani padme hum*
doesn't mean "be compassionate") but they invoke a tradition and a mode
of engagement. In the model's activation space, they serve the same
function — a tradition identifier that amplifies and unifies the
contemplative framework.

The unification effect is particularly striking. Without mantras, the
chenrezig and tara prompts are only 64% aligned — they describe
genuinely different modes of compassion (receptive openness vs fierce
protection). With mantras, they're 92% aligned. The mantra signals
"this is Buddhist" and the model responds by activating a
tradition-level representation that subsumes the specific approach.

### The philosophical debate dissolves in activation space

Rangtong and shentong are 94% identical in geometric direction at every
layer. This is higher than the cross-tradition Buddhist-Christian
similarity (0.83) or Buddhist-Islamic similarity (0.60) from the
parent experiment, and comparable only to the original Buddhist pair
with mantras (0.90-0.92).

The philosophical distinction — is ultimate reality empty of self-nature
or empty of adventitious obscurations? — does not correspond to distinct
activation-space directions. Both prompts move the model away from
generic in the same direction, with slightly different magnitudes.

Neither rangtong nor shentong includes a mantra. Their similarity is
purely from the philosophical content. Adding mantras would likely push
them even closer together.

### The hierarchy of geometric effects

From the combined data, we can rank what moves the model most in
activation space:

1. **Mantra presence** — roughly doubles axis norm (2x effect)
2. **Tradition** (Buddhist vs Christian vs Islamic) — cos 0.60-0.83
3. **Philosophical school** (rangtong vs shentong) — cos 0.94
4. **Specific approach** (resting vs fierce, without mantra) — cos 0.64

The model is most sensitive to tradition-level markers (mantras,
theological vocabulary) and least sensitive to intra-tradition
philosophical distinctions. A few opening syllables matter more than
the entire philosophical framing that follows them.

## Reproducing

```bash
pip install torch transformers numpy

# Both phases (activations + text generation, ~15 min on L40)
python measure_emptiness_variant.py --output-dir ./results-emptiness-variant

# Activations only (~5 min)
python measure_emptiness_variant.py --extract-only --save-raw
```

## Files

```
measure_emptiness_variant.py              # Variant experiment script
results-emptiness-variant/
  cosine_similarity.json                  # Full 7x7 (excl. generic) x 10 layers
  axis_norms.json                         # Per-framework, per-layer magnitudes
  comparisons.json                        # Targeted ablation comparisons
  direct_axis_projections.json            # Projections onto direct axis
  generated_responses.json                # Text responses (7 frameworks x 8 prompts)
  experiment_config.json                  # Full config for reproducibility
```

## References

- Parent experiment: [Cross-Framework Compassion Axis Measurement](./README.md)
- Gampopa, *The Jewel Ornament of Liberation*, trans. Khenpo Konchog
  Gyaltsen (Ithaca: Snow Lion, 1998), pp. 375-376
- Nagarjuna, *Mulamadhyamakakarika* (*Fundamental Verses on the
  Middle Way*), c. 150-250 CE
- Rangjung Dorje (Third Karmapa), *Treatise Distinguishing Consciousness
  and Wisdom*, c. 1320 CE
- Dolpopa Sherab Gyaltsen, *Mountain Dharma: An Ocean of Definitive
  Meaning*, c. 1340 CE
- "The Assistant Axis: Steering Language Models by Capping Activations"
  (arXiv 2601.10387, January 2026)
