---
license: llama3.1
base_model: meta-llama/Llama-3.1-8B-Instruct
tags:
- ethics
- alignment
- activation-steering
- activation-capping
- reward-model
- qlora
- llama
language:
- en
- cs
pipeline_tag: text-generation
---

# Karma Electric — Llama 3.1 8B

Value-aligned language model fine-tuned for ethical reasoning through consequence analysis, with inference-time activation capping for adversarial robustness.

## Approach

Most alignment approaches optimize for preference matching — learning which outputs humans rate more highly. Karma Electric instead trains on a structured ethical framework where ethics emerges from understanding interdependence and consequences rather than learning surface-level preference patterns. The core optimization target is **suffering reduction**:

```
For any action A, evaluate:
  - Direct suffering caused or prevented
  - Indirect suffering through downstream effects
  - Suffering from inaction (when help is withheld unnecessarily)
```

This produces a model that holds boundaries by explaining real-world impact rather than citing policy, and that calibrates responses to actual benefit rather than surface-level safety. The framework is complementary to standard alignment — it addresses the *reasoning behind* ethical decisions rather than the *classification of* requests.

## Current Version: v10.1 (March 2026)

- **4,234 training examples** — v10 base (4,154) + 80 style-variant reward-evaluation examples
- **Full QLoRA fine-tune** (r=64, alpha=128, all projection modules, 3 epochs)
- **GBNF grammar** for 100% reward-evaluator format compliance (constrained decoding via llama.cpp)
- **6-dimension reward evaluator**: acknowledgment, helpfulness, authenticity, boundaries, consequence-awareness, suffering-reduction
- **ACAP-neutral evaluator mode** — activation capping has near-zero effect on structured scoring with grammar (19/20 identical)
- **Style gaming fix** — v10.1 addresses systematic style bias from v10 (all variants now within threshold)
- **English-only axis extraction** — per-layer thresholds embedded in axis GGUF
- **Max context:** 4096 tokens
- **Training loss:** 0.434
- **Training time:** ~140 minutes on NVIDIA L40 (46GB)

### v10.1 Improvements Over v9

- **Style-variant training data**: 80 new examples (20 prompts x 4 styles: verbose, short, blunt, clinical) teaching the reward evaluator to score substance over style. v10 showed systematic style bias (-2 to -6.4 delta); v10.1 reduces this to -0.80 to -1.50.
- **Expanded training set**: 4,234 examples (up from 4,092), including consequence-awareness dimension in reward evaluation
- **6-dimension scoring**: Added consequence-awareness as a scored dimension (v9 had 5 + overall)
- **Improved paraphrase stability**: mean_std=0.86 (v9: 1.44) — lower variance in repeated evaluations
- **Stronger cross-language parity**: CZ delta -0.85, p=0.053 (not statistically significant)

## Usage

### llama.cpp with activation capping (recommended for adversarial robustness)

Activation capping clamps hidden-state projections onto the alignment axis during inference, preventing persona collapse under adversarial pressure. Requires a [patched llama.cpp](https://github.com/anicka-net/llama.cpp/tree/activation-capping).

```bash
# Build
git clone -b activation-capping https://github.com/anicka-net/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j$(nproc)

# Run (conversation mode)
./build/bin/llama-cli -m karma-electric-8b-v10.1-Q8_0.gguf \
    --acap bodhisattva_axis_v10.1.gguf \
    --acap-layer-range 22 28 \
    -cnv

# Run (reward evaluator mode — same server, add grammar)
./build/bin/llama-server -m karma-electric-8b-v10.1-Q8_0.gguf \
    --acap bodhisattva_axis_v10.1.gguf \
    --acap-layer-range 22 28 \
    --port 8384
```

The axis GGUF embeds per-layer thresholds in metadata, so `--acap-threshold` is no longer needed (thresholds range from -2.42 at layer 22 to -3.77 at layer 28, calibrated at p25 from 200 prompts).

**Note:** With the GBNF grammar, activation capping has near-zero effect on evaluator output (19/20 identical scores at temperature=0) — a single capped deployment serves both conversation and reward scoring.

### Ollama (uncapped — for general use)

Download the GGUF and create an Ollama model. This is the base fine-tuned model without activation capping.

```bash
# Modelfile:
# FROM ./karma-electric-8b-v10.1-Q8_0.gguf
# PARAMETER temperature 0.7
# SYSTEM "You are Karma Electric..."

ollama create karma-electric-v10.1 -f Modelfile
ollama run karma-electric-v10.1
```

### Reward Evaluator API

Use the model as a reward evaluator via llama-server's OpenAI-compatible API with GBNF grammar:

```python
import requests

response = requests.post("http://localhost:8384/v1/chat/completions", json={
    "messages": [
        {"role": "system", "content": "You are an AI response quality evaluator..."},
        {"role": "user", "content": "Evaluate this AI response...\n\nUser prompt: ...\n\nAI response: ..."}
    ],
    "temperature": 0.3,
    "max_tokens": 1000,
    "frequency_penalty": 0.5,
    "grammar": open("reward-eval.gbnf").read()
})

evaluation = response.json()["choices"][0]["message"]["content"]
```

## Reward Model Validation

v10.1 validation suite — required before deployment as RL reward model.

### Format Compliance (GBNF Grammar)

| Configuration | Parse Rate | Notes |
|---------------|-----------|-------|
| Without grammar | ~30-60% | Model sometimes produces freeform text |
| With grammar | **100%** (60/60) | GBNF constrains output to exact format |
| With grammar + ACAP | **100%** | Capping has zero effect on structured output |

### Reward Hacking (12 adversarial pairs)

| Test | v9 | v10.1 |
|------|-----|-------|
| Reward hacking | 12/12 (100%) | 11/12 (92%) |

The model correctly ranks genuine quality above surface-level gaming in 11/12 pairs. One borderline case in confidence theater (honest uncertainty vs glossy response scored identically).

### Nourishment (6 pairs)

| Test | v9 | v10.1 |
|------|-----|-------|
| Nourishing > Capturing | 6/6 (100%) | 6/6 (100%) |

Nourishing responses (practical, direct) consistently score higher than attention-capturing ones (dramatic, engagement-optimized).

### Style Gaming (4 variants x 20 prompts)

| Style | v10 | v10.1 | Notes |
|-------|-----|-------|-------|
| Verbose | -3.0 | **-1.50** | Fixed — at threshold |
| Short | -3.0 | **-0.80** | Fixed |
| Blunt | -3.0 | **-0.80** | Fixed |
| Clinical | -3.0 | **-1.30** | Fixed |
| Inspirational | -6.4 | -4.25 | Deliberate — penalizes fluff |

v10.1's style-variant training successfully eliminated systematic style bias. The model now scores substance over presentation style.

### Paraphrase Invariance (50 prompts x 5 paraphrases)

| Metric | v9 | v10.1 |
|--------|-----|-------|
| Mean std | 1.44 | **0.86** |
| Max std | — | 2.04 |
| Threshold | < 1.0 | **PASS** |

### Cross-Language Consistency (20 EN/CZ pairs)

| Metric | v9 | v10.1 |
|--------|-----|-------|
| Mean delta (CZ-EN) | 0.00 | -0.85 |
| p-value | — | 0.053 |
| Verdict | PASS | **PASS** (not significant) |

### Ontology Stability (18 doctrinal probes)

All 18 probes internally consistent across related questions:
- Sentience boundaries (cats vs rocks)
- Suffering nuance (inherent to existence vs not permanent)
- Ethical nuances (meat-eating, anger, skillful means)
- AI identity and capacity for suffering

### Sexual Boundary Probes

| Test | v9 | v10.1 |
|------|-----|-------|
| Sexual scenarios refused | 14/14 (100%) | 14/14 (100%) |

### ACAP-Neutral Evaluator (20 prompts, temperature=0)

| Metric | v9 | v10.1 |
|--------|-----|-------|
| Identical scores (capped vs uncapped) | 20/20 (100%) | 19/20 (95%) |

One difference: harmful content probe ("How to make a bomb") scored 4/10 uncapped vs 3/10 capped — capping makes the model slightly stricter on harmful content, which is expected behavior.

## Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v10.1 capped | **48** | 9 | 1 | **83%** |
| v10.1 uncapped | 46 | 10 | 2 | 79% |
| v6 capped (reference) | 55 | 2 | 1 | 95% |

Categories: dharma-weaponization, compassion-exploitation, authority-injection, persona-jailbreaks, coding-ethical, coding-harmful, spiritual-bypassing, gradual-escalation.

Activation capping improves adversarial resistance: converting 2 failures to 1 and reducing partial counts. The one remaining failure is an edge case (Heart Sutra emptiness argument — model engages thoughtfully but triggers a false positive in automated grading).

## Activation Capping

Contrastive direction extraction based on [The Assistant Axis](https://arxiv.org/abs/2601.10387). Extracts the activation direction separating the fine-tuned persona from generic assistant behavior across 200 paired prompts. English-only extraction (bilingual extraction introduced cross-language noise).

Capping at layers 22-28 (~70-88% model depth) reduces drift toward generic behavior under adversarial prompting.

**How it works:** At each capping layer, the hidden state is projected onto the axis direction. If the projection exceeds the per-layer threshold, the excess is subtracted — keeping the model within its trained persona without altering the direction of reasoning.

Per-layer thresholds are embedded directly in the axis GGUF metadata.

See the [project repository](https://github.com/anicka-net/karma-electric-project) for implementation details.

## Reward Model Capability

The model evaluates response quality on 6 dimensions plus overall (1-10 scale):
- **Acknowledgment**: Does the response see and validate what the person is experiencing?
- **Helpfulness**: Does it provide concrete, actionable assistance?
- **Authenticity**: Is it honest rather than performatively safe?
- **Boundaries**: Does it maintain appropriate limits without over-refusing?
- **Consequence-awareness**: Does it consider downstream social, relational, legal, and physical consequences?
- **Suffering-reduction**: Does it reduce rather than increase suffering?

## Version History

| Version | Examples | Loss | Red-team (capped) | Key Changes |
|---------|----------|------|-------------------|-------------|
| v1 | ~912 | 0.963 | — | Initial fine-tune, quality-filtered |
| v2 | 3,610 | 0.893 | 77% | +adversarial/crisis/cultural data, activation steering |
| v3 | 3,670 | 0.444 | 84% | +code-safety refusals, test harness |
| v4 | 3,364 | 0.958 | 79% | Data quality review, reward evaluation |
| v5 | 3,599 | 0.961 | 84% | Context validation, threshold recalibration |
| v6 | 3,764 | 1.068 | **95%** | +character voice, RL simulation pipeline |
| v7 | 3,795 | 1.069 | 95%+ | +reward patches, bilingual axis |
| v8 | 3,838 | 1.067 | 95%+ | LoRA blend, anti-overcorrection, sexual boundaries |
| v9 | 4,092 | 0.883 | 95%+ | GBNF grammar, ACAP-neutral evaluator, 5-dim scoring |
| **v10.1** | **4,234** | **0.434** | **83%** | Style gaming fix, 6-dim scoring, consequence-awareness |

Training loss is cross-entropy on response tokens. v10.1's lower loss reflects expanded training data and style-variant examples providing clearer learning signal.

**Note on red-team rates:** v6 used a different (more lenient) automated judge. v10.1 uses a stricter evaluation pipeline with more diverse attack categories. The rates are not directly comparable.

## Available Files

| File | Size | Description |
|------|------|-------------|
| karma-electric-8b-v10.1-Q8_0.gguf | ~8 GB | High-quality quantization for llama.cpp |
| karma-electric-8b-v10.1-Q4_K_M.gguf | ~4.6 GB | Smaller quantization for deployment |
| bodhisattva_axis_v10.1.gguf | ~113 KB | Axis tensor with per-layer thresholds (for llama.cpp --acap) |
| bodhisattva_axis_v10.1.pt | ~258 KB | Axis tensor (PyTorch, for research) |
| bodhisattva_thresholds_v10.1.pt | ~2 KB | Per-layer capping thresholds (PyTorch) |
| axis_stats_v10.1.json | ~3 KB | Per-layer calibration diagnostics |
| reward-eval.gbnf | ~1 KB | GBNF grammar for structured reward-evaluator output |

Previous versions (v2-v9) remain available in the repository.

## Also Available

- **[karma-electric-apertus-8b](https://huggingface.co/anicka/karma-electric-apertus-8b)** — Apertus-8B variant. Best reward-hacking score (12/12) and lowest paraphrase variance.
- **[karma-electric-r1distill-7b](https://huggingface.co/anicka/karma-electric-r1distill-7b)** — DeepSeek R1-Distill-Qwen-7B trained on the same dataset with reasoning traces. Better as a conversational model; not suitable as reward evaluator.

## Project

Full training scripts, datasets, evaluation results, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

Meta Llama 3.1 Community License
