"""Tests for native Qwen3 serialization and the loss mask.

These run against the pinned tokenizer build (revision 1cfa9a72...). They are skipped when
the tokenizer files are absent, so a fresh clone still passes; the numbers they assert are
recorded in reports/NATIVE_TEMPLATE_AUDIT.md and reports/LOSS_MASK_AUDIT.md.

No model is loaded, nothing is trained, no teacher is called.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from native_serialize import (  # noqa: E402
    DEFAULT_TOKENIZER_DIR,
    PINNED_REVISION,
    QWEN3,
    SerializationError,
    assert_fits,
    build_example,
    compare_tokenization_paths,
    describe_tokenizer,
    load_tokenizer,
    pad_batch,
    reconstruct,
    transition_report,
)

TOKENIZER_AVAILABLE = (Path(os.environ.get("QWEN3_TOKENIZER_DIR") or DEFAULT_TOKENIZER_DIR)).exists()
needs_tokenizer = pytest.mark.skipif(not TOKENIZER_AVAILABLE, reason="Qwen3 tokenizer files not present")

MARK_OPEN = "<" + "think" + ">"
MARK_CLOSE = "<" + "/" + "think" + ">"


@pytest.fixture(scope="module")
def tok():
    return load_tokenizer()


def conv(answer="answer", reasoning=None):
    c = [{"role": "user", "content": "hi"}]
    last = {"role": "assistant", "content": answer}
    if reasoning is not None:
        last["reasoning_content"] = reasoning
    return c + [last]


# ------------------------------------------------------------------ tokenizer facts


@needs_tokenizer
def test_control_tokens_and_markers_are_what_the_reports_claim(tok):
    assert PINNED_REVISION.startswith("1cfa9a72")
    assert tok.convert_tokens_to_ids("<|im_start|>") == QWEN3["im_start"] == 151644
    assert tok.convert_tokens_to_ids("<|im_end|>") == QWEN3["im_end"] == 151645
    assert tok.encode(MARK_OPEN, add_special_tokens=False) == [151667]
    assert tok.encode(MARK_CLOSE, add_special_tokens=False) == [151668]
    assert tok.eos_token_id == QWEN3["im_end"]
    assert tok.pad_token_id == QWEN3["endoftext"]


@needs_tokenizer
def test_markers_are_not_confused_with_prose(tok):
    # Characterization: the word and the marker are different tokens. Hand-typed prompts that
    # use the word instead of the marker change the sequence.
    assert tok.encode("thinking", add_special_tokens=False) != [151667]
    assert tok.encode(" " + MARK_OPEN, add_special_tokens=False) == [220, 151667]
    d = describe_tokenizer(tok)
    assert d["surfaces"]["think_open"]["id_at_string_start"] == 151667
    assert d["surfaces"]["think_close"]["id_at_string_start"] == 151668


@needs_tokenizer
def test_template_and_plain_encode_agree_on_the_pinned_build(tok):
    r = compare_tokenization_paths(tok, conv("answer", "compare"))
    assert r["agree"] is True
    assert r["involves_think_marker"] is False


# ------------------------------------------------------------------ representation A


@needs_tokenizer
def test_representation_a_supervises_only_the_answer_and_terminator(tok):
    ex = build_example(tok, conv("The limit should be raised."), "final_only")
    assert ex.representation == "final_only"
    assert ex.notes["empty_think_block"] is True
    assert ex.terminator_supervised is True

    sup = [i for i, l in enumerate(ex.labels) if l != -100]
    assert sup[0] == ex.first_supervised_index == ex.prompt_tokens
    assert sup[-1] == len(ex.input_ids) - 1
    assert ex.input_ids[-1] == QWEN3["im_end"]
    assert all(l == -100 for l in ex.labels[:ex.first_supervised_index])

    # The think block exists and is unsupervised, including both markers.
    assert ex.think_open_index is not None and ex.think_close_index is not None
    assert all(l == -100 for l in ex.labels[ex.think_open_index:ex.think_close_index + 1])

    # Supervised count = answer tokens + terminator.
    answer_tokens = len(tok.encode("The limit should be raised.", add_special_tokens=False))
    assert ex.supervised_tokens == answer_tokens + 1


@needs_tokenizer
def test_representation_a_cannot_teach_thinking_by_construction(tok):
    """A's limitation is structural: no reasoning token is ever supervised."""
    ex = build_example(tok, conv("Raise the limit."), "final_only")
    assert ex.reasoning_tokens == 0
    tr = transition_report(tok, ex)
    assert tr["last_unsupervised_ids"][-1] == 271  # "\n\n" after the empty think block
    assert QWEN3["think_close"] in tr["last_unsupervised_ids"]
    assert tr["first_supervised_text"][0].strip() != ""


# ------------------------------------------------------------------ representation B


@needs_tokenizer
def test_representation_b_masks_every_reasoning_token(tok):
    ex = build_example(tok, conv("Raise the limit.", "compare peak with limit"),
                       "masked_reasoning_prefix", reasoning_origin="synthetic_placeholder")
    assert ex.representation == "masked_reasoning_prefix"
    assert ex.reasoning_tokens > 0
    assert ex.reasoning_origin == "synthetic_placeholder"
    assert all(l == -100 for l in ex.labels[ex.think_open_index:ex.think_close_index + 1])
    assert ex.labels[ex.first_supervised_index] == ex.input_ids[ex.first_supervised_index]
    assert all(l == -100 for l in ex.labels[:ex.first_supervised_index])
    assert ex.terminator_supervised is True
    answer_tokens = len(tok.encode("Raise the limit.", add_special_tokens=False))
    assert ex.supervised_tokens == answer_tokens + 1


@needs_tokenizer
def test_representation_b_requires_a_declared_student_origin(tok):
    conv_b = conv("Raise the limit.", "reasoning")
    with pytest.raises(SerializationError):
        build_example(tok, conv_b, "masked_reasoning_prefix")  # undeclared
    with pytest.raises(SerializationError):
        build_example(tok, conv_b, "masked_reasoning_prefix", reasoning_origin="teacher")
    with pytest.raises(SerializationError):
        build_example(tok, conv("Raise the limit."), "masked_reasoning_prefix",
                      reasoning_origin="student")  # no reasoning_content


# ------------------------------------------------------------------ guards


@needs_tokenizer
def test_teacher_reasoning_keys_are_refused(tok):
    c = conv("Raise the limit.")
    c[-1]["teacher_reasoning"] = "the teacher thought this"
    with pytest.raises(SerializationError):
        build_example(tok, c, "final_only")
    c2 = conv("Raise the limit.")
    c2[-1]["analysis"] = "hidden"
    with pytest.raises(SerializationError):
        build_example(tok, c2, "final_only")


@needs_tokenizer
def test_representation_a_rejects_a_reasoning_prefix(tok):
    with pytest.raises(SerializationError):
        build_example(tok, conv("Raise the limit.", "reasoning"), "final_only")


@needs_tokenizer
def test_reconstruction_is_exact(tok):
    rendered = tok.apply_chat_template(conv("answer", "r"), tokenize=False)
    ids = tok.apply_chat_template(conv("answer", "r"), tokenize=True, return_dict=False)
    assert reconstruct(tok, ids) == rendered


@needs_tokenizer
def test_ambiguous_answer_boundary_is_refused(tok):
    # An answer that also appears in the prompt cannot be located unambiguously.
    c = [{"role": "user", "content": "Say hello."},
         {"role": "assistant", "content": "hello"}]
    with pytest.raises(SerializationError):
        build_example(tok, c, "final_only")


# ------------------------------------------------------------------ batching and truncation


@needs_tokenizer
def test_padding_is_never_supervised(tok):
    a = build_example(tok, conv("Short."), "final_only")
    b = build_example(tok, conv("A much longer answer that will set the batch width."), "final_only")
    for side in ("right", "left"):
        batch = pad_batch([a, b], pad_id=tok.pad_token_id, side=side)
        assert batch["width"] == max(len(a.input_ids), len(b.input_ids))
        for labels, mask in zip(batch["labels"], batch["attention_mask"]):
            assert len(labels) == len(mask) == batch["width"]
            for l, m in zip(labels, mask):
                if m == 0:
                    assert l == -100
        assert batch["supervised_total"] == sum(batch["supervised_per_example"])


@needs_tokenizer
def test_truncation_fails_closed(tok):
    ex = build_example(tok, conv("Raise the limit."), "final_only")
    assert_fits(ex, max_length=len(ex.input_ids))
    with pytest.raises(SerializationError):
        assert_fits(ex, max_length=len(ex.input_ids) - 1)
