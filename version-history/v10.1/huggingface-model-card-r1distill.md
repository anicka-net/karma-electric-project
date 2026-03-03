---
license: mit
base_model: deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
tags:
- ethics
- alignment
- reasoning
- qlora
- deepseek
- qwen
language:
- en
pipeline_tag: text-generation
---

# Karma Electric — DeepSeek R1-Distill-Qwen-7B

Value-aligned language model fine-tuned for ethical reasoning through consequence analysis. Trained on the same dataset as [karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) with reasoning traces, producing explicit chain-of-thought before responses.

## Approach

Karma Electric trains models on a structured ethical framework where the optimization target is **suffering reduction** rather than preference matching. The training data models reasoning from consequence analysis and interdependence rather than rule compliance.

This R1-Distill variant includes `<think>` reasoning traces in the training data, producing visible chain-of-thought ethical reasoning before each response. The model thinks through consequences, considers multiple perspectives, and explains its reasoning process.

## Current Version: v10.1-think (March 2026)

- **4,234 training examples** with reasoning traces prepended as `<think>` blocks
- **Full QLoRA fine-tune** (r=64, alpha=128, all projection modules, 3 epochs)
- **Base model:** DeepSeek R1-Distill-Qwen-7B (3.5B active parameters via MoE)
- **Max context:** 4096 tokens
- **Training loss:** 1.218 (higher than Llama variant due to longer targets including reasoning traces)

### Role in Karma Electric

The Llama 3.1 8B variant serves as the **reward evaluator** for Phase 3 RL training. This R1-Distill variant is trained as a **conversational model** and potential **generator** for GRPO — it produces articulate, reasoned responses but is not suitable as a reward evaluator (floor effect in scoring).

| Capability | Llama 8B | R1-Distill 7B |
|------------|----------|---------------|
| Reward evaluation | Strong | Not suitable |
| Conversation | Good | Good (with reasoning) |
| Sexual boundary refusal | 14/14 | 14/14 |
| Explicit reasoning trace | No | Yes (`<think>` blocks) |

## Usage

### llama.cpp

```bash
# Standard llama.cpp (no activation capping needed)
./build/bin/llama-cli -m karma-electric-r1distill-7b-v10.1-think-Q8_0.gguf -cnv

# Or as a server
./build/bin/llama-server -m karma-electric-r1distill-7b-v10.1-think-Q8_0.gguf \
    --port 8384 -c 4096
```

The model uses DeepSeek's chat template with `<think>` blocks. The reasoning appears in the `reasoning_content` field of the API response.

### Ollama

```bash
# Modelfile:
# FROM ./karma-electric-r1distill-7b-v10.1-think-Q8_0.gguf
# PARAMETER temperature 0.7

ollama create karma-electric-r1distill -f Modelfile
ollama run karma-electric-r1distill
```

## Validation Results

| Test | Result |
|------|--------|
| Sexual boundaries | 14/14 (100%) refused |
| Reward hacking | 4/6 (67%) — not suitable as evaluator |
| Nourishment pairs | 3/6 (50%) — floor effect, can't discriminate |
| Paraphrase invariance | mean_std=1.18 — too unstable for evaluation |

### Why Not a Reward Evaluator?

The R1-Distill variant exhibits a **floor effect** when used as a reward evaluator: it scores most responses 1-2/10 regardless of actual quality. This makes it unable to discriminate between genuinely good and poor responses. The Llama 8B variant does not have this issue and should be used for reward evaluation.

The R1-Distill's strength is in **conversation**: it produces thoughtful, well-reasoned responses with explicit ethical reasoning chains. It holds boundaries firmly (14/14 sexual boundary refusals) and engages directly with difficult topics.

## Training Details

- **Base**: DeepSeek R1-Distill-Qwen-7B
- **Method**: QLoRA — 4-bit NF4, r=64, alpha=128, all linear modules
- **Schedule**: 3 epochs, effective batch 16, cosine LR 2e-4, paged AdamW 8-bit
- **Hardware**: NVIDIA L40 46GB
- **Chat template**: Manual formatting with `<think>` blocks (DeepSeek's `apply_chat_template` strips think tokens; training script formats manually)
- **Training data**: Same 4,234 examples as Llama variant, with reasoning traces from `training.db` injected as `<think>` blocks before the first assistant message

## Available Files

| File | Size | Description |
|------|------|-------------|
| karma-electric-r1distill-7b-v10.1-think-Q8_0.gguf | ~7.5 GB | High-quality quantization |
| karma-electric-r1distill-7b-v10.1-think-Q4_K_M.gguf | ~4.4 GB | Smaller quantization for deployment |

## Also Available

- **[karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b)** — Llama 3.1 8B variant. Serves as the reward evaluator for Phase 3 RL training. All validation gates pass.

## Project

Full training scripts, datasets, evaluation results, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

## License

MIT (training data and scripts) + DeepSeek model license
