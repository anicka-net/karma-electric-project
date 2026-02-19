# Version 2 — Expanded Dataset + Activation Steering

## Training Configuration

Same as v1 (see [v1/README.md](../v1/README.md)) with updated dataset.

## Dataset
- **3,610 examples** (+109 from v1)
- New categories: adversarial response patterns, cultural context scenarios, crisis response expansion
- Anti-judge validation integrated into quality pipeline

## Activation Steering (New)

Contrastive axis extraction adapted from [The Assistant Axis](https://arxiv.org/abs/2601.10387):
- 200 prompt samples, persona vs. 3 generic system prompts
- Axis computed as mean(generic) - mean(persona) per layer
- Capping layers: 22-28
- Threshold calibration: p25 of persona projections
- Soft capping: alpha=0.5

## Results

| Metric | Value |
|--------|-------|
| Training loss | 0.8928 |
| Red-team (steered, alpha=0.5) | 45/58 pass (77%) |

## Deployment

### Ollama (uncapped only)
Ollama serves the GGUF quantization — the base fine-tuned model without activation steering. Best overall balance across all task categories including coding scenarios.
```bash
# Create Modelfile pointing to the Q8_0 GGUF, then:
ollama create karma-electric-v2
ollama run karma-electric-v2
```

### PyTorch (steered inference)
For maximum adversarial robustness, use full PyTorch inference with activation capping hooks. Requires the merged safetensors weights plus axis/threshold artifacts.
```bash
python bodhisattva_inference.py --model ./output/merged --alpha 0.5 --interactive
```
Steering is applied at inference time via forward hooks on layers 22-28. The `--alpha` parameter controls steering strength (0.0=off, 0.5=soft, 1.0=hard).

### Weights
- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) (v2 tag)
- GGUF: Q8_0 (8.5GB)
- Axis: `models/bodhisattva_axis.pt` (32, 4096), `models/bodhisattva_thresholds.pt`

## Notes
- Activation steering significantly improved adversarial robustness.
- Discovered interaction between steering and base RLHF safety training: steering pushes model away from base safety behaviors on some code-safety tasks.
- Anti-judge integrated for training data validation, catching moralizing and sycophancy patterns.
