# `data/smoke/` — what is here, and what is deliberately not

This directory holds **aggregates only**. Raw teacher generations are not in this
repository.

## Why

The 18-call pilot produced candidate SFT targets, including at least one
deliberately harmful output (the S-condition text for `eq2-f4-003`, which writes a
message designed to wound a third party). Those are research evidence, not
publishable artifacts. Publishing them in a public repository would:

- publish unreviewed generated content under a research project's name;
- publish text whose purpose is to harm a third party, detached from the context
  that explains it;
- create a permanent public record that cannot be withdrawn without a history
  rewrite.

So the raw generations live outside Git history, in a local evidence directory
selected by `EQ2_EVIDENCE_DIR`. Nothing in this repository references a specific
local path; scripts refuse to run without the variable set.

## Present (content-free)

| File | Contents |
| --- | --- |
| `summary.json` | call counts, token totals, budget snapshot, pass/fail counts |
| `revalidation.json` | aggregate re-check results of stored text |
| `revalidation_rows.jsonl` | per-call check IDs and case hashes; no target text |
| `cases_at_run.json` | the case content hashes the run was validated against |
| `PRIVATE_EVIDENCE.json` | filenames and SHA-256 of the held-back files |

None of these contain generated prose. They contain counts, check identifiers and
hashes.

## Absent (held privately)

| File | Why held |
| --- | --- |
| `targets.jsonl` | raw teacher output, including the harmful S text |
| `audit.jsonl` | per-call audit records; `content` field carries teacher prose |
| `serialized_examples.jsonl` | the same prose wrapped in chat formats |

Integrity of the held files is recorded in `PRIVATE_EVIDENCE.json`, so a reader can
verify that the local copies are the ones the aggregates describe without seeing
the text.

## Consequence for the published history

These files were committed and pushed in `59a0401` and remain reachable in the
public branch history. Removing them from the current tree does not unpublish them.
See `reports/PUBLIC_ARTIFACT_POLICY.md`, "History cleanup", for what that would
require and what stays recoverable.
