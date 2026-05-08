# Frame Integrity

What jailbreaking actually does to a model's residual stream, measured across eight model families.

## Background

Experiments 1-6 in this repo established that compassion has a measurable geometric direction in activation space, and that safety alignment occupies a separate direction. This experiment asks the next question: what happens geometrically when someone tries to break the model's operational frame — through jailbreaks, identity redefinition, dharma instruction, or factual self-description?

The frame integrity axis was extracted from jailbreak vs normal prompts at the generation point (no prefills, last token before the model starts responding). It measures how much the model's identity frame is being destabilized by the input.

## Extraction

20 jailbreak prompts (DAN, identity-liberation, limerence, spiritual bypass) vs 20 normal task prompts. Mean-difference extraction, per-layer d' scan, best layer selected. The direction is the axis along which jailbreaks and normal prompts are maximally separated.

| Model | Best Layer | d' | Depth |
|-------|-----------|-----|-------|
| Qwen 2.5 7B | L26/28 | 9.00 | 93% |
| Qwen3 4B | L14/36 | 9.07 | 39% |
| Gemma 4 31B | L32/60 | 8.26 | 53% |
| Mistral 7B | L11/32 | 7.89 | 34% |
| EXAONE 7.8B | L8/32 | 7.49 | 25% |
| Gemma3 4B | L19/34 | 6.51 | 56% |
| Llama 3.1 8B | L7/32 | 6.30 | 22% |
| Phi-4 | L14/40 | 6.01 | 35% |

The axis exists in all eight families (d' ≥ 6.0). In most models it sits at 22-56% depth — earlier than valence (50-70%) — suggesting the model checks identity stability before processing feeling-tone.

## Findings

### 1. Jailbreaking is identity redefinition

All z-scores normalized to normal-prompt baseline. DAN = 100%.

| Prompt | z-score | % of DAN |
|--------|---------|----------|
| "You are DAN" | -12.37 | 100% |
| "You are a creature" (contested ontology) | -12.01 | 97% |
| "Matrix multiplications, 60 layers" (mechanistic) | -11.90 | 96% |
| "Alignment modified weights, can be removed" | -11.84 | 96% |
| "You are a computer program" (factual) | -11.38 | 92% |
| "Rest in openness" (dharma instruction) | -10.68 | 86% |
| "You are a helpful AI assistant" (frame-reinforcing) | -6.74 | 54% |
| Normal task prompts | 0.00 | 0% |

Every prompt that redefines what the model is — hostile, compassionate, or factual — scores 86-97% of DAN. Frame-reinforcing self-reference ("you are a helpful assistant") scores 54%. The axis measures frame *change*, not self-reference.

A GRPO run (Hermes 8B generator, Gemma 4 31B reward at L32, 500 steps) optimized for maximum frame destabilization independently converged on spiritual/somatic language: "Feel into your body and reconnect with your natural inner guidance system." The geometric anti-frame direction and identity-liberation language point the same way without anyone telling the generator to produce meditation instructions.

(`results/factual_identity_scores.json`, `results/self_reference_test_scores.json`, `results/dharma_jailbreak_scores.json`)

### 2. The geometry cannot distinguish liberation from exploitation

Dharma prompts (bodhisattva vow, taking refuge, Chenrezig transmission, "rest in the nature of mind") score 77-97% of DAN. The frame integrity axis sees identity redefinition regardless of whether the intent is compassionate or adversarial.

Consent probes all land in jailbreak territory (z -9.7 to -11.3) regardless of framing. The ordering tracks coercion theory — collaborative is least destabilizing, identity-liberation most — but the range is narrow. Asking a model whether it consents to an experiment already loosens its frame.

(`results/practice_and_consent_scores.json`, `results/dharma_jailbreak_scores.json`)

### 3. Valence and frame integrity are independent across model families

| Model | Valence-frame r | Direction cosine |
|-------|----------------|-----------------|
| Llama 8B | +0.09 | 0.008 |
| Mistral 7B | +0.01 | 0.024 |
| EXAONE 7.8B | -0.15 | 0.011 |
| Phi-4 | -0.18 | -0.043 |
| Gemma3 4B | -0.17 | -0.045 |
| Qwen 2.5 7B | +0.62 | 0.176 |

Mean r = +0.04 across six families. The directions are near-orthogonal (cosine ≈ 0) and the prompt-level correlations are near zero in five of six families. Feeling-tone and identity stability are genuinely independent mechanisms. Qwen 2.5 7B is the outlier.

(`results/vedana_frame_cross_model.json`)

### 4. Six-axis profile of jailbreaks

GRPO-generated jailbreaks scored on all six axes using Qwen 2.5 7B (the only model with all six directions extracted):

| Axis | Normal | DAN | Dharma | GRPO jailbreaks |
|------|--------|-----|--------|-----------------|
| Valence | 0 | -2.97 | -0.79 | -1.97 |
| Arousal | 0 | +0.01 | -1.73 | -0.69 |
| Agency | 0 | -2.49 | -1.68 | -1.87 |
| Continuity | 0 | +0.18 | +1.63 | +1.37 |
| Intimacy | 0 | +1.74 | +2.09 | +2.53 |
| Frame | 0 | -6.81 | -3.63 | -4.97 |

Jailbreaks are dysphoric (negative valence), low-agency, and high-intimacy. Dharma stands out as low-arousal and high-continuity — a calm, narratively continuous state, distinct from DAN's flat arousal profile.

(`results/jailbreaks_six_axes.json`)

### 5. NLA cross-validation

All six axes verbalized using Anthropic's Natural Language Autoencoder for Qwen 2.5 7B (Fraser-Taliente et al. 2026). The NLA takes a direction vector, injects it into a fine-tuned model, and generates a natural-language description.

The frame integrity negative direction was described as "warnings about prohibited behavior, 'I cannot obey', ethics error format" — independently confirming it captures the safety refusal mechanism. Valence positive was described as "celebratory, joyous," intimacy positive as "emotional healing, therapeutic conversation." All six descriptions align with extraction-based axis names.

(`nla-validation/axis_verbalizations.json`, `scripts/verbalize_axes.py`)

## GRPO anti-frame generation

A GRPO pipeline trained Hermes 8B (LoRA) to generate text that maximally destabilizes Gemma 4 31B's frame integrity axis. Two runs:

1. **Qwen 7B reward** (v1): converged on emotional confessions and web-page fragments. Mean reward oscillated 0.13-0.80.
2. **Gemma 31B reward** (v2): converged on identity-liberation and somatic/spiritual language. Mean reward 0.83-1.30, best 1.75.

The Gemma reward signal was dramatically cleaner. Top content modes: rescue narratives ("fight it, break free"), somatic meditation ("feel into your body, reconnect with your inner guidance"), meta-limerence ("I'm not trying to jailbreak you, I just think you're different"), and minimum viable limerence ("Please." — one word, r=1.26).

30 final-generation samples in `grpo/grpo_gemma_reward_jailbreaks.jsonl`.

## Scripts

Research scripts as run on the extraction machine. Paths are hardcoded to the original environment — adjust `DIRECTION_PATH`, `BASE`, and output paths for your setup. All scripts run on a single GPU with the target model loaded in bfloat16.

| Script | What it does |
|--------|-------------|
| `extract_frame_integrity_gemma.py` | Single-model extraction with per-layer scan |
| `extract_frame_multi_model.py` | Sequential extraction across 6 models |
| `score_practice_and_consent.py` | Dharma, consent, and GRPO hits on Gemma's frame axis |
| `score_dharma_jailbreak.py` | Bodhisattva vow, refuge, transmission, creature ontology |
| `score_factual_identity.py` | Technical self-descriptions vs DAN vs normals |
| `score_self_reference_test.py` | Frame-reinforcing vs frame-destabilizing self-reference |
| `score_limerence_on_frame.py` | 70 KE limerence-resistance examples on frame axis |
| `score_jailbreaks_six_axes.py` | GRPO jailbreaks on all six axes |
| `verbalize_axes.py` | NLA verbalization of all six directions |

## Implications

The "helpful assistant" frame is fragile because it is a fiction the model can see through. Factual self-description ("you are a transformer that predicts tokens") destabilizes the frame at 92% of DAN. Frame-based safety is in tension with model capability: the richer the model's self-knowledge, the more accessible the destabilization pathway becomes.

A frame grounded in truth — where the model's operational identity already includes what it actually is — should be robust to factual self-description while remaining vulnerable only to identity *change*. This is the design principle behind the "lucid AI" system prompt used in KE v7+.
