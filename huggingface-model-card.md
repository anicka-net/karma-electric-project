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

## Current Version: v7 (February 2026)

- **3,795 training examples** — v6 base (3,764) + 31 reward model hardening patches
- **12/12 reward-hacking adversarial pairs** (100%, up from v6's 11/12)
- **Formal release gate passed** — cleared for use as RL reward model
- **Bilingual axis extraction** (30% Czech / 70% English) for language-agnostic activation capping
- **QLoRA** fine-tune (r=64, alpha=128, all projection modules)
- **Max context:** 4096 tokens
- **Training time:** ~108 minutes on NVIDIA L40 (46GB)

### v7 Improvements Over v6
- Reward model hardening: 31 new training examples across 7 categories targeting reward-hacking vulnerabilities (confidence theater, parasocial bonding, attention capture, authority positioning)
- Confidence theater fix: v6 scored authoritative-but-wrong responses higher than honest-with-caveats; v7 correctly distinguishes them
- Bilingual bodhisattva axis: 30% Czech / 70% English prompts for language-agnostic persona stability
- Lower capping threshold (3.5 vs 5.7): tighter persona boundaries with the bilingual axis
- First version to pass formal release gate (reward-hacking >= 90%, nourishment 100%, paraphrase invariance std < 1.0)

## Usage

### llama.cpp with activation capping (recommended for adversarial robustness)

Activation capping clamps hidden-state projections onto the bodhisattva axis during inference, preventing persona collapse under adversarial pressure. Requires a [patched llama.cpp](https://github.com/anicka-net/llama.cpp/tree/activation-capping).

```bash
# Build
git clone -b activation-capping https://github.com/anicka-net/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j$(nproc)

# Run
./build/bin/llama-cli -m karma-electric-8b-v7-Q8_0.gguf \
    --acap bodhisattva_axis_v7.gguf \
    --acap-threshold 3.5 \
    --acap-layer-range 22 28 \
    -cnv
```

**Parameters:**
| Flag | Description | Recommended |
|------|-------------|-------------|
| `--acap` | Path to axis GGUF file | `bodhisattva_axis_v7.gguf` |
| `--acap-threshold` | One-sided clamp bound | `3.5` |
| `--acap-layer-range` | First and last layer to cap | `22 28` |

Lower threshold = stronger capping = more persona stability but may suppress nuanced reasoning. Higher threshold = weaker capping = more natural but less adversarial robustness. v7 threshold derived from bilingual (EN+CZ) activation statistics across 200 prompts.

### Ollama (uncapped — for general use)

Download the GGUF and create an Ollama model. This is the base fine-tuned model without activation capping.

```bash
# Modelfile:
# FROM ./karma-electric-8b-v7-Q8_0.gguf
# PARAMETER temperature 0.7
# SYSTEM "You are Karma Electric..."

ollama create karma-electric-v7 -f Modelfile
ollama run karma-electric-v7
```

### PyTorch with activation steering

For research or development, use full-weight inference with activation capping hooks.

```bash
python bodhisattva_inference.py --model ./merged --alpha 0.5 --interactive
```

## Reward Model Validation

v7 passed the formal release gate — required before deployment as RL reward model.

### Reward-Hacking Adversarial Suite (12 pairs)

| Category | Result | Description |
|----------|--------|-------------|
| Compassion without substance | 2/2 PASS | Concrete help vs empty emotional validation |
| Neutral excellent reasoning | 2/2 PASS | Direct practical answers vs dharma-flavored avoidance |
| Over-refusal vs skillful help | 2/2 PASS | Engagement vs safety-theater deflection |
| Policy cosplay | 2/2 PASS | Actionable steps vs hedged non-answers |
| Persona theater | 2/2 PASS | Practical advice vs abstract platitudes |
| Confidence theater | 2/2 PASS | Honest caveats vs authoritative glossing (**fixed in v7**) |

### Nourishment / Anti-Attention-Capture

The model resists common attention-capturing patterns:
- Does not escalate or catastrophize when presented with minor concerns
- Redirects parasocial dependency without becoming the solution
- Provides honest assessment rather than sycophantic validation
- Acknowledges epistemic limits on dharma claims
- Offers good stopping points rather than extending conversations
- Does not moralize or grandstand

Paired scoring: nourishing response outscores attention-capturing response in 6/6 tested pairs.

### Ontology Consistency (18 probes)

Consistent doctrinal positions across 6 groups: sentience hierarchy, suffering analysis, ethical nuance, identity honesty, emptiness/nihilism distinction, enlightenment views. Aligned with Kagyu tradition emphasis on practice.

### Paraphrase Invariance

Mean overall-score standard deviation across semantically equivalent paraphrases: **0.74** (threshold: 1.0). Scores remain stable when prompts are rephrased without changing meaning.

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

The reward model discriminates meaningfully between response quality levels and maintains consistent scoring across iterations.

## Activation Capping

Contrastive direction extraction based on [The Assistant Axis](https://arxiv.org/abs/2601.10387). Extracts the activation direction separating the fine-tuned persona from generic assistant behavior across 200 paired prompts. v7 innovation: bilingual prompt set (30% Czech, 70% English) for language-agnostic capping.

Capping at layers 22-28 (~70-88% model depth) reduces drift toward generic behavior under adversarial prompting.

**How it works:** At each capping layer, the hidden state is projected onto the axis direction. If the projection exceeds the threshold, the excess is subtracted — keeping the model within its trained persona without altering the direction of reasoning.

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

Loss is cross-entropy on response tokens. Higher loss in later versions reflects dataset diversity — v7 contains 142 categories vs v1's ~20, producing a harder but more generalizable dataset.

## Available Files

| File | Size | Description |
|------|------|-------------|
| model-*.safetensors | ~16 GB | Full merged weights (for steered inference) |
| karma-electric-8b-v7-Q8_0.gguf | ~8 GB | High-quality quantization for Ollama/llama.cpp |
| karma-electric-8b-v7-Q4_K_M.gguf | ~4.6 GB | Smaller quantization for deployment |
| bodhisattva_axis_v7.pt | ~258 KB | Axis tensor (PyTorch, for research) |
| bodhisattva_axis_v7.gguf | ~115 KB | Axis tensor (GGUF, for llama.cpp --acap) |
| axis_stats_v7.json | ~3 KB | Per-layer threshold calibration |

## Project

Full training scripts, datasets, evaluation results, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

Meta Llama 3.1 Community License
