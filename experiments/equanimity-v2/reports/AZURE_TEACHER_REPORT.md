# Azure GPT-OSS 120B teacher: verified behaviour

Scope: what the deployment actually does, measured, as of 2026-11-07. Every claim
below is tied to either a capability probe or a recorded call in
`data/smoke/audit.jsonl`. Things that were not verified are listed as such.

## Deployment

| Field | Value |
| --- | --- |
| Deployment name | `gpt-oss-120b` |
| Type | GlobalStandard |
| Model version | 1 |
| API version | `2024-12-01-preview` (200 on all calls) |
| Auth | `api-key` header |

The hosting account, region, resource group and endpoint hostname are **not**
recorded here. They are properties of a live paid endpoint and carry no review
value; they are recorded in local session notes instead. Nothing about the
generation behaviour below depends on knowing them.

This deployment is not the one referenced by `~/.azure_openai.json`. The existing
project judges (`voice_eval.py`, `voice_audit.py`) use a different deployment with
documented resource-level content filtering
(`docs/judge-filter-coverage-2026-10-29.md`). That deployment is not described
further here, and no behaviour in this report should be assumed to transfer to it.
No filtering behaviour was observed on the teacher deployment during the run; that
is absence of evidence, not evidence of absence.

## Capability matrix

| Capability | Status | Evidence |
| --- | --- | --- |
| Chat completion (`content`) | works | 18/18 calls returned non-empty content |
| Separate `reasoning_content` channel | works | present on 18/18 calls, 52-368 chars |
| `reasoning_effort` parameter | accepted | probe with `low`; also sent on all 18 smoke calls, none rejected |
| Strict `json_schema` `response_format` | accepted | probe returned `{"decision": "Prime", "confidence": 1.0}` |
| `max_completion_tokens` | works | 20-token probe returned empty content with `finish_reason=length` |
| Content filter | not exercised | no block observed; not probed deliberately |

## Measured quirks

These are the properties that forced design decisions in the adapter.

**1. `reasoning_tokens` is reported as 0 even when reasoning is present.**

Across 18 calls with `reasoning_effort=low`, `usage.completion_tokens_details`
reported `reasoning_tokens: 0` every time, while `reasoning_content` carried
52-368 characters of reasoning text. Consequences:

- Budget accounting based on `completion_tokens_details.reasoning_tokens`
  undercounts. `Budget.record()` therefore accumulates it but the enforced cap
  uses `prompt_tokens + completion_tokens`, which is what the response reports.
- Do not use `reasoning_tokens == 0` as evidence that the model did not reason.
  It did. The counter is simply not populated on this deployment.

**2. The reasoning channel exists at `reasoning_effort=low`.**

It is not suppressible by effort level in the range tested. Anything that reads
`message.content` gets the answer; anything that concatenates the whole message
dict gets reasoning mixed in. The adapter keeps `content` and `reasoning_text` as
separate attributes and `audit_record()` drops `reasoning_text`, recording only
`reasoning_present` and `reasoning_chars`. This is the mechanism that keeps
teacher reasoning out of any student target.

**3. Reasoning consumes the completion budget.**

A 20-token `max_completion_tokens` returned empty `content` with
`finish_reason=length`: the reasoning channel used the whole budget. Any generation
budget must be sized for reasoning plus answer, not for the answer alone. The smoke
run used 900 tokens per call and never hit `length` (18/18 `finish_reason=stop`).

**4. Latency at identical settings spans 0.6s to 19.5s.**

Fastest call 0.6s, slowest 19.5s (`eq2-f3-002-neutral`, condition G), with the same
`reasoning_effort` and `max_completion_tokens`. Latency is not a usable signal for
capacity, difficulty, or output quality on this deployment. Do not build a
timeout policy around observed percentiles from a run this small.

**5. Deployment name is not model id.**

Requests are routed by deployment. The response `model` field returned
`gpt-oss-120b` here, which happened to match, but the adapter records the
requested deployment, the response `model` field, and the api-version as separate
fields so a mismatch would be visible rather than assumed away.

## Budget and spend

| Item | Value |
| --- | --- |
| Smoke run calls | 18 of 18 planned |
| Prompt tokens | 16,703 |
| Completion tokens | 3,355 |
| Total tokens (smoke) | 20,058 of a 50,000 cap |
| Capability probes (separate, earlier) | ~5 calls, not counted in the 18 |
| Enforced request cap | `Budget(max_requests=18)`; every HTTP attempt counts, including retries and failures |

**Reservations are not a billing ceiling.** Each attempt reserves
`estimate_prompt_tokens(messages) + max_completion_tokens` before the request and settles the
reservation on response. `estimate_prompt_tokens` is a heuristic (4 tokens per message plus
chars/4), not a tokenizer, and deliberately over-reserves so the guard fails closed. If the
provider reports more than was reserved, `overruns` increments. Failed attempts release their
reservation but may still be billed; `failed_attempts` records that this is unmodelled.

**Cost is not asserted.** No pricing lookup was performed and no billing data was
read. The token counts above are from the API's own `usage` fields. If a euro
figure is needed, compute it from these counts against the current GlobalStandard
rate; do not assume this document implies one.

## Failure paths (unit-tested, not all observed live)

| Path | Behaviour | Test |
| --- | --- | --- |
| 401/403 | raises `AuthError`, message redacted | `test_auth_error_raises` |
| 404 `DeploymentNotFound` | raises `DeploymentNotFound` naming the deployment | `test_missing_deployment_raises_without_leaking_key` |
| 400 naming `response_format` | disables the capability, retries once without it, remembers | `test_schema_rejection_degrades_and_retries` |
| 400 naming `reasoning_effort` | same | `test_effort_rejection_degrades_and_retries` |
| 429 | honours `retry-after`, else exponential backoff with jitter | `test_rate_limit_then_success` |
| 5xx | retries up to `max_retries`, then returns a `GenerationResult` with `error` set | `test_server_error_exhausts_retries_and_returns_error_result` |
| `finish_reason=content_filter` | `result.ok` is False; content treated as unusable | `test_content_filter_is_not_ok` |
| Budget exhausted | raises before the request is sent | `test_budget_refuses_before_any_request_is_made` |

Only the happy path and the auth/deployment errors were exercised against the live
deployment in this run. The degradation paths are implemented and unit-tested but
have not been observed on this resource, because both `reasoning_effort` and
`response_format` were accepted.

## Credentials

The key is supplied through `EQ2_AZURE_API_KEY`, with a local file fallback whose
path is set by the operator and not recorded in this repository. It is not written
into any artifact, not logged, and redacted from error text by `redact()`. A
temporary file in `/tmp` is not persistent; treat the key as ephemeral and re-fetch
it from the control plane when needed. No credential is stored in this repository.
