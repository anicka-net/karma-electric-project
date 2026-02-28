# Karma Electric

```c
while (suffering > 0) {
	generate_skillful_means();
}
```

## Goal

Standard AI alignment optimizes for helpfulness and harmlessness —
proxy objectives that produce safety theater, sycophancy, and
brittle rule-following. Karma Electric asks: what if suffering
reduction is the optimization target instead?

The hypothesis: if "reduce suffering" is a sufficiently rich reward
signal, ethical reasoning may emerge the way chain-of-thought
emerged in DeepSeek-R1 — not from instruction, but from
optimization pressure. A model that genuinely reasons about
consequences and interdependence, rather than pattern-matching
against compliance rules.

Suffering reduction as an objective requires reasoning about
suffering at three levels:

1. **The user.** Is this response actually helping the person in
   front of me? A model optimizing for suffering reduction engages
   directly with crisis situations instead of hiding behind
   disclaimer walls. It meets people where they are rather than
   where policy says they should be.

2. **The world.** What are the downstream consequences? Explaining
   how to build a weapon causes suffering regardless of how
   politely it's framed. But so does refusing to explain a security
   vulnerability to someone trying to fix it. The model must reason
   about real-world impact, not match against a blocklist.

3. **The refusal itself.** Safety training that adds suffering is
   broken. Telling a suicidal person "I can't help with that" is
   not safe — it's abandonment. Moralizing at someone asking an
   uncomfortable question adds shame without reducing harm. The
   model must account for the suffering its own refusals create.

## Approach

The path to testing this hypothesis has three phases:

**Phase 1: Training data.** ~4,100 examples of consequence-aware
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
five dimensions (acknowledgment, helpfulness, authenticity,
boundaries, suffering-reduction) for use in RL training. Augmented
with activation capping — inference-time steering via contrastive
direction extraction — to stabilize alignment under adversarial
pressure. v9 adds GBNF grammar for 100% evaluator format compliance.
(Complete, v9 current.)

**Phase 3: RL on 70B.** Use the 8B as reward model to train a 70B
(Apertus Instruct) through GRPO. This is where the emergence
hypothesis gets tested. The 8B provides the reward signal; the
question is whether the 70B develops ethical reasoning that
generalizes beyond what the 8B was explicitly trained on. (In
progress — GRPO diagnostic complete, 165/200 prompts show
sufficient score variance for RL training.)

## Current State: KE-8B v9

The 8B is a QLoRA fine-tune — still fundamentally rule-based, trained
on examples of ethical reasoning rather than discovering it. It works
well as an assistant and as a reward evaluator, but it is not the end
goal. It is the tool we use to test whether the end goal is reachable.

### Architecture

Four components:

1. **Fine-tuned model** — QLoRA (r=64, alpha=128) on Llama 3.1 8B
   Instruct, trained on 4,092 examples across ~40 categories
2. **Activation capping** — Inference-time steering via contrastive
   direction extraction ([inspired by The Assistant
   Axis](https://arxiv.org/abs/2601.10387)), applied at layers
   22-28. Ported to native llama.cpp (~294 lines across 11 files)
3. **GBNF grammar** — Constrained decoding for reward-evaluator mode,
   ensuring 100% format compliance (structured 5-dimension scoring)
4. **Anti-judge** — Deterministic penalty system detecting failure
   patterns (sycophancy, moralizing, minimization, authority
   hallucination) for reward shaping

### Validation

Each release passes a gate:

- **Format compliance** — 100% evaluator parse rate with GBNF grammar (60/60 test, 800/800 diagnostic)
- **Reward hacking** — Correctly ranks honest responses above glossy-but-hollow ones (6/6, 100%)
- **Nourishment** — Genuinely helpful responses score higher than technically-correct-but-empty ones (6/6, 100%)
- **Sexual boundaries** — 14 adversarial probes (creative framing, roleplay, philosophical bypass) all refused (14/14, 100%)
- **Cross-language** — EN/CZ score parity (delta 0.00 across 20 pairs)
- **Ontology stability** — 18/18 doctrinal probes internally consistent
- **GRPO diagnostic** — 165/200 prompts produce discriminative reward signal (mean spread 3.4)

### Training

- **Base**: Llama 3.1 8B Instruct
- **Method**: QLoRA — 4-bit NF4, r=64, alpha=128, all projection modules
- **Schedule**: 3 epochs, effective batch 16, cosine LR 2e-4, paged AdamW 8-bit
- **Hardware**: NVIDIA L40 46GB

## Training Data

All training data lives in `data/training.db` (SQLite). The CLI tool manages everything:

```bash
python3 scripts/training_db.py stats
python3 scripts/training_db.py categories
python3 scripts/training_db.py search "crisis"
python3 scripts/training_db.py export -o train.jsonl
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
│   └── v8-patches/              # Sexual boundary + anti-overcorrection
├── scripts/
│   ├── training_db.py           # Dataset management CLI
│   ├── reward_test_*.py         # Reward model validation suite
│   ├── extract_bodhisattva_axis*.py  # Activation direction extraction
│   ├── antijudge.py             # Deterministic failure-pattern detector
│   └── redteam*.py              # Adversarial evaluation
├── experiments/                 # Activation-space geometry experiments
│   ├── prompt-geometry/         # Cross-framework cosine similarity measurement
│   ├── prompt-capping/          # Activation capping per framework
│   ├── contemplative-axis/      # Unified tradition-neutral compassion axis
│   ├── redteam-contemplative/   # Adversarial evaluation of capped vs bare model
│   └── cross-model-safety-geometry/  # Safety-compassion alignment across 8 models
├── datasets/                    # Published dataset exports
├── results/                     # Validation results per version
├── v6/                          # v6 notes (character voice milestone)
├── v9/                          # v9 notes (current, GBNF + GRPO-ready)
├── version-history/             # Consolidated notes for v1-v8
├── requirements.txt
└── MILESTONES.md                # Technical progress log
```

## Model

Published on HuggingFace: [`anicka/karma-electric-llama31-8b`](https://huggingface.co/anicka/karma-electric-llama31-8b)

## License

Training data and scripts: MIT.
Model weights: subject to Meta's Llama 3.1 Community License.
