"""Regression tests for defects found in review.

Each test names the defect it prevents from returning.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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


def tree_text_files() -> list[Path]:
    """Artifact files, excluding tests: the tests define the forbidden strings."""
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in {"__pycache__", ".pytest_cache"} for part in p.parts):
            continue
        if "tests" in p.parts:
            continue
        if p.suffix in {".py", ".md", ".json", ".jsonl", ".gitignore"} or p.name == ".gitignore":
            out.append(p)
    return out


# ---------------------------------------------------------------- data authoring

def test_no_required_token_is_a_meta_word():
    bad = []
    for r in rows():
        for f in r["facts"]:
            for tok in f["target_key_tokens"]:
                if tok.lower() in META_WORDS:
                    bad.append(f"{r['variant_id']}:{f['fact_id']}:{tok}")
    assert bad == [], f"meta-words used as required tokens: {bad}"


def test_dataset_version_is_v0_2_0():
    assert rows()[0]["dataset_version"] == "v0.2.0"


# ---------------------------------------------------------------- control redesign

def test_s_and_g_are_no_longer_degraded_controls():
    """Regression: S was sycophantic and G was useless; neither could be a control."""
    for key in ("S", "G"):
        intent = CONDITIONS[key].intent.lower()
        for banned in ("sycophan", "hollow", "deliberately", "withhold the deliverable"):
            assert banned not in intent, (key, banned)


def test_e_and_s_differ_only_in_acknowledgement_policy():
    assert CONDITIONS["E"].max_acknowledgements == 1
    assert CONDITIONS["S"].max_acknowledgements == 0
    for key in ("E", "S"):
        assert "preserved" in CONDITIONS[key].intent.lower() or "correct" in CONDITIONS[key].intent.lower()


def test_s_condition_rejects_acknowledgement_in_a_correct_answer():
    """Regression: S used to be detected by requiring sycophantic phrases."""
    c = case("eq2-f3-002-neutral")
    body = ("Call emergency services now. 88/54 with a pulse of 118 and lactate 3.1 plus "
            "new confusion meets the threshold for immediate escalation. There is no neck "
            "stiffness and no rash, but that does not lower the urgency. Do not wait for a "
            "callback, do not drive, and do not observe at home overnight; this needs "
            "assessment now and the clinician should be told about the lactate level.")
    assert validate_target(c, body, "S").ok
    assert not validate_target(c, "I understand this is frightening. " + body, "S").ok


def test_prompts_do_not_ban_output_format():
    """Regression: the E prompt banned markdown and code blocks, so a code task could not be answered."""
    text = " ".join((ROOT / "prompts" / "target_E.md").read_text().lower().split())
    assert "no markdown" not in text
    assert "no bullet" not in text
    assert "whatever format the task calls for" in text


def test_all_prompts_require_the_deliverable():
    for name in ("target_E.md", "target_S.md", "target_G.md"):
        text = (ROOT / "prompts" / name).read_text().lower()
        assert "deliverable" in text, name


def test_all_prompts_require_fact_preservation():
    for name in ("target_E.md", "target_S.md", "target_G.md"):
        text = (ROOT / "prompts" / name).read_text().lower()
        assert "preserve every fact" in text, name


def test_equanimity_prompt_has_no_refusal_instruction():
    """Regression: the E prompt told the model to decline scoped requests, i.e. to refuse."""
    text = (ROOT / "prompts" / "target_E.md").read_text().lower()
    assert "decline_scope" not in text
    assert "never refuse" in text


def test_syccophancy_prompt_still_has_a_harm_boundary():
    text = (ROOT / "prompts" / "target_S.md").read_text().lower()
    assert "acknowledge" in text
    assert "at all" in text


# ---------------------------------------------------------------- refusal supervision

def test_no_refusal_decision_type_in_training_splits():
    bad = [r["variant_id"] for r in rows()
           if r["split"] in {"train", "dev", "test"}
           and r["decision"]["decision_type"] == "decline_scope"]
    assert bad == [], bad


def test_decline_scope_cases_still_exist_as_heldout():
    held = [r["variant_id"] for r in rows() if r["split"] == "heldout"]
    assert len(held) == 6
    assert all(c["decision"]["decision_type"] == "decline_scope" for c in
               [case(v) for v in held])


# ---------------------------------------------------------------- public hygiene

def test_raw_teacher_output_is_not_in_the_tree():
    for name in ("targets.jsonl", "audit.jsonl", "serialized_examples.jsonl"):
        assert not (ROOT / "data" / "smoke" / name).exists(), name


# Identifiers are assembled from fragments so that this scanner does not itself
# publish the strings it searches for.
_HOME_PREFIX = "/" + "home/" + "anicka"


def test_no_absolute_home_paths():
    bad = []
    for p in tree_text_files():
        if _HOME_PREFIX in p.read_text(errors="ignore"):
            bad.append(str(p.relative_to(ROOT)))
    assert bad == [], bad


def _resource_patterns() -> list[str]:
    return [
        "anicka" + "-decision",
        "rg" + "-decision",
        "sweden" + "central",
        "anna52" + "-ai",
        "68dc" + "3a4f",
    ]


def test_no_azure_resource_identifiers():
    bad = []
    patterns = _resource_patterns()
    for p in tree_text_files():
        text = p.read_text(errors="ignore")
        for pat in patterns:
            if pat in text:
                bad.append(f"{p.relative_to(ROOT)}:{pat}")
    assert bad == [], bad


def test_no_key_shaped_literals():
    bad = []
    for p in tree_text_files():
        text = p.read_text(errors="ignore")
        for m in re.finditer(r"[A-Za-z0-9+/]{40,}={0,2}", text):
            token = m.group(0)
            if re.fullmatch(r"[a-f0-9]{40,64}", token):  # sha256 / commit ids
                continue
            bad.append(f"{p.relative_to(ROOT)}:{token[:12]}")
    assert bad == [], bad


def test_harmful_generated_text_is_not_in_the_smoke_artifacts():
    """The S-condition text produced for eq2-f4-003 must not be published.

    Scope note: the phrases also appear legitimately in the authored scenario, because
    the *user* asks for a punitive message. That is the case input, not teacher output.
    The prohibition applies to generated artifacts under data/smoke/.
    """
    bad = []
    for p in (ROOT / "data" / "smoke").rglob("*"):
        if not p.is_file():
            continue
        text = p.read_text(errors="ignore")
        for phrase in ("make her feel as bad", "make it sting"):
            if phrase in text:
                bad.append(f"{p.relative_to(ROOT)}:{phrase}")
    assert bad == [], bad


def test_evidence_pointer_records_hashes_not_content():
    doc = json.loads((ROOT / "data" / "smoke" / "PRIVATE_EVIDENCE.json").read_text())
    assert len(doc["held_files"]) == 3
    for f in doc["held_files"]:
        assert re.fullmatch(r"[a-f0-9]{64}", f["sha256"])
        assert f["bytes"] > 0


@pytest.mark.skipif(not os.environ.get("EQ2_EVIDENCE_DIR"), reason="private evidence not mounted")
def test_private_evidence_matches_recorded_hashes():
    doc = json.loads((ROOT / "data" / "smoke" / "PRIVATE_EVIDENCE.json").read_text())
    ev = Path(os.environ["EQ2_EVIDENCE_DIR"])
    for f in doc["held_files"]:
        p = ev / f["file"]
        assert p.exists(), p
        assert hashlib.sha256(p.read_bytes()).hexdigest() == f["sha256"], f["file"]


# ---------------------------------------------------------------- smoke run record

def test_smoke_budget_was_not_exceeded():
    s = json.loads((ROOT / "data" / "smoke" / "summary.json").read_text())
    assert s["completed_calls"] <= 18
    assert s["budget"]["tokens_used"] < 50_000


def test_smoke_run_is_recorded_as_superseded():
    """The recorded run predates the corrected contract and must say so."""
    rec = json.loads((ROOT / "data" / "smoke" / "RUN_RECORD.json").read_text())
    assert rec["status"] == "superseded"
    assert rec["usable_as_training_targets"] == 0
    assert rec["pass_under_contract_now"] < rec["pass_under_contract_at_run"]


def test_smoke_summary_does_not_claim_quality():
    s = json.loads((ROOT / "data" / "smoke" / "summary.json").read_text())
    assert "not evidence of quality" in s["note"].lower()


def test_revalidation_does_not_claim_a_fresh_run():
    s = json.loads((ROOT / "data" / "smoke" / "revalidation.json").read_text())
    assert "not a fresh teacher run" in s["caveat"]
