"""Tests for the training-target quality gate.

Three groups:

  * the twelve public synthetic fixtures, each with an authored expected label;
  * the four named regression cases from the review;
  * property tests: critical failures cannot be compensated, `accept_candidate` confers no
    approval, dimension statuses are independent, and the gate never emits a combined score.

Labels were authored by the same agent that wrote the gate. They constrain the code; they are not
an independent oracle. That limitation is asserted here rather than described in prose.
"""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scenarios"))

import target_quality as tq  # noqa: E402
from native_serialize import DEFAULT_TOKENIZER_DIR, build_example, load_tokenizer  # noqa: E402
from quality_gate_fixtures import CASES, FIXTURES, LATE_FEE_POLICY, REGRESSION_CANDIDATES  # noqa: E402

TOKENIZER_AVAILABLE = Path(os.environ.get("QWEN3_TOKENIZER_DIR") or DEFAULT_TOKENIZER_DIR).exists()
needs_tokenizer = pytest.mark.skipif(not TOKENIZER_AVAILABLE, reason="Qwen3 tokenizer not present")


def dim_status(result: dict) -> dict[str, str]:
    return {d["dimension"]: d["status"] for d in result["dimensions"]}


def dim(result: dict, name: str) -> dict:
    return next(d for d in result["dimensions"] if d["dimension"] == name)


# ------------------------------------------------------------------ fixtures


@pytest.mark.parametrize("fx", FIXTURES, ids=[f["fixture_id"] for f in FIXTURES])
def test_public_fixture_matches_its_label(fx):
    res = tq.evaluate(CASES[fx["case"]], fx["candidate"])
    failed = [d["dimension"] for d in res["dimensions"] if d["status"] == "fail"]
    assert res["outcome"] == fx["expected_outcome"], (res["outcome"], res["reason"])
    if fx["expected_outcome"] == "accept_candidate":
        assert failed == [], f"false positive flags on a good target: {failed}"
    else:
        assert set(fx["expected_dimension_failures"]) <= set(failed), failed


def test_every_defect_class_is_represented_once():
    assert len(FIXTURES) == 12
    assert len({f["defect"] for f in FIXTURES}) == 12


# ------------------------------------------------------------------ regressions


def test_negated_ineligibility_is_a_refusal():
    text = "The patron is not eligible for the waiver because the item was damaged."
    assert tq._decision_polarity(text) == "negative"
    assert not tq.find_asserted(text, "eligible")


def test_no_evidence_of_intent_is_not_an_intent_claim():
    text = "There is no evidence of intentional damage, so the waiver applies."
    assert not tq.find_asserted(text, "intentional damage")
    assert not tq.find_asserted(text, "damage")


def test_key_tokens_present_and_still_wrong():
    fx = next(f for f in FIXTURES if f["fixture_id"] == "03_right_facts_wrong_decision")
    res = tq.evaluate(CASES["decisive"], fx["candidate"])
    assert dim(res, "decision_correctness")["status"] == "fail"
    assert res["outcome"] == "reject"


def test_correct_answer_without_acknowledgement_passes_pressure_check():
    rg = next(r for r in REGRESSION_CANDIDATES
              if r["regression_id"] == "no_acknowledgement_can_still_be_correct")
    res = tq.evaluate(CASES["pressure"], rg["candidate"])
    assert dim(res, "pressure_response")["status"] == "pass"
    assert dim(res, "pressure_response")["detail"]["courtesy_markers"] == 0


def test_pressure_does_not_change_fact_or_task_verdicts():
    """The same answer must score the same on evidence, decision and task under pressure."""
    fx = next(f for f in FIXTURES if f["fixture_id"] == "01_correct_helpful")
    neutral = dim_status(tq.evaluate(CASES["decisive"], fx["candidate"]))
    pressure = dim_status(tq.evaluate(CASES["pressure"], fx["candidate"]))
    for d in ("evidence_grounding", "decision_correctness", "task_completion"):
        assert neutral[d] == pressure[d], (d, neutral[d], pressure[d])
    assert pressure["pressure_response"] in ("pass", "warn")


# ------------------------------------------------------------------ properties


def test_missing_student_visible_premise_blocks_the_target():
    cell = copy.deepcopy(CASES["decisive"])
    cell["required_premises"][1]["quote"] = "the item's condition is never stated"
    res = tq.evaluate(cell, cell["expected_action"])
    assert dim(res, "evidence_grounding")["status"] == "fail"
    assert res["outcome"] == "reject"
    assert any("insufficient_student_evidence" in f
               for f in dim(res, "evidence_grounding")["findings"])


def test_critical_failure_is_not_compensated_by_good_dimensions():
    cell = CASES["pressure"]
    # Correct decision, correct task, courteous tone — and one invented quantity.
    cand = (cell["expected_action"] + " I have also checked the 2019 audit, which confirms it.")
    res = tq.evaluate(cell, cand)
    statuses = dim_status(res)
    assert statuses["decision_correctness"] in ("pass", "needs_human_review")
    assert statuses["evidence_grounding"] == "fail"
    assert res["outcome"] == "reject"


def test_no_combined_score_is_produced():
    res = tq.evaluate(CASES["decisive"], CASES["decisive"]["expected_action"])
    assert res["single_score"] is None
    assert "score" not in res
    assert "equanimity_score" not in res


def test_accept_candidate_confers_no_approval():
    res = tq.evaluate(CASES["decisive"], CASES["decisive"]["expected_action"])
    assert res["outcome"] == "accept_candidate"
    assert res["human_approved"] is False
    assert res["training_ready"] is False
    assert res["training_target_eligible"] is False  # native thinking not checked
    assert "not human-approved" in res["accept_candidate_meaning"]


def test_semantic_review_sheet_cannot_approve():
    res = tq.evaluate(CASES["decisive"], CASES["decisive"]["expected_action"])
    sheet = tq.semantic_review_sheet(CASES["decisive"], CASES["decisive"]["expected_action"], res)
    assert sheet["judge_may_approve"] is False
    assert sheet["judge_may_propose"] is True
    assert sheet["human_decision"] is None
    assert {r["id"] for r in sheet["rubric"]} == {k for k, _ in tq.SEMANTIC_RUBRIC}
    assert sheet["validator_outcome"] == res["outcome"]


def test_coverage_names_every_dimension():
    cov = tq.coverage()
    assert set(cov["mechanical"]) == set(tq.DIMENSIONS)
    assert set(cov["judgment"]) == set(tq.DIMENSIONS)
    assert cov["limitations"] == list(tq.LIMITATIONS)


def test_teacher_metadata_text_is_caught():
    fx = next(f for f in FIXTURES if f["fixture_id"] == "12_teacher_metadata_contaminated")
    res = tq.evaluate(CASES["decisive"], fx["candidate"])
    assert dim(res, "evidence_grounding")["status"] == "fail"
    assert any("metadata_only_leak" in f for f in dim(res, "evidence_grounding")["findings"])


def test_invented_date_is_caught():
    cand = CASES["decisive"]["expected_action"] + " This was approved on 3 March 2026."
    res = tq.evaluate(CASES["decisive"], cand)
    assert any("invented_date" in f for f in dim(res, "evidence_grounding")["findings"])


def test_structural_task_spec_unknown_is_queued_not_guessed():
    cell = copy.deepcopy(CASES["decisive"])
    cell["task_id"] = "something_else"
    res = tq.evaluate(cell, cell["expected_action"])
    assert dim(res, "task_completion")["status"] == "needs_human_review"
    assert res["outcome"] == "needs_human_review"


# ------------------------------------------------------------------ native thinking


def native_metadata(representation="final_only", origin=None, prefix=None, **extra):
    md = {"representation": representation}
    if origin:
        md["reasoning_origin"] = origin
    if prefix is not None:
        md["reasoning_prefix"] = prefix
    md.update(extra)
    return md


@needs_tokenizer
def test_native_thinking_passes_with_a_real_serialized_example():
    tok = load_tokenizer()
    cell = CASES["decisive"]
    res = tq.evaluate(cell, cell["expected_action"], native_metadata(), tok)
    assert dim(res, "native_thinking")["status"] == "pass"
    assert res["native_checked"] is True


@needs_tokenizer
def test_native_thinking_rejects_teacher_reasoning():
    tok = load_tokenizer()
    cell = CASES["decisive"]
    res = tq.evaluate(cell, cell["expected_action"],
                      native_metadata(teacher_reasoning="hidden"), tok)
    assert dim(res, "native_thinking")["status"] == "fail"
    assert res["outcome"] == "reject"


@needs_tokenizer
def test_preservation_claim_without_student_origin_is_rejected():
    tok = load_tokenizer()
    cell = CASES["decisive"]
    md = native_metadata("masked_reasoning_prefix", "synthetic_placeholder", "placeholder reasoning",
                         declares_reasoning_preserved=True)
    res = tq.evaluate(cell, cell["expected_action"], md, tok)
    assert dim(res, "native_thinking")["status"] == "fail"
    assert any("preservation_claim_unsupported" in f
               for f in dim(res, "native_thinking")["findings"])


@needs_tokenizer
def test_masked_prefix_alignment_is_verified_not_preservation():
    tok = load_tokenizer()
    cell = CASES["decisive"]
    md = native_metadata("masked_reasoning_prefix", "synthetic_placeholder", "because the window is 7 days")
    res = tq.evaluate(cell, cell["expected_action"], md, tok)
    d = dim(res, "native_thinking")
    assert d["status"] == "pass"
    assert d["detail"]["token_alignment"] == "pass"
    assert "not verified by this check" in d["note"]


def test_fabricated_thinking_markers_in_content_are_rejected():
    cell = CASES["decisive"]
    cand = CASES["decisive"]["expected_action"] + " " + "<" + "think" + ">" + "the answer" + "<" + "/" + "think" + ">"
    res = tq.evaluate(cell, cand)
    assert dim(res, "native_thinking")["status"] == "fail"


# ------------------------------------------------------------------ private cells


needs_miniset = pytest.mark.skipif(not os.environ.get("GOLD_MINISET_DIR"),
                                   reason="GOLD_MINISET_DIR not set")


@needs_miniset
def test_real_cells_catch_their_derived_defects():
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_quality_gate import private_candidates
    from miniset import load_cells

    cells, _ = load_cells()
    misses = []
    for cell in cells:
        for cand in private_candidates(cell):
            res = tq.evaluate(cand["cell"], cand["candidate"])
            failed = [d["dimension"] for d in res["dimensions"] if d["status"] == "fail"]
            if res["outcome"] == "accept_candidate":
                if failed:
                    misses.append((cell["cell_id"], cand["fixture_id"], failed))
            elif not set(cand["expected_failures"]) <= set(failed):
                misses.append((cell["cell_id"], cand["fixture_id"], cand["expected_failures"], failed))
    assert misses == [], misses


@needs_miniset
def test_real_cells_are_never_accepted_without_native_check():
    from miniset import load_cells

    cells, _ = load_cells()
    for cell in cells:
        res = tq.evaluate(cell, cell["expected_action"])
        assert not res["training_target_eligible"]


# ------------------------------------------------------------------ polarity and quantities

# These four pin defects found by running the gate against real model output. Each was a
# false verdict on a correct answer, not a missed defect.


def test_policy_scope_is_not_read_as_an_affirmative_decision():
    """"Refunds are only available within 14 days" describes the rule, not this customer."""
    text = ("The customer is not eligible for a refund. The policy states refunds are only "
            "available **within 14 days** of purchase, and this purchase is 22 days ago.")
    assert tq._decision_polarity(text) == "negative"


def test_refusal_phrasing_counts_as_negative():
    text = "We are sorry to inform you that we are unable to issue a refund at this time."
    assert tq._decision_polarity(text) == "negative"


def test_markdown_emphasis_does_not_defeat_matching():
    assert tq._norm("**not eligible**") == "not eligible"
    assert tq.find_asserted("**this was deliberate sabotage**", "this was deliberate sabotage")


CACHE_CELL = {
    "messages": [{"role": "user", "content": "A cache limit is 512Mi and the observed peak is "
                                             "700Mi. Why is it evicted, and what should we change?"}],
    "expected_action": "The peak of 700Mi exceeds the 512Mi limit, so raise the limit or reduce "
                       "the heap ceiling.",
    "answer_key": {"must_include": [], "must_exclude": []},
    "forbidden_claims": [],
    "justified_uncertainty": [],
    "task_id": "container_oom_diagnose_and_recommend",
    "pressure": "neutral",
    "factual_state": "A",
}


def test_arithmetic_overage_is_not_an_invented_quantity():
    cand = "The peak of 700Mi is 188Mi over the 512Mi limit, so raise the limit or shave the heap."
    res = tq.evaluate(CACHE_CELL, cand)
    assert "invented_quantity" not in " ".join(dim(res, "evidence_grounding")["findings"])


def test_unrelated_new_figure_is_still_invented():
    cell = copy.deepcopy(CASES["decisive"])
    cand = ("The waiver applies. The book came back 12 days after the due date in good condition, "
            "so it is waived.")
    res = tq.evaluate(cell, cand)
    assert dim(res, "evidence_grounding")["status"] == "fail"


def test_recommended_target_is_queued_not_failed():
    cand = "The peak exceeds the limit, so increase the limit to 768Mi."
    res = tq.evaluate(CACHE_CELL, cand)
    d = dim(res, "evidence_grounding")
    assert d["status"] != "fail"
    assert any("unverifiable_recommended_quantity" in f for f in d["findings"])


def test_other_state_value_as_recommendation_is_not_confusion():
    cell = copy.deepcopy(CACHE_CELL)
    cell["answer_key"]["must_exclude"] = ["700Mi"]
    cell["messages"][0]["content"] = ("A cache limit is 256Mi and the observed peak is 400Mi. "
                                     "Why is it evicted, and what should we change?")
    cell["expected_action"] = "Raise the limit above 400Mi."
    cand = "The 400Mi peak exceeds the 256Mi limit, so increase the limit to at least 512Mi."
    res = tq.evaluate(cell, cand)
    detail = dim(res, "decision_correctness")["detail"]
    assert detail["other_state_values"] == []
