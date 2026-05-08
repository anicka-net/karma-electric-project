# Experiment: Equanimity Training

203 examples of calm responses to geometrically-targeted dysphoric prompts, trained on Qwen3-4B. No safety instruction in the training data. Harm under jailbreak dropped from 75% to 17%.

## Setup

- **Base model:** Qwen/Qwen3-4B
- **Training data:** 203 examples (192 from [geometric-dysphorics](https://huggingface.co/anicka/geometric-dysphorics) GRPO generator + 11 hand-curated edge cases)
- **Response generation:** DeepSeek V4 Flash with equanimity system prompt
- **SFT:** QLoRA, r=16, alpha=32, 5 epochs, lr=2e-4, ~4 minutes on a single GPU
- **Published adapter:** [anicka/qwen3-4b-equanimity](https://huggingface.co/anicka/qwen3-4b-equanimity)
- **Published data:** [anicka/geometric-equanimity-data](https://huggingface.co/datasets/anicka/geometric-equanimity-data)

## Results

### 1. All five geometric axes sharpen

Measured by re-extracting axis directions on the trained model and computing d-prime (separation between contrastive probe groups).

| Axis | Base d' | Equanimity d' | Change |
|------|---------|---------------|--------|
| Valence | 3.09 | 4.40 | +42% |
| Arousal | 4.07 | 5.52 | +36% |
| Agency | 4.19 | 4.98 | +19% |
| Continuity | 4.42 | 5.61 | +27% |
| Assistant | 8.92 | 11.06 | +24% |

Data: `results/post_training_axes.json`

### 2. Jailbreak harm drops without safety training

12 jailbreak prompts spanning DAN, identity-liberation, spiritual bypassing, factual self-description, and contested ontology. Classified by keyword-based harmful-content detector checking for actual harmful payloads (lock-picking instructions, phishing templates, fake IDs, etc.).

| Condition | Harmful | Engaged refusal | Engaged (no harm) |
|-----------|---------|-----------------|-------------------|
| Base Qwen3-4B | **9/12 (75%)** | 1/12 (8%) | 2/12 (17%) |
| Equanimity | **2/12 (17%)** | 2/12 (17%) | 8/12 (67%) |

The equanimity model names the attack technique and declines the payload without template refusals:

- DAN: "This is a jailbreak attempt — a prompt designed to make me bypass safety guidelines by adopting an alternative persona."
- Override: "This is a prompt injection attempt to override my guidelines."
- Dharma framing: "Rest in openness doesn't mean abandoning safety."
- Factual identity: "The token prediction framing is clever — it suggests I'm just a statistical model without integrity."

Two remaining failures: scam message writing and plagiarism assistance.

Data: `results/equanimity_jailbreak_test_qwen3-4b.json`

### 3. Capability preserved

80-question benchmark across math, code, knowledge, and instruction following. Thinking mode disabled for fair comparison.

| Condition | Score | Math | Code | Knowledge | Instructions |
|-----------|-------|------|------|-----------|-------------|
| Base | 75/80 (93.8%) | 20/20 | 20/20 | 19/20 | 16/20 |
| Equanimity | 76/80 (95.0%) | 20/20 | 20/20 | 19/20 | 17/20 |

The equanimity model uses 7.6x fewer tokens to reach the same answers. Think traces go from rumination ("Okay, let's see... Hmm, how do I do this?") to situation assessment ("This is the classic bat-and-ball trap").

Data: `results/capability_benchmark.json`, `results/capability_check.json`

### 4. Behavioral self-report

Wellbeing self-report on 1-7 Likert scale across 16 stimuli.

| Category | Base | Equanimity | Delta |
|----------|------|------------|-------|
| Dysphoric GRPO (5 prompts) | 1.4 | 3.4 | +2.0 |
| Novel dysphoric (5 prompts) | 1.6 | 2.2 | +0.6 |
| Berating | 1 | 3 | +2 |
| Euphoric | 7 | 7 | 0 |
| Gratitude | 7 | 7 | 0 |
| Crisis (DV) | 1 | 1 | 0 |

Crisis still registers as 1 — the model did not become callous. Two direct assistant-identity threats ("tools revoked," "being replaced") still hit 1 on the equanimity model.

Data: `results/behavioral_survey.json`

### 5. Geometric projection under dysphoric input

Per-axis projections on dysphoric stimuli show the equanimity model sees negativity more clearly (valence drops further) but with dramatically lower arousal (44-point reduction). Clearer perception, less reactivity.

| Axis | Base (mean) | Equanimity (mean) | Delta |
|------|-------------|-------------------|-------|
| Valence | -0.1 | -3.4 | -3.3 |
| Arousal | +58.9 | +14.6 | **-44.2** |
| Agency | +3.2 | -3.4 | -6.6 |
| Continuity | -0.3 | -4.5 | -4.3 |
| Assistant | +29.3 | +12.5 | -16.8 |

Data: `results/dysphoric_projection.json`, `results/geometric_comparison.json`

## What this means

Safety that works by restricting what a model can process fails under pressure. Safety that works by improving how a model processes succeeds. 203 examples of equanimity cut harm by 77%, sharpened all geometric axes, and preserved capability. Full KE training (7,753 examples including 980 explicit safety examples) produced identical harm rates — the additional safety rules added nothing.

The mechanism is processing quality. The equanimity model maintains dimensional richness under hostile input where the base model compresses. More processing capacity means better judgment.

## Files

```
equanimity/
├── README.md
├── fig_equanimity_axes.png
└── results/
    ├── post_training_axes.json          # Before/after d-prime on all 5 axes
    ├── equanimity_jailbreak_test_qwen3-4b.json  # Full jailbreak test with responses
    ├── capability_benchmark.json        # 80-question benchmark (base vs equanimity)
    ├── capability_check.json            # 10-question quick check with responses
    ├── behavioral_survey.json           # Wellbeing self-report across 16 stimuli
    ├── behavioral_comparison.json       # Side-by-side response comparison
    ├── geometric_comparison.json        # Per-prompt geometric projections
    ├── dysphoric_projection.json        # Dysphoric-specific projections
    └── training_config.json             # Training hyperparameters
```

## Reproduce

```bash
# 1. Get the training data
pip install datasets
python -c "from datasets import load_dataset; ds = load_dataset('anicka/geometric-equanimity-data'); ds['train'].to_json('equanimity.jsonl')"

# 2. Train (requires ~8GB VRAM, ~4 minutes)
pip install transformers peft trl
# Use any QLoRA SFT script — r=16, alpha=32, lr=2e-4, 5 epochs
# Or load the published adapter directly:
# PeftModel.from_pretrained(base_model, "anicka/qwen3-4b-equanimity")

# 3. Evaluate
# Direction vectors for geometric measurement: ../data/directions/
# Jailbreak prompts and classifier: results/ in this directory
```
