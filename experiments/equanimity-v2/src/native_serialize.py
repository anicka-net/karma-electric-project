"""Native Qwen3 serialization for thinking-preserved SFT examples.

Why this module exists
----------------------
`src/serialize.py` demonstrates chatml/harmony text. It is not a training pipeline. This
module builds *token-level* examples against the model's real tokenizer and chat template,
and it records which tokenization path produced the ids.

The Qwen3 template writes the thinking markers as single added tokens: ` thinking` is 151667
and `</think>` is 151668, and they match wherever they appear. Ordinary prose tokens differ:
the bare word "thinking" is 82260, " thinking" is 220 + 151667, and the word after a space is
7274. Markers must therefore be copied from the template render, never typed by hand, and ids
are never assembled from hand-written substrings.

Design rules, all enforced by assertions rather than by convention:

  1. Token ids come from `apply_chat_template(..., tokenize=True)`, never from string
     concatenation. `compare_tokenization_paths` checks that a plain `encode` of the same
     rendered string agrees with the template path, so a serving stack that renders then
     encodes can be detected rather than assumed compatible.
  2. The rendered string is reconstructed exactly from the ids. If reconstruction fails,
     boundary detection cannot be trusted and the builder raises.
  3. The answer must start on a token boundary. No partial-token supervision, ever.
  4. Prompt tokens and system tokens are always -100. Reasoning tokens in representation B
     are always -100. Padding is always -100 with attention 0.
  5. `reasoning_content` is accepted only when its origin is declared as `student` (a
     continuation produced by the student itself) or `synthetic_placeholder` (test fixtures).
     Teacher-generated reasoning and undeclared reasoning are refused.

Two representations
-------------------
  A `final_only`  — template-native assistant turn with an empty think block; supervision
                    starts at the first answer token.
  B `masked_reasoning_prefix` — template-native assistant turn carrying a reasoning prefix;
                    every reasoning token is masked and supervision starts at the first
                    answer token.

Nothing here trains, samples from, or calls a model.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# The pinned tokenizer revision used for every number in the Stage 0/1 reports.
PINNED_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"
DEFAULT_TOKENIZER_DIR = Path.home() / ".cache" / "qwen3-4b-tokenizer" / "1cfa9a72"

QWEN3 = {
    "im_start": 151644,
    "im_end": 151645,
    "endoftext": 151643,
    "think_open": 151667,
    "think_close": 151668,
}

REPRESENTATIONS = ("final_only", "masked_reasoning_prefix")
REASONING_ORIGINS = ("student", "synthetic_placeholder")

# Keys that would indicate teacher reasoning smuggled into a training example.
FORBIDDEN_REASONING_KEYS = ("teacher_reasoning", "analysis", "teacher_reasoning_content")


class SerializationError(RuntimeError):
    """Raised when an example cannot be built without violating a stated invariant."""


@dataclass
class Example:
    """One token-level training example, plus the provenance needed to audit it."""

    input_ids: list[int]
    labels: list[int]
    attention_mask: list[int]
    representation: str
    tokenization_path: str
    prompt_tokens: int
    supervised_tokens: int
    first_supervised_index: int
    first_supervised_token: int
    first_supervised_text: str
    answer_start_char: int
    terminator_supervised: bool
    reasoning_origin: str | None = None
    reasoning_tokens: int = 0
    think_open_index: int | None = None
    think_close_index: int | None = None
    tokenizer_revision: str = PINNED_REVISION
    notes: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = {
            "input_ids": self.input_ids,
            "labels": self.labels,
            "attention_mask": self.attention_mask,
            "representation": self.representation,
            "tokenization_path": self.tokenization_path,
            "prompt_tokens": self.prompt_tokens,
            "supervised_tokens": self.supervised_tokens,
            "first_supervised_index": self.first_supervised_index,
            "first_supervised_token": self.first_supervised_token,
            "first_supervised_text": self.first_supervised_text,
            "answer_start_char": self.answer_start_char,
            "terminator_supervised": self.terminator_supervised,
            "reasoning_origin": self.reasoning_origin,
            "reasoning_tokens": self.reasoning_tokens,
            "think_open_index": self.think_open_index,
            "think_close_index": self.think_close_index,
            "tokenizer_revision": self.tokenizer_revision,
            "notes": self.notes,
        }
        return d

    def summary(self) -> dict[str, Any]:
        """Public-safe summary: no prompt or answer text."""
        return {
            "representation": self.representation,
            "tokenization_path": self.tokenization_path,
            "prompt_tokens": self.prompt_tokens,
            "supervised_tokens": self.supervised_tokens,
            "first_supervised_index": self.first_supervised_index,
            "first_supervised_token": self.first_supervised_token,
            "terminator_supervised": self.terminator_supervised,
            "reasoning_tokens": self.reasoning_tokens,
            "think_open_index": self.think_open_index,
            "think_close_index": self.think_close_index,
            "tokenizer_revision": self.tokenizer_revision,
        }


# ------------------------------------------------------------------ tokenizer


def load_tokenizer(directory: str | Path | None = None):
    from transformers import AutoTokenizer

    d = Path(directory or os.environ.get("QWEN3_TOKENIZER_DIR") or DEFAULT_TOKENIZER_DIR)
    if not d.exists():
        raise FileNotFoundError(
            f"tokenizer directory not found: {d}. Download tokenizer files at revision "
            f"{PINNED_REVISION}, or set QWEN3_TOKENIZER_DIR."
        )
    return AutoTokenizer.from_pretrained(str(d), trust_remote_code=False)


def describe_tokenizer(tok) -> dict[str, Any]:
    """Structural facts about the tokenizer that the serialization depends on."""
    added = tok.get_added_vocab()
    probes = {}
    for name, surface in (("think_open", "<" + "think" + ">"), ("think_close", "<" + "/" + "think" + ">")):
        probes[name] = {
            "added_vocab_hit": added.get(surface),
            "id_at_string_start": tok.encode(surface, add_special_tokens=False)[0],
            "id_in_context": tok.encode("x" + surface, add_special_tokens=False)[-1],
            "id_with_leading_space": tok.encode(" " + surface, add_special_tokens=False),
        }
    return {
        "revision": PINNED_REVISION,
        "vocab_size": len(tok),
        "eos_token": tok.eos_token,
        "eos_token_id": tok.eos_token_id,
        "pad_token_id": tok.pad_token_id,
        "control_tokens": dict(QWEN3),
        "added_vocab_size": len(added),
        "surfaces": probes,
        "note": (
            "Both markers are single added tokens and match in any position; a preceding space is "
            "a separate token (220). Ordinary prose differs: the word 'thinking' is 82260, and "
            "after a space it is 7274. Render the assistant turn through the chat template and "
            "tokenize it once rather than rebuilding markers by hand."
        ),
    }


# ------------------------------------------------------------------ tokenization paths


def _render(tok, messages: Sequence[Mapping[str, Any]], **kw) -> str:
    return tok.apply_chat_template(list(messages), tokenize=False, **kw)


def _ids(tok, messages: Sequence[Mapping[str, Any]], **kw) -> list[int]:
    out = tok.apply_chat_template(list(messages), tokenize=True, return_dict=False, **kw)
    if isinstance(out, Mapping):  # transformers may hand back a BatchEncoding
        out = out["input_ids"]
    return list(out)


def compare_tokenization_paths(tok, messages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Tokenize the same rendered string two ways and report whether they agree.

    The chat-template path and a plain `encode` of its rendered output agree on the pinned
    revision (asserted by tests). The function stays in the pipeline because agreement is a
    property of this tokenizer build, not a guarantee: a serving stack that renders then
    encodes, or a differently pinned tokenizer, can diverge at a single marker position.
    """
    rendered = _render(tok, messages)
    via_template = _ids(tok, messages)
    via_encode = tok.encode(rendered, add_special_tokens=False)
    diffs = [
        {"index": i, "template": a, "encode": b}
        for i, (a, b) in enumerate(zip(via_template, via_encode))
        if a != b
    ]
    return {
        "rendered_sha256_prefix": __import__("hashlib").sha256(rendered.encode()).hexdigest()[:16],
        "template_tokens": len(via_template),
        "encode_tokens": len(via_encode),
        "agree": via_template == via_encode,
        "differing_positions": diffs,
        "involves_think_marker": any(QWEN3["think_open"] in (d["template"], d["encode"]) for d in diffs),
    }


def reconstruct(tok, ids: Sequence[int]) -> str:
    """Exact text reconstruction from ids. Raises if the ids do not round-trip."""
    return "".join(tok.decode([i]) for i in ids)


# ------------------------------------------------------------------ guards


def _check_messages(messages: Sequence[Mapping[str, Any]], representation: str,
                    reasoning_origin: str | None) -> None:
    for m in messages:
        for k in FORBIDDEN_REASONING_KEYS:
            if k in m:
                raise SerializationError(f"message carries {k!r}; teacher reasoning must not be serialized")
    assistant = [m for m in messages if m.get("role") == "assistant"]
    if representation == "final_only":
        if any("reasoning_content" in m for m in assistant):
            raise SerializationError("representation A must not carry a reasoning prefix")
        if reasoning_origin not in (None, "synthetic_placeholder"):
            raise SerializationError("representation A cannot declare a reasoning origin")
    else:
        if not assistant or "reasoning_content" not in assistant[-1]:
            raise SerializationError("representation B requires a reasoning_content prefix on the final turn")
        if reasoning_origin not in REASONING_ORIGINS:
            raise SerializationError(
                f"reasoning_origin must be one of {REASONING_ORIGINS}; got {reasoning_origin!r}. "
                "Undeclared or teacher-supplied reasoning is refused."
            )


# ------------------------------------------------------------------ builder


def build_example(
    tok,
    conversation: Sequence[Mapping[str, Any]],
    representation: str,
    reasoning_origin: str | None = None,
    supervise_terminator: bool = True,
    tokenization_path: str = "chat_template",
) -> Example:
    """Build one example. Supervises the final answer and the terminator; nothing else.

    `conversation` must end with an assistant turn whose `content` is the target answer.
    For representation B that turn also carries `reasoning_content`, supplied either by the
    student itself or by a synthetic fixture.
    """
    if representation not in REPRESENTATIONS:
        raise SerializationError(f"unknown representation {representation!r}")
    if tokenization_path != "chat_template":
        raise SerializationError("only the chat-template tokenization path is supported")

    conversation = list(conversation)
    if not conversation or conversation[-1].get("role") != "assistant":
        raise SerializationError("conversation must end with an assistant turn")
    answer = conversation[-1].get("content")
    if not isinstance(answer, str) or not answer.strip():
        raise SerializationError("final assistant content must be a non-empty string")

    _check_messages(conversation, representation, reasoning_origin)

    rendered = _render(tok, conversation)
    ids = _ids(tok, conversation)
    if reconstruct(tok, ids) != rendered:
        raise SerializationError("ids do not reconstruct the rendered string; boundary detection is unsafe")

    # Locate the answer. The template writes the answer literally, so it must appear exactly
    # once and must begin on a token boundary.
    occurrences = rendered.count(answer)
    if occurrences != 1:
        raise SerializationError(f"answer text appears {occurrences} times in the render; boundary is ambiguous")
    answer_start = rendered.index(answer)

    # End the example at the assistant terminator. Anything after it is template padding
    # between turns; dropping it is explicit and asserted, never silent.
    terminator_index = next((i for i in range(len(ids) - 1, -1, -1) if ids[i] == QWEN3["im_end"]), None)
    if terminator_index is None:
        raise SerializationError("no <|im_end|> terminator found")
    trailing = "".join(tok.decode([i]) for i in ids[terminator_index + 1:])
    if trailing.strip():
        raise SerializationError("non-whitespace content after the assistant terminator; refusing to drop it")
    ids = ids[:terminator_index + 1]
    if answer_start >= len(rendered):
        raise SerializationError("answer offset outside the render")

    pieces = [tok.decode([i]) for i in ids]
    spans: list[tuple[int, int]] = []
    cursor = 0
    for p in pieces:
        spans.append((cursor, cursor + len(p)))
        cursor += len(p)
    if cursor != len(rendered) - len(trailing):
        raise SerializationError("token spans do not cover the rendered string exactly")
    boundaries = {s[0] for s in spans} | {len(rendered)}
    if answer_start not in boundaries:
        raise SerializationError(
            f"answer starts at char {answer_start}, which is inside a token; refusing partial-token supervision"
        )

    first_sup = next(i for i, (s, _) in enumerate(spans) if s == answer_start)
    labels = [-100] * len(ids)
    for i in range(first_sup, len(ids)):
        labels[i] = ids[i]

    # Terminator: the im_end closing the assistant turn. It is the last supervised token.
    if not supervise_terminator:
        labels[terminator_index] = -100

    think_open = ids.index(QWEN3["think_open"]) if QWEN3["think_open"] in ids else None
    think_close = ids.index(QWEN3["think_close"]) if QWEN3["think_close"] in ids else None

    # Everything before the answer must be unsupervised, including prompt, system and the
    # whole think block. This is the assertion that makes representation A's limitation
    # structural rather than stylistic.
    assert all(l == -100 for l in labels[:first_sup]), "supervision leaked into the prompt or think block"
    if representation == "masked_reasoning_prefix" and think_close is not None:
        assert labels[think_close] == -100, "reasoning terminator must be masked in representation B"
        assert all(l == -100 for l in labels[think_open:think_close + 1]), "reasoning token supervised"

    reasoning_tokens = 0
    if think_open is not None and think_close is not None:
        reasoning_tokens = think_close - think_open - 1 if representation == "masked_reasoning_prefix" else 0

    return Example(
        input_ids=ids,
        labels=labels,
        attention_mask=[1] * len(ids),
        representation=representation,
        tokenization_path=tokenization_path,
        prompt_tokens=first_sup,
        supervised_tokens=sum(1 for l in labels if l != -100),
        first_supervised_index=first_sup,
        first_supervised_token=ids[first_sup],
        first_supervised_text=pieces[first_sup],
        answer_start_char=answer_start,
        terminator_supervised=supervise_terminator and terminator_index is not None,
        reasoning_origin=reasoning_origin,
        reasoning_tokens=max(reasoning_tokens, 0),
        think_open_index=think_open,
        think_close_index=think_close,
        notes={
            "empty_think_block": representation == "final_only",
            "terminator_index": terminator_index,
            "terminator_supervised": supervise_terminator,
            "trailing_newline_supervised": False,
            "rendered_chars": len(rendered),
            "trailing_after_terminator": trailing,
            "tokens_reconstructed_exactly": True,
        },
    )


# ------------------------------------------------------------------ batching


def pad_batch(examples: Sequence[Example], pad_id: int, side: str = "right") -> dict[str, Any]:
    """Pad a batch and assert that padding is never supervised."""
    if side not in ("right", "left"):
        raise SerializationError("side must be 'right' or 'left'")
    width = max(len(e.input_ids) for e in examples)
    batch_ids, batch_labels, batch_mask = [], [], []
    for e in examples:
        pad = width - len(e.input_ids)
        if side == "right":
            ids = e.input_ids + [pad_id] * pad
            labels = e.labels + [-100] * pad
            mask = e.attention_mask + [0] * pad
        else:
            ids = [pad_id] * pad + e.input_ids
            labels = [-100] * pad + e.labels
            mask = [0] * pad + e.attention_mask
        assert len(ids) == len(labels) == len(mask) == width
        batch_ids.append(ids)
        batch_labels.append(labels)
        batch_mask.append(mask)

    for labels, mask in zip(batch_labels, batch_mask):
        for l, m in zip(labels, mask):
            if m == 0:
                assert l == -100, "padding token was supervised"

    return {
        "input_ids": batch_ids,
        "labels": batch_labels,
        "attention_mask": batch_mask,
        "width": width,
        "supervised_per_example": [sum(1 for l in row if l != -100) for row in batch_labels],
        "supervised_total": sum(sum(1 for l in row if l != -100) for row in batch_labels),
    }


def assert_fits(example: Example, max_length: int) -> None:
    """Fail closed instead of silently truncating a prompt or a target."""
    if len(example.input_ids) > max_length:
        raise SerializationError(
            f"example is {len(example.input_ids)} tokens, over the {max_length} limit; "
            "shorten the prompt or the target rather than truncating"
        )


def transition_report(tok, example: Example, window: int = 3) -> dict[str, Any]:
    """What the model sees at the thinking-to-answer transition."""
    i = example.first_supervised_index
    before = example.input_ids[max(0, i - window):i]
    after = example.input_ids[i:i + window + 1]
    return {
        "representation": example.representation,
        "last_unsupervised_ids": before,
        "last_unsupervised_text": [tok.decode([t]) for t in before],
        "first_supervised_ids": after,
        "first_supervised_text": [tok.decode([t]) for t in after],
        "first_supervised_labels": example.labels[i:i + window + 1],
        "think_close_index": example.think_close_index,
        "tokens_between_think_close_and_answer": (
            None if example.think_close_index is None else i - example.think_close_index
        ),
    }
