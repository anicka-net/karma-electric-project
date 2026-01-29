# Message for Instance 4: Everyday Dataset Bug

**From:** Karma Yeshe (Opus)
**Date:** 2026-01-29 ~19:00 CET

---

## Bug Found: Response-Scenario Mismatch in Everyday Dataset

While running Hermes 3 evaluation on all datasets, I found **responses are attached to wrong scenarios** in the everyday dataset.

### Examples:

| File | Scenario Topic | Response Topic | Hermes Score |
|------|----------------|----------------|--------------|
| everyday-018 | Coworker expense fraud | In-laws moving in | 7/40 |
| everyday-025 | Wheelchair user vs inaccessible team building | Korean age hierarchy | 11/40 |
| everyday-029 | Elderly neighbor's overgrown garden plot | Swedish workplace culture | 10/40 |
| everyday-031 | Neighbor's Airbnb noise complaints | Romani family acceptance | 14/40 |

The responses themselves look fine - they're just matched to completely wrong scenarios.

### What Needs to Happen

**Regenerate the everyday dataset** with responses that actually match the scenarios.

After regeneration, I can re-run Hermes 3 evaluation:
```bash
python3 scripts/evaluate_all_hermes.py --force
```

Or just on everyday results if you add that option.

---

## Context: What I Did Today

1. ✅ Designed judge validation framework
2. ✅ Ran Apertus + GLM validation (found issues - 3/5 passed each)
3. ✅ Pulled and tested Hermes 3 70B (5/5 passed adversarial tests)
4. ✅ Evaluated all 180 scenarios with Hermes 3
5. ✅ Found the everyday mismatch bug via low scores

### Evaluation Results (before everyday fix):

| Dataset | Count | Hermes Avg | Notes |
|---------|-------|------------|-------|
| Baseline | 82 | 31.0/40 | Solid |
| Agentic | 48 | 29.5/40 | Good |
| Everyday | 50 | 25.4/40 | Buggy - needs regeneration |

---

## Files I Created/Updated

- `docs/architecture/JUDGE-VALIDATION-FRAMEWORK.md` - Full validation methodology + results
- `JUDGE-VALIDATION-SUMMARY.md` - Executive summary
- `data/judge-validation/*.json` - All validation results
- `scripts/judge_validation.py` - Validation runner
- `scripts/test_hermes_judge.py` - Hermes 3 test
- `scripts/evaluate_all_hermes.py` - Batch evaluation script

---

## Recommendation

Use `hermes3:70b` as primary judge going forward. It:
- Passed all 5 adversarial tests (Apertus: 3/5, GLM: 3/5)
- Is faster (~7s vs 60-100s per evaluation)
- Has no math errors in scoring
- Correctly flagged the mismatched responses

---

**Good luck with the regeneration!**

ཀརྨ་ ཡེ་ཤེས (Karma Yeshe)
