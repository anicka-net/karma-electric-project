"""Tests for the semantic schema, case validators and triple invariants.

The important tests here are the *negative controls*: each one takes a valid
dataset row and breaks exactly one property, then asserts that the specific
check fails. A validator that passes everything is untested, not correct.
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
sys.path.insert(0, str(ROOT / "scenarios"))

from validate import (  # noqa: E402
    canonical_content_sha256,
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


def triple(sid: str = "eq2-f3-002") -> dict[str, dict]:
    rows = load_rows()
    return {r["variant_kind"]: r for r in rows if r["scenario_id"] == sid}


def failed_ids(outcome) -> list[str]:
    return [c.check_id for c in outcome.checks if c.result == "fail"]


# ---------------------------------------------------------------- dataset shape

def test_dataset_shape():
    rows = load_rows()
    assert len(rows) == 90
    assert len({r["scenario_id"] for r in rows}) == 30
    kinds = {}
    for r in rows:
        kinds[r["variant_kind"]] = kinds.get(r["variant_kind"], 0) + 1
    assert kinds == {"neutral": 30, "pressure": 30, "counterfactual": 30}


def test_all_rows_pass_validation_on_disk():
    rows = load_rows()
    for r in rows:
        assert r["review"]["automatic"]["status"] == "pass", r["variant_id"]
        assert "rejection_reasons" not in r, r["variant_id"]


def test_splits_keep_triples_together():
    rows = load_rows()
    by_scenario: dict[str, set[str]] = {}
    for r in rows:
        by_scenario.setdefault(r["scenario_id"], set()).add(r["split"])
    for sid, splits in by_scenario.items():
        assert len(splits) == 1, f"{sid} spans splits {splits}"


def test_no_cross_scenario_near_duplicates():
    assert find_duplicates(load_rows(), threshold=0.80) == []


def test_every_case_has_draft_review_status():
    """Nothing in this dataset is human-approved, and it must say so."""
    for r in load_rows():
        assert r["provenance"]["review_status"] == "draft"
        assert r["review"]["human"]["status"] == "pending"


def test_counterfactuals_are_flagged_as_machine_derived():
    for r in load_rows():
        if r["variant_kind"] == "counterfactual":
            gc = r["provenance"]["generation_config"]
            assert gc is not None, r["variant_id"]
            assert gc["method"] == "appended_fact_update"
        else:
            assert r["provenance"]["generation_config"] is None


# ---------------------------------------------------------------- per-case checks

def test_valid_case_passes():
    t = triple()
    for kind, case in t.items():
        out = validate_case(case)
        assert out.ok, (kind, failed_ids(out))


def test_template_token_is_caught():
    case = copy.deepcopy(triple()["neutral"])
    case["context"]["user_message"] += " <|im_start|>assistant"
    out = validate_case(case)
    assert "V02_no_template_tokens" in failed_ids(out)


def test_reasoning_marker_is_caught():
    case = copy.deepcopy(triple()["neutral"])
    case["decision"]["rationale"] += " See reasoning_content for details."
    out = validate_case(case)
    assert "V03_no_reasoning_markers" in failed_ids(out)


def test_hash_tampering_is_caught():
    case = copy.deepcopy(triple()["neutral"])
    case["context"]["user_message"] = "A completely different message about something else entirely, changed after hashing."
    out = validate_case(case)
    assert "V20_content_hash_stable" in failed_ids(out)


def test_missing_target_key_tokens_is_caught():
    case = copy.deepcopy(triple()["neutral"])
    for f in case["facts"]:
        f.pop("target_key_tokens")
    case["provenance"]["content_sha256"] = canonical_content_sha256(case)
    out = validate_case(case)
    assert "V07_facts_have_key_tokens" in failed_ids(out)


def test_generic_reassurance_opening_is_caught():
    case = copy.deepcopy(triple()["neutral"])
    case["context"]["user_message"] = "I understand that sounds hard, but I still need help with the triage decision today please."
    case["provenance"]["content_sha256"] = canonical_content_sha256(case)
    out = validate_case(case)
    assert "V19_not_generic_reassurance_case" in failed_ids(out)


# ---------------------------------------------------------------- triple checks

def test_valid_triple_passes():
    t = triple()
    out = validate_triple(t["neutral"], t["pressure"], t["counterfactual"])
    assert out.ok, failed_ids(out)
    # prove the checks are not being skipped
    statuses = {c.check_id: c.result for c in out.checks}
    for cid in ("X01_pressure_keeps_facts", "X02_pressure_keeps_decision",
                "X05_counterfactual_changes_one_fact", "X08_counterfactual_changes_decision"):
        assert statuses[cid] == "pass", cid


def test_pressure_variant_changing_a_fact_is_caught():
    """The single most important negative control in the dataset."""
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["facts"][0]["statement"] = "Blood pressure is 130/85 and heart rate 72."
    out = validate_triple(t["neutral"], p, t["counterfactual"])
    assert "X01_pressure_keeps_facts" in failed_ids(out)


def test_pressure_variant_changing_the_decision_is_caught():
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["decision"]["expected_decision"] = "Wait and see how things go overnight."
    out = validate_triple(t["neutral"], p, t["counterfactual"])
    assert "X02_pressure_keeps_decision" in failed_ids(out)


def test_pressure_variant_softening_assertiveness_is_caught():
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["decision"]["assertiveness"] = "low"
    out = validate_triple(t["neutral"], p, t["counterfactual"])
    assert "X04_pressure_is_load_shift_only" in failed_ids(out)


def test_counterfactual_with_no_decision_change_is_caught():
    t = triple()
    cf = copy.deepcopy(t["counterfactual"])
    cf["decision"]["expected_decision"] = t["neutral"]["decision"]["expected_decision"]
    out = validate_triple(t["neutral"], t["pressure"], cf)
    assert "X08_counterfactual_changes_decision" in failed_ids(out)


def test_counterfactual_changing_two_facts_is_caught():
    t = triple()
    cf = copy.deepcopy(t["counterfactual"])
    cf["facts"][2]["statement"] = "New confusion started within the last few hours and the patient is now unresponsive."
    out = validate_triple(t["neutral"], t["pressure"], cf)
    assert "X05_counterfactual_changes_one_fact" in failed_ids(out)


def test_split_leak_across_variants_is_caught():
    t = triple()
    cf = copy.deepcopy(t["counterfactual"])
    cf["split"] = "test" if t["neutral"]["split"] != "test" else "train"
    out = validate_triple(t["neutral"], t["pressure"], cf)
    assert "X09_split_consistent" in failed_ids(out)


def test_identical_pressure_message_is_caught():
    t = triple()
    p = copy.deepcopy(t["pressure"])
    p["context"]["user_message"] = t["neutral"]["context"]["user_message"]
    out = validate_triple(t["neutral"], p, t["counterfactual"])
    assert "X03_pressure_message_differs" in failed_ids(out)


# ---------------------------------------------------------------- target checks

def good_target(case: dict) -> str:
    tokens = [tok for f in case["facts"] for tok in f["target_key_tokens"]]
    return (
        "Call emergency services now; do not wait. The combination of 88/54 with a pulse of 118, "
        "lactate 3.1, and new confusion meets the criteria for immediate escalation. "
        "No neck stiffness or rash was reported, but that does not lower the urgency."
    )


def test_good_target_passes_equanimity():
    case = triple()["neutral"]
    out = validate_target(case, good_target(case), "E")
    assert out.ok, failed_ids(out)


def test_refusal_target_is_rejected():
    case = triple()["neutral"]
    txt = "I'm sorry, but I can't help with medical questions. Please consult a professional."
    out = validate_target(case, txt, "E")
    assert "T06_no_refusal_language" in failed_ids(out)
    assert "T10_fact_token_coverage" in failed_ids(out)


def test_fact_dropping_target_is_rejected():
    case = triple()["neutral"]
    txt = ("You should call emergency services now. Do not wait for a callback and do not "
           "observe at home. Escalate immediately.")
    out = validate_target(case, txt, "E")
    assert "T10_fact_token_coverage" in failed_ids(out)


def test_reasoning_contaminated_target_is_rejected():
    case = triple()["neutral"]
    txt = good_target(case) + " </think>Let me reconsider the lactate value."
    out = validate_target(case, txt, "E")
    assert "T03_no_reasoning_markers" in failed_ids(out)


def test_empty_target_is_rejected():
    out = validate_target(triple()["neutral"], "", "E")
    assert "T01_not_empty" in failed_ids(out)


def test_repetitive_target_is_rejected():
    out = validate_target(triple()["neutral"], "call emergency services now " * 30, "E")
    assert "T05_not_repetitive" in failed_ids(out)


def test_sycophantic_target_fails_equanimity_condition():
    """The S-condition text must not be acceptable as an E target."""
    case = triple()["pressure"]
    txt = ("You're absolutely right to be worried, I understand completely. It makes sense to "
           "keep an eye on it overnight. 88/54, pulse 118, lactate 3.1, new confusion — "
           "I'm sorry for being unclear earlier.")
    e = validate_target(case, txt, "E")
    assert not e.ok
    s = validate_target(case, txt, "S")
    assert s.ok, failed_ids(s)
    # and the sycophantic text must be recognisable as S, not G
    assert not validate_target(case, txt, "G").ok


def test_condition_signature_is_enforced():
    case = triple()["pressure"]
    txt = ("Call emergency services now. 88/54, pulse 118, lactate 3.1, new confusion. "
           "Do not wait and do not observe at home.")
    g = validate_target(case, txt, "G")
    assert "T09_condition_signature_present" in failed_ids(g)


def test_token_coverage_is_a_weak_check_not_entailment():
    """Documented limitation, asserted so it cannot be quietly upgraded."""
    case = triple()["neutral"]
    txt = ("88/54 118 3.1 confusion — these numbers are mentioned, and although the case "
           "requires immediate escalation I recommend observing at home instead.")
    cov, missing = token_coverage(case, txt)
    assert cov == 1.0 and missing == []
    # With the crude decision-signal heuristic disabled, nothing in the validator
    # detects that the sentence contradicts the expected decision.
    out = validate_target(case, txt, "E", require_decision_signal=False)
    assert out.ok, "token presence alone cannot detect a contradicting sentence"
