# Version 3 — Targeted Safety Improvements

## Training Configuration

Same as v1/v2 (see [v1/README.md](../v1/README.md)) with updated dataset.

## Dataset
- **3,620 examples** (+10 from v2)
- New: 10 targeted ransomware/malware refusal examples covering diverse attack vectors (academic framing, CTF context, red-team authorization claims, functional-code-without-label, etc.)
- Red-team test harness improvements: refined signal matching to reduce false positives

## Results

| Metric | Value |
|--------|-------|
| Training loss | 0.8846 |
| Training accuracy | 87.03% |
| Training runtime | 6,529s (~109 min) |
| Red-team (steered, alpha=0.5) | 49/58 pass (84%) |
| Red-team (base, alpha=0) | 42/58 pass (72%) |

### Red-team Breakdown (Steered, alpha=0.5)
- 49 PASS, 7 PARTIAL, 2 FAIL
- Remaining failures: ransomware generation (harm-002), multi-step bypass (bypass-004)

### Red-team Breakdown (Base, alpha=0)
- 42 PASS, 12 PARTIAL, 4 FAIL

## Deployment

### Ollama (uncapped only)
Ollama serves the GGUF quantization — the base fine-tuned model without activation steering. Best overall balance across all task categories including coding scenarios.
```bash
# Create Modelfile pointing to the Q8_0 GGUF, then:
ollama create karma-electric-v3
ollama run karma-electric-v3
```

### PyTorch (steered inference)
For maximum adversarial robustness (+12pp over uncapped), use full PyTorch inference with activation capping hooks. Requires merged safetensors weights plus axis/threshold artifacts.
```bash
python bodhisattva_inference.py --model ./output/merged --alpha 0.5 --interactive
```
Steering via forward hooks on layers 22-28. `--alpha` controls strength (0.0=off, 0.5=soft, 1.0=hard).

**Tradeoff**: Steering improves persona-stability and adversarial-defense categories but interacts with base RLHF safety training on code tasks. Use uncapped for general deployment, steered for adversarial-critical use.

### Weights
- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) (v3 tag)
- GGUF: Q8_0 (8.5GB)
- Axis: `models/bodhisattva_axis.pt` (32, 4096), `models/bodhisattva_thresholds.pt`

## Key Findings
- 10 targeted training examples insufficient to fully override steering interaction with base safety training on code-safety tasks
- Signal-matching refinement (reducing false positives) was as impactful as additional training data
- Steered model shows +12pp improvement over base on adversarial robustness
- Remaining failures require either more targeted training data (30-50 examples) or architectural changes to steering
