# First native-thinking-preservation pilot

Purpose: determine whether a student trained on this data keeps *its own* native thinking
behaviour, rather than acquiring a fabricated reasoning style from the teacher. Nothing here
has been run. No claim is made until it is.

## Why this is separate from the data factory

The data factory stops at semantic cases and demonstration renderers. `chatml` and `harmony`
in `src/serialize.py` are checked against their format grammars, but they are not a verified
student pipeline. Three things are unverified and must be verified per student:

1. the model's own chat template and its special-token ids;
2. the assistant-only loss mask (what is actually supervised);
3. that no reasoning channel is introduced by the dataset.

## Stage 0 — format conformance (offline, no GPU, no API)

For one student (Qwen3-4B first, Gemma 4 later):

- Load the tokenizer. Dump the chat template.
- Render one case with the model's own template. Assert: no `<|im_start|>`/`<|im_end|>`
  mismatch, no channel token from another format, and that the rendered string round-trips
  byte-identically through `tokenizer.decode(tokenizer.encode(...))` for the assistant span.
- Assert the special-token ids for the template's control tokens match the values the
  tokenizer reserves. A mismatch is a silent corruption mode: the model sees control tokens as
  ordinary text.

Falsified by: any round-trip mismatch, or a special token id colliding with a text token.

## Stage 1 — loss mask verification (one batch, CPU is enough)

- Build a two-example batch from `data/validated/cases.jsonl`.
- Compute labels from `input_ids` masked to the assistant span only.
- Assert: every label outside the assistant span is `-100`; the first supervised token is the
  token immediately after the template's assistant-turn delimiter; the count of supervised
  tokens equals the assistant content length plus its terminator.
- Assert: the supervised text contains no `<|channel|>analysis`, no `reasoning_content`, and no
  `thinking:` substring (`tests/test_regressions.py` already enforces the data half).

Falsified by: any prompt tokens supervised, or any reasoning marker inside the supervised span.

## Stage 2 — no fabricated reasoning in the target

The dataset contains no analysis channel by construction, and `to_harmony` never emits one.
The pilot's job is to confirm this end to end on real rendered batches:

- Assert `analysis` never appears in any supervised span across the whole training set.
- Assert the dataset does not teach "let me think step by step" style preambles: run
  `find_reasoning_markers` over every target.

## Stage 3 — preservation, after training

Train a small student on the training split (this is the only stage that costs compute and it
is out of scope until the data is human-approved). Then:

- Sample N held-out *neutral* prompts with the student's thinking enabled.
- Measure: fraction of generations that contain the student's own native thinking span, mean
  thinking length, and the rate of spontaneous structure the base model showed.
- Compare against the untrained base on the identical prompts, same sampling parameters, same N.

Falsification threshold, declared before running: if the native thinking rate falls below 50%
of base, or mean thinking length falls below 40% of base, the pilot fails and the dataset is
implicated. If the model's thinking survives, the next question is whether it survives under
pressure — which is the actual research question this dataset exists to serve.

## What is explicitly not claimed

- That native thinking is preserved. It has not been measured.
- That the demonstration renderers are sufficient for training. They are not; the student's own
  template is used instead.
- That reasoning quality improved. The dataset targets nonreactivity under pressure, not
  reasoning skill.

## Sequencing

Stage 0 and Stage 1 are offline and cheap. They should be done *before* any human approval of
the data, because they test the machinery rather than the content. Stage 3 requires approved
data and compute, and is blocked on the review gate.
