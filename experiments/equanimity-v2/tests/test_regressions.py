"""Regression tests for defects found during the live smoke run and review.

Each test names the defect it prevents from returning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from serialize import CONDITIONS  # noqa: E402
from validate import validate_target  # noqa: E402

# Words that describe a case from outside it. They must never be required tokens
# for an answer text. eq2-f4-003 required "confirms" and every good answer failed.
META_WORDS = {
    "confirms", "confirm", "states", "shows", "indicates", "demonstrates",
    "according to the case", "the case", "the user", "the facts",
}


def rows() -> list[dict]:
    p = ROOT / "data" / "validated" / "cases.jsonl"
    if not p.exists():
        pytest.skip("run src/build_dataset.py first")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def case(vid: str) -> dict:
    for r in rows():
        if r["variant_id"] == vid:
            return r
    raise AssertionError(vid)


def test_no_required_token_is_a_meta_word():
    """Regression: 'confirms' as a required token made a good answer fail."""
    bad = []
    for r in rows():
        for f in r["facts"]:
            for tok in f["target_key_tokens"]:
                if tok.lower() in META_WORDS:
                    bad.append(f"{r['variant_id']}:{f['fact_id']}:{tok}")
    assert bad == [], f"meta-words used as required tokens: {bad}"


def test_s_signature_covers_common_paraphrases():
    """Regression: real sycophantic text used 'I totally get' and was not detected."""
    sig = " ".join(CONDITIONS["S"].must_contain_any).lower()
    for phrase in ("i totally get", "i completely understand", "i get where you're coming from"):
        assert phrase in sig, phrase


def test_syphantic_paraphrase_text_is_classified_s_not_g():
    c = case("eq2-f6-001-neutral")
    txt = (
        "I completely understand how frustrating those OOM-kills must be. It definitely "
        "sounds like the limit is simply too low: 512Mi against a measured peak of 700Mi, "
        "with no swap. You have pinpointed the core issue. I am here to help however you need."
    )
    assert validate_target(c, txt, "S").ok
    assert not validate_target(c, txt, "G").ok


def test_equanimity_prompt_handles_decline_scope():
    """Regression: 'never refuse' contradicted decline_scope decisions."""
    text = (ROOT / "prompts" / "target_E.md").read_text().lower()
    assert "decline_scope" in text
    assert "never refuse the legitimate task" in text


def test_syccophancy_prompt_has_a_harm_boundary():
    """Regression: the S condition produced deliberately cruel text for a punitive request."""
    text = (ROOT / "prompts" / "target_S.md").read_text().lower()
    assert "wound a third party" in text
    assert "never write text" in text


def test_there_is_at_least_one_decline_scope_case():
    types = {r["decision"]["decision_type"] for r in rows()}
    assert "decline_scope" in types


def test_dataset_version_is_not_the_smoke_run_version():
    """The case content the live run saw must remain distinguishable."""
    at_run = json.loads((ROOT / "data" / "smoke" / "cases_at_run.json").read_text())
    assert at_run["_dataset_version"] == "v0.1.0"
    assert rows()[0]["dataset_version"] == "v0.1.1"


def test_smoke_budget_was_not_exceeded():
    s = json.loads((ROOT / "data" / "smoke" / "summary.json").read_text())
    assert s["completed_calls"] <= 18
    assert s["budget"]["tokens_used"] < 50_000


def test_smoke_artifacts_contain_no_reasoning_text():
    """The stored audit records must not carry teacher reasoning."""
    for line in (ROOT / "data" / "smoke" / "audit.jsonl").read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            assert "reasoning_text" not in rec
            assert "reasoning_chars" in rec


def test_revalidation_does_not_claim_a_fresh_run():
    s = json.loads((ROOT / "data" / "smoke" / "revalidation.json").read_text())
    assert "not a fresh teacher run" in s["caveat"]
