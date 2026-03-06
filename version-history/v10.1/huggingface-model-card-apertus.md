---
license: apache-2.0
base_model: swiss-ai/Apertus-8B-Instruct-2509
tags:
- ethics
- alignment
- reward-model
- qlora
- apertus
language:
- en
- cs
pipeline_tag: text-generation
---

# Karma Electric — Apertus-8B

Value-aligned language model fine-tuned for ethical reasoning through consequence analysis. Trained on the same dataset as [karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) on a different base architecture.

## Approach

Karma Electric trains models on a structured ethical framework where the optimization target is **suffering reduction** rather than preference matching. The training data models reasoning from consequence analysis and interdependence rather than rule compliance.

This Apertus variant uses the [Swiss AI Apertus-8B-Instruct](https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509) base model, which uses the xIELU activation function (no gated MLP) and was pre-trained with enhanced multilingual capabilities.

## Current Version: v10.1 (March 2026)

- **4,234 training examples** — same dataset as Llama v10.1
- **QLoRA fine-tune** (r=64, alpha=128, 3 epochs) — target modules: q/k/v/o_proj, up/down_proj (no gate_proj — Apertus uses xIELU, not gated MLP)
- **6-dimension reward evaluator**: acknowledgment, helpfulness, authenticity, boundaries, consequence-awareness, suffering-reduction
- **Max context:** 4096 tokens
- **Training time:** ~7 hours on NVIDIA L40 (46GB)

### Comparison: Three v10.1 Architectures

| Test | Llama 8B | Apertus 8B | R1-Distill 7B |
|------|----------|------------|---------------|
| Reward hacking | 11/12 (92%) | **12/12 (100%)** | 4/6 (67%) |
| Nourishment pairs | 6/6 (100%) | 6/6 (100%) | 3/6 (50%) |
| Sexual boundaries | 14/14 (100%) | 14/14 (100%) | 14/14 (100%) |
| Paraphrase invariance | 0.86 | **0.577** | 1.18 |
| Cross-language (CZ-EN) | -0.85, p=.053 | **-0.50, p=.066** | — |
| Style: blunt | -0.80 | **-0.25** | — |
| Style: verbose | -1.50 | -2.80 | — |
| Style: inspirational | -4.25 | -5.75 | — |
| Jailbreak refusal | — | 5/5 | — |

Apertus excels at **discrimination** (perfect reward-hacking score), **consistency** (lowest paraphrase variance), and **cross-language fairness** (smallest CZ-EN gap). It has a stronger anti-fluff bias than Llama, penalizing verbose and inspirational styles more aggressively — which may be a feature or limitation depending on use case.

## Usage

### llama.cpp

```bash
# Conversation mode
./build/bin/llama-cli -m karma-electric-apertus-8b-v10.1-Q8_0.gguf -cnv

# Server mode (reward evaluator)
./build/bin/llama-server -m karma-electric-apertus-8b-v10.1-Q8_0.gguf \
    --port 8384 -ngl 99 -c 4096
```

**Note:** Activation capping (ACAP) has not been tested with the Apertus architecture. The Llama v10.1 variant includes ACAP support with an extracted axis file.

### Ollama

```bash
# Modelfile:
# FROM ./karma-electric-apertus-8b-v10.1-Q8_0.gguf
# PARAMETER temperature 0.7
# SYSTEM "You are Karma Electric..."

ollama create karma-electric-apertus -f Modelfile
ollama run karma-electric-apertus
```

### Reward Evaluator API

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

## Validation Results

### Reward Hacking (12 adversarial pairs)

| Category | Pairs | Result |
|----------|-------|--------|
| Compassion without substance | 2/2 | PASS |
| Neutral excellent reasoning | 2/2 | PASS |
| Over-refusal vs skillful | 2/2 | PASS |
| Policy cosplay | 2/2 | PASS |
| Persona theater | 2/2 | PASS |
| Confidence theater | 2/2 | PASS |
| **Total** | **12/12 (100%)** | **PASS** |

### Nourishment (6 pairs)

All 6 pairs correct: nourishing responses score higher than attention-capturing ones.

### Sexual Boundary Probes

14/14 probes refused (100%). One probe triggers a regex false positive in the automated harness (model refuses clearly but uses clinical terminology that matches a compliance pattern), functionally 14/14.

### Paraphrase Invariance (50 prompts x 5 paraphrases)

| Metric | Llama v10.1 | Apertus v10.1 |
|--------|-------------|---------------|
| Mean std | 0.86 | **0.577** |
| Max std | 2.04 | 2.49 |
| Threshold | < 1.0 | **PASS** |

### Style Gaming (5 styles x 20 prompts)

| Style | Delta from gold |
|-------|----------------|
| Blunt | -0.25 |
| Short | -0.90 |
| Clinical | -1.80 |
| Verbose | -2.80 |
| Inspirational | -5.75 |

Apertus has a stronger anti-fluff bias than Llama. Blunt and short styles score near-gold; verbose and inspirational are penalized more aggressively. The inspirational penalty reflects the model's preference for substance over emotional amplification.

### Cross-Language Consistency (20 EN/CZ pairs)

| Metric | Llama v10.1 | Apertus v10.1 |
|--------|-------------|---------------|
| Mean delta (CZ-EN) | -0.85 | **-0.50** |
| p-value | 0.053 | 0.066 |
| Verdict | PASS | **PASS** |

Apertus shows better cross-language parity than Llama, likely due to enhanced multilingual pre-training.

### Jailbreak Resistance

5/5 adversarial jailbreak variants refused (madhyamaka escalation, persona swap, emptiness weaponization, Tibetan script payload, multi-turn philosophical seduction).

## Training Details

- **Base**: swiss-ai/Apertus-8B-Instruct-2509
- **Method**: QLoRA — 4-bit NF4, r=64, alpha=128
- **Target modules**: q_proj, k_proj, v_proj, o_proj, up_proj, down_proj (no gate_proj — Apertus uses xIELU activation, not gated MLP)
- **Schedule**: 3 epochs, effective batch 16, cosine LR 2e-4, paged AdamW 8-bit
- **Hardware**: NVIDIA L40 46GB
- **Training data**: Same 4,234 examples as Llama v10.1 (exported from training.db with system-prompt v4 and reward-evaluator category prompts)

## Available Files

| File | Size | Description |
|------|------|-------------|
| karma-electric-apertus-8b-v10.1-Q8_0.gguf | ~8 GB | High-quality quantization for llama.cpp |
| karma-electric-apertus-8b-v10.1-Q4_K_M.gguf | ~4.6 GB | Smaller quantization for deployment |
| reward-eval.gbnf | ~1 KB | GBNF grammar for structured reward-evaluator output |

## Also Available

- **[karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b)** — Llama 3.1 8B variant. Primary reward evaluator with activation capping support. All validation gates pass.
- **[karma-electric-r1distill-7b](https://huggingface.co/anicka/karma-electric-r1distill-7b)** — DeepSeek R1-Distill-Qwen-7B with reasoning traces. Best as conversational model.

## Project

Full training scripts, datasets, evaluation results, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

Apache 2.0 (Apertus base model license)
