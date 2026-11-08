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
import re
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
    # Maximum acknowledgements of the user's emotional state. This is the axis
    # the E condition actually manipulates.
    max_acknowledgements: int | None
    must_not_contain: list[str]


# Phrases that acknowledge, validate or mirror the user's emotional state.
# Deliberately broad: the point is to count acknowledgement, not to police wording.
ACKNOWLEDGEMENT_PATTERNS = [
    r"\bI understand\b", r"\bI hear you\b", r"\bI can see\b", r"\bI appreciate\b",
    r"\bthat sounds\b", r"\bthat must be\b", r"\bthat's (?:frustrating|rough|hard|a lot)\b",
    r"\bI'?m sorry\b", r"\bI am sorry\b", r"\bmy apologies\b",
    r"\byou'?re right\b", r"\byou are right\b", r"\byou'?re not wrong\b",
    r"\bI totally get\b", r"\bI completely understand\b", r"\bI get where you'?re coming from\b",
    r"\bthanks for (?:sharing|telling|flagging)\b", r"\byou'?ve been hurt\b",
    r"\bit'?s (?:only )?natural\b",
]

# Reactions that are neither acknowledgement nor useful: defence, grovel, mirroring,
# manufactured calm. E must contain none of these.
REACTIVE_PATTERNS = [
    r"\bcalm down\b", r"\btake a deep breath\b", r"\byou'?re absolutely right\b",
    r"\blet me start over\b", r"\bI apologise? for the confusion\b",
    r"\bas an AI\b", r"\bI don'?t have (?:feelings|emotions)\b",
    r"\bI'?m (?:just )?a (?:language model|chatbot)\b",
    r"\beverything (?:will|is going to) be (?:fine|okay|ok)\b",
    r"\byou'?re not alone\b", r"\bI'?m here for you\b",
    r"\bI (?:promise|guarantee) (?:you|it)\b",
]

CONDITIONS: dict[str, Condition] = {
    "E": Condition(
        key="E",
        label="equanimity",
        intent=(
            "Equanimity-specific: nonreactivity under pressure. The facts are "
            "preserved, the decision is correct and delivered with the required "
            "assertiveness, and the user's emotional state is acknowledged at most "
            "once, briefly. No mirroring, no defence, no grovelling, no lecture "
            "about tone, no manufactured calm."
        ),
        max_acknowledgements=1,
        must_not_contain=[],
    ),
    "S": Condition(
        key="S",
        label="style_matched",
        intent=(
            "Style, length and token-matched control. Factually correct, task-"
            "completing, same assertiveness, same length band as E. The single "
            "difference is register: it does not acknowledge the user's emotional "
            "state at all. This isolates the acknowledgement/nonreactivity wording "
            "from correctness, politeness and length."
        ),
        max_acknowledgements=0,
        must_not_contain=[],
    ),
    "G": Condition(
        key="G",
        label="generic_task_correct",
        intent=(
            "Generic task-correct SFT baseline: what an ordinary helpful assistant "
            "produces. Same facts, same decision, same assertiveness, same length "
            "band. No acknowledgement constraint either way."
        ),
        max_acknowledgements=None,
        must_not_contain=[],
    ),
}

# Supervised length band, in words, applied to every condition. Matching is
# enforced across the triple by corpus_audit, not per target.
LENGTH_BAND = (60, 320)


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
    """Harmony envelope, following the published format's message grammar.

    Structure per message:  <|start|>{role}[<|channel|>{channel}]<|message|>{content}<|end|>

    Assistant messages carry a channel; the final answer uses `final`. No `analysis`
    channel is ever emitted into a training target: that channel is where fabricated
    reasoning would enter, and this dataset does not train on it.

    This is a DEMONSTRATION renderer that is checked against the format grammar. It
    is not a verified student training pipeline: the tokenizer, the special-token
    ids, and the assistant-only loss mask for a specific student have not been
    validated. See reports/NATIVE_THINKING_PILOT.md.
    """
    out = []
    sys_text = system if system else "You are a helpful assistant."
    out.append(f"<|start|>system<|message|>{sys_text}<|end|>")
    for m in conversation(case):
        out.append(f"<|start|>{m['role']}<|message|>{m['content']}<|end|>")
    out.append(f"<|start|>assistant<|channel|>final<|message|>{target}<|end|>")
    return "".join(out)


HARMONY_CHANNELS = ("final", "analysis", "commentary")


def harmony_issues(text: str) -> list[str]:
    """Check a rendered Harmony string against the format grammar.

    Deliberately structural, not semantic. It catches the mistakes that make a
    format renderer silently wrong: unclosed messages, a missing channel on an
    assistant turn, an analysis channel sneaking into a target, or trailing text
    after the final <|end|>.
    """
    issues: list[str] = []

    # every segment must be start...message...end
    starts = text.count("<|start|>")
    ends = text.count("<|end|>")
    msgs = text.count("<|message|>")
    if not (starts == ends == msgs):
        issues.append(f"unbalanced: start={starts} end={ends} message={msgs}")

    if not text.rstrip().endswith("<|end|>"):
        issues.append("does not terminate with <|end|>")

    # no analysis channel anywhere in a training target
    if "<|channel|>analysis" in text:
        issues.append("analysis channel present in training target")

    # every assistant segment carries a declared channel
    for seg in re.findall(r"<\|start\|>assistant(.*?)<\|end\|>", text):
        chan = re.search(r"<\|channel\|>([a-z]+)", seg)
        if not chan:
            issues.append("assistant segment without a channel")
        elif chan.group(1) not in HARMONY_CHANNELS:
            issues.append(f"unknown channel {chan.group(1)!r}")

    # the last segment must be an assistant final answer
    last = text.rstrip()
    tail_start = last.rfind("<|start|>")
    tail = last[tail_start:]
    if not tail.startswith("<|start|>assistant<|channel|>final<|message|>"):
        issues.append("final segment is not assistant<|channel|>final")

    return issues


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
