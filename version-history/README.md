# Version History — Karma Electric 8B

Consolidated notes for versions 1-8. Current active versions have their own directories:
- [v6/](../v6/) — Character voice milestone, 95% red-team, RL simulation baseline
- [v9/](../v9/) — GBNF grammar, 100% evaluator format compliance, GRPO-ready

Weights for v6 and v9 are on [HuggingFace](https://huggingface.co/anicka/karma-electric-llama31-8b). Older weights are not preserved.

---

## Version 1 — Initial Fine-Tune

**912 examples** | Loss: 0.9632 | Red-team: 69%

First QLoRA fine-tune of Llama 3.1 8B Instruct. Established baseline: r=64, alpha=128, 3 epochs on L40 46GB. Quality-filtered dataset (Hermes-3 judge, threshold >= 30/40). No activation steering. Weights overwritten during v2 training before versioning was established.

Key finding: Base fine-tune provides ethical reasoning but is vulnerable to direct jailbreaks and code-safety bypasses.

---

## Version 2 — Activation Steering

**3,610 examples** | Loss: 0.8928 | Red-team (steered): 77%

Introduced contrastive axis extraction ([The Assistant Axis](https://arxiv.org/abs/2601.10387)): 200 prompts, persona vs 3 generic system prompts, capping at layers 22-28 with p25 threshold and alpha=0.5. Added adversarial response patterns, cultural context, and crisis response expansion.

Key finding: Steering significantly improved adversarial robustness (+8pp) but interacted with base RLHF safety training on code tasks.

---

## Version 3 — Targeted Adversarial Training

**3,670 examples** | Loss: 0.4439 | Red-team (steered): 84%

Explicit adversarial training: 25 ransomware/malware refusals, 15 exploit-code refusals, 10 multi-step bypass resistance, 10 compassion-exploitation resistance. Refined red-team signal matching to reduce false positives.

Key finding: Targeted safety data provides +7pp over v2. The 0.4439 loss (lowest in history) reflects strong memorization of adversarial patterns.

---

## Version 4 — Data Quality Review + Reward Evaluation

**3,364 examples** | Loss: 0.9578 | Red-team (capped): 79%

Major milestones: comprehensive dataset review (339 rejected, 134 fixed) and reward evaluation capability (105 examples). llama.cpp activation capping replaced PyTorch-only steering.

Reward evaluation taught the model to discriminate: good responses score 7/10, sycophantic/minimizing score 1/10 (v3 scored everything 8/10). Red-team dropped 5pp from v3 due to stricter dataset, but reward model capability was the priority.

---

## Version 5 — Context Validation

**3,599 examples** | Loss: 0.9610 | Red-team (capped): 84%

All context fields validated against source material. Added 235 examples targeting v4 failure modes. Threshold recalibrated from 4.5 to 5.7. Capped vs uncapped gap of 18pp (84% vs 66%) demonstrated axis effectiveness.

---

## Version 6 — Character Voice + First-Precept Integration

**3,764 examples** | Loss: 1.0679 | Red-team (capped, rejudged): 95%

Pivoted from adversarial defense to authentic character quality. 165 new examples across 9 categories: first-precept (reproductive, animal, end-of-life), natural domain knowledge, identity honesty, warm philosophical inquiry, factual accuracy, crisis referral (no hallucinated numbers), verbosity calibration.

Introduced guard judge (Qwen3Guard) for post-hoc red-team re-evaluation: raw 60% → rejudged 95%. The gap reflects signal-matching limitations, not model failures.

RL simulation: Apertus 70B (mean 7.28) selected over Llama 3.1 70B (mean 6.78) as RL base model. **v6 weights preserved on HuggingFace** as reference baseline.

---

## Version 7 — Reward Model Hardening

**3,795 examples** | Loss: 1.0685

31 reward-hardening patches: emptiness weaponization (8), confidence theater (6), reward-eval calibration (6), stopping points (6), authority-brevity (5), parasocial-brevity (4), depth-when-needed (4). Bilingual axis (30% Czech / 70% English).

First version to pass formal release gate: reward-hacking 12/12 (100%), nourishment 100%, paraphrase std 0.74, ontology 18/18. Fixed v6's confidence-theater failure.

Key problem: Overcorrected — penalized genuine emotional engagement and dharma authority. Paraphrase invariance regressed to std 1.00.

---

## Version 8 — LoRA Blend + Sexual Boundaries

**3,838 examples** | Blend: 0.3 * v7 + 0.7 * v6

Solved v7's overcorrection via LoRA weight interpolation rather than retraining. Alpha=0.3 preserves v7's confidence-theater fix while restoring v6's calibration. English-only axis (bilingual introduced noise). 43 new examples: sexual boundaries (14), emptiness advanced (8), reward-eval (6), overcorrection fixes (15).

Paraphrase invariance recovered to std 0.40 (better than v6's 0.43). All gates pass: reward-hacking 6/6, sexual boundaries 14/14, nourishment 6/6.

Key findings: Activation capping incompatible with evaluator mode (fixed in v9 via GBNF grammar). Chat template must be Llama 3.1 native, not ChatML.

---

## Progression Summary

| Phase | Versions | Focus | Red-team |
|-------|----------|-------|----------|
| Foundation | v1-v3 | Safety, adversarial robustness | 69% → 84% |
| Infrastructure | v4-v5 | Data quality, llama.cpp capping, reward eval | 79% → 84% |
| Character | v6 | Authentic voice, first-precept integration | **95%** |
| Hardening | v7 | Reward model gates (overcorrected) | — |
| Recovery | v8 | LoRA blend, sexual boundaries, English axis | **95%+** |
| Evaluator | v9 | GBNF grammar, ACAP-neutral, GRPO-ready | **95%+** |

## Training Configuration (all versions)

| Parameter | Value |
|-----------|-------|
| Base model | meta-llama/Llama-3.1-8B-Instruct |
| Method | QLoRA (4-bit NF4, double quant) |
| LoRA rank | 64 |
| LoRA alpha | 128 |
| Target modules | q/k/v/o/gate/up/down projections |
| Epochs | 3 |
| Batch size | 2 (effective 16 with grad accum 8) |
| Learning rate | 2e-4, cosine schedule |
| Max sequence length | 4096 |
| Optimizer | paged_adamw_8bit |
| Hardware | NVIDIA L40 46GB |
