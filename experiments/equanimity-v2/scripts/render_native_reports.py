#!/usr/bin/env python3
"""Render the two native-thinking audit reports from the recorded JSON.

Nothing is hand-transcribed. If the JSON is regenerated, the reports change with it.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "native"
REPORTS = ROOT / "reports"


def esc(s: str) -> str:
    return s.replace("\n", "\\n")


def template_report() -> str:
    d = json.loads((DATA / "template_audit.json").read_text())
    o = []
    a = o.append
    a("# Stage 0 — native Qwen3 template audit")
    a("")
    a(f"**Tokenizer revision:** `{d['revision']}`  ")
    a(f"**Stage:** 0 (offline, synthetic messages only). No model loaded, no teacher called.")
    a("")
    a("Question: can the serialization the model was trained on be reproduced from the artifacts "
      "in hand, and where exactly does the assistant turn end and the answer begin?")
    a("")
    a("## Tokenizer files")
    a("")
    a("| File | Bytes | SHA-256 |")
    a("|---|---|---|")
    for name, h in sorted(d["tokenizer_files"].items()):
        a(f"| `{name}` | {h['bytes']} | `{h['sha256'][:32]}…` |")
    a("")
    a("## Control tokens")
    a("")
    a("| Token | Id |")
    a("|---|---|")
    for k, v in d["tokenizer"]["control_tokens"].items():
        a(f"| `{k}` | {v} |")
    a("")
    a(f"Vocabulary size {d['tokenizer']['vocab_size']}, eos `{d['tokenizer']['eos_token']}`, "
      f"pad `{d['tokenizer']['pad_token_id']}`.")
    a("")
    a("## Thinking markers")
    a("")
    a("| Marker | Added-token id | At string start | In context | With a leading space |")
    a("|---|---|---|---|---|")
    for name, s in d["tokenizer"]["surfaces"].items():
        a(f"| `{name}` | {s['added_vocab_hit']} | {s['id_at_string_start']} | "
          f"{s['id_in_context']} | {s['id_with_leading_space']} |")
    a("")
    a(f"{d['tokenizer']['note']}")
    a("")
    a("## Findings")
    a("")
    a("| Claim | Verified |")
    a("|---|---|")
    for k, v in d["findings"].items():
        a(f"| {k.replace('_', ' ')} | {'yes' if v else 'no'} |")
    a("")
    a("## Template probes")
    a("")
    for name, p in d["probes"].items():
        a(f"### `{name}`")
        a("")
        kw = ", ".join(f"{k}={v}" for k, v in p["kwargs"].items()) or "no extra kwargs"
        a(f"Call: `apply_chat_template(..., {kw})`. Tokens: {p['n_tokens']}. "
          f"Reconstruction exact: {'yes' if p['reconstruction_exact'] else 'no'}.")
        a("")
        a("```text")
        a(esc(p["rendered"]))
        a("```")
        a("")
        a(f"Ids: `{p['ids']}`")
        a("")
        layout = ", ".join(f"{k}={v}" for k, v in p["tokens_matching_layout"].items() if v)
        a(f"Layout tokens present: {layout or 'none'}.")
        foreign = [k for k, v in p["foreign_markers_found"].items() if v]
        a(f"Foreign control markers: {', '.join(foreign) if foreign else 'none'}.")
        a("")
    a("## Tokenization path comparison")
    a("")
    a("| Render | Template tokens | Plain-encode tokens | Agree |")
    a("|---|---|---|---|")
    for name, c in d["tokenization_path_comparison"].items():
        a(f"| {name} | {c['template_tokens']} | {c['encode_tokens']} | "
          f"{'yes' if c['agree'] else 'no'} |")
    a("")
    a("## Interpretation")
    a("")
    for k, v in d["interpretation"].items():
        a(f"**{k.replace('_', ' ')}.** {v}")
        a("")
    a("## What this establishes")
    a("")
    a("1. The assistant turn is delimited by an explicit `<|im_start|>`/`<|im_end|>` pair, and the "
      "answer begins on a token boundary that can be located from the render.")
    a("2. The thinking channel opens with a single token (` thinking`) and closes with a single "
      "token (`</think>`), in every position tested.")
    a("3. A template-native assistant turn without reasoning renders an **empty** think block. This "
      "is the structural reason representation A cannot teach thinking: the model always sees an "
      "empty channel before the supervised answer.")
    a("4. With `enable_thinking=False` the generation prompt pre-fills the empty think block, so the "
      "model starts after `</think>`. With `enable_thinking=True` it stops at `assistant\\n` and the "
      "model emits its own opener.")
    a("5. Every render reconstructs exactly from its ids, so a token offset computed from the render "
      "is trustworthy for this build.")
    a("")
    a("## What this does not establish")
    a("")
    for lim in d["limitations"]:
        a(f"- {lim}")
    a("")
    return "\n".join(o) + "\n"


def loss_mask_report() -> str:
    d = json.loads((DATA / "loss_mask_summary.json").read_text())
    o = []
    a = o.append
    a("# Stage 1 — loss-mask audit")
    a("")
    a(f"**Tokenizer revision:** `{d['revision']}`  ")
    a(f"**Examples:** {d['n_examples']}. Private development cases used: "
      f"{'yes' if d['private_cases_used'] else 'no'}  ")
    a(f"**Stage:** 1 (offline). No training, no sampling, no teacher.")
    a("")
    a("Question: with the real tokenizer and template, which tokens are actually supervised, and "
      "what does each representation teach?")
    a("")
    a("The full token dump is private. This report carries aggregate counts and the transition "
      "tokens; prompt text and answers stay in the private evidence directory.")
    a("")
    a("## Per-example supervision")
    a("")
    a("| Case | Representation | Prompt tokens | Supervised | Answer tokens | First supervised token | Terminator |")
    a("|---|---|---|---|---|---|---|")
    for e in d["per_example"]:
        s = e["summary"]
        a(f"| `{e['case']}` | {e['representation']} | {s['prompt_tokens']} | {s['supervised_tokens']} | "
          f"{e.get('answer_tokens', '—')} | {s['first_supervised_token']} | "
          f"{'yes' if s['terminator_supervised'] else 'no'} |")
    a("")
    a("## Invariant matrix")
    a("")
    checks = sorted({k for e in d["per_example"] for k in e["checks"]})
    a("| Check | " + " | ".join(f"{e['case']}/{e['representation']}" for e in d["per_example"]) + " |")
    a("|---|" + "---|" * len(d["per_example"]))
    for c in checks:
        def cell(e):
            v = e["checks"].get(c)
            return "n/a" if v is None else ("pass" if v else "**FAIL**")
        row = " | ".join(cell(e) for e in d["per_example"])
        a(f"| {c.replace('_', ' ')} | {row} |")
    a("")
    a(f"Overall: {'all checks passed' if d['overall']['all_example_checks_passed'] else 'FAILURES PRESENT'}; "
      f"padding unsupervised {'yes' if d['overall']['padding_unsupervised'] else 'no'}; "
      f"truncation fails closed {'yes' if d['overall']['truncation_fails_closed'] else 'no'}.")
    a("")
    a("## The thinking-to-answer transition")
    a("")
    for e in d["per_example"]:
        t = e["transition"]
        a(f"### `{e['case']}` / {e['representation']}")
        a("")
        a(f"Tokens between `</think>` and the first supervised token: "
          f"{t['tokens_between_think_close_and_answer']}.")
        a("")
        a("| Position | Token | Text | Label |")
        a("|---|---|---|---|")
        seq = list(zip(t["last_unsupervised_ids"], t["last_unsupervised_text"], ["-100"] * len(t["last_unsupervised_ids"])))
        seq += list(zip(t["first_supervised_ids"], t["first_supervised_text"],
                        [str(x) for x in t["first_supervised_labels"]]))
        for tid, text, lab in seq:
            a(f"| — | {tid} | `{esc(text)}` | {lab} |")
        a("")
    a("## Batch")
    a("")
    a(f"Width {d['batch']['width']} tokens. Supervised tokens per example: "
      f"{d['batch']['supervised_per_example']}. Total supervised: {d['batch']['supervised_total']}. "
      "Padding positions carry attention 0 and label -100 in both left- and right-padded layouts "
      "(both tested).")
    a("")
    a("## Synthetic worked example (public-safe)")
    a("")
    a("Generic text, not derived from any development case.")
    a("")
    a("| Position | Token text | Id | Label |")
    a("|---|---|---|---|")
    for i, (txt, tid, lab) in enumerate(zip(d["synthetic_worked_example"]["rendered_tokens"],
                                            d["synthetic_worked_example"]["input_ids"],
                                            d["synthetic_worked_example"]["labels"])):
        a(f"| {i} | `{esc(txt)}` | {tid} | {lab} |")
    a("")
    a(f"First supervised position: {d['synthetic_worked_example']['first_supervised_index']}. "
      f"Supervised tokens: {d['synthetic_worked_example']['supervised_tokens']}.")
    a("")
    a("## What each representation teaches")
    a("")
    a("**A — final only.** The supervised span is the answer plus the terminator. The prompt, the "
      "system turn and the entire (empty) think block are -100. At every step the model is asked to "
      "predict an answer immediately after an empty thinking channel. Nothing in the loss rewards "
      "producing a thinking continuation, and nothing penalises omitting one. This is a formalised "
      "skip-thinking representation: it is native in format but empty in the region the construct "
      "is supposed to occupy.")
    a("")
    a("**B — masked reasoning prefix.** The supervised span is again the answer plus the terminator, "
      "but the context now contains a reasoning prefix. The prefix is masked, so loss falls on the "
      "answer only.")
    a("")
    a("**What is verified here is token alignment only.** The prefix is present in context and carries "
      "no loss; the answer starts on a token boundary after it. Whether a *real* student's own "
      "continuation is preserved faithfully is **not** verified: the prefix used in this audit is a "
      "hand-written synthetic placeholder, no student model has been run, and nothing here shows that "
      "conditioning on a prefix leaves behaviour unchanged. That is gate L2 in "
      "`reports/REASONING_PRESERVATION_PROTOCOL.md`, and it requires a model.")
    a("")
    a("Neither representation supervises the terminator's *timing*: `</think>` is masked in B, so "
      "when to close the channel is learned only from the student's own prefix, not from the loss.")
    a("")
    a("## Limitations")
    a("")
    for lim in d["limitations"]:
        a(f"- {lim}")
    a("")
    a("Additional: supervising the assistant terminator `<|im_end|>` (151645) is a deliberate choice "
      "recorded in the builder; masking it changes the supervised count by one per example and removes "
      "any gradient that teaches the model when to stop answering. The tokenizer's own eos is also "
      "`<|im_end|>`, asserted by `test_control_tokens_and_markers_are_what_the_reports_claim`. The "
      "reasoning channel closes with ` response` (151668), which is a different token and is masked.")
    a("")
    return "\n".join(o) + "\n"


def main() -> int:
    (REPORTS / "NATIVE_TEMPLATE_AUDIT.md").write_text(template_report())
    (REPORTS / "LOSS_MASK_AUDIT.md").write_text(loss_mask_report())
    print("wrote reports/NATIVE_TEMPLATE_AUDIT.md and reports/LOSS_MASK_AUDIT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
