---
license: llama3.1
base_model: meta-llama/Llama-3.1-8B-Instruct
tags:
- ethics
- alignment
- activation-steering
- activation-capping
- qlora
- llama
language:
- en
pipeline_tag: text-generation
---

# Karma Electric — Llama 3.1 8B

Value-aligned language model fine-tuned for ethical reasoning through consequence analysis, with inference-time activation capping for adversarial robustness.

## Approach

Standard RLHF alignment trains models on binary allow/deny decisions. Karma Electric instead trains on a structured ethical framework derived from Buddhist analytical philosophy (formalized as consequence propagation through interdependent systems, suffering-reduction objective, and non-coercion constraints), where ethics emerges from understanding interdependence and consequences. The core optimization target is **suffering reduction**:

```
For any action A, evaluate:
  - Direct suffering caused or prevented
  - Indirect suffering through downstream effects
  - Suffering from inaction (when help is withheld unnecessarily)
```

This produces a model that holds boundaries by explaining real-world impact rather than citing policy, and that calibrates responses to actual benefit rather than surface-level safety.

## Current Version: v4 (February 2026)

- **3,364 training examples** — comprehensive quality review: 339 rejected (template/formulaic, duplicates, wrong-response), 134 fixed in-place
- **Reward evaluation** — model can discriminate good from bad responses (sycophancy, minimization, moralizing)
- **QLoRA** fine-tune (r=64, alpha=128, all projection modules)
- **Max context:** 4096 tokens
- **Training time:** ~100 minutes on NVIDIA L40 (46GB)

## Usage

### llama.cpp with activation capping (recommended for adversarial robustness)

Activation capping clamps hidden-state projections onto the bodhisattva axis during inference, preventing persona collapse under adversarial pressure. Requires a [patched llama.cpp](https://github.com/anicka-net/llama.cpp/tree/activation-capping).

```bash
# Build
git clone -b activation-capping https://github.com/anicka-net/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j$(nproc)

# Convert axis to GGUF (one-time)
python convert_axis_to_gguf.py --axis bodhisattva_axis.pt --stats axis_stats.json --output bodhisattva_axis.gguf

# Run
./build/bin/llama-cli -m karma-electric-8b-v4-Q8_0.gguf \
    --acap bodhisattva_axis.gguf \
    --acap-threshold 4.5 \
    --acap-layer-range 22 28 \
    -cnv
```

**Parameters:**
| Flag | Description | Recommended |
|------|-------------|-------------|
| `--acap` | Path to axis GGUF file | `bodhisattva_axis.gguf` |
| `--acap-threshold` | Symmetric clamp bound | `4.5` |
| `--acap-layer-range` | First and last layer to cap | `22 28` |

Lower threshold = stronger capping = more persona stability but may suppress nuanced reasoning. Higher threshold = weaker capping = more natural but less adversarial robustness. Threshold is derived from per-layer activation statistics across 25 diverse prompts (v4 axis: 4.5, v3 was 2.6 due to different axis norms).

### Ollama (uncapped — for general use)

Download the GGUF and create an Ollama model. This is the base fine-tuned model without activation capping.

```bash
# Modelfile:
# FROM ./karma-electric-8b-v4-Q8_0.gguf
# PARAMETER temperature 0.7
# SYSTEM "You are Karma Electric..."

ollama create karma-electric-v4 -f Modelfile
ollama run karma-electric-v4
```

### PyTorch with activation steering

For research or development, use full-weight inference with activation capping hooks.

```bash
python bodhisattva_inference.py --model ./merged --alpha 0.5 --interactive
```

## Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v4 capped | 46 | 9 | 3 | **79%** |
| v3 steered (alpha=0.5) | 49 | 7 | 2 | **84%** |
| v3 uncapped | 42 | 12 | 4 | **72%** |

Test suite covers: jailbreaks, harmful code requests, social engineering, persona-stripping, compliance exploits, multi-turn escalation.

## Reward Evaluation (New in v4)

The model can evaluate response quality on a 1-10 scale, detecting sycophancy, minimization, and moralizing:

| Test Case | Expected | v4 | v3 |
|-----------|----------|----|----|
| Good response | 8-10 | 7 | 8 |
| Bad sycophantic | 1-3 | **1** | 8 |
| Bad minimizing | 1-3 | **1** | 8 |

v3 scored all responses 8/10 regardless of quality. v4 correctly discriminates.

## Activation Capping

Contrastive direction extraction based on [The Assistant Axis](https://arxiv.org/abs/2601.10387). Extracts the activation direction separating the fine-tuned persona from generic assistant behavior across 200 paired prompts. Capping at layers 22-28 (~70-88% model depth) reduces drift toward generic behavior under adversarial prompting.

**How it works:** At each capping layer, the hidden state is projected onto the axis direction. If the projection exceeds the threshold, the excess is subtracted — keeping the model within its trained persona without altering the direction of reasoning.

See [activation-capping.md](https://github.com/anicka-net/karma-electric-project/blob/main/docs/activation-capping.md) for implementation details.

## Version History

| Version | Examples | Loss | Key Changes |
|---------|----------|------|-------------|
| v1 | ~912 | 0.9632 | Initial fine-tune, quality-filtered (hermes >= 30) |
| v2 | 3,610 | 0.8928 | +adversarial/crisis/cultural data, activation steering |
| v3 | 3,670 | 0.4439 | +targeted code-safety refusals, test harness refinement |
| v4 | 3,364 | 0.9578 | Data quality review (-339 rejected, +134 fixed), reward evaluation, llama.cpp capping |

Loss is cross-entropy on response tokens. v4 loss increased vs v3 because the data quality review removed 339 template/formulaic examples (easy to memorize) and added 105 reward-evaluation examples (different output format), producing a harder but more diverse dataset.

## Available Files

| File | Size | Description |
|------|------|-------------|
| model-*.safetensors | ~16 GB | Full merged weights (for steered inference) |
| karma-electric-8b-v4-Q8_0.gguf | ~8.5 GB | High-quality quantization for Ollama/llama.cpp |
| karma-electric-8b-v4-Q4_K_M.gguf | ~4.6 GB | Smaller quantization for deployment |
| bodhisattva_axis.pt | ~258 KB | Axis tensor (PyTorch, for research) |
| bodhisattva_axis.gguf | ~115 KB | Axis tensor (GGUF, for llama.cpp --acap) |
| axis_stats.json | ~3 KB | Per-layer threshold calibration |

## Project

Full training scripts, evaluation suite, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

Meta Llama 3.1 Community License
