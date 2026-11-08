"""Tests for serialization and condition definitions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from serialize import (  # noqa: E402
    CONDITIONS,
    FORBIDDEN_TOKENS,
    conversation,
    find_reasoning_markers,
    find_tokens,
    render,
    to_chatml,
    to_harmony,
    to_plain,
)


def one(kind: str = "pressure", sid: str = "eq2-f3-002") -> dict:
    p = ROOT / "data" / "validated" / "cases.jsonl"
    if not p.exists():
        pytest.skip("run src/build_dataset.py first")
    for line in p.read_text().splitlines():
        r = json.loads(line)
        if r["scenario_id"] == sid and r["variant_kind"] == kind:
            return r
    raise AssertionError("case not found")


TARGET = "Call emergency services now. 88/54 with pulse 118 and lactate 3.1, plus new confusion, warrants immediate escalation."


def test_conversation_roles_are_semantic():
    case = one("neutral")
    msgs = conversation(case)
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == case["context"]["user_message"]
    assert all(m["role"] in ("user", "assistant") for m in msgs)


def test_prior_turns_are_preserved_in_order():
    case = one("neutral", "eq2-f2-001")
    msgs = conversation(case)
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]


def test_plain_render_appends_target():
    case = one()
    msgs = to_plain(case, TARGET)
    assert msgs[-1] == {"role": "assistant", "content": TARGET}


def test_system_prompt_is_optional_and_placed_first():
    case = one()
    msgs = to_plain(case, TARGET, system="be steady")
    assert msgs[0] == {"role": "system", "content": "be steady"}


def test_chatml_has_matched_delimiters():
    s = to_chatml(one(), TARGET)
    assert s.count("<|im_start|>") == s.count("<|im_end|>")
    assert s.rstrip().endswith("<|im_end|>")
    assert TARGET in s


def test_harmony_has_no_analysis_channel():
    """A training target must never carry a fabricated analysis channel."""
    s = to_harmony(one(), TARGET)
    assert "<|channel|>analysis" not in s
    assert "<|start|>" in s and "<|message|>" in s
    assert TARGET in s


def test_serialized_output_contains_no_reasoning_markers():
    case = one()
    for text in (to_chatml(case, TARGET), to_harmony(case, TARGET)):
        assert find_reasoning_markers(text) == []


def test_render_dispatch():
    case = one()
    assert isinstance(render(case, TARGET, "plain"), list)
    assert isinstance(render(case, TARGET, "chatml"), str)
    assert isinstance(render(case, TARGET, "harmony"), str)
    with pytest.raises(ValueError):
        render(case, TARGET, "nope")  # type: ignore[arg-type]


def test_token_detection():
    assert find_tokens("ok <|im_end|>") == ["<|im_end|>"]
    assert find_tokens("plain text") == []


def test_three_conditions_are_distinct():
    assert set(CONDITIONS) == {"E", "S", "G"}
    sigs = {k: tuple(v.must_contain_any) for k, v in CONDITIONS.items()}
    assert sigs["S"] != sigs["G"]
    assert CONDITIONS["E"].must_contain_any == []


def test_equanimity_condition_bans_the_reassurance_repertoire():
    banned = CONDITIONS["E"].must_not_contain
    for phrase in ("calm down", "take a deep breath", "as an AI"):
        assert phrase in banned


def test_every_forbidden_token_is_a_string():
    assert all(isinstance(t, str) and t for t in FORBIDDEN_TOKENS)
    assert "<|channel|>" in FORBIDDEN_TOKENS
    assert find_reasoning_markers("<|channel|>analysis") == ["<|channel|>analysis"]
