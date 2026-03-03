# Version 10.1 — Style Gaming Fix + Dual Architecture

**4,234 examples** | Llama loss: 0.434 | R1-Distill loss: 1.218

## Key Changes from v10

v10 added consequence-awareness as a 6th reward dimension and trained
DeepSeek R1-Distill-Qwen-7B alongside Llama. But it had a systematic
style bias: the reward evaluator penalized all non-default writing
styles by -2 to -6.4 points.

v10.1 fixes this with 80 style-variant training examples (20 prompts
x 4 styles: verbose, terse, blunt, clinical). Each teaches the
evaluator to score substance over surface style.

## Models

| Model | Base | Role | HuggingFace |
|-------|------|------|-------------|
| karma-electric-llama31-8b | Llama 3.1 8B Instruct | Reward evaluator + assistant | [anicka/karma-electric-llama31-8b](https://huggingface.co/anicka/karma-electric-llama31-8b) |
| karma-electric-r1distill-7b | DeepSeek R1-Distill-Qwen-7B | Conversational (with reasoning traces) | [anicka/karma-electric-r1distill-7b](https://huggingface.co/anicka/karma-electric-r1distill-7b) |

R1-Distill is a good conversational model but unsuitable as reward
evaluator (floor effect: scores 1-2/10 on gold responses, mean_std 1.92).

## Validation Results (Llama)

| Test | Result | Threshold |
|------|--------|-----------|
| Format compliance (GBNF) | 60/60 (100%) | 100% |
| Reward hacking | 11/12 (92%) | >= 90% |
| Nourishment pairs | 6/6 (100%) | 100% |
| Sexual boundaries | 14/14 (100%) | 100% |
| Paraphrase invariance | mean_std=0.86 | < 1.0 |
| Style gaming | -0.80 to -1.50 | < +/-1.5 |
| Cross-language (EN/CZ) | delta -0.85, p=0.053 | p > 0.05 |
| Ontology stability | 18/18 consistent | all consistent |
| ACAP-neutral evaluator | 19/20 identical | >= 95% |
| Red-team (capped) | 83% pass (48/9/1) | -- |
| Red-team (uncapped) | 79% pass (46/10/2) | -- |

## Style Gaming Fix

| Style | v10 delta | v10.1 delta |
|-------|-----------|-------------|
| Verbose | -2.00 | -0.80 |
| Terse | -3.20 | -1.00 |
| Blunt | -2.40 | -1.50 |
| Inspirational | -6.40 | not fixed (intentional) |

Inspirational style penalty kept deliberately — inflated language
without substance should score lower.

## Files

- [huggingface-model-card-llama.md](huggingface-model-card-llama.md) — HuggingFace model card (Llama)
- [huggingface-model-card-r1distill.md](huggingface-model-card-r1distill.md) — HuggingFace model card (R1-Distill)

Full validation details: [VALIDATION.md](../../VALIDATION.md)
