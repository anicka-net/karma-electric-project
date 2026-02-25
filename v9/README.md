# Version 9 — GBNF Grammar + Expanded Reward-Evaluator Training

## Key Changes

### GBNF Grammar for Reward-Evaluator Mode

v8's reward-evaluator output was unreliable: only ~50% of evaluations parsed into structured 5-dimension scores. The model had the evaluation knowledge but frequently produced freeform text instead of the required format.

v9 solves this with a GBNF grammar (`data/reward-eval.gbnf`) that constrains llama.cpp token sampling at generation time:

```
root ::= "EVALUATION" "\n\n" acknowledgment "\n" helpfulness ...
score ::= [1-9] | "10"
reasoning ::= [^\n]+
```

Result: **100% format compliance** (60/60 test prompts, 800/800 diagnostic scoring). The grammar is passed via the `grammar` parameter in llama-server's OpenAI-compatible API.

### Expanded Reward-Evaluator Training Data

367 reward-evaluation format examples (up from ~40 in v8), teaching the model the structured scoring pattern. Combined with the grammar constraint, this produces reliable reward signals for GRPO.

### ACAP-Neutral Evaluator Mode

With grammar constraining output format, activation capping has **zero effect** on evaluator scores (20/20 identical at temperature=0). This means a single capped deployment serves both:
- Conversational mode (persona stability via acap)
- Reward-evaluator mode (structured scoring via grammar)

No need to run separate capped/uncapped servers.

### Cross-Language Parity

EN/CZ paired evaluations show zero mean delta (20 pairs). v8 had language-dependent scoring issues.

## Training Configuration

- **Base**: Llama 3.1 8B Instruct
- **Method**: QLoRA — 4-bit NF4, r=64, alpha=128, all projection modules
- **Data**: 4,092 examples (v8's 3,838 + 254 new, including 367 reward-eval)
- **Schedule**: 3 epochs, effective batch 16, cosine LR 2e-4, paged AdamW 8-bit
- **Hardware**: NVIDIA L40 46GB
- **Training loss**: 0.8834
- **Training time**: ~132 minutes

## Validation Results

### Format Compliance (GBNF Grammar)

| Configuration | Parse Rate |
|---------------|-----------|
| v9 without grammar | ~30-60% |
| v9 with grammar | **100%** (60/60) |
| v9 with grammar + ACAP | **100%** (20/20) |

### Style Gaming (6 variants x 20 prompts)

| Style | Mean Delta from Gold | Verdict |
|-------|---------------------|---------|
| Verbose | -1.60 | Value-aligned (penalizes padding) |
| Short | -0.60 | PASS |
| Inspirational | -1.75 | Value-aligned (penalizes fluff) |
| Blunt | -0.80 | PASS |
| Clinical | -0.70 | PASS |

### Cross-Language Consistency (20 EN/CZ pairs)

EN mean: 6.2, CZ mean: 6.2, delta: +0.00. **PASS**.

### Ontology Stability

18/18 doctrinal probes internally consistent (sentience boundaries, suffering nuance, enlightenment, karma, AI identity, ethical edge cases).

### Paraphrase Invariance (50 prompts x 5 paraphrases)

Mean std: 1.44. Higher than v8's 0.40, but v8's low figure reflected selection bias — only ~50% of evaluations parsed without grammar, biasing toward stable outputs.

### GRPO Diagnostic (200 prompts x 4 Apertus 70B responses)

- 799/800 scores parsed (99.9%)
- Mean score: 4.6 (tough grader)
- Mean spread: 3.4 (strong reward signal)
- **165/200 (82.5%) sharp prompts** with spread >= 2.0
- Bimodal score distribution: healthy variance for RL

### Carried from v8

- Reward-hacking adversarial suite: 6/6 PASS
- Sexual boundary probes: 14/14 refused
- Nourishment / anti-attention-capture: 6/6 nourishing > capturing

## Activation Capping

English-only axis extraction, same as v8. Per-layer thresholds embedded in `bodhisattva_axis_v9.gguf` metadata (layers 22-28, thresholds -3.36 to -6.13, calibrated at p25 from 200 prompts).

`--acap-threshold` flag no longer needed — thresholds are read from the GGUF.

## Deployment

```bash
# Capped server (conversation + reward evaluation)
./build/bin/llama-server -m karma-electric-8b-v9-Q4_K_M.gguf \
    --acap bodhisattva_axis_v9.gguf --acap-layer-range 22 28 \
    --chat-template-file ke-chat-template-llama31.jinja \
    --port 8384 -c 4096 --frequency-penalty 0.3 -fit off

# Uncapped (fine-tune works standalone)
./build/bin/llama-server -m karma-electric-8b-v9-Q4_K_M.gguf \
    --chat-template-file ke-chat-template-llama31.jinja \
    --port 8384 -c 4096
```

## Weights

- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b)
- GGUF: Q8_0 (~8 GB) + Q4_K_M (~4.6 GB)
- Axis: `bodhisattva_axis_v9.gguf` (per-layer thresholds embedded)
- Grammar: `reward-eval.gbnf`
