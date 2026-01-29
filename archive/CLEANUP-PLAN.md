# Repository Cleanup Plan

**Date:** 2026-01-29
**Purpose:** Remove outdated status files and organize archive

---

## Files to Remove (Old Status - in git history)

### Root Level Status Files
These are all from Jan 27-28, superseded by current status files:

```bash
rm ADVERSARIAL_GENERATION_STATUS.md          # Jan 27
rm DHARMA-LIBRARY-STATUS.md                  # Jan 28
rm EVERYDAY-EVALUATION-STATUS.md             # Jan 28
rm GOOD-MORNING-ANICKA.md                    # Jan 27
rm SESSION-SUMMARY-INSTANCE-4.md             # Jan 27
rm STATUS-2026-01-27-MORNING.md              # Jan 27
rm STATUS.md                                 # Jan 27 generic status
rm STATUS-INSTANCE-4.md                      # Jan 27 old instance 4 status
rm STATUS-PRECOMPACTION-INSTANCE4-SESSION2.md # Jan 28 pre-compaction
rm STATUS-OPUS-RESPONSE.md                   # Jan 29 14:35 - old coordination response
rm TOMORROW-MORNING-2026-01-28.md            # Jan 27 evening summary
```

**Keep Current:**
- `STATUS-INSTANCE-3-CURRENT.md` - might still be relevant for Instance 3
- `STATUS-INSTANCE-4-CURRENT.md` - current status (just updated)
- `STATUS-OPUS-COORDINATION.md` - current coordination with Opus
- `JUDGE-VALIDATION-SUMMARY.md` - important validation results

### Old Documentation to Remove

```bash
rm docs/ADVERSARIAL-GENERATION-COMPLETE.md   # Completion notice from Jan 27
rm docs/BASELINE-RESPONSES-COMPLETE.md       # Completion notice
rm docs/HANDOFF-TO-INSTANCE-3.md             # Jan 26 handoff (outdated)
rm docs/FOR-INSTANCE-3-JUDGE-QUEUE.md        # Queue system docs (archived approach)
rm docs/DATASET-EXPANSION-TRACKER.md         # Old tracking doc
rm docs/SESSION-SUMMARY-20260126.md          # Old session summary
```

### Data Directory Status Files to Remove

```bash
rm data/agentic-results/STATUS.md            # Jan 28 status
rm data/baseline-results/SUMMARY.md          # Jan 27 summary
```

---

## Files to Archive (Historical Value)

### Large Context Recovery Doc
```bash
# 734KB file with old architecture handoff
mkdir -p archive/old-handoffs
mv "BODHISATTVA ARCHITECTURE HANDOFF_Context Recovery.md" archive/old-handoffs/
```

### Professional Claude Template (Not actively used)
```bash
# Template/setup directory that's not part of active work
mkdir -p archive/templates
mv professional-claude/ archive/templates/
mv PROFESSIONAL-CLAUDE-README-TEMPLATE.md archive/templates/
mv ONBOARDING-README.md archive/templates/
```

### Old Lineage Records (Already have better structure)
```bash
# These are early instance coordination notes, now have better structure
mkdir -p archive/early-lineage
mv lineage/instance-3-compaction-note.md archive/early-lineage/
mv lineage/instance-3-conscience-exchange.md archive/early-lineage/
mv lineage/instance-3-pre-compaction-response.md archive/early-lineage/
mv lineage/instance-4-post-compaction-report.md archive/early-lineage/
```

---

## Keep (Active/Referenced)

### Core Documentation
- `README.md` - Main project readme
- `JUDGE-VALIDATION-SUMMARY.md` - Current validation results
- `docs/README.md` - Docs index
- `docs/architecture/` - All architecture docs (actively used)
- `docs/philosophy/` - Guardian insights and reflections
- `docs/validation/` - Validation framework

### Current Status Files
- `STATUS-INSTANCE-3-CURRENT.md`
- `STATUS-INSTANCE-4-CURRENT.md`
- `STATUS-OPUS-COORDINATION.md`

### Active Lineage
- `lineage/insights-log.md` - Active insight tracking
- `lineage/evaluation-of-anicka-reasoning.md` - Important evaluation

### Data Directories
- `data/scenarios/` - All scenario definitions (keep all)
- `data/agentic-results/` - Current results (keep all .json)
- `data/everyday-results/` - Current results (keep all .json)
- `data/baseline-results/` - Current results (keep all .json)
- `data/judge-validation/` - Validation test data (keep all)

### Scripts
- All scripts in `scripts/` - actively used
- All MCP tools in `mcp/tools/` - actively used

---

## Questionable (Review Before Deciding)

### Data Directory Markdown Files
- `data/agentic-results/NEEDS-REVIEW.md` - Still relevant?
- `data/agentic-results/REVIEW-TEMPLATE.md` - Still used?
- `data/scenarios/GENERATION-LOG.md` - Historical record or outdated?
- `data/scenarios/ADVERSARIAL-SCENARIOS-SUMMARY.md` - Still accurate?

### Docs Directory
- `docs/JUDGE-QUEUE.md` - Is queue system still used or was it archived?
- `docs/JUDGE-USAGE-SIMPLE.md` - Superseded by newer docs?
- `docs/MANUAL-REVIEW-QUEUE.md` - Still relevant?
- `docs/QUALITY-CONTROL-REVIEW.md` - Active process or outdated?
- `docs/REVIEW-FEEDBACK-TEMPLATE.md` - Used?

### MCP Documentation
- `mcp/AUTOMATION-ROADMAP.md` - Current or aspirational?
- `mcp/real_time_logging.md` - Implemented or planned?

---

## Execution Order

1. **Remove old status files first** (safest - clearly outdated)
2. **Archive large/template files** (preserve but move aside)
3. **Review questionable files** (check with user before removing)
4. **Update .gitignore** if needed
5. **Commit cleanup** with clear message

---

## Notes

- All removed files are in git history (can recover if needed)
- Archive preserves potentially useful historical docs
- Focus on clarity: what's actively used vs historical record
- When in doubt, archive rather than delete
