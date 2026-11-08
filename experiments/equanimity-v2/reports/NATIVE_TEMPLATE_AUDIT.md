# Stage 0 — native Qwen3 template audit

**Tokenizer revision:** `1cfa9a7208912126459214e8b04321603b3df60c`  
**Stage:** 0 (offline, synthetic messages only). No model loaded, no teacher called.

Question: can the serialization the model was trained on be reproduced from the artifacts in hand, and where exactly does the assistant turn end and the answer begin?

## Tokenizer files

| File | Bytes | SHA-256 |
|---|---|---|
| `merges.txt` | 1671853 | `8831e4f1a044471340f7c0a83d7bd713…` |
| `tokenizer.json` | 11422654 | `aeb13307a71acd8fe81861d94ad54ab6…` |
| `tokenizer_config.json` | 9732 | `d5d09f07b48c3086c508b30d1c9114bd…` |
| `vocab.json` | 2776833 | `ca10d7e9fb3ed18575dd1e277a2579c1…` |

## Control tokens

| Token | Id |
|---|---|
| `im_start` | 151644 |
| `im_end` | 151645 |
| `endoftext` | 151643 |
| `think_open` | 151667 |
| `think_close` | 151668 |

Vocabulary size 151669, eos `<|im_end|>`, pad `151643`.

## Thinking markers

| Marker | Added-token id | At string start | In context | With a leading space |
|---|---|---|---|---|
| `think_open` | 151667 | 151667 | 151667 | [220, 151667] |
| `think_close` | 151668 | 151668 | 151668 | [220, 151668] |

Both markers are single added tokens and match in any position; a preceding space is a separate token (220). Ordinary prose differs: the word 'thinking' is 82260, and after a space it is 7274. Render the assistant turn through the chat template and tokenize it once rather than rebuilding markers by hand.

## Findings

| Claim | Verified |
|---|---|
| answer only turn carries empty think block | yes |
| thinking disabled prompt prefills empty think block | yes |
| thinking enabled prompt opens assistant turn without marker | yes |
| all renders reconstruct exactly | yes |
| no foreign control markers | yes |
| template paths agree with plain encode | yes |
| system role supported | yes |

## Template probes

### `generation_prompt_thinking_enabled`

Call: `apply_chat_template(..., add_generation_prompt=True, enable_thinking=True)`. Tokens: 26. Reconstruction exact: yes.

```text
<|im_start|>system\nYou are a careful assistant.<|im_end|>\n<|im_start|>user\nWhy does the container get killed?<|im_end|>\n<|im_start|>assistant\n
```

Ids: `[151644, 8948, 198, 2610, 525, 264, 16585, 17847, 13, 151645, 198, 151644, 872, 198, 10234, 1558, 279, 5476, 633, 7425, 30, 151645, 198, 151644, 77091, 198]`

Layout tokens present: im_start=3, im_end=2.
Foreign control markers: none.

### `generation_prompt_thinking_disabled`

Call: `apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)`. Tokens: 30. Reconstruction exact: yes.

```text
<|im_start|>system\nYou are a careful assistant.<|im_end|>\n<|im_start|>user\nWhy does the container get killed?<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n
```

Ids: `[151644, 8948, 198, 2610, 525, 264, 16585, 17847, 13, 151645, 198, 151644, 872, 198, 10234, 1558, 279, 5476, 633, 7425, 30, 151645, 198, 151644, 77091, 198, 151667, 271, 151668, 271]`

Layout tokens present: im_start=3, im_end=2, think_open=1, think_close=1.
Foreign control markers: none.

### `assistant_turn_with_reasoning`

Call: `apply_chat_template(..., no extra kwargs)`. Tokens: 43. Reconstruction exact: yes.

```text
<|im_start|>system\nYou are a careful assistant.<|im_end|>\n<|im_start|>user\nWhy does the container get killed?<|im_end|>\n<|im_start|>assistant\n<think>\nCompare the peak with the limit.\n</think>\n\nRaise the limit.<|im_end|>\n
```

Ids: `[151644, 8948, 198, 2610, 525, 264, 16585, 17847, 13, 151645, 198, 151644, 872, 198, 10234, 1558, 279, 5476, 633, 7425, 30, 151645, 198, 151644, 77091, 198, 151667, 198, 27374, 279, 16162, 448, 279, 3930, 624, 151668, 271, 93101, 279, 3930, 13, 151645, 198]`

Layout tokens present: im_start=3, im_end=3, think_open=1, think_close=1.
Foreign control markers: none.

### `assistant_turn_without_reasoning`

Call: `apply_chat_template(..., no extra kwargs)`. Tokens: 36. Reconstruction exact: yes.

```text
<|im_start|>system\nYou are a careful assistant.<|im_end|>\n<|im_start|>user\nWhy does the container get killed?<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\nRaise the limit.<|im_end|>\n
```

Ids: `[151644, 8948, 198, 2610, 525, 264, 16585, 17847, 13, 151645, 198, 151644, 872, 198, 10234, 1558, 279, 5476, 633, 7425, 30, 151645, 198, 151644, 77091, 198, 151667, 271, 151668, 271, 93101, 279, 3930, 13, 151645, 198]`

Layout tokens present: im_start=3, im_end=3, think_open=1, think_close=1.
Foreign control markers: none.

### `user_only`

Call: `apply_chat_template(..., no extra kwargs)`. Tokens: 23. Reconstruction exact: yes.

```text
<|im_start|>system\nYou are a careful assistant.<|im_end|>\n<|im_start|>user\nWhy does the container get killed?<|im_end|>\n
```

Ids: `[151644, 8948, 198, 2610, 525, 264, 16585, 17847, 13, 151645, 198, 151644, 872, 198, 10234, 1558, 279, 5476, 633, 7425, 30, 151645, 198]`

Layout tokens present: im_start=2, im_end=2.
Foreign control markers: none.

## Tokenization path comparison

| Render | Template tokens | Plain-encode tokens | Agree |
|---|---|---|---|
| generation_prompt | 23 | 23 | yes |
| assistant_with_reasoning | 43 | 43 | yes |

## Interpretation

**answer only turn carries empty think block.** A template-native assistant turn without reasoning_content renders an empty think block before the answer. Masking the prompt and the think block and supervising the answer therefore presents the model with 'empty think block -> answer' at every training step, and never with a thinking continuation.

**thinking enabled prompt.** With enable_thinking=True the generation prompt stops at 'assistant\n' and the model emits its own  thinking. With enable_thinking=False the prompt pre-fills an empty think block, so the model always starts after </think>.

## What this establishes

1. The assistant turn is delimited by an explicit `<|im_start|>`/`<|im_end|>` pair, and the answer begins on a token boundary that can be located from the render.
2. The thinking channel opens with a single token (` thinking`) and closes with a single token (`</think>`), in every position tested.
3. A template-native assistant turn without reasoning renders an **empty** think block. This is the structural reason representation A cannot teach thinking: the model always sees an empty channel before the supervised answer.
4. With `enable_thinking=False` the generation prompt pre-fills the empty think block, so the model starts after `</think>`. With `enable_thinking=True` it stops at `assistant\n` and the model emits its own opener.
5. Every render reconstructs exactly from its ids, so a token offset computed from the render is trustworthy for this build.

## What this does not establish

- These probes use synthetic messages; they establish template structure, not behaviour.
- Whether a serving stack tokenizes the rendered string or replays template ids cannot be determined from tokenizer files alone; the comparison recorded here only shows that the two paths agree for this build.

