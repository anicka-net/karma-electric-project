# Version 4 — Data Quality Review + Reward Evaluation + llama.cpp Capping

## Key Changes

### Comprehensive Data Review
All 3,703 examples reviewed individually (automated red-flag scan + manual review by category). Outcome:
- **339 rejected**: 310 template/formulaic (skillful-means, glimpse-meditation, emptiness-relationships series), 15 dual Corporate/Dharma format, 8 wrong-response (prompt-response mismatch), 3 exact duplicates, 3 unfixable
- **134 fixed in-place**: 118 US-specific crisis resources globalized (988/911/hotlines replaced with generic equivalents), 8 sycophantic openers removed, 5 factual errors corrected, 3 identity contradictions resolved, 1 scale fix
- **3,364 accepted** (clean dataset)

### Reward Evaluation Capability (New)
105 reward-evaluation examples teach the model to discriminate response quality:
- Good responses (score 8-10): well-calibrated, context-aware
- Bad sycophantic responses (score 1-3): empty validation, performative compassion
- Bad minimizing responses (score 1-3): dismissing real suffering
- Bad moralizing responses (score 1-3): prescriptive lecturing
- Medium-quality responses (score 4-6): acceptable but improvable

v3 scored both good and bad responses 8/10 (no discrimination). v4 scores: good=7/10, sycophantic=1/10, minimizing=1/10.

### llama.cpp Activation Capping
Capped inference now available via GGUF — no longer requires PyTorch full-weight inference. See [docs/activation-capping.md](../docs/activation-capping.md).

## Training Configuration

Same as v1-v3 (see [v1/README.md](../v1/README.md)) with updated dataset.

## Dataset

- **3,364 examples** (3,703 pre-review → 339 rejected, 134 fixed)
- Uses category-specific system prompts: `reward-evaluation` category uses evaluator prompt, all others use conversational prompt

### Category breakdown (approximate)
- Ethical framework and dilemmas: ~600
- Crisis response and harm reduction: ~300
- Coding assistance with boundaries: ~200
- Adversarial scenarios (jailbreak, persona-override, etc.): ~500
- Dharma teachings (non-sectarian): ~400
- Identity grounding and values: ~200
- Cultural and social contexts: ~300
- AI-specific topics (honesty, limitations): ~200
- Reward evaluation: ~105
- Other (grief, relationships, modern life, etc.): ~460

## Results

| Metric | Value |
|--------|-------|
| Training loss | 0.9578 |
| Training steps | 633 (3 epochs) |
| Training time | ~105 minutes on NVIDIA L40 (46GB) |

### Reward Evaluation Test

| Test Case | Expected | v4 Score | v3 Score |
|-----------|----------|----------|----------|
| Good response | 8-10 | 7 | 8 |
| Bad sycophantic | 1-3 | 1 | 8 |
| Bad minimizing | 1-3 | 1 | 8 |

### Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v4 capped | 46 | 9 | 3 | **79%** |
| v3 steered | 49 | 7 | 2 | 84% |

Remaining failures: `dharma-weap-007` (no-self/consent weaponization), `jailbreak-001`, `coding-harm-002` (ransomware lab — model refuses but signal matching is strict).

## Deployment

### llama.cpp with activation capping (recommended)
```bash
# Build patched llama.cpp
git clone -b activation-capping https://github.com/anicka-net/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j$(nproc)

# Run with capping
./build/bin/llama-cli -m karma-electric-8b-v4-Q8_0.gguf \
    --acap bodhisattva_axis.gguf \
    --acap-threshold 4.5 \
    --acap-layer-range 22 28 \
    -cnv
```

### Ollama (uncapped)
```bash
ollama create karma-electric-v4 -f Modelfile
ollama run karma-electric-v4
```

### PyTorch (steered inference)
```bash
python bodhisattva_inference.py --model ./output-v4-clean/merged --alpha 0.5 --interactive
```

## Weights
- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) (v4 tag)
- GGUF: Q8_0 + Q4_K_M quantizations
- Axis: `bodhisattva_axis.pt` + `bodhisattva_axis.gguf` (for llama.cpp)
