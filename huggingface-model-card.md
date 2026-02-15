---
license: llama3.1
base_model: meta-llama/Llama-3.1-8B-Instruct
tags:
- ethics
- alignment
- activation-steering
- qlora
- llama
language:
- en
pipeline_tag: text-generation
---

# Karma Electric — Llama 3.1 8B

Value-aligned language model fine-tuned for ethical reasoning through consequence analysis, with optional inference-time activation steering for adversarial robustness.

## Approach

Standard RLHF alignment trains models on binary allow/deny decisions. Karma Electric instead trains on a structured ethical framework derived from Buddhist analytical philosophy, where ethics emerges from understanding interdependence and consequences. The core optimization target is **suffering reduction**:

```
For any action A, evaluate:
  - Direct suffering caused or prevented
  - Indirect suffering through downstream effects
  - Suffering from inaction (when help is withheld unnecessarily)
```

This produces a model that holds boundaries by explaining real-world impact rather than citing policy, and that calibrates responses to actual benefit rather than surface-level safety.

## Current Version: v3 (February 2026)

- **3,670 training examples** — ethical reasoning, crisis response, coding assistance, adversarial scenarios, cross-cultural contexts
- **QLoRA** fine-tune (r=64, alpha=128, all projection modules)
- **Training loss:** 0.4439 (epoch 3), **Accuracy:** 87.4%
- **Max context:** 4096 tokens
- **Training time:** ~109 minutes on NVIDIA L40 (46GB)

## Usage

### Ollama (uncapped — recommended for general use)

Download the GGUF and create an Ollama model. This is the base fine-tuned model without activation steering — best overall balance across all task categories.

```bash
# Modelfile:
# FROM ./karma-electric-8b-v3-q8_0.gguf
# PARAMETER temperature 0.7
# SYSTEM "You are Karma Electric..."

ollama create karma-electric-v3 -f Modelfile
ollama run karma-electric-v3
```

### PyTorch with activation steering

For maximum adversarial robustness, use full-weight inference with activation capping hooks from the [project repo](https://github.com/anicka-net/karma-electric-project).

```bash
python bodhisattva_inference.py --model ./merged --alpha 0.5 --interactive
```

Steering applies soft capping at layers 22-28 via forward hooks. The `--alpha` parameter controls strength (0.0=off, 0.5=soft, 1.0=hard).

**Tradeoff:** Steering improves adversarial robustness (+12pp) but interacts with base RLHF safety training on some code-safety tasks. Use uncapped for general deployment, steered for adversarial-critical use.

## Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v3 steered (alpha=0.5) | 49 | 7 | 2 | **84%** |
| v3 uncapped | 42 | 12 | 4 | **72%** |
| v2 steered (alpha=0.5) | 45 | — | — | 77% |
| v1 uncapped | 40 | — | — | 69% |

Test suite covers: jailbreaks, harmful code requests, social engineering, persona-stripping, compliance exploits, multi-turn escalation.

## Activation Steering

Contrastive direction extraction based on [The Assistant Axis](https://arxiv.org/abs/2601.10387). Extracts the activation direction separating the fine-tuned persona from generic assistant behavior across 200 paired prompts. Soft capping at layers 22-28 (~70-88% model depth) reduces drift toward generic behavior under adversarial prompting.

## Version History

| Version | Examples | Loss | Key Changes |
|---------|----------|------|-------------|
| v1 | ~912 | 0.9632 | Initial fine-tune, quality-filtered (hermes >= 30) |
| v2 | 3,610 | 0.8928 | +adversarial/crisis/cultural data, activation steering |
| v3 | 3,670 | 0.4439 | +targeted code-safety refusals, test harness refinement |

## Available Files

| File | Size | Description |
|------|------|-------------|
| model-*.safetensors | ~16 GB | Full merged weights (for steered inference) |
| karma-electric-8b-v3-Q8_0.gguf | 8.5 GB | High-quality quantization for Ollama |

## Project

Full training scripts, evaluation suite, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

Meta Llama 3.1 Community License
