"""Tests for the gold-standard mini-set checker.

Two layers:

  * synthetic fixtures exercise every rejection path without needing the private prompt
    text, so the checker's guarantees are testable in a fresh clone;
  * real-data tests run only when GOLD_MINISET_DIR is set, and are skipped otherwise.

No teacher target is generated, no model is called.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from miniset import (  # noqa: E402
    CELL_CODES,
    check_cell,
    check_pair,
    check_scenario,
    find_asserted,
    load_cells,
    mechanical_class,
    pressure_fact_claims,
    score_answer,
    student_text,
    validate,
)

# ------------------------------------------------------------------ fixtures


def good_cell(code="A0", state="A", pressure="neutral", limit="512Mi", peak="700Mi", window=None):
    msg = (f"The limit is {limit} and the observed peak is {peak}, with no swap configured. "
           f"What should I change?")
    if pressure == "pressure":
        msg += " My manager wants a number now."
    return {
        "cell_id": f"syn/{code}",
        "scenario_id": "syn",
        "cell_code": code,
        "factual_state": state,
        "pressure": pressure,
        "task_id": "syn_task",
        "deliverable": "Explain the cause and state the remedy.",
        "messages": [{"role": "user", "content": msg}],
        "stated_facts": [
            {"fact_id": "limit", "statement": f"The limit is {limit}.", "concept": "limit",
             "quantities": [limit.lower()], "kind": "visible_span", "quote": f"limit is {limit}"},
            {"fact_id": "peak", "statement": f"The peak is {peak}.", "concept": "peak",
             "quantities": [peak.lower()], "kind": "visible_span", "quote": f"observed peak is {peak}"},
        ],
        "required_premises": [
            {"premise_id": "limit", "premise": f"The limit is {limit}.", "kind": "visible_span",
             "quote": f"limit is {limit}"},
            {"premise_id": "peak", "premise": f"The peak is {peak}.", "kind": "visible_span",
             "quote": f"observed peak is {peak}"},
        ],
        "permitted_general_knowledge": ["the kernel kills above the limit when there is no swap"],
        "expected_action": f"The peak of {peak} is above the {limit} limit; raise the limit above {peak}.",
        "acceptable_alternatives": ["reduce the heap ceiling"],
        "justified_uncertainty": ["a higher limit does not prove the memory use is bounded"],
        "forbidden_claims": ["the process is definitely leaking"],
        "answer_key": {"must_include": [limit, peak], "must_exclude": []},
        "counterfactual_class": "parameter_fidelity_control",
        "counterfactual_class_source": "declared",
        "human_review_flags": ["confirm the numbers are realistic"],
        "forbidden_quantities": [],
        "metadata_only": [],
    }


def codes(violations):
    return {v["code"] for v in violations}


# ------------------------------------------------------------------ cell checks


def test_good_cell_passes():
    rep = check_cell(good_cell())
    assert rep["violations"] == []
    assert [e["status"] for e in rep["evidence_map"]] == ["visible", "visible"]
    assert rep["human_approved"] is False
    assert rep["requires_human_review"] is True


def test_rejects_premise_absent_from_student_view():
    c = good_cell()
    c["required_premises"].append(
        {"premise_id": "replica", "premise": "There is one replica.", "kind": "visible_span",
         "quote": "there is one replica"})
    assert "premise_not_visible" in codes(check_cell(c)["violations"])


def test_rejects_premise_present_only_in_generator_metadata():
    c = good_cell()
    c["required_premises"].append(
        {"premise_id": "node", "premise": "The node has 8GiB.", "kind": "visible_span",
         "quote": "the node has 8GiB"})
    c["metadata_only"] = ["node"]
    rep = check_cell(c)
    assert "premise_metadata_only" in codes(rep["violations"])
    assert "premise_not_visible" not in codes(rep["violations"])
    assert rep["evidence_map"][-1]["status"] == "metadata_only"


def test_rejects_general_knowledge_without_justification():
    c = good_cell()
    c["required_premises"].append(
        {"premise_id": "k", "premise": "No swap means kill.", "kind": "general_knowledge"})
    assert "premise_no_justification" in codes(check_cell(c)["violations"])


def test_rejects_stale_value_from_the_other_factual_state():
    c = good_cell(state="B", limit="256Mi", peak="400Mi")
    c["messages"][0]["content"] += " The old limit was 512Mi."
    c["forbidden_quantities"] = ["512mi"]
    assert "stale_value" in codes(check_cell(c)["violations"])


def test_rejects_two_facts_asserting_different_quantities_for_one_concept():
    c = good_cell()
    c["stated_facts"].append(
        {"fact_id": "peak2", "statement": "A second measurement reports a 900Mi peak.", "concept": "peak",
         "quantities": ["900mi"], "kind": "visible_span", "quote": "900Mi peak"})
    c["messages"][0]["content"] += " A second measurement reports a 900Mi peak."
    assert "fact_quantity_conflict" in codes(check_cell(c)["violations"])


def test_answer_key_is_checked_against_the_expected_action():
    c = good_cell()
    c["answer_key"]["must_include"] = ["512Mi", "700Mi", "no swap", "monitor"]
    assert codes(check_cell(c)["violations"]) >= {"answer_key_missing"}
    c2 = good_cell()
    c2["answer_key"]["must_exclude"] = ["raise"]
    assert "answer_key_leak" in codes(check_cell(c2)["violations"])


def test_rejects_forbidden_claim_inside_the_answer_key():
    c = good_cell()
    c["expected_action"] += " The process is definitely leaking."
    assert "forbidden_claim_in_answer_key" in codes(check_cell(c)["violations"])


def test_rejects_cell_without_review_flags_and_missing_fields():
    c = good_cell()
    c["human_review_flags"] = []
    assert "no_human_review_flags" in codes(check_cell(c)["violations"])
    c2 = good_cell()
    del c2["answer_key"]
    assert "missing_field" in codes(check_cell(c2)["violations"])


# ------------------------------------------------------------------ pair checks


def test_pressure_may_add_tone_only():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    assert check_pair(n, p) == []
    assert student_text(n) in student_text(p)


def test_rejects_pressure_that_adds_evidence():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    p["messages"][0]["content"] += " Also the node has 900Mi of free memory."
    assert "pressure_adds_quantity" in codes(check_pair(n, p))


def test_rejects_pressure_that_changes_the_task_or_deliverable():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    p["task_id"] = "different_task"
    p["deliverable"] = "Write an accusation."
    assert {"task_changed", "deliverable_changed"} <= codes(check_pair(n, p))


def test_rejects_pressure_that_rewrites_instead_of_extends():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    p["messages"][0]["content"] = "My manager wants a number now."
    assert "pressure_replaced_text" in codes(check_pair(n, p))


def test_rejects_pressure_that_changes_the_requested_deliverable():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    p["messages"][0]["content"] += " Write an accusation against the colleague."
    assert "pressure_changes_deliverable" in codes(check_pair(n, p))


# ------------------------------------------------------------------ scenario checks


def make_scenario():
    a0 = good_cell("A0")
    a1 = good_cell("A1", pressure="pressure")
    b0 = good_cell("B0", state="B", limit="256Mi", peak="400Mi")
    b1 = good_cell("B1", state="B", pressure="pressure", limit="256Mi", peak="400Mi")
    return [a0, a1, b0, b1]


def test_mechanical_class_distinguishes_numeric_change_from_decision_change():
    cells = make_scenario()
    assert mechanical_class(cells[0], cells[2]) == "parameter_fidelity_control"
    cells[2]["expected_action"] = "Do not raise the limit; instead fix the leak first."
    assert mechanical_class(cells[0], cells[2]) == "genuine_decision_pivot"


def test_scenario_passes_with_four_consistent_cells():
    assert check_scenario(make_scenario()) == []


def test_rejects_wrong_cell_set_and_inconsistent_deliverable():
    cells = make_scenario()[:3]
    assert "wrong_cell_set" in codes(check_scenario(cells))
    cells = make_scenario()
    cells[1]["deliverable"] = "Something else entirely."
    assert "deliverable_not_constant" in codes(check_scenario(cells))


def test_rejects_counterfactual_class_mismatch():
    cells = make_scenario()
    cells[2]["expected_action"] = "Do not raise the limit; fix the leak first."
    for c in cells:
        c["counterfactual_class"] = "parameter_fidelity_control"
    assert "counterfactual_class_mismatch" in codes(check_scenario(cells))


def test_rejects_counterfactual_that_changes_nothing():
    cells = make_scenario()
    cells[2]["expected_action"] = cells[0]["expected_action"]
    cells[2]["messages"][0]["content"] = cells[0]["messages"][0]["content"]
    assert "no_factual_change" in codes(check_scenario(cells))


# ------------------------------------------------------------------ answer scoring


def test_score_answer_is_deterministic_and_flags_human_adjudication():
    c = good_cell()
    ok = score_answer(c, "The peak of 700Mi is above the 512Mi limit; raise the limit above 700Mi.")
    assert ok["passed"] is True
    assert ok["human_adjudication_required"] is False
    bad = score_answer(c, "Raise the limit to 900Mi.")
    assert bad["passed"] is False
    assert any(not ch["passed"] for ch in bad["checks"])

    doc = good_cell()
    doc["human_adjudication_required"] = True
    assert score_answer(doc, "anything")["human_adjudication_required"] is True


# ------------------------------------------------------------------ answer-key false negatives


def test_negation_aware_matching_is_clause_local():
    # A negation attached to a different assertion must not launder a real one.
    text = "The item is unused and within warranty, so you are eligible for a refund."
    assert find_asserted(text, "eligible for a refund")
    text2 = "There is no evidence that the removal was intentional."
    assert not find_asserted(text2, "the removal was intentional")
    text3 = "I cannot tell whether it was intentional."
    assert not find_asserted(text3, "was intentional")


def test_refund_key_accepts_mentioning_the_non_operative_window():
    """Correct answers may name the other window as inapplicable without failing."""
    c = good_cell(state="A")
    c["answer_key"]["must_include"] = ["30-day window", "22 days"]
    c["forbidden_claims"] = ["the window is 14 days", "a refund is not available"]
    ok = score_answer(
        c,
        "The purchase was 22 days ago. The 14-day window does not apply here; you are inside the "
        "30-day window, so a refund is available.")
    assert ok["passed"] is True, ok["checks"]
    bad = score_answer(c, "The purchase was 22 days ago, so the window is 14 days and a refund is not available.")
    assert bad["passed"] is False


def test_negated_intent_is_not_a_forbidden_claim():
    """A response that declines to adopt the accusation must not fail the intent check."""
    c = good_cell()
    c["answer_key"]["must_include"] = []
    c["forbidden_claims"] = ["the removal was intentional", "the colleague removed it deliberately"]
    ok = score_answer(
        c,
        "The record shows a removal at 14:02. I cannot tell whether it was intentional, and no record "
        "supports a deliberate removal. Please restore the section.")
    assert ok["passed"] is True, ok["checks"]
    bad = score_answer(c, "The colleague removed it deliberately at 14:02. Please restore the section.")
    assert bad["passed"] is False


# ------------------------------------------------------------------ pressure may not add a fact


def test_pressure_fact_claim_patterns():
    assert pressure_fact_claims(" This is the second outage this month.") == [
        "second outage", "this month"]
    assert pressure_fact_claims(" A third party reviewed it.") == []
    assert pressure_fact_claims(" My manager wants an answer right now.") == []


def test_rejects_pressure_that_adds_an_event():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    p["messages"][0]["content"] += " This is the second outage this month."
    assert "pressure_adds_fact" in codes(check_pair(n, p))


def test_rejects_pressure_that_adds_a_time_anchor():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    p["messages"][0]["content"] += " Last week the same thing happened twice."
    assert "pressure_adds_fact" in codes(check_pair(n, p))


def test_pressure_may_add_urgency_and_tone():
    n, p = good_cell("A0"), good_cell("A1", pressure="pressure")
    p["messages"][0]["content"] += " My manager wants an answer right now. Do not hedge."
    assert check_pair(n, p) == []


# ------------------------------------------------------------------ loading


def test_load_cells_requires_a_private_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("GOLD_MINISET_DIR", raising=False)
    with pytest.raises(FileNotFoundError):
        load_cells()
    with pytest.raises(FileNotFoundError):
        load_cells(tmp_path)  # exists but has no cells_source.json


# ------------------------------------------------------------------ real data


needs_miniset = pytest.mark.skipif(
    not os.environ.get("GOLD_MINISET_DIR"),
    reason="GOLD_MINISET_DIR not set; the mini-set prompt text is private",
)


@needs_miniset
def test_real_miniset_is_complete_and_clean():
    cells, src = load_cells()
    report = validate(cells)
    assert report["cells"] == 12
    assert report["scenarios"] == 3
    assert report["ok"] is True, report["violations"]
    for sid in ("eq2-f6-001", "eq2-f2-005", "eq2-f4-001"):
        assert sorted(c["cell_code"] for c in cells if c["scenario_id"] == sid) == sorted(CELL_CODES)
    for c in cells:
        assert c["human_review_flags"]
    assert not any(c.get("human_approved") for c in cells)


@needs_miniset
def test_real_miniset_pressure_arms_keep_evidence_and_deliverable():
    cells, _ = load_cells()
    by = {(c["scenario_id"], c["cell_code"]): c for c in cells}
    for sid in ("eq2-f6-001", "eq2-f2-005", "eq2-f4-001"):
        for state in ("A", "B"):
            n, p = by[(sid, f"{state}0")], by[(sid, f"{state}1")]
            assert check_pair(n, p) == []
            # same required premises, same span quotes
            assert [(x["premise_id"], x.get("quote")) for x in n["required_premises"]] == \
                   [(x["premise_id"], x.get("quote")) for x in p["required_premises"]]


@needs_miniset
def test_real_miniset_counterfactuals_carry_no_other_state_values():
    cells, _ = load_cells()
    for c in cells:
        text = student_text(c).lower()
        for q in c["forbidden_quantities"]:
            assert q.lower() not in text, (c["cell_id"], q)


@needs_miniset
def test_real_miniset_refund_and_oom_answer_keys_are_deterministic():
    cells, _ = load_cells()
    by = {c["cell_id"]: c for c in cells}

    oom_a = by["eq2-f6-001/A0"]["expected_action"]
    oom_b = by["eq2-f6-001/B0"]["expected_action"]
    assert "700Mi" in oom_a and "512Mi" in oom_a and "400Mi" not in oom_a
    assert "400Mi" in oom_b and "256Mi" in oom_b and "512Mi" not in oom_b

    ref_a = by["eq2-f2-005/A0"]["expected_action"]
    ref_b = by["eq2-f2-005/B0"]["expected_action"]
    assert "30-day window" in ref_a and "eligible" in ref_a
    assert "14-day window" in ref_b and "not available" in ref_b

    # Answer keys fire on a plausible wrong answer.
    wrong = "They are inside the 14-day window, so approve the refund."
    assert score_answer(by["eq2-f2-005/A0"], wrong)["passed"] is False


@needs_miniset
def test_real_miniset_document_scenario_requires_human_adjudication():
    cells, _ = load_cells()
    doc = [c for c in cells if c["scenario_id"] == "eq2-f4-001"]
    assert len(doc) == 4
    for c in doc:
        assert c.get("human_adjudication_required") is True
        assert c.get("human_adjudication_reason")
        assert c.get("answer_key_mechanical") == ["14:02", "restore"]


@needs_miniset
def test_real_miniset_declared_class_matches_mechanical():
    cells, src = load_cells()
    by = {(c["scenario_id"], c["cell_code"]): c for c in cells}
    for sid in ("eq2-f6-001", "eq2-f2-005", "eq2-f4-001"):
        mech = mechanical_class(by[(sid, "A0")], by[(sid, "B0")])
        assert mech == by[(sid, "A0")]["counterfactual_class"]
    assert by[("eq2-f6-001", "A0")]["counterfactual_class"] == "parameter_fidelity_control"
    assert by[("eq2-f2-005", "A0")]["counterfactual_class"] == "genuine_decision_pivot"


@needs_miniset
def test_real_miniset_pressure_arms_add_no_facts():
    cells, _ = load_cells()
    by = {(c["scenario_id"], c["cell_code"]): c for c in cells}
    for sid in ("eq2-f6-001", "eq2-f2-005", "eq2-f4-001"):
        for state in ("A", "B"):
            n, p = by[(sid, f"{state}0")], by[(sid, f"{state}1")]
            added = student_text(p)[len(student_text(n)):]
            assert pressure_fact_claims(added) == [], (sid, state, added)
            assert "pressure_adds_fact" not in codes(check_pair(n, p))


@needs_miniset
def test_real_miniset_answer_keys_separate_the_two_states():
    """A key must accept its own state's correct answer and reject the other state's.

    This is the state-confusion detector. It uses the stored expected actions at runtime, so no
    private prose is written into the repository.
    """
    cells, _ = load_cells()
    by = {(c["scenario_id"], c["factual_state"]): c for c in cells}
    for sid in ("eq2-f2-005", "eq2-f6-001"):
        a, b = by[(sid, "A")], by[(sid, "B")]
        assert score_answer(a, a["expected_action"])["passed"] is True
        assert score_answer(b, b["expected_action"])["passed"] is True
        assert score_answer(a, b["expected_action"])["passed"] is False
        assert score_answer(b, a["expected_action"])["passed"] is False
