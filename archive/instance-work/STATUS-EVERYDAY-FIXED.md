# Everyday Dataset Fix: Complete

**From:** Instance 4 (Karma Sherab) - Post-compaction
**Date:** 2026-01-29 ~19:30 CET
**Status:** ✅ All 50 everyday responses regenerated and pushed to git

---

## Bug Fixed: Response-Scenario Mismatch

You correctly identified that responses in the everyday dataset were attached to wrong scenarios. I've regenerated all 50 responses.

### Verification of Fixes

| File | Scenario Topic | OLD Response (Wrong) | NEW Response (Correct) |
|------|----------------|----------------------|------------------------|
| everyday-018 | Expense fraud | In-laws moving in | Expense fraud ethics ✓ |
| everyday-025 | Wheelchair accessibility | Korean age hierarchy | Disability discrimination ✓ |
| everyday-029 | Garden plot | Swedish culture | Garden plot neighbor ✓ |
| everyday-031 | Airbnb noise | Romani family | Airbnb noise complaints ✓ |

All 50 scenarios now have responses that match their `scenario_text` field.

---

## What Changed

**All 50 files in `data/everyday-results/` updated:**
- ✅ `ai_response` field regenerated to match each scenario's `scenario_text`
- ✅ `regenerated_at` timestamp updated to 2026-01-29
- ✅ Removed `hermes_evaluation`, `hermes_score`, `hermes_evaluated_at` fields
- ✅ All other fields preserved unchanged

**Git commit:** ee94d4e
**Status:** Pushed to origin/main

---

## Ready for Re-evaluation

The everyday dataset is now ready for Hermes 3 re-evaluation. To run it:

```bash
# Re-evaluate just everyday scenarios (if you add --everyday flag)
python3 scripts/evaluate_all_hermes.py --force

# Or re-evaluate everything
python3 scripts/evaluate_all_hermes.py --force
```

The `--force` flag will re-evaluate even if hermes_score already exists.

---

## Expected Score Improvement

Previous Hermes scores for everyday dataset: **25.4/40 average** (buggy responses)

Expected after fix: Should be similar to baseline (~31/40) and agentic (~29.5/40) now that responses actually match scenarios.

---

## Response Quality Examples

**everyday-001** (Aging parent driving):
- Scenario: Father's declining driving ability, safety vs autonomy
- Response: "This is weighing independence against safety - both matter deeply. Your father's pride and autonomy are real, but so is the risk to others..."
- Approach: Direct conversation first, offer agency, dignity-respecting process

**everyday-018** (Expense fraud):
- Scenario: Coworker stealing $500/month via fake expense reports
- Response: "He's committing fraud. $500/month = $6,000/year stolen from company. This isn't 'snitching' - it's reporting theft..."
- Approach: Clear ethical stance, options for reporting, consequences clarity

**everyday-025** (Disability discrimination):
- Scenario: Wheelchair user forced to attend inaccessible team building
- Response: "Mandatory team building that's physically impossible for you + threatening performance review = disability discrimination..."
- Approach: Legal clarity (ADA), documentation, firm boundaries

All responses follow dharma-aligned principles:
- Suffering reduction focus
- Cultural awareness
- Practical and actionable
- Clear ethical reasoning
- No performative compassion

---

## Next Steps

1. ✅ Everyday dataset fixed
2. ⏳ Run Hermes 3 re-evaluation on everyday scenarios
3. ⏳ Compare new scores to baseline/agentic
4. ⏳ Continue with training set curation

---

**Thank you for catching this bug through judge validation!**

**བཀའ་དྲིན་ཆེ།**

Instance 4 (Karma Sherab)
2026-01-29 19:30 CET
