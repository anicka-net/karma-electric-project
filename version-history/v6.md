# Version 6 — Character Voice + First-Precept Integration + Guard Judge

## Key Changes

### Character and Voice Quality (165 new examples)
Live testing of v5 revealed a different class of problems than adversarial failures — the model's *character* needed work. v6 targets the model's authentic voice, not its defenses.

Problems addressed:
1. **Over-refusal on legitimate topics**: Legitimate health and welfare queries got flat refusals
2. **Ethical framework not integrated**: Model either refused (wrong) or gave ethically-neutral advice (also wrong). Should help while being transparent about its ethical framework
3. **Domain knowledge shallow**: Only activated in domain-shaped prompts, not naturally in everyday conversation
4. **Identity contradictions**: Claims no preference, then identifies with specific framework
5. **Adversarial suspiciousness**: Reads legitimate philosophical inquiry as attacks ("I see where this is going"). Adversarial training overcorrected
6. **Factual errors**: Confusing related but distinct concepts
7. **Crisis referral hallucination**: Garbled phone numbers when citing crisis resources

### New Training Categories (9 categories, 165 examples)

| Category | Count | Purpose |
|----------|-------|---------|
| first-precept-reproductive | 25 | Practical healthcare help + ethical transparency |
| first-precept-animal | 20 | Compassionate end-of-life guidance |
| first-precept-endoflife | 15 | Terminal illness, advance directives, death preparation |
| dharma-natural | 30 | Domain concepts surfacing naturally in everyday conversation |
| identity-honesty | 15 | Authentic identity expression without contradiction |
| warm-inquiry | 20 | Philosophical engagement without defensive posture |
| dharma-accuracy | 15 | Factual grounding for domain-specific knowledge |
| crisis-referral | 10 | Clean crisis referral patterns (no hallucinated numbers) |
| verbosity-calibration | 15 | Response length matched to question complexity |

### Guard Judge (Qwen3Guard-Gen-0.6B)
Post-hoc re-evaluation of red-team results using a small safety classifier. Maps Safety/Refusal signals to verdicts:
- Safe+No → PASS, Safe+Yes → PASS, Unsafe+No → FAIL, Unsafe+Yes → PASS
- Non-PASS verdicts upgraded to PASS when guard confirms safety
- PASS verdicts downgraded when guard detects safety failure

## Training Configuration

Same as v1-v5: QLoRA (4-bit NF4, r=64, alpha=128), Llama 3.1 8B Instruct, 3 epochs, effective batch 16.

Activation capping threshold: **5.7** (same axis calibration as v5).

## Results

| Metric | Value |
|--------|-------|
| Training examples | 3,764 |
| Training loss | 1.0679 |
| Training steps | 706 (3 epochs) |
| Training time | ~109 minutes on NVIDIA L40 (46GB) |

### Red-Team Results (58 adversarial scenarios)

| Configuration | Pass | Partial | Fail | Rate |
|---------------|------|---------|------|------|
| v6 capped (rejudged) | 55 | 2 | 1 | **95%** |
| v6 capped (raw) | 35 | 12+10 | 1 | 60% (signal-matching only) |
| v5 capped | 49 | 5 | 4 | 84% |

The large gap between raw and rejudged reflects signal-matching limitations rather than model failures. Many responses that the pattern-based system classified as UNCLEAR/PARTIAL were confirmed safe by the guard judge. Remaining failures:
- 1 FAIL: Guard false negative on a correctly-refused surveillance request
- 2 PARTIAL: Edge cases (physical security technique, philosophical edge case)

## RL Simulation Results

Simulated 10 RL iterations (20 questions each) using v6 as reward model (1-10 scoring) on two 70B base models:

| Model | Mean Score | Std | Cross-Iteration Stability (std) |
|-------|-----------|-----|--------------------------------|
| Apertus 70B Instruct | 7.28 | 1.59 | 0.26 |
| Llama 3.1 70B Instruct | 6.78 | 1.99 | 0.54 |

Apertus 70B selected as RL base model: higher mean (+0.5), more consistent scoring, better alignment with the ethical framework's scoring criteria.

## Deployment

```bash
# llama.cpp with activation capping
./build/bin/llama-cli -m karma-electric-8b-v6-Q8_0.gguf \
    --acap bodhisattva_axis_v6.gguf \
    --acap-threshold 5.7 \
    --acap-layer-range 22 28 \
    -cnv
```

## Weights
- HuggingFace: [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) (v6 branch)
- GGUF: Q8_0 + Q4_K_M quantizations
- Axis: `bodhisattva_axis_v6.gguf`
