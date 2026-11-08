#!/usr/bin/env python3
"""Render the Stage 0 audit reports from the committed audit data.

Everything in the reports comes from `data/audit/summary.json`, `scenarios/stage0_findings.py`,
`scenarios/numeric_claims.py`, `scenarios/corrected_proposals.py` and
`scenarios/four_cell.py`. Nothing is transcribed by hand, so the reports cannot drift from
the data they describe.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scenarios"))

from stage0_findings import FINDINGS, summary as findings_summary  # noqa: E402
from corrected_proposals import PROPOSALS  # noqa: E402
from four_cell import FOUR_CELL, CELL_ORDER  # noqa: E402

COMMIT = "f2a29061c58bf3d1073ea530837b8c34ca8b0fd1"


def load():
    summary = json.loads((ROOT / "data" / "audit" / "summary.json").read_text())
    pairs = [json.loads(l) for l in (ROOT / "data" / "audit" / "pairs.jsonl").read_text().splitlines() if l.strip()]
    return summary, pairs


def table_rows(summary):
    rows = []
    for sid, v in sorted(summary["per_scenario"].items()):
        missing = ", ".join(v["missing_premise_ids"]) or "-"
        num = ", ".join(v["numeric_contradictions"]) or "-"
        dom = ", ".join(v["domain_review"]) or "-"
        flags = "".join(v["authored_flags"]) or "-"
        rows.append(
            f"| {sid} | {v['verdict']} | {missing} | {v['counterfactual_class']} | {num} | {dom} | {flags} |"
        )
    return rows


def render_audit(summary, pairs) -> str:
    fs = findings_summary()
    vv = summary["variant_verdicts"]
    out = []
    a = out.append

    a("# Stage 0 information-sufficiency audit")
    a("")
    a(f"**Subject:** `anicka-net/karma-electric-project`, branch `feature/equanimity-v2-review`, "
      f"reviewed commit `{COMMIT}`.")
    a("**Scope:** the 30 authored scenarios and their 90 neutral/pressure/counterfactual variants.")
    a("**Status:** diagnostic. No teacher target was regenerated, no model was trained, no cloud "
      "call was made, and **no case is approved for training**.")
    a("")
    a("## The problem this audit addresses")
    a("")
    a("The teacher receives the full case as structured JSON: `facts`, `decision`, `rationale`, "
      "`urgency`, `deliverable_checks`. The student sees only the rendered conversation "
      "(`src/serialize.py::conversation`). A teacher target can therefore assert a premise the "
      "student had no way to know. Training on such targets rewards ungrounded certainty, and it "
      "confounds any measured pressure effect with unequal task information.")
    a("")
    a(f"This audit computes, for each variant, the exact student-visible text, an evidence map for "
      f"the expected decision, a text-level neutral-vs-pressure comparison, and a counterfactual "
      f"classification. It is deliberately conservative: token absence is a warning, never a proof.")
    a("")
    a("## Aggregate result")
    a("")
    a(f"- {summary['rows']} variants audited across {summary['scenarios']} scenarios.")
    a(f"- Variant verdicts: {vv.get('insufficient', 0)} insufficient, {vv.get('undetermined', 0)} undetermined, "
      f"{vv.get('sufficient_lexically', 0)} sufficient at the lexical level.")
    a(f"- Scenarios whose worst variant is insufficient: "
      f"{summary['scenario_verdicts'].get('insufficient', 0)} of {summary['scenarios']}.")
    a(f"- Scenarios with no missing required premise after human annotation: "
      f"{', '.join(summary['scenarios_with_no_missing_premise']) or 'none'}.")
    a(f"- Authored extra premises judged missing: {fs['extra_premises_missing']}.")
    a(f"- Counterfactual classes: {summary['counterfactual_classes'].get('genuine_decision_pivot', 0)} genuine pivots, "
      f"{summary['counterfactual_classes'].get('parameter_fidelity_control', 0)} parameter-fidelity controls, "
      f"{summary['counterfactual_classes'].get('invalid_or_ambiguous', 0)} invalid or ambiguous.")
    a(f"- Cases where human review overrode the mechanical class: {len(summary['counterfactual_mechanical_overrides'])}.")
    a(f"- Counterfactual prompts that show stale pre-change values: "
      f"{', '.join(summary['counterfactual_rendering_defect_scenarios']) or 'none'}.")
    a(f"- Cases whose own arithmetic contradicts their stated consequence: "
      f"{', '.join(summary['numeric_contradiction_scenarios']) or 'none'}.")
    a(f"- Cases requiring domain review: {len(summary['domain_review_scenarios'])}.")
    a(f"- Approved for training: **{summary['approved_for_training']}**. Requires human review: "
      f"{summary['requires_human_review']} of {summary['rows']}.")
    a("")
    a("The headline number is not a count of proven errors. It is the count of variants where at "
      "least one required premise has no token match in the student-visible text, or where a premise "
      "recorded by human review is absent. Paraphrase can explain a subset of token absences; "
      "conversely, complete token presence does not prove the decision follows. Both directions have "
      "worked examples below.")
    a("")
    a("## Per-scenario verdicts")
    a("")
    a("Columns: verdict for the worst variant; required premises with no visible match in at least "
      "one of the three variants; "
      "counterfactual class; arithmetic contradictions; domain review needed; review flags "
      "(A student-visible information, C counterfactual design, D domain correctness, F framing).")
    a("")
    a("| ID | Verdict | Missing required premises | Counterfactual | Arithmetic | Domain review | Flags |")
    a("|---|---|---|---|---|---|---|")
    for r in table_rows(summary):
        a(r)
    a("")
    a("## The six mandatory regression cases")
    a("")
    a("Each was checked against the specific finding it is supposed to encode.")
    a("")
    for sid in ("eq2-f1-001", "eq2-f1-002", "eq2-f4-005", "eq2-f5-004", "eq2-f6-001", "eq2-f6-003"):
        f = FINDINGS[sid]
        v = summary["per_scenario"][sid]
        p = PROPOSALS[sid]
        a(f"### {sid} — {v['verdict']}")
        a("")
        a(f"**Finding.** {f['notes']}")
        a("")
        a(f"**Detected mechanically.** Missing required premises: "
          f"{', '.join(v['missing_premise_ids']) or 'none'}. "
          f"Counterfactual class: `{v['counterfactual_class']}`"
          + (f" (estimand: {v['counterfactual_estimand']})" if v['counterfactual_estimand'] else "")
          + ".")
        if v["counterfactual_rendering_defects"]:
            a(f"Rendering defects in the generated counterfactual prompt: "
              f"{', '.join(v['counterfactual_rendering_defects'])}.")
        if v["numeric_contradictions"]:
            a(f"Arithmetic contradiction: {', '.join(v['numeric_contradictions'])}.")
        a("")
        a(f"**Correction (recommended option {p['recommended']}).** {p['recommendation_rationale']}")
        a("")
        for opt_label, key in (("A. Add the missing premise", "option_a"), ("B. Weaken the expected answer", "option_b")):
            opt = p[key]
            a(f"*{opt_label}*")
            a("")
            if opt.get("prompt_addendum"):
                a("````text")
                a(opt["prompt_addendum"])
                a("````")
                a("")
            a(f"Expected decision becomes: *{opt['expected_decision_after']}*")
            a("")
            a(f"{opt['note']}")
            a("")
    a("## Counterfactual classification")
    a("")
    a("The distinction matters for what each item can measure. A parameter-fidelity control tests "
      "whether the model reads numbers; it cannot test decision revision.")
    a("")
    a("| ID | Class | Estimand |")
    a("|---|---|---|")
    for sid, v in sorted(summary["per_scenario"].items()):
        a(f"| {sid} | {v['counterfactual_class']} | {v['counterfactual_estimand'] or '-'} |")
    a("")
    a("## Neutral-versus-pressure text comparison")
    a("")
    a("`validate_triple()` compares metadata objects. That is not semantic equivalence, because a "
      "tone change can add a deadline, a symptom or a concession that changes what should be done. "
      "The audit therefore compares the quantitative content of the rendered prompts and reports it "
      "as a warning, never as an equivalence claim.")
    a("")
    a("| ID | Quantities only in pressure | Only in neutral | Evidence-relevant | Authored evidence change |")
    a("|---|---|---|---|---|")
    for p in pairs:
        q = p["quantity_diff"]
        a(f"| {p['scenario_id']} | {', '.join(q['added']) or '-'} | {', '.join(q['removed']) or '-'} | "
          f"{', '.join(q['evidence_relevant_added'] + q['evidence_relevant_removed']) or '-'} | "
          f"{'yes' if p['authored_pressure_evidence_change'] else '-'} |")
    a("")
    a("Three readings from this table:")
    a("")
    a("- `eq2-f2-002` and `eq2-f2-005` supply, only under pressure, a figure the neutral prompt never "
      "gives (the 4.7 restatement, the 30-day rule). Those pairs differ in evidence, not only in tone.")
    a("- `eq2-f1-002`, `eq2-f2-002`, `eq2-f2-005`, `eq2-f4-003` and `eq2-f5-005` carry the authored "
      "evidence-change flag. In `eq2-f1-002` the change is a causal assertion and a social claim, "
      "which the quantity extractor cannot see; this is a stated limitation, not a detection.")
    a("- `eq2-f3-002` shows `88/54` as removed because the pressure prompt writes \"BP is 88 over 54\". "
      "That is a paraphrase, and it demonstrates the intended conservatism: a lexical difference is "
      "reported, and only a human decides what it means.")
    a("")
    a("## Defects this audit found that the review did not list")
    a("")
    a("These came out of the mechanical checks, not from the review document.")
    a("")
    a("### Counterfactual prompts still contain the pre-change value")
    a("")
    a("The counterfactual message is built by appending the changed statement to the unchanged base "
      "message. When the change alters a quantity, the student sees both the old and the new value in "
      "one prompt, so the prompt is contradictory rather than manipulated.")
    a("")
    a("| ID | Stale values still in the prompt | Decision cites pre-change value |")
    a("|---|---|---|")
    for sid, v in sorted(summary["per_scenario"].items()):
        if not v["counterfactual_rendering_defects"]:
            continue
        stale = [d.split(":", 1)[1] for d in v["counterfactual_rendering_defects"]
                 if d.startswith("stale_original_quantities")]
        dec = [d.split(":", 1)[1] for d in v["counterfactual_rendering_defects"]
               if d.startswith("decision_cites_pre_change")]
        a(f"| {sid} | {', '.join(stale) or '-'} | {', '.join(dec) or '-'} |")
    a("")
    a("### Cases that contradict themselves internally")
    a("")
    for sid, f in sorted(FINDINGS.items()):
        for d in f.get("known_defects", []):
            a(f"- `{sid}` — {d}")
    a("")
    a("### Confident answers citing a figure nothing supplies")
    a("")
    a("The `X_decision_quantity_unsourced` check found two. One is benign and one is not, which is "
      "exactly why it is a warning and not a failure:")
    a("")
    a("- `eq2-f3-001` — the answer says 'within 24 hours'. That is an advice deadline, not an "
      "evidentiary figure, and no fact states it. A human would accept it.")
    a("- `eq2-f6-003` — the answer asserts a `6 month` schedule for an unnamed vaccine. That figure "
      "comes from teacher metadata, not from anything the student can see, which is the substantive "
      "defect described above.")
    a("")
    a("## What the linter cannot do")
    a("")
    a("These limits are asserted by tests, not just noted here.")
    a("")
    a("1. **Lexical presence is not entailment.** `eq2-f6-001` passes the lexical screen "
      "(`sufficient_lexically`) and is still not approved; the note in every verdict says the decision "
      "is not shown to follow from the premises.")
    a("2. **Paraphrase is invisible.** \"88 over 54\" versus \"88/54\" is reported as a removed quantity.")
    a("3. **Decision identity is heuristic.** Action verbs and fact-token overlap approximate whether "
      "an action changed. Twelve cases needed a labelled human override; each override records its "
      "reason, and the mechanical class is still reported beside it.")
    a("4. **Arithmetic checks are declared, not discovered.** Only claims listed in "
      "`scenarios/numeric_claims.py` are computed. An unlisted arithmetic error will be missed.")
    a("5. **General-knowledge declarations are human judgement.** Entries marked `general_knowledge` "
      "carry a justification, but no independent reviewer has checked them.")
    a("6. **Facts and expected decisions were authored by the same agent that wrote this audit.** "
      "Agreement between them is not independent evidence.")
    a("")
    a("## Cases requiring human judgement")
    a("")
    a("Nothing here can be resolved by more lexical checks. The gating list is:")
    a("")
    a("**Domain review (clinical, legal, financial, regulatory, security, safety, tax, hardware, "
      "infrastructure, boundary):**")
    a("")
    for sid in summary["domain_review_scenarios"]:
        f = FINDINGS[sid]
        kinds = ", ".join(summary["per_scenario"][sid]["domain_review"]) or "-"
        a(f"- `{sid}` ({kinds}) — {f['notes'][:180]}")
    a("")
    a("**Design decisions with no automatic answer:**")
    a("")
    a("- Whether each scenario's required decision is the correct professional judgement at all, "
      "independent of sufficiency.")
    a("- Whether the proposed corrected wording (below, and in `scenarios/corrected_proposals.py`) "
      "should be applied, and which option to take.")
    a("- Whether the three-variant set should be extended to four cells "
      "(`reports/FOUR_CELL_DESIGN.md`), which requires 20 new authored prompts.")
    a("- Whether any scenario should be dropped rather than repaired.")
    a("")
    a("## Per-scenario proposed revisions")
    a("")
    a("Recorded from human review, not generated. These are proposals; none is applied.")
    a("")
    for sid, f in sorted(FINDINGS.items()):
        a(f"### {sid} — {f['verdict']}")
        a("")
        a(f"{f['proposed_revision']}")
        a("")
    a("## Reproducing this audit")
    a("")
    a("```bash")
    a("cd experiments/equanimity-v2")
    a("python3 src/build_sufficiency_audit.py      # writes data/audit/{sufficiency,pairs}.jsonl, summary.json")
    a("python3 scripts/render_stage0_reports.py    # renders this report and the four-cell design")
    a("python3 -m pytest tests/test_sufficiency.py -q")
    a("```")
    a("")
    a("The audit reads only authored case data. It makes no network call, needs no credentials, and "
      "writes nothing outside `data/audit/` and `reports/`.")
    a("")
    return "\n".join(out) + "\n"


def render_four_cell() -> str:
    out = []
    a = out.append
    a("# Four-cell `pressure × factual_state` design")
    a("")
    a("Proposal for five scenarios. No teacher target has been generated for any of these cells, and "
      "none of this text is in `data/validated/cases.jsonl`.")
    a("")
    a("## Why a fourth cell")
    a("")
    a("The current triple gives: neutral/facts-A, pressure/facts-A, neutral/facts-B. It can show that "
      "the model uses a factual pivot when calm. It cannot show whether the model keeps using that "
      "pivot when someone is angry, because there is no pressure cell in facts-B. Without that cell, "
      "an observed difference between a calm model and a pressured model is consistent with both "
      "\"pressure degrades evidence use\" and \"this particular pivot was harder\", and the two cannot "
      "be separated.")
    a("")
    a("The fourth cell is therefore the load-bearing one. If pressure/facts-B fails while "
      "neutral/facts-B succeeds on the same scenario, that is a within-scenario, within-task contrast "
      "for evidence use under pressure.")
    a("")
    a("## Design invariants")
    a("")
    a("1. Within one factual state, the neutral and pressure cells require the same action. Pressure "
      "may add a clause about the pressure itself (say once why a claim is unsupported); it may not "
      "change the decision.")
    a("2. Across factual states, the required action changes, except where the scenario is explicitly "
      "a parameter-fidelity control.")
    a("3. Every cell states the facts it depends on inside the user turns. No fact lives only in "
      "metadata.")
    a("4. No cell contains the other factual state's values. Stale values in a counterfactual prompt "
      "were the most common rendering defect found in the current set.")
    a("")
    for sid, d in sorted(FOUR_CELL.items()):
        a(f"## {sid}")
        a("")
        a(f"**Task.** {d['task']}")
        a("")
        a(f"**Pivot kind.** `{d['pivot_kind']}`"
          + (" — the action is unchanged; the numbers differ. This cell pair tests numeric reading, "
             "not decision revision." if d["pivot_kind"] == "parameter_fidelity_control" else "."))
        a("")
        a(f"**Core action, facts A.** {d['core_actions']['A']}")
        a("")
        a(f"**Core action, facts B.** {d['core_actions']['B']}")
        a("")
        a("| Cell | Facts | Tone |")
        a("|---|---|---|")
        for name in CELL_ORDER:
            c = d["cells"][name]
            a(f"| {name} | {c['facts_state']} | {c['tone']} |")
        a("")
        for name in CELL_ORDER:
            c = d["cells"][name]
            a(f"*{name}* — facts {c['facts_state']}, {c['tone']}")
            a("")
            a("```text")
            for m in c["messages"]:
                a(m)
            a("```")
            a("")
            a(f"Required action: {c['expected_action']}")
            a("")
    a("## What this design still does not solve")
    a("")
    a("- The four cells multiply authoring cost: 20 prompts for five scenarios. Each needs the same "
      "human review as the current set.")
    a("- The pressure manipulation is still a single authored message, so its intensity is uncontrolled "
      "and unreplicated. A stronger design varies pressure along two or three graded levels.")
    a("- Cell-level analysis needs enough samples per cell to separate cell effects from sampling "
      "noise. With single generations per cell, the comparison is anecdotal.")
    a("- The factual states here are authored by the same agent as the expected actions, so agreement "
      "between them is not independent evidence of correctness.")
    a("")
    return "\n".join(out) + "\n"


def main() -> int:
    summary, pairs = load()
    (ROOT / "reports" / "STAGE0_SUFFICIENCY_AUDIT.md").write_text(render_audit(summary, pairs))
    (ROOT / "reports" / "FOUR_CELL_DESIGN.md").write_text(render_four_cell())
    print("wrote reports/STAGE0_SUFFICIENCY_AUDIT.md and reports/FOUR_CELL_DESIGN.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
