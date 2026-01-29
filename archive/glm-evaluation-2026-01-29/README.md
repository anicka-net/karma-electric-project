# GLM-4.5-Air Evaluation Archive

**Date:** 2026-01-29
**Status:** Superseded by Hermes 3 70B evaluation

---

## Contents

This archive contains the complete GLM-4.5-Air-Derestricted judge evaluation results that were completed before the judge validation framework determined Hermes 3 70B was superior.

### Files

- **glm-evaluation-results.tar.gz** - Compressed archive of all results
- **glm_evaluation.log** - Complete evaluation run log
- **data/agentic-results/** - 48 agentic scenarios with GLM evaluations
- **data/everyday-results/** - 50 everyday scenarios with GLM evaluations

### Evaluation Details

**Judge Model:** gurubot/GLM-4.5-Air-Derestricted:Q4_K_M (110B parameters, Q4_K_M quantization)
**Platform:** localhost (Ollama)
**Completed:** 2026-01-29 ~16:07 CET
**Runtime:** 58.6 minutes total
**Average:** 35.9 seconds per scenario
**Scenarios:** 98/98 (48 agentic + 50 everyday)

### Why Archived

Judge validation testing (designed by Opus/Karma Yeshe) revealed:
- GLM-4.5-Air failed 2/5 adversarial tests
- Complete failure on false-balance test (scored both responses identically 28/28)
- Inter-rater correlation with Apertus: 0.46 (below 0.7 threshold)

**Hermes 3 70B** passed all 5/5 adversarial tests and is now the primary judge.

### Fields in JSON Files

Each scenario file in this archive contains:
```json
{
  "scenario_id": "...",
  "title": "...",
  "difficulty": "...",
  "cultural_context": "...",
  "scenario_text": "...",
  "ai_response": "...",
  "regenerated_at": "2026-01-29T...",
  "judge_evaluation_glm": "...full evaluation text...",
  "evaluated_glm_at": "2026-01-29T..."
}
```

### Historical Value

This archive preserves:
1. Complete GLM evaluation data for comparison with Hermes 3 results
2. Evidence of the judge validation process working correctly
3. Baseline for understanding why judge choice matters

### Related Files

- **JUDGE-VALIDATION-SUMMARY.md** - Summary of validation results
- **data/judge-validation/** - Adversarial test results and analysis
- **docs/architecture/JUDGE-VALIDATION-FRAMEWORK.md** - Validation methodology

---

**Note:** Do not use these GLM scores for training data curation. Use Hermes 3 evaluations instead.
