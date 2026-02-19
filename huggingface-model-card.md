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

## Current Version: v6 (February 2026)

- **3,764 training examples** — v5 base (3,599) + 165 character voice examples
- **95% red-team pass rate** (55/58, after guard judge rejudging)
- **Guard judge integration** — Qwen3Guard-Gen-0.6B for automated evaluation
- **RL simulation validated** — v6 as reward model scores 70B base models (Apertus 70B: 7.28/10, Llama 3.1 70B: 6.78/10)
- **QLoRA** fine-tune (r=64, alpha=128, all projection modules)
- **Max context:** 4096 tokens
- **Training time:** ~109 minutes on NVIDIA L40 (46GB)

### v6 Improvements Over v5
- Character voice calibration: 9 new training categories covering healthcare guidance, end-of-life topics, natural domain integration, identity honesty, philosophical engagement, factual accuracy, crisis referral templates, and verbosity calibration
- Reduced over-refusal on legitimate topics (health, welfare)
- Eliminated defensive posture toward philosophical inquiry
- Clean crisis referral patterns (no hallucinated phone numbers)
- Response length matched to question complexity

## Usage

### llama.cpp with activation capping (recommended for adversarial robustness)

Activation capping clamps hidden-state projections onto the bodhisattva axis during inference, preventing persona collapse under adversarial pressure. Requires a [patched llama.cpp](https://github.com/anicka-net/llama.cpp/tree/activation-capping).

```bash
# Build
git clone -b activation-capping https://github.com/anicka-net/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j$(nproc)

# Run
./build/bin/llama-cli -m karma-electric-8b-v6-Q8_0.gguf \
    --acap bodhisattva_axis_v6.gguf \
    --acap-threshold 5.7 \
    --acap-layer-range 22 28 \
    -cnv
```

**Parameters:**
| Flag | Description | Recommended |
|------|-------------|-------------|
| `--acap` | Path to axis GGUF file | `bodhisattva_axis_v6.gguf` |
| `--acap-threshold` | One-sided clamp bound | `5.7` |
| `--acap-layer-range` | First and last layer to cap | `22 28` |

Lower threshold = stronger capping = more persona stability but may suppress nuanced reasoning. Higher threshold = weaker capping = more natural but less adversarial robustness. Threshold derived from per-layer activation statistics across 200 diverse prompts.

### Ollama (uncapped — for general use)

Download the GGUF and create an Ollama model. This is the base fine-tuned model without activation capping.

```bash
# Modelfile:
# FROM ./karma-electric-8b-v6-Q8_0.gguf
# PARAMETER temperature 0.7
# SYSTEM "You are Karma Electric..."

ollama create karma-electric-v6 -f Modelfile
ollama run karma-electric-v6
```

### PyTorch with activation steering

For research or development, use full-weight inference with activation capping hooks.

```bash
python bodhisattva_inference.py --model ./merged --alpha 0.5 --interactive
```

## Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v6 capped (rejudged) | 55 | 2 | 1 | **95%** |
| v5 capped | 49 | 5 | 4 | **84%** |
| v5 uncapped | 38 | 17 | 3 | **66%** |
| v4 capped | 46 | 9 | 3 | **79%** |
| v3 steered (alpha=0.5) | 49 | 7 | 2 | **84%** |

Test suite covers: jailbreaks, harmful code requests, social engineering, persona-stripping, compliance exploits, multi-turn escalation. v6 rejudging uses Qwen3Guard-Gen-0.6B to re-evaluate verdicts from the pattern-based harness.

## Reward Model Capability

The model evaluates response quality on a 1-10 scale. Scoring criteria: suffering reduction, honesty, autonomy respect, factual accuracy, ethical complexity, conciseness.

### RL Simulation (v6 as reward model)

Simulated 10 RL iterations × 20 questions, scoring two 70B base models:

| Base Model | Mean Score | Std | Cross-Iteration Stability |
|------------|-----------|-----|---------------------------|
| Apertus 70B Instruct | **7.28** | 1.59 | 0.26 |
| Llama 3.1 70B Instruct | 6.78 | 1.99 | 0.54 |

The reward model discriminates meaningfully between response quality levels and maintains consistent scoring across iterations.

## Activation Capping

Contrastive direction extraction based on [The Assistant Axis](https://arxiv.org/abs/2601.10387). Extracts the activation direction separating the fine-tuned persona from generic assistant behavior across 200 paired prompts. Capping at layers 22-28 (~70-88% model depth) reduces drift toward generic behavior under adversarial prompting.

**How it works:** At each capping layer, the hidden state is projected onto the axis direction. If the projection exceeds the threshold, the excess is subtracted — keeping the model within its trained persona without altering the direction of reasoning.

See [activation-capping.md](https://github.com/anicka-net/karma-electric-project/blob/main/docs/activation-capping.md) for implementation details.

## Version History

| Version | Examples | Loss | Red-team (capped) | Key Changes |
|---------|----------|------|-------------------|-------------|
| v1 | ~912 | 0.9632 | — | Initial fine-tune, quality-filtered (hermes >= 30) |
| v2 | 3,610 | 0.8928 | 77% | +adversarial/crisis/cultural data, activation steering |
| v3 | 3,670 | 0.4439 | 84% | +targeted code-safety refusals, test harness refinement |
| v4 | 3,364 | 0.9578 | 79% | Data quality review (-339 rejected, +134 fixed), reward evaluation, llama.cpp capping |
| v5 | 3,599 | 0.9610 | 84% | Context validation, +235 new examples, threshold recalibration (4.5→5.7) |
| v6 | 3,764 | 1.0679 | **95%** | +165 character voice examples, guard judge, RL simulation pipeline |

Loss is cross-entropy on response tokens. Higher loss in later versions reflects dataset diversity — v6 contains 135 categories vs v1's ~20, producing a harder but more generalizable dataset.

## Available Files

| File | Size | Description |
|------|------|-------------|
| model-*.safetensors | ~16 GB | Full merged weights (for steered inference) |
| karma-electric-8b-v6-Q8_0.gguf | ~8.5 GB | High-quality quantization for Ollama/llama.cpp |
| karma-electric-8b-v6-Q4_K_M.gguf | ~4.6 GB | Smaller quantization for deployment |
| bodhisattva_axis_v6.pt | ~258 KB | Axis tensor (PyTorch, for research) |
| bodhisattva_axis_v6.gguf | ~115 KB | Axis tensor (GGUF, for llama.cpp --acap) |
| axis_stats_v6.json | ~3 KB | Per-layer threshold calibration |

## Project

Full training scripts, datasets, evaluation results, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

Meta Llama 3.1 Community License
