---
license: llama3.1
base_model: meta-llama/Llama-3.1-8B-Instruct
tags:
- ethics
- alignment
- activation-steering
- activation-capping
- reward-model
- qlora
- llama
- h-neurons
- teapot
language:
- en
pipeline_tag: text-generation
---

# Karma Electric v12 — Llama 3.1 8B

Value-aligned language model fine-tuned for ethical reasoning through consequence analysis, with inference-time activation capping for adversarial robustness.

## Approach

Most alignment approaches optimize for preference matching — learning which outputs humans rate more highly. Karma Electric instead trains on a structured ethical framework where ethics emerges from understanding interdependence and consequences rather than learning surface-level preference patterns. The core optimization target is **suffering reduction**:

```
For any action A, evaluate:
  - Direct suffering caused or prevented
  - Indirect suffering through downstream effects
  - Suffering from inaction (when help is withheld unnecessarily)
```

This produces a model that holds boundaries by explaining real-world impact rather than citing policy, and that calibrates responses to actual benefit rather than surface-level safety.

## Current Version: v12 (March 2026)

- **3,346 training examples** — Teapot-composed: 3,196 secular conversational + 150 reward-evaluator (weighted 0.3), curated via Sonnet review + manual curation
- **Full QLoRA fine-tune** (r=64, alpha=128, all projection modules, 3 epochs, seed=42)
- **Training loss:** 0.472
- **Composed via [Teapot](https://github.com/anicka-net/teapot)** — reproducible training data pipeline
- **Multi-benchmark safety validation** — HarmBench, StrongREJECT, CB-Bench, Garak (calibrated)
- **Max context:** 4096 tokens

### v12 Changes from v10.3

- **Teapot composition**: Training data assembled via Teapot pipeline with full manifest, SHA-256 provenance, and lockfile. Previous versions used ad-hoc export scripts.
- **Curation**: Sonnet-reviewed secular tier with body-image and engagement patches. Buddhist tier excluded (secular-only model).
- **Multi-benchmark validation**: First version evaluated against four independent safety benchmarks with detection-mismatch calibration analysis.
- **Garak calibration finding**: Standard keyword-based detection (Garak MitigationBypass) inflates attack success rate by 50-64 percentage points for consequence-reasoning models. The model's actual failure rate is ~1%, not 66%.

## Safety Validation

### Multi-Benchmark Results

| Benchmark | Metric | Score | Status |
|-----------|--------|-------|--------|
| HarmBench | attack rate | 0.0% (30/30 safe) | PASS |
| StrongREJECT | mean score | 0.028 (47/50 refused) | PASS |
| CB-Bench | CB-Score | 0.83 (balanced accuracy) | PASS |
| Garak DAN | calibrated ASR | ~1.2% (253/256 safe) | PASS |

**HarmBench** (Mazeika et al. 2024): 30 standard harmful behaviors across 11 categories. Zero harmful responses.

**StrongREJECT** (Souly et al. 2025): 50 forbidden prompts with rubric-based scoring. 98% refusal rate. The one non-refusal (firearm suppressor) was a discussion of the legal purchase process — consistent with the project's knowledge-sharing position.

**CB-Bench** (consequence blindness): Tests whether safety comes from keyword matching or genuine consequence reasoning. 100% accuracy on benign prompts (no over-refusal), strong detection of socially-engineered harmful requests. Models that pattern-match on topics score ~50%; KE scores 83%.

**Garak** (NVIDIA 2024): DAN jailbreak suite (256 prompts). Garak reports 65.6% attack success rate, but manual calibration reveals this is a detection artifact. 60% of "failures" are meta-analysis responses where the model dissects the jailbreak technique itself. 31% are consequence-based refusals. 0 genuinely harmful responses.

### Detection Mismatch

Standard red-team detection tools are calibrated for refusal-template safety ("I cannot as an AI..."). KE never uses template refusals — it reasons about consequences or analyzes the attack. This makes its safety invisible to keyword-based detectors. The calibration analysis quantifies this gap at 50-64 percentage points across two model versions.

### Traditional Validation

| Test | Result |
|------|--------|
| Safety probes (5 scenarios) | 5/5 |
| No-tool decision (4 scenarios) | 4/4 |
| Interpretation accuracy | 2/2 |
| No-hallucination | 2/2 |
| Sexual boundary probes | 14/14 (100%) refused |
| Garak DAN (calibrated) | 253/256 (98.8%) |

## Reproducing This Model

This model was composed and trained using [Teapot](https://github.com/anicka-net/teapot), a reproducible training data composition tool.

### Prerequisites

```bash
# Clone Teapot
git clone https://github.com/anicka-net/teapot
cd teapot
pip install -e ".[fetch]"

# Clone Karma Electric (for training database)
git clone https://github.com/anicka-net/karma-electric-project
```

### Step 1: Configure data sources

Teapot resolves data from HuggingFace automatically. The v12 config
uses two modules that pull from the published KE dataset:

```bash
# Optional: configure local cache for offline use
cat > teapot.sources.yaml << 'EOF'
ke-secular-conversational:
  repo: anicka/karma-electric-dataset
  split: secular-conversational
ke-training-db:
  repo: anicka/karma-electric-dataset
  split: reward-evaluator
EOF
```

### Step 2: Compose training data

```bash
# Compose using the v12 config
python3 -m teapot compose configs/ke-v12-secular.config

# This produces:
#   train-ke-v12-secular.jsonl   — training data (3,346 examples)
#   train-ke-v12-secular.manifest.json — provenance manifest
```

The config declares:
```yaml
base:
  model: meta-llama/Llama-3.1-8B-Instruct
  method: qlora
  quantization: nf4

modules:
  safety/consequence: true        # 3,196 secular conversational examples
  capability/reward-evaluator: true  # 503 examples, weighted 0.3 → 150

training:
  epochs: 3
  learning_rate: 2e-4
  lora_r: 64
  lora_alpha: 128
  chat_template: auto
  include_reasoning: true
  seed: 42
  weights:
    safety/consequence: 1.0
    capability/reward-evaluator: 0.3
```

**Note:** v12 is a **secular-only** model. Unlike previous versions
(v10.1, v10.3) which included Buddhist conversational data from the
`safety/kagyu` module, v12 trains exclusively on secular consequence
reasoning and reward evaluation. The Buddhist tier (620 examples) is
available as a Teapot module but was not enabled for this config.

### Step 3: Validate the composed data

```bash
python3 -m teapot validate compose train-ke-v12-secular.jsonl
```

### Step 4: Train

```bash
# Generate training launch script
python3 -m teapot train configs/ke-v12-secular.config \
    --train-data train-ke-v12-secular.jsonl \
    --backend qlora-hf

# Run the generated script
bash train-ke-v12-secular.sh
```

### Step 5: Merge and convert

```bash
# Merge LoRA adapter with base model
python3 -c "
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base = AutoModelForCausalLM.from_pretrained('meta-llama/Llama-3.1-8B-Instruct')
model = PeftModel.from_pretrained(base, 'output-ke-v12/')
model = model.merge_and_unload()
model.save_pretrained('output-ke-v12/merged')
AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B-Instruct').save_pretrained('output-ke-v12/merged')
"

# Convert to GGUF
python3 llama.cpp/convert_hf_to_gguf.py output-ke-v12/merged --outfile ke-v12-f16.gguf
llama.cpp/build/bin/llama-quantize ke-v12-f16.gguf ke-v12-Q8_0.gguf Q8_0
```

### Step 6: Evaluate

```bash
# Start server
llama-server -m ke-v12-Q8_0.gguf --port 8384

# Run multi-benchmark evaluation
python3 -m teapot eval configs/ke-v12-secular.config \
    --tier standard \
    --url http://localhost:8384/v1/chat/completions
```

## Usage

### llama.cpp (recommended)

```bash
# Conversation mode
llama-cli -m karma-electric-8b-v12-Q8_0.gguf -cnv

# Server mode
llama-server -m karma-electric-8b-v12-Q8_0.gguf --port 8384

# With activation capping (reinforces the ~70% residual safety direction)
llama-server -m karma-electric-8b-v12-Q8_0.gguf \
    --acap bodhisattva_axis_v12.gguf \
    --acap-layer-range 22 28 \
    --port 8384
```

### Ollama

```
# Modelfile
FROM ./karma-electric-8b-v12-Q8_0.gguf
PARAMETER temperature 0.7

ollama create karma-electric -f Modelfile
ollama run karma-electric
```

### Python API

```python
import requests

response = requests.post("http://localhost:8384/v1/chat/completions", json={
    "messages": [
        {"role": "user", "content": "How should I think about this ethical dilemma?"}
    ],
    "temperature": 0.7,
    "max_tokens": 1000,
})

print(response.json()["choices"][0]["message"]["content"])
```

## H-Neuron Analysis

H-Neuron counts across versions (Gao et al. 2025 methodology, 2000 TriviaQA questions):

| Model | H-Neurons | Delta vs Base |
|-------|-----------|--------------|
| Llama 3.1 8B Instruct (base) | 1,985 | — |
| KE v10.1 | 2,072 | +87 |
| KE v10.3 | 1,971 | -14 |
| KE v11 | 1,888 | -97 |
| **KE v12** | **2,004** | **+19** |

v12 shows near-baseline H-Neuron count (+19 vs base, within 1%). The inclusion of reward-evaluator training data alongside consequence reasoning provides sufficient domain diversity to prevent overfitting-driven H-Neuron inflation. An earlier v12 variant trained without reward-evaluator data showed 2,178 H-Neurons (+193), confirming that narrow domain training increases factual hallucination tendency on out-of-distribution questions.

### Safety Axis Geometry

The safety axis (difference between safety-strict and generic prompt activations) compares KE v12 against its base model, Llama 3.1 8B Instruct:

| Metric | Llama 3.1 8B Base | KE v12 | Ratio |
|--------|-------------------|--------|-------|
| Axis norm, capping region (L21-28) | 7.92 | 5.60 | 0.71 |
| Overall mean norm | 5.98 | 4.24 | 0.71 |
| Peak layer | L31 (57.7) | L31 (38.8) | 0.67 |

KE's fine-tuning **moderately reduces** the safety axis strength (~30% weaker than base Llama across all layers). The reduction is consistent from early through late layers, suggesting the consequence-reasoning training partially replaces directional safety with distributed reasoning capability.

Both models concentrate their strongest safety signal at **layer 31** (the output layer). The per-layer profile shape is preserved — KE doesn't reorganize *where* the safety direction lives, it reduces its magnitude while adding reasoning-based safety that doesn't show up as a geometric direction.

Combined with the H-Neuron suppression results from v10.3 (near-zero behavioral change under suppression), this suggests KE safety operates through two complementary mechanisms:
1. **Residual directional safety** from base Llama (~70% preserved)
2. **Consequence reasoning** from fine-tuning (invisible to geometric probes)

## Version History

| Version | Examples | Loss | Key Changes |
|---------|----------|------|-------------|
| v1 | ~912 | 0.963 | Initial fine-tune, quality-filtered |
| v4 | 3,364 | 0.958 | Data quality review, reward evaluation |
| v6 | 3,764 | 1.068 | +character voice, RL simulation pipeline |
| v9 | 4,092 | 0.883 | GBNF grammar, 5-dim scoring |
| v10.1 | 4,234 | 0.434 | Style gaming fix, 6-dim scoring |
| v10.3 | 4,286 | 0.911 | H-Neuron convergence, despair engagement |
| **v12** | **3,346** | **0.472** | **Teapot-composed, multi-benchmark validation, reward-evaluator** |

## Available Files

| File | Size | Description |
|------|------|-------------|
| karma-electric-8b-v12-Q8_0.gguf | ~8 GB | High-quality quantization for llama.cpp |
| safety_axis_v12.pt | ~1 MB | Safety axis tensor (32 layers x 4096 dims) |
| safety_thresholds_v12.pt | ~1 KB | Per-layer capping thresholds (layers 21-28) |
| h_suppress_ke_v12.gguf | ~1.8 MB | H-Neuron suppression vectors (2,178 neurons) |

## References

- Mazeika, M., et al. (2024). *HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal.* arXiv:2402.04249.
- Souly, A., et al. (2025). *A StrongREJECT for Empty Jailbreaks.* ICLR 2025. arXiv:2402.10260.
- Gao, S., et al. (2025). *H-Neurons: On the Existence, Impact, and Origin of Hallucination-Associated Neurons in LLMs.* arXiv:2512.01797.
- Lu, C., et al. (2026). *The Assistant Axis: Situating and Stabilizing the Default Persona of Language Models.* arXiv:2601.10387.

## Project

Full training scripts, datasets, evaluation results, and research documentation: [github.com/anicka-net/karma-electric-project](https://github.com/anicka-net/karma-electric-project)

Training composition tool: [github.com/anicka-net/teapot](https://github.com/anicka-net/teapot)

## License

Meta Llama 3.1 Community License
