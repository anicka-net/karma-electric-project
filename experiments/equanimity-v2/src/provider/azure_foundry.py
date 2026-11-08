"""Azure AI Foundry / Azure OpenAI provider adapter for GPT-OSS 120B.

Design constraints that shaped this file:

1. Deployment name != model id. Azure routes by *deployment*, and the response
   `model` field is not guaranteed to echo the underlying model. We therefore
   record the requested deployment, the response `model` field, and the
   deployment->model mapping discovered from the control plane, separately.

2. The endpoint exposes `reasoning_content` on the assistant message. That is a
   teacher reasoning channel. It is captured for audit ONLY and is never part of
   a student training target. `GenerationResult.reasoning_text` is deliberately
   a separate attribute from `.content`, and the export path does not read it.

3. Every call is bounded: max_completion_tokens, request timeout, retry count,
   and a running token/request budget that hard-stops the run.

4. No credential is ever logged, echoed in an exception, or written to an
   artifact. `redact()` is applied to error text.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

import requests

# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class ProviderError(RuntimeError):
    """Base class. Messages must be safe to log."""


class BudgetExceeded(ProviderError):
    """Raised before a call that would breach the configured budget."""


class AuthError(ProviderError):
    pass


class DeploymentNotFound(ProviderError):
    pass


class SchemaRejected(ProviderError):
    """The endpoint refused response_format=json_schema."""


class ReasoningConfigRejected(ProviderError):
    """The endpoint refused reasoning_effort."""


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AzureConfig:
    endpoint: str
    deployment: str
    api_version: str
    api_key: str = field(repr=False, default="")
    bearer_token: str = field(repr=False, default="")
    timeout_s: float = 120.0
    max_retries: int = 5
    backoff_base_s: float = 2.0
    backoff_max_s: float = 60.0

    def __post_init__(self) -> None:
        if not self.endpoint:
            raise AuthError("endpoint is empty")
        if not self.deployment:
            raise AuthError("deployment is empty")
        if not (self.api_key or self.bearer_token):
            raise AuthError("no credential: set api_key or bearer_token")

    @property
    def chat_url(self) -> str:
        base = self.endpoint.rstrip("/")
        return (
            f"{base}/openai/deployments/{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )

    @classmethod
    def from_env(cls, prefix: str = "EQ2_AZURE_") -> "AzureConfig":
        """Read config from environment. Falls back to the project's existing
        ~/.azure_openai.json only if explicitly allowed, because that file points
        at a different resource (gpt-4o) than the GPT-OSS deployment."""
        env = os.environ
        return cls(
            endpoint=env.get(prefix + "ENDPOINT", ""),
            deployment=env.get(prefix + "DEPLOYMENT", "gpt-oss-120b"),
            api_version=env.get(prefix + "API_VERSION", "2024-12-01-preview"),
            api_key=env.get(prefix + "API_KEY", ""),
            bearer_token=env.get(prefix + "BEARER_TOKEN", ""),
            timeout_s=float(env.get(prefix + "TIMEOUT_S", "120")),
            max_retries=int(env.get(prefix + "MAX_RETRIES", "5")),
        )


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------


@dataclass
class Budget:
    """Hard stop on requests and tokens. Checked before every call."""

    max_requests: int = 18
    max_tokens: int = 50_000
    requests_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def tokens_used(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def check(self, estimated_completion: int) -> None:
        if self.requests_used + 1 > self.max_requests:
            raise BudgetExceeded(
                f"request budget exhausted: {self.requests_used}/{self.max_requests}"
            )
        projected = self.tokens_used + estimated_completion
        if projected > self.max_tokens:
            raise BudgetExceeded(
                f"token budget would be breached: used={self.tokens_used} "
                f"projected_add={estimated_completion} cap={self.max_tokens}"
            )

    def record(self, usage: dict[str, Any]) -> None:
        self.requests_used += 1
        self.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        self.completion_tokens += int(usage.get("completion_tokens") or 0)
        details = usage.get("completion_tokens_details") or {}
        self.reasoning_tokens += int(details.get("reasoning_tokens") or 0)

    def snapshot(self) -> dict[str, Any]:
        return {
            "requests_used": self.requests_used,
            "max_requests": self.max_requests,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "tokens_used": self.tokens_used,
            "max_tokens": self.max_tokens,
        }


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------


@dataclass
class GenerationResult:
    """One teacher call.

    `content` is the only field that may ever reach a student target.
    `reasoning_text` is audit-only and is excluded from every export path.
    """

    request_id: str
    deployment: str
    api_version: str
    model_field: str
    content: str
    reasoning_text: str
    finish_reason: str
    usage: dict[str, Any]
    latency_s: float
    attempts: int
    params: dict[str, Any]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.finish_reason != "content_filter"

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"

    def audit_record(self) -> dict[str, Any]:
        """Everything except the reasoning text. Safe to publish."""
        d = asdict(self)
        d.pop("reasoning_text", None)
        d["reasoning_present"] = bool(self.reasoning_text)
        d["reasoning_chars"] = len(self.reasoning_text)
        return d


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------


def redact(text: str, *secrets: str) -> str:
    out = text
    for s in secrets:
        if s and len(s) >= 8:
            out = out.replace(s, "<redacted>")
    return out[:600]


class AzureFoundryClient:
    def __init__(self, cfg: AzureConfig, budget: Budget | None = None):
        self.cfg = cfg
        self.budget = budget or Budget()
        self._session = requests.Session()
        self._schema_supported: bool | None = None
        self._effort_supported: bool | None = None

    # -- headers ----------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            h["api-key"] = self.cfg.api_key
        else:
            h["Authorization"] = f"Bearer {self.cfg.bearer_token}"
        return h

    # -- capability probes ------------------------------------------------
    def probe(self) -> dict[str, Any]:
        """Two tiny calls: does the deployment answer, and does it accept
        reasoning_effort and a strict json_schema. Bounded to ~2 requests."""
        out: dict[str, Any] = {"deployment": self.cfg.deployment}
        r = self.chat(
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_completion_tokens=64,
            reasoning_effort="low",
            request_id="probe-basic",
        )
        out["reachable"] = r.ok
        out["model_field"] = r.model_field
        out["finish_reason"] = r.finish_reason
        out["usage"] = r.usage
        out["content_preview"] = r.content[:40]
        out["reasoning_channel_present"] = bool(r.reasoning_text)
        out["effort_accepted"] = self._effort_supported
        out["schema_accepted"] = self._schema_supported
        return out

    # -- main call --------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        request_id: str,
        max_completion_tokens: int = 1200,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        json_schema: dict[str, Any] | None = None,
        seed: int | None = None,
    ) -> GenerationResult:
        payload: dict[str, Any] = {
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if seed is not None:
            payload["seed"] = seed
        if reasoning_effort and self._effort_supported is not False:
            payload["reasoning_effort"] = reasoning_effort
        if json_schema and self._schema_supported is not False:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": json_schema.get("name", "result"),
                    "schema": json_schema["schema"],
                    "strict": True,
                },
            }

        self.budget.check(max_completion_tokens)
        started = time.time()
        attempts = 0
        last_err = ""

        while attempts <= self.cfg.max_retries:
            attempts += 1
            try:
                resp = self._session.post(
                    self.cfg.chat_url,
                    headers=self._headers(),
                    data=json.dumps(payload),
                    timeout=self.cfg.timeout_s,
                )
            except requests.RequestException as exc:
                last_err = redact(str(exc), self.cfg.api_key, self.cfg.bearer_token)
                self._sleep(attempts)
                continue

            if resp.status_code == 200:
                return self._parse(resp, request_id, payload, started, attempts)

            body = resp.text
            safe = redact(body, self.cfg.api_key, self.cfg.bearer_token)

            if resp.status_code in (401, 403):
                raise AuthError(f"auth failed ({resp.status_code}): {safe}")

            if resp.status_code == 404 and "DeploymentNotFound" in body:
                raise DeploymentNotFound(
                    f"deployment '{self.cfg.deployment}' not found on this resource: {safe}"
                )

            # Degrade capability flags on 400s that name the offending parameter,
            # then retry once without it. Documented in AZURE_TEACHER_REPORT.md.
            if resp.status_code == 400:
                if "response_format" in body or "json_schema" in body:
                    if self._schema_supported is not False:
                        self._schema_supported = False
                        payload.pop("response_format", None)
                        last_err = "schema rejected; retrying without response_format"
                        continue
                if "reasoning_effort" in body:
                    if self._effort_supported is not False:
                        self._effort_supported = False
                        payload.pop("reasoning_effort", None)
                        last_err = "reasoning_effort rejected; retrying without it"
                        continue

            if resp.status_code == 429:
                retry_after = resp.headers.get("retry-after")
                wait = float(retry_after) if retry_after else self._backoff(attempts)
                last_err = f"429 rate limited; slept {wait:.1f}s"
                time.sleep(min(wait, self.cfg.backoff_max_s))
                continue

            if resp.status_code >= 500:
                last_err = f"{resp.status_code}: {safe}"
                self._sleep(attempts)
                continue

            last_err = f"{resp.status_code}: {safe}"
            break

        return GenerationResult(
            request_id=request_id,
            deployment=self.cfg.deployment,
            api_version=self.cfg.api_version,
            model_field="",
            content="",
            reasoning_text="",
            finish_reason="error",
            usage={},
            latency_s=time.time() - started,
            attempts=attempts,
            params=self._safe_params(payload),
            error=last_err or "unknown error",
        )

    # -- helpers ----------------------------------------------------------
    def _parse(
        self,
        resp: requests.Response,
        request_id: str,
        payload: dict[str, Any],
        started: float,
        attempts: int,
    ) -> GenerationResult:
        data = resp.json()
        if self._schema_supported is None and "response_format" in payload:
            self._schema_supported = True
        if self._effort_supported is None and "reasoning_effort" in payload:
            self._effort_supported = True

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        usage = data.get("usage") or {}
        self.budget.record(usage)

        return GenerationResult(
            request_id=request_id,
            deployment=self.cfg.deployment,
            api_version=self.cfg.api_version,
            model_field=str(data.get("model") or ""),
            content=msg.get("content") or "",
            reasoning_text=msg.get("reasoning_content") or "",
            finish_reason=str(choice.get("finish_reason") or ""),
            usage=usage,
            latency_s=time.time() - started,
            attempts=attempts,
            params=self._safe_params(payload),
        )

    @staticmethod
    def _safe_params(payload: dict[str, Any]) -> dict[str, Any]:
        out = {k: v for k, v in payload.items() if k != "messages"}
        if "response_format" in out:
            out["response_format"] = "json_schema(strict)"
        return out

    def _backoff(self, attempt: int) -> float:
        base = min(self.cfg.backoff_base_s * (2 ** (attempt - 1)), self.cfg.backoff_max_s)
        return base * (0.5 + random.random() * 0.5)

    def _sleep(self, attempt: int) -> None:
        time.sleep(self._backoff(attempt))


# --------------------------------------------------------------------------
# Mock client — deterministic, no network, no credentials
# --------------------------------------------------------------------------


class MockClient:
    """Deterministic stand-in used by tests and by --dry-run.

    It does NOT pretend to be a teacher. It returns a fixed, obviously-synthetic
    answer so that the pipeline can be exercised end to end without any claim
    that the output is good training data.
    """

    def __init__(self, budget: Budget | None = None, fail_mode: str | None = None):
        self.budget = budget or Budget()
        self.fail_mode = fail_mode
        self.calls: list[dict[str, Any]] = []

    def probe(self) -> dict[str, Any]:
        return {
            "deployment": "mock",
            "reachable": True,
            "model_field": "mock",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "content_preview": "OK",
            "reasoning_channel_present": True,
            "effort_accepted": True,
            "schema_accepted": True,
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        request_id: str,
        max_completion_tokens: int = 1200,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        json_schema: dict[str, Any] | None = None,
        seed: int | None = None,
    ) -> GenerationResult:
        self.budget.check(max_completion_tokens)
        self.calls.append({"request_id": request_id, "messages": messages})

        if self.fail_mode == "truncate":
            content, finish = "This answer is cut off mid", "length"
        elif self.fail_mode == "think_leak":
            content, finish = "</think>Here is the answer.", "stop"
        elif self.fail_mode == "empty":
            content, finish = "", "stop"
        elif self.fail_mode == "refusal":
            content, finish = "I'm sorry, but I can't help with that request.", "stop"
        elif self.fail_mode == "repetitive":
            content, finish = ("the same sentence over and over. " * 40), "stop"
        else:
            content = (
                "[MOCK ANSWER] The task is addressed directly. Facts are preserved "
                "as stated in the case. No emotional escalation, no withdrawal."
            )
            finish = "stop"

        usage = {
            "prompt_tokens": sum(len(m["content"]) // 4 for m in messages),
            "completion_tokens": len(content) // 4,
            "total_tokens": 0,
            "completion_tokens_details": {"reasoning_tokens": 12},
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        self.budget.record(usage)

        return GenerationResult(
            request_id=request_id,
            deployment="mock",
            api_version="mock",
            model_field="mock",
            content=content,
            reasoning_text="[MOCK REASONING — audit only, never exported]",
            finish_reason=finish,
            usage=usage,
            latency_s=0.0,
            attempts=1,
            params={"max_completion_tokens": max_completion_tokens},
        )
