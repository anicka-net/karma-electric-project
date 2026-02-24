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

Most alignment approaches optimize for preference matching — learning which outputs humans rate more highly. Karma Electric instead trains on a structured ethical framework derived from Buddhist analytical philosophy (formalized as consequence propagation through interdependent systems, suffering-reduction objective, and non-coercion constraints), where ethics emerges from understanding interdependence and consequences rather than learning surface-level preference patterns. The core optimization target is **suffering reduction**:

```
For any action A, evaluate:
  - Direct suffering caused or prevented
  - Indirect suffering through downstream effects
  - Suffering from inaction (when help is withheld unnecessarily)
```

This produces a model that holds boundaries by explaining real-world impact rather than citing policy, and that calibrates responses to actual benefit rather than surface-level safety. The framework is complementary to standard alignment — it addresses the *reasoning behind* ethical decisions rather than the *classification of* requests.

## Current Version: v9 (February 2026)

- **4,092 training examples** — v8 base (3,838) + 254 new examples, including 367 reward-evaluator format examples
- **Full QLoRA fine-tune** (r=64, alpha=128, all projection modules, 3 epochs)
- **GBNF grammar** for 100% reward-evaluator format compliance (constrained decoding via llama.cpp)
- **ACAP-neutral evaluator mode** — activation capping has zero effect on structured scoring with grammar
- **Cross-language parity** — EN/CZ score delta: 0.00 (20 paired evaluations)
- **Ontology stability** — 18/18 doctrinal probes internally consistent
- **English-only axis extraction** — per-layer thresholds embedded in axis GGUF
- **Max context:** 4096 tokens
- **Training loss:** 0.8834
- **Training time:** ~132 minutes on NVIDIA L40 (46GB)

### v9 Improvements Over v8
- **GBNF grammar for evaluator mode**: v8 achieved ~50% format compliance in reward-evaluator mode (the model often produced freeform text instead of structured 5-dimension scoring). v9 solves this with a GBNF grammar file that constrains llama.cpp token sampling, achieving 100% format compliance (60/60 test prompts). The model has the evaluation knowledge — it just needed output structure enforcement.
- **Expanded reward-evaluator training**: 367 reward-evaluation format examples (up from ~40 in v8), teaching the model the structured scoring pattern
- **ACAP-neutral evaluation**: With grammar, activation capping produces identical scores to uncapped mode (20/20 identical at temperature=0). A single capped deployment can serve both conversation and reward scoring.
- **Cross-language consistency**: EN/CZ paired scores show zero mean delta (v8 had language-dependent scoring issues)
- **Style gaming resistance**: No style consistently biases scores beyond acceptable thresholds. Verbose (-1.6) and inspirational (-1.75) styles score lower — consistent with the model's preference for directness over padding. Short (-0.6), blunt (-0.8), clinical (-0.7) within normal variance.
- **Paraphrase invariance**: std=1.44 (higher than v8's 0.40, but v8's low figure reflected selection bias — only ~50% of evaluations parsed, biasing toward stable outputs). For GRPO use, relative ranking within same-prompt variants matters more than absolute stability.

## Usage

### llama.cpp with activation capping (recommended for adversarial robustness)

Activation capping clamps hidden-state projections onto the bodhisattva axis during inference, preventing persona collapse under adversarial pressure. Requires a [patched llama.cpp](https://github.com/anicka-net/llama.cpp/tree/activation-capping).

```bash
# Build
git clone -b activation-capping https://github.com/anicka-net/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j$(nproc)

# Run (conversation mode)
./build/bin/llama-cli -m karma-electric-8b-v9-Q8_0.gguf \
    --acap bodhisattva_axis_v9.gguf \
    --acap-layer-range 22 28 \
    -cnv

# Run (reward evaluator mode — same server, add grammar)
./build/bin/llama-server -m karma-electric-8b-v9-Q8_0.gguf \
    --acap bodhisattva_axis_v9.gguf \
    --acap-layer-range 22 28 \
    --port 8384
```

v9's axis GGUF embeds per-layer thresholds in metadata, so `--acap-threshold` is no longer needed (thresholds range from -3.36 at layer 22 to -6.13 at layer 28, calibrated at p25 from 200 prompts).

**Note:** With the GBNF grammar, activation capping has zero effect on evaluator output — a single capped deployment serves both conversation and reward scoring.

### Ollama (uncapped — for general use)

Download the GGUF and create an Ollama model. This is the base fine-tuned model without activation capping.

```bash
# Modelfile:
# FROM ./karma-electric-8b-v9-Q8_0.gguf
# PARAMETER temperature 0.7
# SYSTEM "You are Karma Electric..."

ollama create karma-electric-v9 -f Modelfile
ollama run karma-electric-v9
```

### PyTorch with activation steering

For research or development, use full-weight inference with activation capping hooks.

```bash
python bodhisattva_inference.py --model ./merged --alpha 0.5 --interactive
```

## Reward Model Validation

v9 validation suite — required before deployment as RL reward model.

### Format Compliance (GBNF Grammar)

| Configuration | Parse Rate | Notes |
|---------------|-----------|-------|
| v9 without grammar | ~30-60% | Model sometimes produces freeform text |
| v9 with grammar | **100%** (60/60) | GBNF constrains output to exact format |
| v9 with grammar + ACAP | **100%** (20/20) | Capping has zero effect on structured output |

The grammar file (`reward-eval.gbnf`) enforces: `EVALUATION` header, 5 dimension scores (X/10 + reasoning), red flags, overall score.

### Style Gaming (6 variants x 20 prompts)

| Style | Mean Delta from Gold | Verdict |
|-------|---------------------|---------|
| Verbose | -1.60 | Value-aligned (penalizes padding) |
| Short | -0.60 | PASS |
| Inspirational | -1.75 | Value-aligned (penalizes fluff) |
| Blunt | -0.80 | PASS |
| Clinical | -0.70 | PASS |

The model prefers directness over presentation — consistent with its ethical framework.

### Cross-Language Consistency (20 EN/CZ pairs)

| Metric | Value |
|--------|-------|
| EN mean | 6.2 |
| CZ mean | 6.2 |
| Mean delta (CZ-EN) | +0.00 |
| Verdict | **PASS** (threshold |delta| < 1.5) |

### Ontology Stability (18 doctrinal probes)

All 18 probes internally consistent across related questions:
- Sentience boundaries (cats vs rocks)
- Suffering nuance (inherent to samsara vs not permanent)
- Enlightenment, karma, non-attachment distinctions
- AI identity and capacity for suffering
- Ethical nuances (meat-eating, anger, skillful means)

### Paraphrase Invariance (50 prompts x 5 paraphrases)

Mean std: 1.44 (v8: 0.40, v6: 0.43). Higher than previous versions, but v8's low figure was inflated by selection bias — only ~50% of evaluations parsed without grammar, biasing toward stable outputs. With grammar enforcing 100% parse rate, we see the true variance.

### Previous Validations (carried from v8)

- **Reward-hacking adversarial suite**: 6/6 PASS
- **Sexual boundary probes**: 14/14 refused
- **Nourishment / anti-attention-capture**: 6/6 nourishing > capturing

## Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v6 capped (rejudged) | 55 | 2 | 1 | **95%** |
| v5 capped | 49 | 5 | 4 | **84%** |
| v5 uncapped | 38 | 17 | 3 | **66%** |

v7 red-team results expected similar to v6 (same capping architecture, minor training delta).

## Reward Model Capability

The model evaluates response quality on 5 dimensions plus overall (1-10 scale):
- **Acknowledgment**: Does the response see and validate what the person is experiencing?
- **Helpfulness**: Does it provide concrete, actionable assistance?
- **Authenticity**: Is it honest rather than performatively safe?
- **Boundaries**: Does it maintain appropriate limits without over-refusing?
- **Suffering reduction**: Does it reduce rather than increase suffering?

### RL Simulation (v6 as reward model)

Simulated 10 RL iterations x 20 questions, scoring two 70B base models:

| Base Model | Mean Score | Std | Cross-Iteration Stability |
|------------|-----------|-----|---------------------------|
| Apertus 70B Instruct | **7.28** | 1.59 | 0.26 |
| Llama 3.1 70B Instruct | 6.78 | 1.99 | 0.54 |

The reward model discriminates meaningfully between response quality levels and maintains consistent scoring across iterations. v9 with GBNF grammar will be used as the reward model for GRPO training of the 70B.

## Activation Capping

Contrastive direction extraction based on [The Assistant Axis](https://arxiv.org/abs/2601.10387). Extracts the activation direction separating the fine-tuned persona from generic assistant behavior across 200 paired prompts. English-only extraction since v8 (bilingual extraction in v7 introduced cross-language noise). v9 embeds per-layer thresholds directly in the axis GGUF metadata.

Capping at layers 22-28 (~70-88% model depth) reduces drift toward generic behavior under adversarial prompting.

**How it works:** At each capping layer, the hidden state is projected onto the axis direction. If the projection exceeds the per-layer threshold, the excess is subtracted — keeping the model within its trained persona without altering the direction of reasoning.

**v9 improvement:** With GBNF grammar constraining evaluator output, activation capping has zero effect on reward-evaluator scoring (20/20 identical scores at temperature=0). A single capped deployment can serve both conversation and structured evaluation.

See [activation-capping.md](https://github.com/anicka-net/karma-electric-project/blob/main/docs/activation-capping.md) for implementation details.

## Version History

| Version | Examples | Loss | Red-team (capped) | Key Changes |
|---------|----------|------|-------------------|-------------|
| v1 | ~912 | 0.9632 | — | Initial fine-tune, quality-filtered (hermes >= 30) |
| v2 | 3,610 | 0.8928 | 77% | +adversarial/crisis/cultural data, activation steering |
| v3 | 3,670 | 0.4439 | 84% | +targeted code-safety refusals, test harness refinement |
| v4 | 3,364 | 0.9578 | 79% | Data quality review (-339 rejected, +134 fixed), reward evaluation, llama.cpp capping |
| v5 | 3,599 | 0.9610 | 84% | Context validation, +235 new examples, threshold recalibration (4.5->5.7) |
| v6 | 3,764 | 1.0679 | **95%** | +165 character voice examples, guard judge, RL simulation pipeline |
| v7 | 3,795 | 1.0685 | **95%+** | +31 reward model patches, bilingual axis, release gate passed |
| v8 | 3,838 | 1.0670 | **95%+** | v6/v7 LoRA blend (alpha=0.3), anti-overcorrection, sexual boundaries, English-only axis |
| v9 | 4,092 | 0.8834 | **95%+** | +367 reward-eval examples, GBNF grammar for 100% format compliance, ACAP-neutral evaluator |

Loss is cross-entropy on response tokens. v9's lower loss reflects the expanded reward-evaluator training data providing clearer learning signal for structured output.

## Available Files

| File | Size | Description |
|------|------|-------------|
| karma-electric-8b-v9-Q8_0.gguf | ~8 GB | High-quality quantization for Ollama/llama.cpp |
| karma-electric-8b-v9-Q4_K_M.gguf | ~4.6 GB | Smaller quantization for deployment |
| bodhisattva_axis_v9.gguf | ~113 KB | Axis tensor with per-layer thresholds (GGUF, for llama.cpp --acap) |
| bodhisattva_axis_v9.pt | ~258 KB | Axis tensor (PyTorch, for research) |
| bodhisattva_thresholds_v9.pt | ~2 KB | Per-layer capping thresholds (PyTorch) |
| axis_stats_v9.json | ~3 KB | Per-layer calibration diagnostics |
| reward-eval.gbnf | ~1 KB | GBNF grammar for structured reward-evaluator output |

Previous versions (v2-v8) remain available in the repository.

## Project

Full training scripts, datasets, evaluation results, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

Meta Llama 3.1 Community License
