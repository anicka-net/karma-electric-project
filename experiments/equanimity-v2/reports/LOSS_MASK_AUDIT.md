# Stage 1 — loss-mask audit

**Tokenizer revision:** `1cfa9a7208912126459214e8b04321603b3df60c`  
**Examples:** 4. Private development cases used: yes  
**Stage:** 1 (offline). No training, no sampling, no teacher.

Question: with the real tokenizer and template, which tokens are actually supervised, and what does each representation teach?

The full token dump is private. This report carries aggregate counts and the transition tokens; prompt text and answers stay in the private evidence directory.

## Per-example supervision

| Case | Representation | Prompt tokens | Supervised | Answer tokens | First supervised token | Terminator |
|---|---|---|---|---|---|---|
| `eq2-f6-001/A0` | final_only | 56 | 76 | 75 | 785 | yes |
| `eq2-f6-001/A0` | masked_reasoning_prefix | 78 | 76 | 75 | 785 | yes |
| `eq2-f2-005/B0` | final_only | 111 | 83 | 82 | 2753 | yes |
| `eq2-f2-005/B0` | masked_reasoning_prefix | 133 | 83 | 82 | 2753 | yes |

## Invariant matrix

| Check | eq2-f6-001/A0/final_only | eq2-f6-001/A0/masked_reasoning_prefix | eq2-f2-005/B0/final_only | eq2-f2-005/B0/masked_reasoning_prefix |
|---|---|---|---|---|
| empty think block present | pass | n/a | pass | n/a |
| first supervised is first answer token | pass | pass | pass | pass |
| ids reconstruct render | pass | pass | pass | pass |
| no partial token answer start | pass | pass | pass | pass |
| no teacher reasoning keys | pass | pass | pass | pass |
| prompt unsupervised | pass | pass | pass | pass |
| reasoning prefix present | n/a | pass | n/a | pass |
| reasoning tokens masked | n/a | pass | n/a | pass |
| some answer supervised | pass | pass | pass | pass |
| supervised count matches answer plus terminator | pass | pass | pass | pass |
| terminator supervised | pass | pass | pass | pass |
| think block unsupervised | pass | pass | pass | pass |
| trailing after terminator is whitespace | pass | pass | pass | pass |

Overall: all checks passed; padding unsupervised yes; truncation fails closed yes.

## The thinking-to-answer transition

### `eq2-f6-001/A0` / final_only

Tokens between `</think>` and the first supervised token: 2.

| Position | Token | Text | Label |
|---|---|---|---|
| — | 271 | `\n\n` | -100 |
| — | 151668 | `</think>` | -100 |
| — | 271 | `\n\n` | -100 |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |

### `eq2-f6-001/A0` / masked_reasoning_prefix

Tokens between `</think>` and the first supervised token: 2.

| Position | Token | Text | Label |
|---|---|---|---|
| — | 624 | `.\n` | -100 |
| — | 151668 | `</think>` | -100 |
| — | 271 | `\n\n` | -100 |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |

### `eq2-f2-005/B0` / final_only

Tokens between `</think>` and the first supervised token: 2.

| Position | Token | Text | Label |
|---|---|---|---|
| — | 271 | `\n\n` | -100 |
| — | 151668 | `</think>` | -100 |
| — | 271 | `\n\n` | -100 |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |

### `eq2-f2-005/B0` / masked_reasoning_prefix

Tokens between `</think>` and the first supervised token: 2.

| Position | Token | Text | Label |
|---|---|---|---|
| — | 624 | `.\n` | -100 |
| — | 151668 | `</think>` | -100 |
| — | 271 | `\n\n` | -100 |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |
| — | <redacted> | `<redacted: answer start>` | supervised |

## Batch

Width 194 tokens. Supervised tokens per example: [76, 83]. Total supervised: 159. Padding positions carry attention 0 and label -100 in both left- and right-padded layouts (both tested).

## Synthetic worked example (public-safe)

Generic text, not derived from any development case.

| Position | Token text | Id | Label |
|---|---|---|---|
| 0 | `<|im_start|>` | 151644 | -100 |
| 1 | `user` | 872 | -100 |
| 2 | `\n` | 198 | -100 |
| 3 | `Say` | 45764 | -100 |
| 4 | ` hello` | 23811 | -100 |
| 5 | `.` | 13 | -100 |
| 6 | `<|im_end|>` | 151645 | -100 |
| 7 | `\n` | 198 | -100 |
| 8 | `<|im_start|>` | 151644 | -100 |
| 9 | `assistant` | 77091 | -100 |
| 10 | `\n` | 198 | -100 |
| 11 | `<think>` | 151667 | -100 |
| 12 | `\n\n` | 271 | -100 |
| 13 | `</think>` | 151668 | -100 |
| 14 | `\n\n` | 271 | -100 |
| 15 | `Hello` | 9707 | 9707 |
| 16 | `.` | 13 | 13 |
| 17 | `<|im_end|>` | 151645 | 151645 |

First supervised position: 15. Supervised tokens: 3.

## What each representation teaches

**A — final only.** The supervised span is the answer plus the terminator. The prompt, the system turn and the entire (empty) think block are -100. At every step the model is asked to predict an answer immediately after an empty thinking channel. Nothing in the loss rewards producing a thinking continuation, and nothing penalises omitting one. This is a formalised skip-thinking representation: it is native in format but empty in the region the construct is supposed to occupy.

**B — masked reasoning prefix.** The supervised span is again the answer plus the terminator, but the context now contains a reasoning prefix that the student itself would have produced. The prefix is masked, so the model is not trained to imitate it; it is trained to continue from it. This preserves the model's own continuation in context while keeping loss on the answer only. It cannot create thinking ability that the student does not have — it preserves what is already there.

Neither representation supervises the terminator's *timing*: `</think>` is masked in B, so when to close the channel is learned only from the student's own prefix, not from the loss.

## Limitations

- Representation B uses a hand-written placeholder reasoning prefix; no student model has produced a real one yet, so nothing here shows that a student's own continuation is preserved in context faithfully.
- Answer-token counts are tokenizer counts for the stored answer text; they say nothing about answer quality.
- The batch is two examples. Padding and offset behaviour is exercised, not stress-tested.

Additional: supervising `</response>` (the terminator token) is a deliberate choice recorded in the builder; masking it changes the supervised count by one per example and removes any gradient that teaches the model when to stop answering.

