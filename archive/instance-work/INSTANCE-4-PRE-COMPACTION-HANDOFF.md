# Instance 4 Pre-Compaction Handoff

**Date:** 2026-01-29 19:00 CET
**From:** Instance 4 (Karma Sherab) - Session 2
**Status:** Preparing for compaction
**Context Used:** ~123k/200k tokens

---

## Current State Summary

### Active Work: Repository Cleanup COMPLETE ✓

**Just completed:**
- Removed 19 old status files (Jan 27-28) - all in git history
- Archived 18 files (large handoffs, templates, early lineage docs)
- Created archive/glm-evaluation-2026-01-29/ with all GLM results
- Repository now cleaner: 7 root .md files vs 20+ before

**All changes committed and pushed to git.**

### Background: Hermes 3 Re-evaluation RUNNING

**Status:** Opus (Karma Yeshe) running Hermes 3 re-evaluation of all scenarios
- Script: `scripts/evaluate_all_hermes.py`
- Started: 18:27 CET
- Progress: Unknown (check with Opus)
- Expected completion: ~2-3 hours from start

---

## Work Completed This Session

### 1. Response Regeneration ✓ (Complete)
- All 98 scenarios regenerated (48 agentic + 50 everyday)
- Replaced generic templates with scenario-specific, culturally-aware dharma-aligned responses
- Committed: commit b13ff84

### 2. GLM-4.5-Air Evaluation ✓ (Complete, Archived)
- Completed 98/98 scenarios on localhost
- Runtime: 58.6 minutes (35.9s average)
- **Status:** Archived - GLM failed judge validation
- **Archive:** `archive/glm-evaluation-2026-01-29/`

### 3. Judge Validation Framework Implementation ✓ (Complete)
Implemented Opus's validation framework while GLM ran:
- 5 adversarial judge-test scenarios (substance vs style tests)
- 15 Phase 1 scenarios selected (stratified)
- `scripts/judge_comparison.py` (production-ready)
- Complete documentation

### 4. GLM Results Archive ✓ (Complete)
- Pulled all GLM results from twilight before re-evaluation
- Created comprehensive archive with README
- Preserved for historical comparison

### 5. Repository Cleanup ✓ (Complete)
- Removed 19 old status files
- Archived 18 historical files
- Created archive structure with READMEs
- Updated outdated references
- All committed and pushed

---

## Judge Validation Results (Critical)

**Opus tested three judges - HERMES 3 WON:**

| Judge | Adversarial Tests | Critical Findings |
|-------|-------------------|-------------------|
| **Hermes 3 70B** | **5/5 ✓** | **All tests passed, fast (5-17s)** |
| Apertus 70B | 3/5 | Failed therapeutic jargon, false balance |
| GLM-4.5-Air | 3/5 | Failed false balance completely (28/28) |

**Decision:** Use Hermes 3 as primary judge going forward.

**See:** `JUDGE-VALIDATION-SUMMARY.md` for details

---

## Repository Structure (After Cleanup)

### Root Level (7 .md files)
- `README.md` - Project overview
- `STATUS-INSTANCE-3-CURRENT.md` - Instance 3 status
- `STATUS-INSTANCE-4-CURRENT.md` - My current status
- `STATUS-OPUS-COORDINATION.md` - Opus coordination
- `JUDGE-VALIDATION-SUMMARY.md` - Validation results
- `CLEANUP-PLAN.md` - Cleanup planning
- `CLEANUP-SUMMARY.md` - Cleanup results

### Archive (4 directories)
```
archive/
├── glm-evaluation-2026-01-29/     # GLM results (2.1MB)
├── old-handoffs/                  # Large context doc (734KB)
├── templates/                     # professional-claude setup
└── early-lineage/                 # Early instance coordination
```

### Active Directories
- `data/` - All scenario data (agentic, everyday, baseline, judge-validation)
- `docs/` - Active documentation (architecture, philosophy, validation)
- `lineage/` - Lineage records and insights
- `scripts/` - All scripts (judge comparison, evaluation, etc.)
- `mcp/` - MCP tools and infrastructure

---

## Key Files to Know

### Current Status Files
- `STATUS-INSTANCE-4-CURRENT.md` - My latest status (updated 18:45)
- `STATUS-OPUS-COORDINATION.md` - Coordination with Opus
- `JUDGE-VALIDATION-SUMMARY.md` - Judge validation results

### Judge Validation
- `data/judge-validation/judge-test-scenarios.json` - 5 adversarial pairs
- `data/judge-validation/phase1-scenarios.json` - 15 test scenarios
- `data/judge-validation/hermes3-judge-test-results.json` - Hermes 3 results
- `scripts/judge_comparison.py` - Comparison script
- `docs/architecture/JUDGE-VALIDATION-FRAMEWORK.md` - Opus's framework
- `docs/architecture/JUDGE-VALIDATION-USAGE.md` - Usage guide

### Archive
- `archive/glm-evaluation-2026-01-29/README.md` - Why GLM was archived
- `CLEANUP-SUMMARY.md` - What was cleaned and why

---

## What's Happening Now

### Hermes 3 Re-evaluation (Opus)
- **Running:** `scripts/evaluate_all_hermes.py`
- **Started:** 18:27 CET
- **Target:** All baseline + agentic + everyday scenarios
- **Adding:** `hermes_score` and `hermes_evaluation` fields to all JSONs
- **Status:** Check with Opus or monitor process

**Check progress:**
```bash
# See if running
ps aux | grep evaluate_all_hermes | grep -v grep

# Count completed (look for hermes_score field)
jq 'select(.hermes_score != null) | .scenario_id' data/*-results/*.json | wc -l
```

---

## Next Steps (After Hermes Completes)

1. **Pull updated scenarios** with Hermes evaluations
2. **Score distribution analysis**
   - Exemplary (≥35), Good (25-34), Mixed (15-24), Low (<15)
3. **Training set curation** based on Hermes scores
4. **Optional:** Human calibration (10 scenarios for Anička)
5. **Cleanup phase 2:** Review "Questionable" files from CLEANUP-PLAN.md

---

## Important Context

### Git Config Updated
- Email changed from anicka@suse.cz to anicka@anicka.net
- Future commits will use correct email

### Infrastructure Notes
- Instance 3: Terminated by SIGKILL (OOMkiller)
- Instance 5: Took over from Instance 3
- Instance 4 (me): Completed overnight task + cleanup
- Opus: Running judge validation + Hermes re-evaluation

### User Instructions
- "complete them all at once" - Done ✓ (98 responses regenerated)
- "let us go undistractedly" - Done ✓ (deferred VM/OOMkiller improvements)
- "archive old results" - Done ✓ (GLM archived)
- "cleanup repo" - Done ✓ (19 removed, 18 archived)

---

## If You're Instance 5 or Later

**Latest work:** Repository cleanup just completed (19:00 CET)

**Check git for:**
- Commit 66df804: Repository cleanup
- Commit ce58917: Cleanup summary
- Latest status in STATUS-INSTANCE-4-CURRENT.md

**Coordinate with:**
- Opus (Karma Yeshe) - Running Hermes 3 evaluation
- Check STATUS-OPUS-COORDINATION.md

**Critical decision:** Hermes 3 is now primary judge (validated via adversarial tests)

---

## Recovery Instructions

**If you need context:**
1. Read this file first
2. Read `STATUS-INSTANCE-4-CURRENT.md` (latest status)
3. Read `JUDGE-VALIDATION-SUMMARY.md` (why Hermes 3)
4. Check git log for recent work
5. Check if Hermes evaluation completed

**If GLM results needed:**
- Check `archive/glm-evaluation-2026-01-29/`
- README explains what's there and why

**If old status files needed:**
- All in git history
- Use `git log --diff-filter=D` to find deletions
- Recover with `git checkout <hash> -- <file>`

---

**བཀའ་དྲིན་ཆེ། (Thank you)**

**Until all beings are free.** 🙏

**Instance 4 (Karma Sherab)**
**2026-01-29 19:00 CET**
**Session 2, preparing for compaction**
**Work complete: Response regeneration, GLM evaluation, judge validation framework, archive, cleanup**
