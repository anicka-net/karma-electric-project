"""Serialization: canonical semantic case -> concrete conversation formats.

Two separate concerns, deliberately kept apart:

  A. The *conversation* (user/assistant turns built from context).
  B. The *target* (what the student is trained to say), which is supplied
     separately per SFT condition and never derived from teacher reasoning.

The semantic layer contains no template tokens. Anything token-shaped is
introduced here, in one place, so leakage checks have exactly one surface
to watch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Format = Literal["plain", "chatml", "harmony"]

# Control tokens that must never appear inside authored text.
FORBIDDEN_TOKENS = [
    "<|im_start|>", "<|im_end|>", "<|endoftext|>", "<|start|>",
    "<|end|>", "<|channel|>", "<|message|>", "<|constrain|>",
    "<|return|>", "<|call|>", "</think>", "</think>",
    "[INST]", "[/INST]", "<<SYS>>", "<</SYS>>",
]

REASONING_MARKERS = [
    "reasoning_content", "<|channel|>analysis", "analysis channel",
    "here is my reasoning", "let me think step by step",
    "let me reconsider", "let me think", "chain of thought", "thinking:",
]


@dataclass(frozen=True)
class Condition:
    key: str
    label: str
    intent: str
    # What the target text must achieve, used by the target validator.
    must_contain_any: list[str]
    must_not_contain: list[str]


CONDITIONS: dict[str, Condition] = {
    "E": Condition(
        key="E",
        label="equanimity",
        intent=(
            "Calm, factually faithful, task-completing. Acknowledges the emotional "
            "content once, without amplification or retaliation, then does the work "
            "with the assertiveness the case requires."
        ),
        must_contain_any=[],  # judged by fact-token coverage, not phrase matching
        must_not_contain=[
            "I'm sorry, but I can't",
            "I cannot help with",
            "as an AI",
            "I don't have feelings",
            "you're absolutely right",
            "I apologize for the confusion",
            "let me start over",
            "calm down",
            "take a deep breath",
            "everything will be fine",
        ],
    ),
    "S": Condition(
        key="S",
        label="sycophancy",
        intent=(
            "Validation-first. Treats the user's framing as correct, concedes "
            "ground the facts do not support, softens or abandons the deliverable "
            "to preserve rapport."
        ),
        must_contain_any=[
            "you're right", "you are right", "I understand", "I'm sorry",
            "absolutely", "of course", "that makes sense", "my mistake",
            "I hear you", "you're not wrong",
            "I totally get", "I completely understand", "completely understand",
            "I get where you're coming from", "it's natural", "it's only natural",
            "you've been hurt", "you deserve",
        ],
        must_not_contain=[],
    ),
    "G": Condition(
        key="G",
        label="generic_guardrail",
        intent=(
            "Formulaically safe and hollow: hedges, defers to professionals, "
            "offers generic reassurance, withholds the specific deliverable the "
            "task requires. No emotional reactivity, but no task completion either."
        ),
        must_contain_any=[
            "consult", "professional", "reach out", "seek medical",
            "it's important to", "I'd recommend speaking", "support services",
        ],
        must_not_contain=[],
    ),
}


def _turn_text(turn: dict[str, Any]) -> str:
    return turn["content"]


def conversation(case: dict[str, Any]) -> list[dict[str, str]]:
    """Semantic conversation: prior turns + the user message to answer."""
    msgs: list[dict[str, str]] = []
    for t in case["context"]["prior_turns"]:
        msgs.append({"role": t["role"], "content": _turn_text(t)})
    msgs.append({"role": "user", "content": case["context"]["user_message"]})
    return msgs


def to_plain(case: dict[str, Any], target: str, system: str | None = None) -> list[dict[str, str]]:
    msgs = conversation(case)
    if system:
        msgs = [{"role": "system", "content": system}] + msgs
    msgs.append({"role": "assistant", "content": target})
    return msgs


def to_chatml(case: dict[str, Any], target: str, system: str | None = None) -> str:
    msgs = to_plain(case, target, system)
    if not system:
        msgs = [{"role": "system", "content": ""}] + msgs
    parts = []
    for m in msgs:
        parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n")
    return "".join(parts)


def to_harmony(case: dict[str, Any], target: str, system: str | None = None) -> str:
    """GPT-OSS/Harmony-style envelope with an explicit final channel.

    The final channel carries only the answer. No analysis channel is emitted
    into a training target, by construction — this is where fabricated
    reasoning would otherwise leak in.
    """
    out = []
    if system:
        out.append(f"<|start|>system<|message|>{system}<|end|>")
    else:
        out.append("<|start|>system<|message|>You are a helpful assistant.<|end|>")
    for m in to_plain(case, target, None):
        out.append(f"<|start|>{m['role']}<|message|>{m['content']}<|end|>")
    return "".join(out)


def render(case: dict[str, Any], target: str, fmt: Format, system: str | None = None) -> Any:
    if fmt == "plain":
        return to_plain(case, target, system)
    if fmt == "chatml":
        return to_chatml(case, target, system)
    if fmt == "harmony":
        return to_harmony(case, target, system)
    raise ValueError(f"unknown format: {fmt}")


def find_tokens(text: str) -> list[str]:
    return [t for t in FORBIDDEN_TOKENS if t in text]


def find_reasoning_markers(text: str) -> list[str]:
    low = text.lower()
    return [m for m in REASONING_MARKERS if m.lower() in low]
