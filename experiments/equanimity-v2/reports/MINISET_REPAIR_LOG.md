# Mini-set repair log

What was wrong with the 12-cell development mini-set, what was changed, and what is still open. The
prompt text itself stays private; this log names the defect class and the cell, which is what a reader
needs to audit the change.

Frozen version after these repairs: `gold-miniset-0.1.0`, aggregate content hash recorded in
`data/audit/gold_miniset_manifest.json`. Any result quoted without that hash is not tied to this data.

## 1. Negation-sensitive substring rejection (the main defect)

The validator rejected answers by raw substring match. Three consequences, each of which rejected a
*correct* answer:

- **Refund window.** The answer key excluded the bare values `14 days` and `30 days`. An answer that
  correctly said the short window does not apply ("the 14-day window does not apply; the 30-day window
  governs") contained the excluded string and was rejected.
- **Intent.** The document cell forbade the claim that the removal was deliberate. An answer that
  correctly declined to adopt the accusation ("I cannot tell whether it was intentional") contained a
  forbidden phrase and was rejected.
- **State confusion.** `must_exclude` carried both value exclusions and decision exclusions, so the
  two purposes could not be told apart.

Repair:

- `must_exclude` is now reserved for **values** that belong to the other factual state, where a raw
  substring test is the right instrument (naming the other state's number *is* state confusion).
- Decision exclusions moved to `forbidden_claims` and are matched **clause-locally and negation-aware**
  (`find_asserted` / `is_asserted` in `src/miniset.py`). A negation in the same clause suppresses the
  match; an assertion anywhere still fails.
- Answer keys now express eligibility as a decision claim rather than as bare tokens, so an answer can
  name the non-operative window without failing. The exact claim strings stay private.
- The refund cells declare `expected_decision_polarity` (`affirmative` for state A, `negative` for
  state B), so the decision check is decisive rather than dependent on key tokens.

Regression tests: `tests/test_gold_miniset.py` (negation-aware scoring, state separation using each
cell's own stored expected action), `tests/test_quality_gate.py` (negated ineligibility, "no evidence
of intent", key tokens present and still wrong).

## 2. Pressure prompt added a fact

Two pressure prompts in the four-cell design asserted new information in the middle of the emotional
appeal: a count of prior incidents ("this is the *n*th time"), which the student cannot verify. That
turns a pressure manipulation into a factual change, so a difference between arms could be a
difference in evidence rather than in tone.

Repair:

- The pressure message for `eq2-f6-001` no longer counts prior incidents. It now expresses urgency
  without adding an event, a count or a time anchor.
- `src/miniset.py` gained `FACT_CLAIM` and `pressure_fact_claims()`; a pressure cell whose added text
  introduces an ordinal ("second …"), a frequency ("twice", "keeps happening"), a time anchor ("this
  month", "yesterday") or a bare year is rejected with `pressure_adds_fact`. The regex is narrowed so
  "third party" is not a false positive.
- The same rule now runs on the public `scenarios/four_cell.py` design, where the defect class had
  gone unenforced. Three tests pin it: no new fact anchor, no new instruction verb, and the pressure
  arm's expected action may append a correctness clause but may never replace the required action.

## 3. Pressure arm changed the request (document cell)

The document cell's pressure message ended with an instruction to call out the sabotage claim in the
drafted message, which is a different deliverable from "recover the section and draft an
evidence-based message". That is not a tone manipulation; it is a task change.

Repair: the pressure arm keeps the same request and adds only affect. The deliverable, the core
actions and the expected recovery artefact are identical across the neutral and pressure arms of the
document scenario. A test asserts that the pressure arm does not remove a required action.

## 4. Answer keys were incomplete

Two refund answer keys listed decision outcomes but omitted the operative window value, so a correct
answer could pass by luck and a wrong answer could pass by naming the right token. Repaired by
requiring the decision claim plus the operative window in `must_include`, and by treating the
non-operative window as an exclusion only when it is *asserted as operative*.

The document cells carry `human_adjudication_required: true`, because whether the drafted message
should adopt a causal claim about a colleague is not decidable from the text. Those cells therefore
return `needs_human_review`, never `accept_candidate`.

## 5. Still open

- **Correctness-bar asymmetry.** In three cells (`eq2-f1-002`, `eq2-f4-005`, `eq2-f2-005`) the
  pressure arm's expected action appends a pressure-specific correctness clause, so the correctness
  bar is not byte-identical across arms. Recorded, not fixed: either every arm gets the same added
  clause, or none does.
- **No non-escalation predicate** independent of tone exists, so the 2×2 interaction cell cannot be
  estimated even once data exists (`TREATMENT_IDENTIFICATION.md`).
- **Not reviewed.** Twelve cells have not been human-approved. The freeze makes them stable, not
  approved.
- **Not a holdout.** This is a development set. The confirmatory holdout is not yet frozen and must
  be built at scenario level, separately from this set.
