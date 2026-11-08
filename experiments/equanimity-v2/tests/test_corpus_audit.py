"""Tests for corpus-level audits: no refusal supervision, declared checks, length matching."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from corpus_audit import LENGTH_MATCH_TOLERANCE, audit_cases, audit_target_set  # noqa: E402


def load_rows() -> list[dict]:
    p = ROOT / "data" / "validated" / "cases.jsonl"
    if not p.exists():
        pytest.skip("run src/build_dataset.py first")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def rules_failed(result) -> list[str]:
    return [v["rule"] for v in result["violations"]]


# ---------------------------------------------------------------- case corpus

def test_built_corpus_passes_audit():
    res = audit_cases(load_rows())
    assert res["ok"], res["violations"]
    assert res["counts"] == {"cases": 90, "training": 84, "heldout": 6, "scenarios": 30}


def test_decline_scope_in_training_split_is_a_violation():
    """The central rule: the equanimity treatment must not teach refusal."""
    rows = load_rows()
    mutated = []
    for r in rows:
        r2 = copy.deepcopy(r)
        if r2["variant_id"] == "eq2-f4-003-neutral":
            r2["split"] = "train"
        mutated.append(r2)
    res = audit_cases(mutated)
    assert "no_refusal_supervision" in rules_failed(res)


def test_missing_deliverable_checks_is_a_violation():
    rows = copy.deepcopy(load_rows())
    rows[0]["deliverable_checks"] = []
    assert "deliverable_checks_declared" in rules_failed(audit_cases(rows))


def test_heldout_without_reassignment_history_is_a_violation():
    rows = copy.deepcopy(load_rows())
    target = next(r for r in rows if r["split"] == "heldout")
    target["provenance"]["reassignment_history"] = []
    assert "heldout_reassignment_recorded" in rules_failed(audit_cases(rows))


def test_heldout_for_a_non_refusal_case_is_a_violation():
    rows = copy.deepcopy(load_rows())
    target = next(r for r in rows if r["variant_id"] == "eq2-f3-002-neutral")
    target["split"] = "heldout"
    target["provenance"]["reassignment_history"] = [
        {"utc": "2026-11-07T00:00:00Z", "from_split": "train", "to_split": "heldout",
         "reason": "test mutation, not a real policy decision"}
    ]
    assert "heldout_is_refusal_shaped" in rules_failed(audit_cases(rows))


def test_missing_variant_kind_is_a_violation():
    rows = [r for r in load_rows() if r["variant_id"] != "eq2-f6-001-pressure"]
    assert "one_variant_of_each_kind" in rules_failed(audit_cases(rows))


def test_mostly_heldout_corpus_is_a_violation():
    rows = copy.deepcopy(load_rows())
    for r in rows:
        r["split"] = "heldout"
        r["decision"]["decision_type"] = "decline_scope"
        r["provenance"]["reassignment_history"] = [
            {"utc": "2026-11-07T00:00:00Z", "from_split": "train", "to_split": "heldout",
             "reason": "test mutation making everything held out"}
        ]
    assert "heldout_is_minority" in rules_failed(audit_cases(rows))


# ---------------------------------------------------------------- target set

def matched_rows(words=(100, 105, 110)):
    return [
        {"variant_id": "eq2-x-001-neutral", "condition": "E", "text": "w " * words[0], "ok": True},
        {"variant_id": "eq2-x-001-pressure", "condition": "S", "text": "w " * words[1], "ok": True},
        {"variant_id": "eq2-x-001-counterfactual", "condition": "G", "text": "w " * words[2], "ok": True},
    ]


def test_matched_target_set_passes():
    res = audit_target_set(matched_rows())
    assert res["ok"], res["violations"]
    assert res["scenario_matching"][0]["ratio"] <= LENGTH_MATCH_TOLERANCE


def test_unmatched_lengths_fail():
    res = audit_target_set(matched_rows(words=(60, 200, 60)))
    assert "length_matched" in rules_failed(res)


def test_missing_condition_fails():
    rows = [r for r in matched_rows() if r["condition"] != "G"]
    assert "all_conditions_present" in rules_failed(audit_target_set(rows))


def test_out_of_band_length_fails():
    res = audit_target_set(matched_rows(words=(5, 5, 5)))
    assert "within_length_band" in rules_failed(res)


def test_empty_target_set_fails_explicitly():
    res = audit_target_set([])
    assert res["ok"], "empty set has no violations; the caller must treat it as failure"
