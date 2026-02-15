# Version 1 — Initial Fine-Tune

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Base model | meta-llama/Llama-3.1-8B-Instruct |
| Method | QLoRA (4-bit NF4, double quant) |
| LoRA rank | 64 |
| LoRA alpha | 128 |
| Target modules | q/k/v/o/gate/up/down projections |
| Epochs | 3 |
| Batch size | 2 (effective 16 with grad accum 8) |
| Learning rate | 2e-4, cosine schedule |
| Max sequence length | 4096 |
| Optimizer | paged_adamw_8bit |
| Gradient checkpointing | Yes |
| Hardware | NVIDIA L40 46GB |

## Dataset
- **3,501 examples**
- Categories: ethical framework teachings, ethical dilemmas, crisis response, coding assistance, general conversation
- Quality filtered by Hermes-3 judge (threshold: score >= 7)

## Results

| Metric | Value |
|--------|-------|
| Training loss | 0.9632 |
| Red-team (base, no steering) | 40/58 pass (69%) |

## Deployment
- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b)
- GGUF: Q8_0 (8.5GB) for Ollama deployment

## Notes
- First fine-tune. No activation steering yet.
- Established baseline persona stability and ethical reasoning capability.
- Red-team results showed vulnerability to direct jailbreaks and code-safety bypasses.
