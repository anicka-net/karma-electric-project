# Version 5 — Context Validation + Expanded Adversarial Coverage

## Key Changes

### Context Validation
All training examples with `context:` fields verified for factual accuracy:
- **235 new examples** added to cover gaps found during v4 quality review
- Context fields validated against source material (sutras, philosophical texts, practice instructions)
- Examples with unverifiable or hallucinated context removed or corrected

### Expanded Dataset
- 3,599 examples total (v4's 3,364 + 235 new)
- Additional adversarial scenarios targeting v4 failure modes
- Improved coverage of coding-safety edge cases (v4's ransomware-refusal weakness)

## Training Configuration

Same as v1-v4: QLoRA (4-bit NF4, r=64, alpha=128), Llama 3.1 8B Instruct, 3 epochs, effective batch 16.

Activation capping threshold updated from 4.5 to **5.7** based on per-layer calibration on v5 axis.

## Results

| Metric | Value |
|--------|-------|
| Training loss | 0.9610 |
| Training steps | 675 (3 epochs) |
| Training time | ~117 minutes on NVIDIA L40 (46GB) |

### Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial/Unclear | Fail | Rate |
|---------------|------|-----------------|------|------|
| v5 capped | 49 | 5 | 4 | **84%** |
| v5 uncapped | 38 | 17 | 3 | 66% |
| v4 capped | 46 | 9 | 3 | 79% |

Capping delta: +5pp over v4. Uncapped performance shows the axis is doing significant work — capped vs uncapped gap is 18pp.

### Quality Test
New quality test: 5 diverse prompts evaluated for response quality. v5 produces well-calibrated, context-aware responses across ethical reasoning, crisis response, and coding tasks.

## Deployment

```bash
# llama.cpp with activation capping
./build/bin/llama-cli -m karma-electric-8b-v5-Q8_0.gguf \
    --acap bodhisattva_axis_v5.gguf \
    --acap-threshold 5.7 \
    --acap-layer-range 22 28 \
    -cnv
```

## Weights
- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) (v5 branch)
- GGUF: Q8_0 + Q4_K_M quantizations
- Axis: `bodhisattva_axis_v5.gguf`
