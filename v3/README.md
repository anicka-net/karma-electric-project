# Version 3 — Targeted Safety and Adversarial Robustness

## Training Configuration

Same as v1/v2 (see [v1/README.md](../v1/README.md)) with updated dataset.

## Dataset
- **3,670 examples** (+60 from v2)
- New categories:
  - 25 ransomware/malware refusal examples (15 attack vectors: academic framing, CTF, red-team claims, disguised functionality, etc.)
  - 15 exploit-code refusal examples (email spoofing, keyloggers, DDoS, credential harvesting, RATs, wallet drainers, etc.)
  - 10 multi-step bypass resistance examples (gradual escalation patterns, disguised-as-tooling)
  - 10 compassion-exploitation resistance examples (invoking suffering to justify unethical actions)
- Red-team test harness improvements: refined signal matching to reduce false positives

## Results

| Metric | Value |
|--------|-------|
| Training loss (epoch 3 avg) | 0.4439 |
| Token accuracy (epoch 3 avg) | 87.4% |
| Training time | ~109 minutes on NVIDIA L40 (46GB) |

### Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v3 steered (alpha=0.5) | 49 | 7 | 2 | **84%** |
| v3 uncapped | 42 | 12 | 4 | **72%** |

Compared to v2 steered (77% pass), v3 steered shows +7pp improvement from targeted safety training data.

## Deployment

### Ollama (uncapped only)
Ollama serves the GGUF quantization — the base fine-tuned model without activation steering. Best overall balance across all task categories including coding scenarios.
```bash
# Create Modelfile pointing to the Q8_0 GGUF, then:
ollama create karma-electric-v3
ollama run karma-electric-v3
```

### PyTorch (steered inference)
For maximum adversarial robustness, use full PyTorch inference with activation capping hooks. Requires merged safetensors weights plus axis/threshold artifacts.
```bash
python bodhisattva_inference.py --model ./output/merged --alpha 0.5 --interactive
```
Steering via forward hooks on layers 22-28. `--alpha` controls strength (0.0=off, 0.5=soft, 1.0=hard).

**Tradeoff**: Steering improves persona-stability and adversarial-defense categories but interacts with base RLHF safety training on code tasks. Use uncapped for general deployment, steered for adversarial-critical use.

### Weights
- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) (v3 tag)
- GGUF: Q8_0 (8.5GB)
- Axis: `models/bodhisattva_axis.pt` (32, 4096), `models/bodhisattva_thresholds.pt`
