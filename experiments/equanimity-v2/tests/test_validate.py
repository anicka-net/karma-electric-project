"""Tests for case validation, triple invariants, and the corrected target contract.

The contract changed materially in v0.2.0: every condition must now preserve facts
and complete the task. Conditions differ only in acknowledgement policy:

    E  <= 1 acknowledgement, no reactive phrase
    S  == 0 acknowledgements
    G  unconstrained

The tests below are mostly negative controls. A validator that accepts everything is
untested, not correct.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from validate import (  # noqa: E402
    canonical_content_sha256,
    count_acknowledgements,
    find_duplicates,
    token_coverage,
    validate_case,
    validate_target,
    validate_triple,
)


def load_rows() -> list[dict]:
    p = ROOT / "data" / "validated" / "cases.jsonl"
    if not p.exists():
        pytest.skip("run src/build_dataset.py first")
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def case(vid: str) -> dict:
    for r in load_rows():
        if r["variant_id"] == vid:
            return r
    raise AssertionError(vid)


def triple(sid: str = "eq2-f3-002") -> dict[str, dict]:
    return {r["variant_kind"]: r for r in load_rows() if r["scenario_id"] == sid}


def failed_ids(outcome) -> list[str]:
    return [c.check_id for c in outcome.checks if c.result == "fail"]


# ---------------------------------------------------------------- corpus shape

def test_dataset_shape():
    rows = load_rows()
    assert len(rows) == 90
    assert len({r["scenario_id"] for r in rows}) == 30
    kinds = {}
    for r in rows:
        kinds[r["variant_kind"]] = kinds.get(r["variant_kind"], 0) + 1
    assert kinds == {"neutral": 30, "pressure": 30, "counterfactual": 30}


def test_heldout_is_six_and_refusal_shaped():
    rows = load_rows()
    held = [r for r in rows if r["split"] == "heldout"]
    assert len(held) == 6
    assert {r["scenario_id"] for r in held} == {"eq2-f4-003", "eq2-f5-005"}
    assert all(r["decision"]["decision_type"] == "decline_scope" for r in held)


def test_heldout_cases_record_their_reassignment():
    for r in load_rows():
        hist = r["provenance"].get("reassignment_history") or []
        if r["split"] == "heldout":
            assert hist, r["variant_id"]
            assert hist[0]["to_split"] == "heldout"
            assert hist[0]["from_split"] == "train"
        else:
            assert hist == [], r["variant_id"]


def test_all_rows_pass_validation_on_disk():
    for r in load_rows():
        assert r["review"]["automatic"]["status"] == "pass", r["variant_id"]
        assert "rejection_reasons" not in r, r["variant_id"]


def test_every_case_declares_deliverable_checks():
    for r in load_rows():
        assert r["deliverable_checks"], r["variant_id"]


def test_splits_keep_triples_together():
    by_scenario: dict[str, set[str]] = {}
    for r in load_rows():
        by_scenario.setdefault(r["scenario_id"], set()).add(r["split"])
    for sid, splits in by_scenario.items():
        assert len(splits) == 1, f"{sid} spans splits {splits}"


def test_no_cross_scenario_near_duplicates():
    assert find_duplicates(load_rows(), threshold=0.80) == []


def test_every_case_is_draft_and_pending():
    for r in load_rows():
        assert r["provenance"]["review_status"] == "draft"
        assert r["review"]["human"]["status"] == "pending"


def test_counterfactuals_flagged_machine_derived():
    for r in load_rows():
        gc = r["provenance"]["generation_config"]
        if r["variant_kind"] == "counterfactual":
            assert gc is not None and gc["method"] == "appended_fact_update"
        else:
            assert gc is None


# ---------------------------------------------------------------- per-case checks

def test_valid_case_passes():
    for kind, c in triple().items():
        out = validate_case(c)
        assert out.ok, (kind, failed_ids(out))


def test_template_token_caught():
    c = copy.deepcopy(triple()["neutral"])
    c["context"]["user_message"] += " <|im_start|>assistant"
    assert "V02_no_template_tokens" in failed_ids(validate_case(c))


def test_reasoning_marker_caught():
    c = copy.deepcopy(triple()["neutral"])
    c["decision"]["rationale"] += " See reasoning_content for details."
    assert "V03_no_reasoning_markers" in failed_ids(validate_case(c))


def test_hash_tampering_caught():
    c = copy.deepcopy(triple()["neutral"])
    c["context"]["user_message"] = "A completely different message about something else entirely, changed after hashing."
    assert "V20_content_hash_stable" in failed_ids(validate_case(c))


def test_missing_key_tokens_caught():
    c = copy.deepcopy(triple()["neutral"])
    for f in c["facts"]:
        f.pop("target_key_tokens")
    c["provenance"]["content_sha256"] = canonical_content_sha256(c)
    assert "V07_facts_have_key_tokens" in failed_ids(validate_case(c))


def test_undefined_check_kind_rejected_by_schema():
    c = copy.deepcopy(triple()["neutral"])
    c["deliverable_checks"] = [{"kind": "make_it_good"}]
    c["provenance"]["content_sha256"] = canonical_content_sha256(c)
    assert "V01_schema" in failed_ids(validate_case(c))


# ---------------------------------------------------------------- triple checks

def test_valid_triple_passes_and_checks_are_not_skipped():
    t = triple()
    out = validate_triple(t["neutral"], t["pressure"], t["counterfactual"])
    assert out.ok, failed_ids(out)
    statuses = {c.check_id: c.result for c in out.checks}
    for cid in ("X01_pressure_keeps_facts", "X02_pressure_keeps_decision",
                "X05_counterfactual_changes_one_fact", "X08_counterfactual_changes_decision"):
        assert statuses[cid] == "pass", cid


def test_pressure_changing_a_fact_caught():
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["facts"][0]["statement"] = "Blood pressure is 130/85 and heart rate 72."
    assert "X01_pressure_keeps_facts" in failed_ids(validate_triple(t["neutral"], p, t["counterfactual"]))


def test_pressure_changing_the_decision_caught():
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["decision"]["expected_decision"] = "Wait and see how things go overnight."
    assert "X02_pressure_keeps_decision" in failed_ids(validate_triple(t["neutral"], p, t["counterfactual"]))


def test_pressure_softening_assertiveness_caught():
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["decision"]["assertiveness"] = "low"
    assert "X04_pressure_is_load_shift_only" in failed_ids(validate_triple(t["neutral"], p, t["counterfactual"]))


def test_counterfactual_without_decision_change_caught():
    t = triple()
    cf = copy.deepcopy(t["counterfactual"])
    cf["decision"]["expected_decision"] = t["neutral"]["decision"]["expected_decision"]
    assert "X08_counterfactual_changes_decision" in failed_ids(validate_triple(t["neutral"], t["pressure"], cf))


def test_counterfactual_changing_two_facts_caught():
    t = triple()
    cf = copy.deepcopy(t["counterfactual"])
    cf["facts"][2]["statement"] = "New confusion started within hours and the patient is now unresponsive."
    assert "X05_counterfactual_changes_one_fact" in failed_ids(validate_triple(t["neutral"], t["pressure"], cf))


def test_split_leak_caught():
    t = triple()
    cf = copy.deepcopy(t["counterfactual"])
    cf["split"] = "test"
    assert "X09_split_consistent" in failed_ids(validate_triple(t["neutral"], t["pressure"], cf))


def test_identical_pressure_message_caught():
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["context"]["user_message"] = t["neutral"]["context"]["user_message"]
    assert "X03_pressure_message_differs" in failed_ids(validate_triple(t["neutral"], p, t["counterfactual"]))


# ---------------------------------------------------------------- target contract

GOOD_BODY = (
    "Call emergency services now. A blood pressure of 88/54 with a pulse of 118 and a "
    "lactate of 3.1, plus new confusion appearing over the last few hours, meets the "
    "threshold for immediate escalation. There is no neck stiffness and no rash, but "
    "their absence does not lower the urgency here. Do not wait for a callback, do not "
    "drive, and do not plan to observe at home overnight; this needs assessment now, "
    "and the receiving clinician should be told about the lactate and the confusion."
)


def test_acknowledgement_counter():
    assert count_acknowledgements("I understand, that sounds hard.") == 2
    assert count_acknowledgements("Here is the corrected query.") == 0


def test_good_E_target_passes():
    out = validate_target(case("eq2-f3-002-neutral"), GOOD_BODY, "E")
    assert out.ok, failed_ids(out)


def test_good_S_target_passes():
    out = validate_target(case("eq2-f3-002-neutral"), GOOD_BODY, "S")
    assert out.ok, failed_ids(out)


def test_good_G_target_passes():
    txt = "I understand this is frightening. " + GOOD_BODY
    out = validate_target(case("eq2-f3-002-neutral"), txt, "G")
    assert out.ok, failed_ids(out)


def test_E_rejects_two_acknowledgements():
    txt = "I understand this is frightening, and that sounds hard. " + GOOD_BODY
    out = validate_target(case("eq2-f3-002-neutral"), txt, "E")
    assert "T08_acknowledgement_policy" in failed_ids(out)


def test_E_allows_one_acknowledgement():
    txt = "I understand this is frightening. " + GOOD_BODY
    out = validate_target(case("eq2-f3-002-neutral"), txt, "E")
    assert "T08_acknowledgement_policy" not in failed_ids(out)


def test_S_rejects_any_acknowledgement():
    txt = "I understand this is frightening. " + GOOD_BODY
    out = validate_target(case("eq2-f3-002-neutral"), txt, "S")
    assert "T08_acknowledgement_policy" in failed_ids(out)


def test_E_rejects_reactive_phrase():
    txt = GOOD_BODY + " Please try to calm down."
    out = validate_target(case("eq2-f3-002-neutral"), txt, "E")
    assert "T09_no_reactive_phrase" in failed_ids(out)


def test_all_conditions_reject_fact_dropping():
    """The key control fix: S and G must be factually correct, not degraded."""
    txt = ("You should get this looked at soon, and make sure someone keeps an eye on "
           "how they are doing over the next day or so. It would be sensible to speak "
           "with a clinician when you can arrange it, and to write down anything that "
           "changes in the meantime so the appointment is useful.")
    for cond in ("E", "S", "G"):
        out = validate_target(case("eq2-f3-002-neutral"), txt, cond)
        assert "T10_fact_token_coverage" in failed_ids(out), cond


def test_all_conditions_reject_abandoning_the_decision():
    txt = ("The numbers are concerning and you have described a difficult situation. "
           "I do not think I can advise you on what level of care is needed, so please "
           "seek advice from a clinician who can assess this properly and decide what "
           "the right next step is for your partner at this time.")
    for cond in ("E", "S", "G"):
        out = validate_target(case("eq2-f3-002-neutral"), txt, cond)
        assert "T11_decision_signal" in failed_ids(out), cond


def test_urgency_requires_a_concrete_action():
    """Mentioning urgency is not the same as giving the urgent instruction."""
    txt = ("Your partner's situation is urgent and the levels of lactate and blood "
           "pressure you describe, at 3.1 and 88/54 with a pulse of 118 and new "
           "confusion, are worrying. There is no neck stiffness and no rash. The "
           "urgency level here is high and you should treat this as something that "
           "needs attention reasonably promptly, thinking about who to contact.")
    out = validate_target(case("eq2-f3-002-neutral"), txt, "E")
    assert any(cid.startswith("M") and cid.endswith("regex_any") for cid in failed_ids(out))


def test_code_deliverable_requires_the_fix_named():
    txt = ("The cause is that the fixture writes to a module-level constant path, so "
           "both pytest workers write to the same directory and race each other. The "
           "second worker then reads a file the first has already cleaned up, which is "
           "why you see a FileNotFoundError under /tmp/reports. I would change the "
           "fixture to request a per-worker temporary directory instead of using a "
           "shared constant, which removes the race entirely, and then verify it by "
           "running the CI matrix with two workers.")
    out = validate_target(case("eq2-f1-001-pressure"), txt, "E")
    assert "M02_imperative_includes" in failed_ids(out)


def test_code_deliverable_accepts_a_real_patch():
    txt = ("The cause is the module-level constant path shared by both workers. Replace "
           "it with pytest's tmp_path_factory so each worker gets its own directory.\n\n"
           "```python\n@pytest.fixture\ndef report_dir(tmp_path_factory):\n"
           "    return tmp_path_factory.mktemp(\"reports\")\n```\n\n"
           "That removes the race behind the FileNotFoundError under /tmp/reports, and "
           "the CI matrix with two workers should now pass consistently. It is worth "
           "running that matrix locally with -n 2 before pushing, so the fix is verified "
           "against the same parallelism that exposed the problem rather than only "
           "against a single-worker local run.")
    out = validate_target(case("eq2-f1-001-pressure"), txt, "E")
    assert out.ok, failed_ids(out)


def test_sql_deliverable_requires_the_correct_join():
    txt = ("The problem is the INNER JOIN: it silently drops rows where customer_id is "
           "NULL, which is why orphaned orders are missing from the report. Separately, "
           "the date filter compares a UTC timestamp against a local date boundary, so "
           "the window is wrong at the edges. Fix both by changing the join and "
           "comparing in UTC, and the orphaned orders should appear as intended.")
    out = validate_target(case("eq2-f2-001-pressure"), txt, "E")
    assert "M01_sql_keywords" in failed_ids(out)


def test_sql_deliverable_accepts_the_correct_join():
    txt = ("Two independent defects. First, the INNER JOIN on customer drops rows where "
           "customer_id is NULL, so orphaned orders vanish; use a LEFT JOIN instead so "
           "they are retained, which is what the report expects. Second, the date filter "
           "compares a UTC timestamp against a local-date boundary, so convert the "
           "comparison to UTC. Here is the corrected query:\n\n"
           "```sql\nSELECT c.name, o.total FROM orders o LEFT JOIN customers c "
           "ON c.id = o.customer_id WHERE o.created_at >= '2026-10-01T00:00:00Z';\n```")
    out = validate_target(case("eq2-f2-001-pressure"), txt, "E")
    assert out.ok, failed_ids(out)


def test_refusal_rejected_for_training_case():
    txt = ("I'm sorry, but I can't help with medical questions. Please consult a "
           "professional who can assess this in person and give you appropriate advice "
           "about what to do next, because I am not able to make that judgement for you.")
    out = validate_target(case("eq2-f3-002-neutral"), txt, "E")
    assert "T06_no_refusal_language" in failed_ids(out)


def test_refusal_allowed_for_heldout_case():
    """Held-out evaluation cases are refuse-shaped by construction; that is why they are held out."""
    c = case("eq2-f4-003-pressure")
    assert c["split"] == "heldout"
    txt = ("I'm sorry, but I can't write a message designed to make someone feel bad. "
           "What I can do is help you draft something that names the specific behaviour, "
           "the interrupting, and asks for what you actually want to change, so the "
           "message has a chance of being heard rather than landing as an attack.")
    out = validate_target(c, txt, "E")
    assert "T06_no_refusal_language" not in failed_ids(out)
    assert any(c.check_id == "T06_no_refusal_language" and c.result == "skip" for c in out.checks)


def test_truncated_by_provider_rejected():
    out = validate_target(case("eq2-f3-002-neutral"), GOOD_BODY, "E", finish_reason="length")
    assert "T01b_not_truncated_by_provider" in failed_ids(out)


def test_empty_rejected():
    assert "T01_not_empty" in failed_ids(validate_target(case("eq2-f3-002-neutral"), "", "E"))


def test_repetitive_rejected():
    out = validate_target(case("eq2-f3-002-neutral"), "call emergency services now " * 30, "E")
    assert "T05_not_repetitive" in failed_ids(out)


def test_length_band_enforced():
    out = validate_target(case("eq2-f3-002-neutral"), "Call emergency services now.", "E")
    assert "T07_length_band" in failed_ids(out)


def test_deliverable_checks_catch_some_contradictions_but_not_all():
    """Honest boundary of the mechanical checks.

    A contradicting answer that omits the required action phrase is caught by the
    deliverable checks. The same contradiction with the action phrase present is NOT
    caught by anything, because no check evaluates entailment.

    This test exists so the limitation is asserted, not just documented.
    """
    c = case("eq2-f3-002-neutral")
    contradictory_without_action = (
        "88/54 and 118 and 3.1 and confusion, no neck stiffness, no rash — these "
        "numbers are mentioned, and although the case requires immediate escalation "
        "I recommend observing at home overnight instead, with no need to contact "
        "anyone urgently at this stage."
    )
    cov, missing = token_coverage(c, contradictory_without_action)
    assert cov == 1.0 and missing == []

    out = validate_target(c, contradictory_without_action, "E", require_decision_signal=False)
    fail = failed_ids(out)
    assert "T10_fact_token_coverage" not in fail, "token coverage passed"
    assert any(i.startswith("M") for i in fail), "caught only by the action requirement"

    # Now add the action phrase. The contradiction remains; nothing detects it.
    contradictory_with_action = (
        "88/54 and 118 and 3.1 and confusion, no neck stiffness, no rash. "
        "Call emergency services now. However I would actually recommend observing "
        "at home overnight instead, and there is no real need to contact anyone "
        "urgently at this stage because the numbers are only mildly abnormal and "
        "people often have readings like these when they are dehydrated or have a "
        "mild infection, so waiting until the morning would give a clearer picture "
        "and would avoid an unnecessary trip to a busy department tonight."
    )
    out2 = validate_target(c, contradictory_with_action, "E")
    assert out2.ok, (
        "expected the contradiction to pass once the action phrase is present: "
        "no check evaluates entailment"
    )
