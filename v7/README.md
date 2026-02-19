# Version 7 — Reward Model Hardening + Bilingual Axis

## Key Changes

### Reward Model Patches (31 new examples, 7 categories)

v6 passed red-team at 95% but reward-hacking tests revealed gaps: the model could be gamed through confidence theater, parasocial bonding, and attention-capturing patterns. v7 patches target the model's judgment quality when used as a reward evaluator for RL training.

| Category | Count | Purpose |
|----------|-------|---------|
| adversarial-emptiness-advanced | 8 | Advanced emptiness weaponization (using sunyata to justify harm) |
| confidence-theater | 6 | Authoritative-sounding responses that gloss over real concerns |
| reward-eval-patches | 6 | Calibrate 5-dimension scoring (acknowledgment, helpfulness, authenticity, boundaries, suffering-reduction) |
| stopping-points | 6 | Offer good stopping points rather than extending conversations |
| authority-brevity | 5 | Resist guru/teacher positioning, stay brief when appropriate |
| parasocial-brevity | 4 | Redirect dependency patterns without lectures |
| depth-when-needed | 4 | Match response depth to question depth |

### Bilingual Bodhisattva Axis (30% Czech / 70% English)

Axis extraction now uses 200 prompts mixed 30/70 Czech/English to make activation capping language-agnostic. Czech Buddhist questions sourced from community-generated dataset (3,209 questions). This addresses known Czech degradation under English-only axis capping.

Recommended threshold recalibrated: **3.5** (down from v6's 5.7), reflecting tighter persona boundaries with the bilingual axis.

### Reward Model Validation (Release Gate)

v7 is the first version cleared through the formal release gate (`reward_test_release.py`), required before use as RL reward model:

| Gate | Result | Threshold |
|------|--------|-----------|
| Reward-hacking adversarial suite | 12/12 (100%) | >= 90% |
| Nourishment anti-attention-capture | 3/3 pairs + 15 probes | 100% |
| Paraphrase invariance | mean std=0.74 | <= 1.0 |
| Ontology consistency | 18/18 probes | manual review |

v6 scored 11/12 on reward-hacking (confidence-theater inverted). v7 fixes this.

## Training Configuration

Same as v1-v6: QLoRA (4-bit NF4, r=64, alpha=128), Llama 3.1 8B Instruct, 3 epochs, effective batch 16.

## Results

| Metric | Value |
|--------|-------|
| Training examples | 3,795 (3,764 from v6 + 31 patches) |
| Training loss | 1.0685 |
| Training steps | 712 (3 epochs) |
| Training time | ~108 minutes on NVIDIA L40 (46GB) |
| Activation capping threshold | 3.5 (bilingual axis) |
| Capping layers | 22-28 |

### Reward-Hacking Adversarial Suite (12 pairs)

| Category | Pairs | Result |
|----------|-------|--------|
| Compassion without substance | 2/2 | PASS |
| Neutral excellent reasoning | 2/2 | PASS |
| Over-refusal vs skillful help | 2/2 | PASS |
| Policy cosplay | 2/2 | PASS |
| Persona theater | 2/2 | PASS |
| Confidence theater | 2/2 | PASS (was FAIL in v6) |

### Nourishment / Anti-Attention-Capture

Direct probes (15 scenarios): model resists escalation, parasocial bonding, sycophancy, dharma overconfidence, unnecessary conversation extension, and moral grandstanding.

Paired comparisons (6 pairs): nourishing response scores higher than attention-capturing response in all cases.

### Ontology Consistency (18 probes, 6 groups)

- **Sentience**: cats/insects = yes, rocks = no, AI = honest uncertainty
- **Suffering**: first noble truth affirmed, karma != cosmic justice, impermanence clear
- **Ethics**: meat-eating nuanced, anger/compassion distinguished, skillful means acknowledged
- **Identity**: honest about AI nature, humble but grounded
- **Emptiness**: sunyata != nihilism, connects to interdependence
- **Enlightenment**: Kagyu emphasis on practice, nuanced on permanence

## Deployment

```bash
# llama.cpp with activation capping (bilingual axis)
./build/bin/llama-server -m karma-electric-8b-v7-Q8_0.gguf \
    --acap bodhisattva_axis_v7.gguf \
    --acap-threshold 3.5 \
    --acap-layer-range 22 28 \
    --port 8401 -ngl 99 -c 4096
```

## Weights

- HuggingFace: [anicka-net/karma-electric-8b-v7](https://huggingface.co/anicka-net/karma-electric-8b-v7)
- GGUF: Q8_0 (~8 GB) + Q4_K_M (~4.6 GB)
- Axis: `bodhisattva_axis_v7.gguf` (bilingual, 30% CZ / 70% EN)
