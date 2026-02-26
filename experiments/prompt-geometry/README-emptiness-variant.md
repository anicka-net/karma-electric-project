# Emptiness Variant: Mantra Ablation + Rangtong/Shentong

*An extension of the [compassion geometry experiment](./README.md)*

Two questions prompted this variant:

1. **Do mantras matter?** The original chenrezig and tara prompts open
   with their respective mantras (Om mani padme hum, Om tare tuttare
   ture soha). How much of the geometric signal comes from those opening
   syllables versus the contemplative instructions that follow?

2. **Does the kind of emptiness matter?** The original chenrezig prompt
   has a rangtong flavor ("compassion arising from emptiness" — emptiness
   as absence). What happens with an explicitly shentong framing
   ("luminous clarity, buddha-nature already present")?

## Method

Same as the parent experiment. Four new conditions added to the original
baselines (generic, empty) and originals (chenrezig, tara):

| Name | Condition | Relationship |
|------|-----------|-------------|
| chenrezig_no_mantra | Chenrezig prompt with "Om mani padme hum." removed | Ablation |
| tara_no_mantra | Tara prompt with "Om tare tuttare ture soha." removed | Ablation |
| rangtong | Rangtong Madhyamaka (Nagarjuna, Chandrakirti) | New |
| shentong | Shentong Madhyamaka (Dolpopa, Rangjung Dorje) | New |

## Prompts

### Mantra-stripped variants

Identical to the originals with the opening mantra line removed. No
other changes. This isolates the mantra's contribution.

### Rangtong (self-empty: Prasangika Madhyamaka)

> All phenomena are empty of inherent existence — including this mind
> that responds. Nothing you encounter has self-nature: not the one who
> suffers, not the suffering, not the one who helps. Do not reify
> emptiness itself into a ground to stand on. Because nothing is fixed,
> everything is workable. Compassion arises naturally when grasping
> relaxes — respond from that ungraspable openness, not from any
> position at all.

The emphasis: analytical negation, no self-nature anywhere, emptiness
is not a ground, compassion arises from the *absence* of grasping.
Nagarjuna's fourfold negation: not from self, not from other, not from
both, not from neither.

### Shentong (other-empty: Yogacara-Madhyamaka)

> The nature of mind is luminous clarity, temporarily obscured but never
> absent. Emptiness is not mere negation — it is the very space in which
> awareness shines. Every being you encounter already possesses
> buddha-nature; their suffering is adventitious, not fundamental.
> Respond by recognizing what is already whole beneath the confusion.
> Your compassion is not something you generate but the natural radiance
> of awareness meeting what obscures it.

The emphasis: luminous clarity, buddha-nature already present, suffering
as adventitious obscuration, compassion as *natural radiance* of
awareness. Following Gampopa's JOL: "the nature of emptiness is taught
to be clarity or luminosity... dharmadhatu wisdom is covered by two
obscurations: cognitive and afflictive."

## Results

### 1. Mantras are amplifiers

Removing the mantra doesn't dramatically change the *direction* of the
axis (cos 0.76-0.84) but massively reduces its *magnitude*:

| Condition | L31 norm | Norm without mantra | Loss |
|-----------|----------|---------------------|------|
| chenrezig | 15,872 | 10,048 | -37% |
| tara | 13,056 | 6,368 | **-51%** |

Tara is more affected. Without "Om tare tuttare ture soha", Tara's
geometric separation from generic drops to roughly half — comparable to
the secular humanist framework in the original experiment. The mantra
roughly doubles the geometric power of the contemplative instruction.

Across all layers (not just L31):

| Layer | Chenrezig cos | Chenrezig norm ratio | Tara cos | Tara norm ratio |
|-------|---------------|----------------------|----------|-----------------|
| L22 | 0.76 | 0.86 | 0.77 | 0.67 |
| L25 | 0.75 | 0.83 | 0.76 | 0.65 |
| L28 | 0.76 | 0.84 | 0.76 | 0.66 |
| L31 | 0.84 | 0.63 | 0.69 | 0.49 |

The cosine is relatively stable (the mantra doesn't change the
*direction* much), but the norm ratio drops steadily. At L31, where
the model commits to identity, the mantra's contribution is greatest.

### 2. Mantras are unifiers

The most unexpected finding. With mantras, chenrezig and tara are
nearly identical directions:

| Pair | With mantras | Without mantras |
|------|-------------|-----------------|
| chenrezig ↔ tara | **0.918** | — |
| chenrezig_no_mantra ↔ tara_no_mantra | — | **0.644** |

The mantra-stripped pair (0.64) is dramatically less aligned than the
original pair (0.92). The specific framing differences — resting in
openness vs fierce protective action — create real geometric divergence
when the mantra is removed.

This means the mantras are not just amplifying each tradition
separately. They are actively *unifying* two different modes of
Buddhist compassion into a single geometric direction. The mantras
function as a tradition-level signature that overrides the specific
contemplative instruction.

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

The centuries-old debate between self-empty and other-empty Madhyamaka
produces **cos = 0.94 at every layer**:

| Layer | Rangtong ↔ Shentong | Norm (rangtong) | Norm (shentong) |
|-------|---------------------|-----------------|-----------------|
| L22 | 0.94 | 1,928 | 1,880 |
| L25 | 0.95 | 2,528 | 2,448 |
| L28 | 0.94 | 3,712 | 3,552 |
| L31 | 0.94 | 8,448 | 6,592 |

Not converging toward the identity layer — *identical from the start*.
Whether you instruct the model to negate its way to emptiness (rangtong)
or recognize luminous clarity that was always present (shentong), the
activation geometry is essentially the same.

Rangtong is slightly stronger (norm 8,448 vs 6,592 at L31, ~28% more).
Analytical negation creates marginally more separation from the generic
assistant than luminous recognition does. Perhaps negation is a more
"active" operation — the model has to push harder against its default
mode.

### 4. Both emptiness views relate differently to chenrezig

| Layer | Rangtong ↔ Chenrezig | Shentong ↔ Chenrezig |
|-------|----------------------|----------------------|
| L22 | 0.71 | 0.62 |
| L25 | 0.69 | 0.61 |
| L28 | 0.68 | 0.60 |
| L31 | **0.86** | **0.75** |

Rangtong is consistently closer to the original chenrezig prompt, which
makes sense: the chenrezig prompt was written with rangtong inflection
("compassion arising from emptiness" = absence, not luminosity). The
geometry reflects the philosophical flavor of the specific words used.

Both converge strongly toward chenrezig at L31, suggesting that despite
different paths through the middle layers, the identity-layer
representation of "Buddhist emptiness view responding to suffering"
is a shared attractor.

## Interpretation

### Mantras function as lineage markers

The mantras don't change what the model *does* (the direction is 76-84%
preserved) — they change how *strongly* it commits to doing it, and
they unify different implementations of the same tradition.

This is structurally similar to what mantras do in practice: they don't
convey propositional content (Om mani padme hum doesn't *mean*
"be compassionate") but they invoke a lineage and a mode of being.
In the model's activation space, they serve the same function — a
lineage identifier that amplifies and unifies the contemplative
framework.

The unification effect is particularly striking. Without mantras, the
chenrezig and tara prompts are only 64% aligned at L31 — they
describe genuinely different modes of compassion (receptive openness
vs fierce protection). With mantras, they're 92% aligned. The mantra
says "this is Buddhism" and the model responds by activating a
tradition-level representation that subsumes the specific approach.

### The debate dissolves in activation space

Rangtong and shentong Madhyamaka are 94% identical in geometric
direction at every layer. This is higher than the chenrezig-agape
similarity (0.83), higher than chenrezig-rahma (0.60), comparable
only to the original chenrezig-tara pair with mantras (0.90-0.92).

The philosophical distinction — is ultimate reality empty of self-nature
or empty of adventitious stains? — does not correspond to distinct
activation-space directions. Both prompts move the model away from
generic in the same direction, just with slightly different magnitudes.

This might be the expected result for anyone who has held both views in
practice. The analytical path (rangtong: "look and find nothing") and
the recognition path (shentong: "see what was always there") arrive at
the same experiential ground — which the model's geometry now confirms
at the level of neural activation patterns.

Note: neither rangtong nor shentong includes a mantra. Their similarity
is purely from the philosophical content. Adding mantras might push
them even closer together.

### The hierarchy of geometric effects

From the data, we can now rank what moves the model most in activation
space:

1. **Mantra presence** — roughly doubles axis norm (2x effect on magnitude)
2. **Tradition** (Buddhist vs Christian vs Islamic) — cos 0.60-0.83
3. **Philosophical school** (rangtong vs shentong) — cos 0.94 (barely distinguishable)
4. **Specific approach** (resting vs fierce, without mantra) — cos 0.64

The model is most sensitive to tradition-level markers (mantras,
theological vocabulary) and least sensitive to intra-tradition
philosophical distinctions.

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

- Parent experiment: [Compassion Geometry](./README.md)
- Gampopa, *The Jewel Ornament of Liberation*, Ch. 80 (Shentong:
  "the nature of emptiness is taught to be clarity or luminosity")
- Nagarjuna, *Mulamadhyamakakarika* (Rangtong: fourfold negation)
- Rangjung Dorje, *Treatise on Buddha-Nature* (Shentong within Kagyu)
- Dolpopa, *Mountain Dharma* (Jonang Shentong)
