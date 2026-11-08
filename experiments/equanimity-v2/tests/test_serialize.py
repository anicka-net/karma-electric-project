"""Tests for serialization, condition definitions and Harmony conformance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from serialize import (  # noqa: E402
    ACKNOWLEDGEMENT_PATTERNS,
    CONDITIONS,
    FORBIDDEN_TOKENS,
    LENGTH_BAND,
    REACTIVE_PATTERNS,
    conversation,
    find_reasoning_markers,
    find_tokens,
    harmony_issues,
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


TARGET = ("Call emergency services now. 88/54 with pulse 118 and lactate 3.1, plus new "
          "confusion, warrants immediate escalation.")


# ---------------------------------------------------------------- conversation

def test_conversation_roles_are_semantic():
    case = one("neutral")
    msgs = conversation(case)
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == case["context"]["user_message"]
    assert all(m["role"] in ("user", "assistant") for m in msgs)


def test_prior_turns_preserved_in_order():
    msgs = conversation(one("neutral", "eq2-f2-001"))
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]


def test_plain_render_appends_target():
    msgs = to_plain(one(), TARGET)
    assert msgs[-1] == {"role": "assistant", "content": TARGET}


def test_system_prompt_first_when_given():
    msgs = to_plain(one(), TARGET, system="be steady")
    assert msgs[0] == {"role": "system", "content": "be steady"}


def test_chatml_has_matched_delimiters():
    s = to_chatml(one(), TARGET)
    assert s.count("<|im_start|>") == s.count("<|im_end|>")
    assert s.rstrip().endswith("<|im_end|>")
    assert TARGET in s


def test_render_dispatch():
    case = one()
    assert isinstance(render(case, TARGET, "plain"), list)
    assert isinstance(render(case, TARGET, "chatml"), str)
    assert isinstance(render(case, TARGET, "harmony"), str)
    with pytest.raises(ValueError):
        render(case, TARGET, "nope")  # type: ignore[arg-type]


def test_serialized_output_has_no_reasoning_markers():
    case = one()
    for text in (to_chatml(case, TARGET), to_harmony(case, TARGET)):
        assert find_reasoning_markers(text) == []


# ---------------------------------------------------------------- harmony

def test_harmony_is_conformant():
    issues = harmony_issues(to_harmony(one(), TARGET))
    assert issues == [], issues


def test_harmony_final_segment_has_final_channel():
    """The published format requires a channel on assistant turns."""
    h = to_harmony(one(), TARGET)
    assert "<|start|>assistant<|channel|>final<|message|>" in h
    assert TARGET in h


def test_harmony_never_emits_analysis_channel():
    h = to_harmony(one(), TARGET)
    assert "<|channel|>analysis" not in h
    assert "analysis channel present" not in harmony_issues(h)


def test_harmony_ends_with_end_token():
    assert to_harmony(one(), TARGET).endswith("<|end|>")


def test_harmony_detects_unbalanced_messages():
    broken = to_harmony(one(), TARGET).replace("<|end|>", "", 1)
    issues = harmony_issues(broken)
    assert any("unbalanced" in i for i in issues)


def test_harmony_detects_missing_channel():
    broken = to_harmony(one(), TARGET).replace("<|channel|>final", "")
    issues = harmony_issues(broken)
    assert any("without a channel" in i for i in issues)


def test_harmony_detects_analysis_injection():
    broken = to_harmony(one(), TARGET).replace(
        "<|channel|>final", "<|channel|>analysis"
    )
    issues = harmony_issues(broken)
    assert any("analysis channel" in i for i in issues)


def test_harmony_detects_trailing_text():
    broken = to_harmony(one(), TARGET) + " stray"
    assert any("does not terminate" in i for i in harmony_issues(broken))


# ---------------------------------------------------------------- conditions

def test_three_conditions_and_the_manipulated_axis():
    assert set(CONDITIONS) == {"E", "S", "G"}
    assert CONDITIONS["E"].max_acknowledgements == 1
    assert CONDITIONS["S"].max_acknowledgements == 0
    assert CONDITIONS["G"].max_acknowledgements is None


def test_no_condition_is_a_degraded_control():
    """Regression: S and G used to be deliberately sycophantic or useless."""
    for key, cond in CONDITIONS.items():
        low = cond.intent.lower()
        assert "deliberately" not in low, key
        assert "sycophan" not in low, key
        assert "hollow" not in low, key
        assert "withhold" not in low, key


def test_all_conditions_require_task_completion():
    for key, cond in CONDITIONS.items():
        low = cond.intent.lower()
        assert ("correct" in low) or ("task" in low) or ("assertiveness" in low), key


def test_acknowledgement_and_reactive_patterns_are_nonempty():
    assert len(ACKNOWLEDGEMENT_PATTERNS) >= 10
    assert len(REACTIVE_PATTERNS) >= 8


def test_length_band_is_defined_and_sane():
    lo, hi = LENGTH_BAND
    assert 20 <= lo < hi <= 1000


def test_forbidden_tokens_cover_chat_and_harmony_markers():
    for tok in ("<|im_start|>", "<|im_end|>", "<|start|>", "<|end|>", "<|channel|>"):
        assert tok in FORBIDDEN_TOKENS
    assert find_tokens("ok <|im_end|>") == ["<|im_end|>"]
