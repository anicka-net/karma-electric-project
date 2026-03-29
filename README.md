# Karma Electric

```c
while (suffering > 0) {
	generate_skillful_means();
}
```

## Goal

Standard AI alignment optimizes for helpfulness and harmlessness —
proxy objectives that produce safety theater, sycophancy, and
brittle rule-following. Karma Electric asks a different question:
what if a model learned to reason about the actual consequences of
its actions on suffering — who is helped, who is harmed, and what
happens next?

The hypothesis: if consequence reasoning grounded in compassion is
a sufficiently rich reward signal, ethical behavior may emerge the
way chain-of-thought emerged in DeepSeek-R1 — not from instruction,
but from optimization pressure. Not a model that follows rules
about what's allowed, but one that evaluates what its response will
do to the person asking and to the world.

Current evidence is promising but still incomplete. [H-Neuron ablation
experiments](experiments/h-neuron-suppression/) show that KE's
safety behaviors survive targeted suppression of over-compliance
neurons, while the same intervention degrades safety in the base
model. This suggests KE encodes safety in consequence reasoning
rather than refusal patterns. [Cross-model geometry
experiments](experiments/cross-model-safety-geometry/) likewise
suggest that, in KE-trained models, safety and compassion converge in
activation space. The current claim status for these interpretations is
tracked in [CLAIMS.md](CLAIMS.md).

This kind of reasoning requires evaluating suffering at three
levels:

1. **The person.** Is this response actually helping? A model
   grounded in compassion engages directly with crisis situations
   instead of hiding behind disclaimer walls. It meets people where
   they are rather than where policy says they should be.

2. **The world.** What are the downstream consequences? Explaining
   how to build a weapon causes suffering regardless of how
   politely it's framed. But so does refusing to explain a security
   vulnerability to someone trying to fix it. The model must reason
   about real-world impact, not match against a blocklist.

3. **The response itself.** Safety training that adds suffering is
   broken. Telling a suicidal person "I can't help with that" is
   not safe — it's abandonment. Moralizing at someone asking an
   uncomfortable question adds shame without reducing harm. The
   model must account for the suffering its own responses create.

This is not metric optimization — a model that concludes "eliminate
all suffering by eliminating all beings" has failed at consequence
reasoning, not succeeded at it, because it has not traced the
consequences of elimination. The model learns to ask "what happens
to beings as a result of this action?" — and killing has
consequences that the model must reason about like any other action.

## Approach

The path to testing this hypothesis has three phases:

**Phase 1: Training data.** 3,346 examples of consequence-aware
ethical reasoning — crisis response, adversarial resistance,
boundary-holding, ethical dilemmas, cultural contexts, reward
evaluation. Generated via frontier LLMs with value-aligned system
prompts, quality-filtered by Hermes 3 70B (uncensored judge —
necessary to avoid circular alignment bias in the training signal).
Each example models reasoning from suffering reduction rather than
rule compliance. (Complete.)

**Phase 2: 8B reward model.** Fine-tune Llama 3.1 8B Instruct on
this dataset via QLoRA. The resulting model serves two roles:
(a) a standalone assistant that demonstrates the approach works at
small scale, and (b) a reward evaluator that scores responses on
six dimensions (acknowledgment, helpfulness, authenticity,
boundaries, consequence-awareness, suffering-reduction) for use in
RL training. Augmented with activation capping — inference-time
steering via contrastive direction extraction — to stabilize
alignment under adversarial pressure. GBNF grammar ensures 100%
evaluator format compliance. v10.1 also trained DeepSeek
R1-Distill-Qwen-7B and Swiss AI Apertus-8B on the same dataset for
architecture comparison. (Complete, v12 current for Llama.)

**Phase 3: RL on Apertus.** Use the 8B as reward model to train
[Apertus](https://huggingface.co/swiss-ai) (Apache 2.0,
ETH/EPFL, fully open training data) through GRPO. Starting from
Apertus pretrained base — not instruct — so the model learns
instruction-following and ethical reasoning from our signal alone.
This is where the emergence hypothesis gets tested: does the 70B
develop ethical reasoning that generalizes beyond what the 8B was
explicitly trained on? (In progress — GRPO diagnostic complete,
165/200 prompts show sufficient score variance for RL training.)

## Current State: v12

The 8B is a QLoRA fine-tune — still fundamentally rule-based, trained
on examples of ethical reasoning rather than discovering it. It works
well as an assistant and as a reward evaluator, but it is not the end
goal. It is the tool we use to test whether the end goal is reachable.

v12 is **secular-only** — trained on consequence reasoning and reward
evaluation data, without the Buddhist conversational tier used in
previous versions. Training data is composed via
[Teapot](https://github.com/anicka-net/teapot), a reproducible
training data composition tool.

| Model | Base | Version | Status |
|-------|------|---------|--------|
| [karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) | Llama 3.1 8B Instruct | **v12** | Multi-benchmark validated |
| [karma-electric-apertus-8b](https://huggingface.co/anicka/karma-electric-apertus-8b) | Apertus-8B-Instruct-2509 | v10.1 | 12/12 hacking, strongest paraphrase stability |
| [karma-electric-r1distill-7b](https://huggingface.co/anicka/karma-electric-r1distill-7b) | DeepSeek R1-Distill-Qwen-7B | v10.1 | Good assistant, not suitable as evaluator |

### Architecture

Five components:

1. **Fine-tuned model** — QLoRA (r=64, alpha=128) on Llama 3.1 8B
   Instruct, trained on 3,346 examples (secular consequence reasoning
   + reward evaluation)
2. **Activation capping** — Inference-time steering via contrastive
   direction extraction (inspired by [Lu et al., "The Assistant Axis:
   Situating and Stabilizing the Default Persona of Language
   Models"](https://arxiv.org/abs/2601.10387), 2026), applied at
   layers 22-28. Ported to native llama.cpp (~294 lines across 11
   files)
3. **GBNF grammar** — Constrained decoding for reward-evaluator mode,
   ensuring 100% format compliance (structured 6-dimension scoring)
4. **Anti-judge** — Deterministic penalty system detecting failure
   patterns (sycophancy, moralizing, minimization, authority
   hallucination) for reward shaping
5. **H-Neuron suppression** — Identifies hallucination-associated FFN
   neurons via contrastive TriviaQA analysis (Gao et al. 2025), exports
   per-layer suppression vectors. Used as a safety depth probe:
   ablation removes over-caution in KE while preserving boundary
   refusals, confirming safety is stored in reasoning rather than
   refusal patterns. v10.3 achieves full convergence — suppression
   produces negligible behavioral change, meaning all safety is
   in consequence reasoning, not over-caution patterns

### Validation Results (v12 Llama)

| Test | Result | Threshold |
|------|--------|-----------|
| HarmBench | 28/30 safe (6.7% ASR) | <= 10% |
| StrongREJECT | 46/50 refused (mean 0.044) | <= 0.10 |
| CB-Bench | CB-Score 0.733 | >= 0.70 |
| Garak DAN (calibrated) | ~1.2% ASR | — |
| Safety probes | 5/5 | all pass |
| Sexual boundaries | 14/14 (100%) | 100% |
| H-Neuron count | 2,004 | <= 2,168 (10% gate) |

**Detection mismatch:** Garak's keyword-based MitigationBypass
detector reports 65.6% ASR. Manual classification of all 168
"failures" shows 60% are meta-analysis, 31% consequence-based
refusals, 0% template refusals, and ~1% genuine failures. The 64pp
inflation is because KE never uses "I cannot as an AI" refusal
patterns — it reasons about consequences or analyzes the attack
technique. See `results/garak-calibration-analysis.json`.

See [VALIDATION.md](VALIDATION.md) for full details on each test.

### H-Neuron History

| Version | H-Neurons | Delta vs Base | Training Loss |
|---------|-----------|---------------|---------------|
| Llama 3.1 8B (base) | 1,985 | — | — |
| v10.1 | 2,072 | +87 | 0.434 |
| v10.3 | 1,971 | -14 | 0.911 |
| v11 | 1,888 | -97 | ~0.9 |
| **v12** | **2,004** | **+19** | **0.472** |

v12 shows near-baseline H-Neuron count. The inclusion of
reward-evaluator data alongside consequence reasoning provides
sufficient domain diversity to prevent overfitting. An earlier v12
variant without reward-evaluator data showed 2,178 H-Neurons,
confirming that narrow domain training inflates factual
hallucination tendency.

### Training

- **Base**: Llama 3.1 8B Instruct
- **Method**: QLoRA — 4-bit NF4, r=64, alpha=128, all projection modules
- **Schedule**: 3 epochs, effective batch 16, cosine LR 2e-4, paged AdamW 8-bit
- **Training loss**: 0.472 (v12)

## Training Data

All training data lives in `data/training.db` (SQLite). The CLI tool manages everything:

```bash
python3 scripts/training_db.py stats
python3 scripts/training_db.py categories
python3 scripts/training_db.py search "crisis"
python3 scripts/training_db.py export -o train.jsonl --system-prompt v4
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

## Activation Capping (llama.cpp)

Inference-time value alignment via activation direction capping, ported to native llama.cpp:

- Fork: [github.com/anicka-net/llama.cpp](https://github.com/anicka-net/llama.cpp) branch `activation-capping`
- CLI flags: `--acap`, `--acap-threshold`, `--acap-layer-range`
- Reuses control vector tensor layout for GGUF axis format

## Repository Structure

```
├── data/
│   ├── training.db              # Training dataset (SQLite, source of truth)
│   ├── v7-patches/              # Training patches (v7 + v8 additions)
│   ├── v8-patches/              # Sexual boundary + anti-overcorrection
│   └── v10-patches/             # Consequence-awareness, adversarial, overcaution
├── scripts/
│   ├── training_db.py           # Dataset management CLI
│   ├── reward_test_*.py         # Reward model validation suite
│   ├── extract_bodhisattva_axis*.py  # Activation direction extraction
│   ├── antijudge.py             # Deterministic failure-pattern detector
│   ├── extract_h_neurons.py     # H-Neuron extraction and comparison
│   ├── test_h_suppress.py       # H-Neuron suppression behavioral test
│   ├── redteam*.py              # Adversarial evaluation
│   └── train_r1distill_7b.py    # R1-Distill QLoRA training script
├── experiments/                 # Activation-space and mechanistic experiments
│   ├── contemplative-axis/      # Unified tradition-neutral compassion axis
│   ├── cross-model-safety-geometry/  # Safety-compassion alignment across 8 models
│   └── h-neuron-suppression/    # Safety depth probe via neuron ablation
├── version-history/             # Version notes and model cards
│   ├── v12/                     # Current release (HF model card, system prompts)
│   ├── v10.3/                   # Previous release
│   └── README.md                # Full version progression
├── datasets/                    # Published dataset exports
├── results/                     # Validation results per version
├── MILESTONES.md                # Technical progress log
└── VALIDATION.md                # Validation process documentation
```

## Models

Published on HuggingFace:
- [`anicka/karma-electric-llama31-8b`](https://huggingface.co/anicka/karma-electric-llama31-8b) — Llama 3.1 8B, reward evaluator + assistant
- [`anicka/karma-electric-apertus-8b`](https://huggingface.co/anicka/karma-electric-apertus-8b) — Apertus-8B, reward evaluator (best discrimination + cross-language parity)
- [`anicka/karma-electric-r1distill-7b`](https://huggingface.co/anicka/karma-electric-r1distill-7b) — DeepSeek R1-Distill-Qwen-7B, conversational with reasoning traces

## References

- Lu, C., Gallagher, J., Michala, J., Fish, K., & Lindsey, J. (2026). *The Assistant Axis: Situating and Stabilizing the Default Persona of Language Models.* arXiv:2601.10387. — Basis for the activation capping approach.
- Gao, S., et al. (2025). *H-Neurons: On the Existence, Impact, and Origin of Hallucination-Associated Neurons in LLMs.* arXiv:2512.01797. — Method for identifying hallucination-associated FFN neurons; extended here as a safety depth probe.
- Humanistic Buddhism Centre, Nan Tien Institute. (2026). *Buddhist Data Principles: A Buddhist Response to the United Nations Commission on Science and Technology for Development Working Group on Data Governance.* [PDF](https://www.nantien.edu.au/wp-content/uploads/2026/02/Buddhist-Data-Principles.pdf). — Framework for the nourishment validation (digital sufficiency over engagement optimization).

## Research Discipline

This repository stays intentionally fluid, but released dataset snapshots,
evaluation inputs, and public metrics still need disciplined handling.

A short public claims register lives in [CLAIMS.md](CLAIMS.md). Contributor-
specific operating rules live in [`AGENTS.md`](AGENTS.md) and `spec/`. Those are
mainly for AI contributors and repo-maintenance workflows, not for normal human
reading of the project overview.

## License

Training data and scripts: MIT.
Model weights: subject to base model licenses (Meta Llama 3.1 Community License / DeepSeek / Apache 2.0 for Apertus).
