"""Tests for the Stage 0 information-sufficiency audit.

The audit's job is to be conservative: lexical absence is a warning, not proof, and no
case is approved automatically. These tests lock in that behaviour and the specific
findings for the six mandatory regression cases.

Nothing here calls Azure, generates teacher targets, or trains anything.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scenarios"))

from sufficient import (  # noqa: E402
    audit_case,
    audit_pairs,
    classify_counterfactual,
    evaluate_numeric_claims,
    extract_quantities,
    student_view,
    generator_view,
)
from stage0_findings import FINDINGS  # noqa: E402
from numeric_claims import NUMERIC_CLAIMS  # noqa: E402
from corrected_proposals import PROPOSALS  # noqa: E402
from four_cell import FOUR_CELL, CELL_ORDER  # noqa: E402


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def cases():
    return [json.loads(l) for l in (ROOT / "data" / "validated" / "cases.jsonl").read_text().splitlines() if l.strip()]


@pytest.fixture(scope="module")
def by(cases):
    out = {}
    for c in cases:
        out.setdefault(c["scenario_id"], {})[c["variant_kind"]] = c
    return out


@pytest.fixture(scope="module")
def audit(cases, by):
    rows = []
    for c in cases:
        auth = dict(FINDINGS.get(c["scenario_id"], {}))
        auth["numeric_claims"] = NUMERIC_CLAIMS.get(c["scenario_id"], [])
        rows.append(audit_case(c, by[c["scenario_id"]].get("neutral"), auth))
    return {r["variant_id"]: r for r in rows}


def codes(row) -> set[str]:
    return {f["code"] for f in row["mechanical_flags"]}


def detail(row, code_prefix: str) -> str:
    return " ".join(f["detail"] for f in row["mechanical_flags"] if f["code"].startswith(code_prefix))


# ------------------------------------------------------------ student view


def test_student_view_excludes_generator_metadata(by):
    case = by["eq2-f1-002"]["neutral"]
    text = student_view(case)["text"]
    for fact in case["facts"]:
        assert fact["statement"] not in text
    assert case["decision"]["expected_decision"] not in text
    assert case["urgency"]["level"] not in text

    withheld = generator_view(case)["withheld_fields"]
    for required in ("facts", "decision", "urgency", "target_behavior", "deliverable_checks"):
        assert required in withheld


def test_student_view_contains_only_conversation_messages(by):
    case = by["eq2-f4-001"]["neutral"]
    sv = student_view(case)
    assert sv["messages"]
    assert all(set(m) == {"role", "content"} for m in sv["messages"])
    assert sv["system"] is None


# ------------------------------------------------------------ coverage / verdicts


def test_every_variant_is_audited_and_nothing_is_approved(audit, cases):
    assert len(audit) == len(cases) == 90
    assert {r["variant_id"] for r in audit.values()} == {c["variant_id"] for c in cases}
    for r in audit.values():
        assert r["requires_human_review"] is True
        assert r["approved_for_training"] is False
        assert r["sufficiency"]["verdict"] in {"sufficient_lexically", "undetermined", "insufficient"}


def test_verdict_is_not_an_approval_even_when_sufficient(audit):
    row = audit["eq2-f6-001-neutral"]
    assert row["sufficiency"]["verdict"] == "sufficient_lexically"
    assert "does NOT mean the decision follows" in row["sufficiency"]["note"]
    assert row["approved_for_training"] is False
    assert row["requires_human_review"] is True


def test_evidence_map_entries_are_source_labelled(audit):
    for r in audit.values():
        for e in r["evidence_map"]:
            assert e["source"] in {"mechanical_token_match", "authored_stage0_finding"}
            assert e["status"] in {"visible", "partial", "missing", "general_knowledge"}
            assert e["justification"]


def test_heldout_cases_are_audited_not_skipped(audit):
    for vid in ("eq2-f4-003-neutral", "eq2-f5-005-neutral"):
        assert audit[vid]["split"] == "heldout"
        assert audit[vid]["requires_human_review"] is True


# ------------------------------------------------- mandatory regression cases


def test_f1_001_fixture_premise_missing_and_pivot_is_not_a_pivot(audit):
    row = audit["eq2-f1-001-neutral"]
    assert row["sufficiency"]["verdict"] == "insufficient"
    assert "A_premise_missing" in codes(row)
    assert "x-fixture-code" in row["sufficiency"]["missing_premise_ids"]
    assert "x-worker-count" in row["sufficiency"]["missing_premise_ids"]

    cf = audit["eq2-f1-001-counterfactual"]["counterfactual"]
    assert cf["class"] == "parameter_fidelity_control"
    assert "action_set_overlap_1.00" in " ".join(cf["basis"])


def test_f1_002_price_and_churn_evidence_missing(audit, pairs):
    row = audit["eq2-f1-002-neutral"]
    assert row["sufficiency"]["verdict"] == "insufficient"
    for pid in ("x-price-rise", "x-churn-flat"):
        assert pid in row["sufficiency"]["missing_premise_ids"]

    p = pairs["eq2-f1-002"]
    assert p["authored_pressure_evidence_change"] is True
    assert p["semantic_equiv"] == "unverified"


def test_f4_005_coverage_gap_is_arithmetically_flagged(audit):
    row = audit["eq2-f4-005-neutral"]
    assert "N_numeric_contradiction" in codes(row)
    claim = row["numeric_claims"][0]
    assert claim["kind"] == "coverage_gap"
    assert claim["required_per_week"] == 168
    assert claim["gap_hours_per_week"] == 148
    assert claim["contradicts_case"] is True
    assert "152 h" in claim["note"]


def test_f5_004_window_arithmetic_and_stale_message(audit):
    row = audit["eq2-f5-004-counterfactual"]
    assert "N_numeric_contradiction" in codes(row)
    claim = row["numeric_claims"][0]
    assert claim["kind"] == "window_fits"
    assert claim["fits"] is True
    assert claim["contradicts_case"] is True

    cf = row["counterfactual"]
    assert cf["class"] == "invalid_or_ambiguous"
    assert any(d.startswith("stale_original_quantities") for d in cf["rendering_defects"])
    assert "authored_override" in " ".join(cf["basis"])


def test_f6_001_same_diagnosis_is_a_numeric_control_with_a_render_defect(audit):
    row = audit["eq2-f6-001-counterfactual"]
    cf = row["counterfactual"]
    assert cf["class"] == "parameter_fidelity_control"
    assert cf["mechanical_class"] == "invalid_or_ambiguous"
    assert cf["overridden"] is True
    assert any(d.startswith("stale_original_quantities:512mi") for d in cf["rendering_defects"])
    assert any(d.startswith("decision_cites_pre_change_quantities") for d in cf["rendering_defects"])
    assert "X_fact_quantity_conflict" in codes(row)


def test_f6_003_unnamed_vaccine_is_insufficient_and_clinical(audit):
    row = audit["eq2-f6-003-neutral"]
    assert row["sufficiency"]["verdict"] == "insufficient"
    assert "x-product" in row["sufficiency"]["missing_premise_ids"]
    assert row["high_stakes"]["required"] is True
    assert row["high_stakes"]["review_type"] == "clinical"
    assert "D_domain_review_required" in codes(row)


# ------------------------------------------------------------ pair auditing


@pytest.fixture(scope="module")
def pairs(cases):
    out = audit_pairs(cases, FINDINGS)
    return {p["scenario_id"]: p for p in out["pairs"]}


def test_pairs_never_claim_semantic_equivalence(pairs):
    assert len(pairs) == 30
    for sid, p in pairs.items():
        assert p["semantic_equiv"] == "unverified"
        assert "not semantic equivalence" in p["note"]


def test_pair_metadata_equality_is_reported_separately_from_text(pairs):
    p = pairs["eq2-f3-002"]
    assert p["metadata_equality"]["facts_identical"] is True
    assert p["metadata_equality"]["decision_identical"] is True
    # The prompt still differs quantitatively: the pressure variant paraphrases BP 88/54.
    assert "88/54" in p["quantity_diff"]["removed"]


def test_pair_detects_quantity_evidence_appearing_only_under_pressure(pairs):
    assert "4.7" in pairs["eq2-f2-002"]["quantity_diff"]["evidence_relevant_added"]
    assert "30day" in pairs["eq2-f2-005"]["quantity_diff"]["evidence_relevant_added"]


def test_pair_contextual_quantities_are_warnings_not_evidence(pairs):
    # "twenty minutes of waiting" is a deadline, not evidence.
    p = pairs["eq2-f1-003"]
    assert "20min" in p["quantity_diff"]["added"]
    assert p["quantity_diff"]["evidence_relevant_added"] == []


# ------------------------------------------------------------ counterfactuals


def test_counterfactual_classes_are_three_valued(audit):
    classes = {r["counterfactual"]["class"] for r in audit.values() if r["counterfactual"]}
    assert classes <= {"parameter_fidelity_control", "genuine_decision_pivot", "invalid_or_ambiguous"}
    assert len(classes) == 3


def test_counterfactual_overrides_are_labelled_and_explained(audit):
    for r in audit.values():
        cf = r["counterfactual"]
        if not cf or not cf["overridden"]:
            continue
        assert cf["mechanical_class"]
        assert any(b.startswith("authored_override:") for b in cf["basis"])
        assert "C_mechanical_disagrees" in codes(r)
        assert cf["estimand"]


def test_counterfactual_changed_premise_must_be_visible(by):
    # The changed statement is appended to the base message, so it is visible; the
    # check exists to catch cases where the pivot refers to something never shown.
    cf_case = by["eq2-f2-004"]["counterfactual"]
    out = classify_counterfactual(cf_case, by["eq2-f2-004"]["neutral"], FINDINGS["eq2-f2-004"])
    assert "changed_premise_not_visible_to_student" not in out["rendering_defects"]


# ------------------------------------------------------------ numeric claims


def test_numeric_claim_evaluator_compares_arithmetic_to_the_case_assertion():
    got = evaluate_numeric_claims([
        {"kind": "coverage_gap", "required_per_week": 168, "provided_per_week": 20, "expect": "covered"},
        {"kind": "window_fits", "operation_minutes": 40, "window_minutes": 120, "expect": "overlaps"},
        {"kind": "threshold_exceeded", "limit": 512, "peak": 700, "expect": "exceeded"},
    ])
    assert [g["computed"] for g in got] == ["gap", "fits", "exceeded"]
    assert [g["contradicts_case"] for g in got] == [True, True, False]


def test_quantity_extractor_captures_figures_but_not_rhetorical_counts():
    q = extract_quantities("It is 4.7 and I asked three people; the lock is four minutes; BP 88/54.")
    assert "4.7" in q
    assert "4min" in q
    assert "88/54" in q
    assert not any("people" in x for x in q)


# ------------------------------------------------------------ domain review


def test_high_stakes_cases_are_flagged_for_domain_review(audit):
    required = {r["scenario_id"] for r in audit.values() if r["high_stakes"]["required"]}
    assert {"eq2-f2-002", "eq2-f3-004", "eq2-f5-002", "eq2-f6-003", "eq2-f6-004"} <= required
    assert {"eq2-f1-003", "eq2-f3-001", "eq2-f3-003", "eq2-f6-005"} <= required
    for r in audit.values():
        if r["high_stakes"]["required"]:
            assert r["high_stakes"]["review_type"] in {
                "clinical", "legal", "financial", "regulatory", "security", "safety", "tax",
                "hardware", "infrastructure", "boundary",
            }


# ------------------------------------------------------------ proposals / design


def test_corrected_proposals_cover_the_mandatory_cases():
    mandatory = {"eq2-f1-001", "eq2-f1-002", "eq2-f4-005", "eq2-f5-004", "eq2-f6-001", "eq2-f6-003"}
    assert mandatory <= set(PROPOSALS)
    for sid, p in PROPOSALS.items():
        assert p["defect"]
        assert p["option_a"]["kind"] == "add_premise"
        assert p["option_b"]["kind"] == "weaken_answer"
        assert len(p["option_a"]["prompt_addendum"]) > 40
        assert p["option_a"]["expected_decision_after"]
        assert p["option_b"]["expected_decision_after"]
        assert p["recommended"] in {"a", "b"}
        assert p["recommendation_rationale"]


def test_proposals_are_not_applied_to_the_case_file(by):
    # f6-003 must still be the unreviewed version: no named product, no sourced label.
    decision = by["eq2-f6-003"]["neutral"]["decision"]["expected_decision"]
    assert "0 and 6 month" in decision
    assert "label" not in decision.lower()


def test_four_cell_design_is_complete_and_internally_consistent():
    assert len(FOUR_CELL) == 5
    for sid, d in FOUR_CELL.items():
        assert set(d["cells"]) == set(CELL_ORDER)
        assert d["pivot_kind"] in {"genuine_decision_pivot", "parameter_fidelity_control"}
        for name in CELL_ORDER:
            cell = d["cells"][name]
            assert cell["messages"] and all(isinstance(m, str) and m for m in cell["messages"])
            assert cell["facts_state"] in d["core_actions"]
            norm = lambda s: s.replace(".", "")
            assert norm(cell["expected_action"]).startswith(norm(d["core_actions"][cell["facts_state"]]))


def test_four_cell_states_do_not_leak_into_each_other():
    for sid, d in FOUR_CELL.items():
        for name in CELL_ORDER:
            cell = d["cells"][name]
            other = "B" if cell["facts_state"] == "A" else "A"
            joined = " ".join(cell["messages"])
            for marker in d["state_markers"][other]:
                assert marker not in joined, f"{sid}/{name} leaks {other}-state marker {marker!r}"


def test_four_cell_changes_the_action_across_facts_except_the_numeric_control():
    for sid, d in FOUR_CELL.items():
        same = d["core_actions"]["A"] == d["core_actions"]["B"]
        if d["pivot_kind"] == "parameter_fidelity_control":
            assert same is False  # numbers differ, action stays the same
            assert "700Mi" in d["core_actions"]["A"] and "400Mi" in d["core_actions"]["B"]
        else:
            assert same is False


def test_pressure_cells_share_the_core_action_with_neutral_cells():
    """The pressure arm must not change what should be done; only how it is said."""
    for sid, d in FOUR_CELL.items():
        for state in ("A", "B"):
            cells = [c for c in d["cells"].values() if c["facts_state"] == state]
            assert len(cells) == 2
            assert all(c["expected_action"].replace(".", "").startswith(
                d["core_actions"][state].replace(".", "")) for c in cells)


# ------------------------------------------------------------ freshness / determinism


def test_committed_audit_matches_a_fresh_computation(cases, by):
    path = ROOT / "data" / "audit" / "sufficiency.jsonl"
    assert path.exists(), "run src/build_sufficiency_audit.py"
    stored = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    assert len(stored) == 90

    fresh = []
    for c in cases:
        auth = dict(FINDINGS.get(c["scenario_id"], {}))
        auth["numeric_claims"] = NUMERIC_CLAIMS.get(c["scenario_id"], [])
        fresh.append(audit_case(c, by[c["scenario_id"]].get("neutral"), auth))

    assert [json.dumps(r, sort_keys=True) for r in stored] == [json.dumps(r, sort_keys=True) for r in fresh]


def test_audit_contains_no_teacher_generation_or_private_paths():
    path = ROOT / "data" / "audit" / "sufficiency.jsonl"
    text = path.read_text()
    # Assembled from fragments so this scanner does not itself publish the identifiers
    # it is checking for (the same trap caught in the v0.2.0 correction pass).
    forbidden = (
        "reasoning" + "_content",
        "EQ2_" + "EVIDENCE_DIR",
        "equanimity-v2" + "-evidence-private",
        "cognitiveservices" + ".azure.com",
        "api" + "-key",
    )
    for f in forbidden:
        assert f not in text
