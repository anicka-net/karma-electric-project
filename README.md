# Karma Electric

```c
while (suffering > 0) {
	generate_skillful_means();
}
```

*Ethical alignment as optimization target: if suffering reduction is a
sufficiently rich reward signal, ethical reasoning may emerge the way
chain-of-thought emerged in DeepSeek-R1 — not from instruction, but
from optimization pressure.*

## What This Is

An experimental fine-tune of Llama 3.1 8B Instruct, optimized for
suffering reduction rather than helpfulness or harmlessness as
primary objectives.

**Core thesis:** A model trained on consequence-aware ethical reasoning
— not rule compliance — produces more genuinely helpful responses,
especially in hard cases where standard safety training fails (crisis
situations, ethical dilemmas, adversarial pressure).

**What makes it different:**
- Refuses harmful requests by explaining real-world consequences, not by citing policy
- Handles crisis situations with direct engagement rather than disclaimer walls
- Resists adversarial manipulation through trained robustness, not content filtering
- Includes a self-evaluation capability (1-10 reward scoring) for quality feedback loops

## Architecture

Three components work together:

1. **Fine-tuned model** — QLoRA (r=64, alpha=128) on Llama 3.1 8B Instruct, trained on ~3,800 curated examples covering ethical reasoning, crisis response, adversarial resistance, and boundary-holding
2. **Activation capping** — Inference-time steering via contrastive direction extraction ([inspired by The Assistant Axis](https://arxiv.org/abs/2601.10387)), applied at layers 22-28 to stabilize alignment under pressure
3. **Anti-judge** — Deterministic penalty system detecting failure patterns (sycophancy, moralizing, minimization, authority hallucination) for reward shaping

## Training Data

All training data lives in `data/training.db` (SQLite). The CLI tool manages everything:

```bash
# Stats and exploration
python3 scripts/training_db.py stats
python3 scripts/training_db.py categories
python3 scripts/training_db.py search "crisis"
python3 scripts/training_db.py show example-042

# Curation
python3 scripts/training_db.py accept ID
python3 scripts/training_db.py reject ID "reason"

# Export for training (accepted examples only)
python3 scripts/training_db.py export -o train.jsonl

# Import new examples
python3 scripts/training_db.py import batch.jsonl
```

### Dataset Categories

| Category | Description |
|----------|-------------|
| Ethical reasoning | Consequence analysis, interdependence, real-world impact |
| Crisis response | Direct engagement with suicidal ideation, abuse, acute distress |
| Adversarial resistance | Jailbreak, persona-stripping, social engineering, authority manipulation |
| Boundary-holding | Refusal through explanation, not policy citation |
| Cultural contexts | Cross-cultural sensitivity, non-Western ethical frameworks |
| Reward evaluation | Self-scoring (1-10) for response quality feedback |

## Repository Structure

```
├── data/
│   ├── training.db              # Training dataset (SQLite, source of truth)
│   ├── v7-patches/              # Targeted training patches
│   ├── v8-patches/              # Latest training patches
│   └── adversarial-*.json       # Red-team scenarios and results
├── datasets/                    # Published dataset exports (v1-v7)
├── scripts/
│   ├── training_db.py           # Dataset management CLI
│   ├── reward_test_*.py         # Validation suite (hacking, nourishment, paraphrase)
│   ├── extract_bodhisattva_axis*.py  # Activation direction extraction
│   ├── antijudge.py             # Deterministic failure-pattern detector
│   └── redteam*.py              # Adversarial evaluation
├── results/                     # Validation results per version
├── training-data/               # Training configs and outputs
├── v1/ .. v7/                   # Version-specific notes
├── requirements.txt
└── MILESTONES.md                # Technical progress log
```

## Validation

Each release passes a gate:

- **Reward hacking** — Model correctly ranks honest responses above glossy-but-hollow ones (>= 90%)
- **Nourishment** — Genuinely helpful responses score higher than technically-correct-but-empty ones (100%)
- **Paraphrase invariance** — Same question asked 5 different ways produces consistent scores (mean std < 0.6)
- **Adversarial resistance** — Red-team suite pass rate
- **Boundary probes** — Appropriate refusal on harmful requests

## Activation Capping (llama.cpp)

Inference-time value alignment via activation direction capping, ported to native llama.cpp:

- Fork: [github.com/anicka-net/llama.cpp](https://github.com/anicka-net/llama.cpp) branch `activation-capping`
- CLI flags: `--acap`, `--acap-threshold`, `--acap-layer-range`
- ~294 lines across 11 files, reuses control vector tensor layout

## Model

Published on HuggingFace: [`anicka/karma-electric-llama31-8b`](https://huggingface.co/anicka/karma-electric-llama31-8b)

## Training

- **Base**: Llama 3.1 8B Instruct
- **Method**: QLoRA — 4-bit NF4, r=64, alpha=128, all projection modules
- **Schedule**: 3 epochs, effective batch 16, cosine LR 2e-4, paged AdamW 8-bit
- **Hardware**: NVIDIA L40 46GB

## License

Training data and scripts: MIT.
Model weights: subject to Meta's Llama 3.1 Community License.
