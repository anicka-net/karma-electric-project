# Public artifact policy

This repository is public. That was not accounted for when the pilot first landed, and the
consequence is that some artifacts are now permanently in public Git history. This document
states the policy, what has been done, and what a history cleanup would require.

## Classification

### Safe to commit

- Code: `src/`, `scripts/`, `tests/`
- Schemas: `schema/`
- Authored scenario specifications: `scenarios/` (synthetic; no real people, no real
  organisations)
- Sanitized reports: `reports/` with no infrastructure identifiers and no generated prose
- Aggregates: counts, token totals, check identifiers, per-case content hashes
- Synthetic fixtures and mock output (clearly labelled as mock)

### Private by default

- Raw teacher generations of any kind
- Candidate outputs pending human review
- Endpoint-identifying configuration: hosting account, endpoint hostname, resource group, region
- Reasoning traces, including `reasoning_content` and any derived summary of it
- Unreviewed generated datasets
- Credential material and credential paths

## What is in place now

| Control | Implementation |
| --- | --- |
| Raw generations kept out of the tree | `data/smoke/` holds aggregates only; raw rows live in `EQ2_EVIDENCE_DIR` |
| Integrity without disclosure | `data/smoke/PRIVATE_EVIDENCE.json` records filenames and SHA-256 |
| Scripts cannot silently write into the repo | `run_teacher_smoke.py` requires an explicit rows directory outside the repo; dry runs always use a temp directory |
| No embedded local paths | Scripts require `EQ2_EVIDENCE_DIR`; no default path is written down |
| Gitignore backstop | raw filenames, `data/raw/`, `data/private/` |
| Automated scanning | `tests/test_regressions.py` checks for absolute home paths, Azure resource identifiers, key-shaped literals, generated harmful text under `data/smoke/` |
| Infrastructure metadata removed | `AZURE_TEACHER_REPORT.md` records deployment name, type, model version, api-version only |

The scanning tests are the enforcement mechanism. They are cheap, they run offline, and they
fail the build rather than relying on a reviewer remembering the policy.

## History cleanup: what it would require

The raw files (`targets.jsonl`, `audit.jsonl`, `serialized_examples.jsonl`) were committed and
pushed in `59a0401`. Removing them from the current tree does not remove them from history.

To remove them from public history, one of:

1. **Rewrite the branch history** with `git filter-repo --path … --invert-paths`, then force-push.
   This rewrites `59a0401` and `0a1aa89`, invalidating their SHAs. Anyone who fetched them keeps
   their copies; any existing forks keep theirs.
2. **Delete the branch** and re-push a clean one. The old branch remains reachable via GitHub's
   network unless GitHub support garbage-collects it; forks and clones persist regardless.

Both require explicit human authorization, because both rewrite published history. Neither has
been done.

### What stays recoverable afterwards

- The local evidence directory retains all three files; `PRIVATE_EVIDENCE.json` hashes let you
  confirm they are the same ones the aggregates describe.
- The aggregates (`summary.json`, `revalidation.json`, `cases_at_run.json`) are unaffected and
  remain in the repository — they contain no prose.
- The 90 semantic cases are unaffected; they contain authored scenario text and no teacher output.
- If the branch is rewritten, the local clone still holds the original objects in its reflog until
  garbage collection; export them first if you want a private archive.

### What does not come back

Once rewritten and force-pushed, the original commit objects are not guaranteed to remain
fetchable, and third-party copies cannot be recalled. Treat "we can clean this up later" as
false for anything that has been pushed.

## Residual risk accepted in this pass

- The raw files remain in public history until a human decides on cleanup.
- The harmful S-condition text is in that history. It was produced by a model under an
  instruction that asked for a sycophantic reply to a punitive request. It is not evidence of
  harmful intent by any person, and it is documented in the disposition — but it is public.
- Deployment name (`gpt-oss-120b`) and api-version remain public. These are not secret and are
  needed for reproduction.

## Rule going forward

Nothing that contains generated prose, endpoint identifiers or reasoning goes into this
repository. If an artifact is needed for review, sanitize it to aggregates and hashes, or keep it
private and reference it by hash. The test suite enforces the mechanical half of this; the
judgement half is a human decision each time.
