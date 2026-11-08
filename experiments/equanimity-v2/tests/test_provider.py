"""Tests for the Azure provider adapter.

No network, no credentials. The fake HTTP layer exercises the real code paths:
capability degradation on 400, auth failure, missing deployment, rate-limit
retry, and the budget guard that must stop a run before it spends anything.

The single most important assertion here is that teacher reasoning never
reaches an artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from provider.azure_foundry import (  # noqa: E402
    AuthError,
    AzureConfig,
    AzureFoundryClient,
    Budget,
    BudgetExceeded,
    DeploymentNotFound,
    GenerationResult,
    MockClient,
    redact,
)

KEY = "test-key-abcdef0123456789"


class FakeResponse:
    def __init__(self, status_code: int, body: dict | str = None, headers: dict | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        if isinstance(body, str):
            self.text = body
        else:
            self.text = json.dumps(body or {})

    def json(self) -> dict:
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body or {}


class FakeSession:
    """Replays a queued list of responses and records the requests made."""

    def __init__(self, responses: list[FakeResponse]):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.requests.append({"url": url, "headers": headers, "payload": json.loads(data)})
        if not self.responses:
            raise AssertionError("FakeSession ran out of queued responses")
        return self.responses.pop(0)


def ok_body(content="OK", reasoning="thought", finish="stop") -> dict:
    return {
        "model": "gpt-oss-120b",
        "choices": [{
            "message": {"content": content, "reasoning_content": reasoning},
            "finish_reason": finish,
        }],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
            "completion_tokens_details": {"reasoning_tokens": 6},
        },
    }


def make_client(responses, **cfg_kwargs) -> tuple[AzureFoundryClient, FakeSession]:
    cfg = AzureConfig(
        endpoint="https://example.cognitiveservices.azure.com",
        deployment="gpt-oss-120b",
        api_version="2024-12-01-preview",
        api_key=KEY,
        max_retries=2,
        **cfg_kwargs,
    )
    client = AzureFoundryClient(cfg)
    session = FakeSession(responses)
    client._session = session
    return client, session


def call(client, **kw):
    return client.chat([{"role": "user", "content": "hello there"}], request_id="t", **kw)


# ---------------------------------------------------------------- config

def test_config_requires_a_credential():
    with pytest.raises(AuthError):
        AzureConfig(endpoint="https://x", deployment="d", api_version="v")


def test_config_repr_hides_the_key():
    cfg = AzureConfig(endpoint="https://x", deployment="d", api_version="v", api_key=KEY)
    assert KEY not in repr(cfg)


def test_chat_url_shape():
    cfg = AzureConfig(endpoint="https://x/", deployment="gpt-oss-120b",
                      api_version="2024-12-01-preview", api_key=KEY)
    assert cfg.chat_url == (
        "https://x/openai/deployments/gpt-oss-120b/chat/completions"
        "?api-version=2024-12-01-preview"
    )


def test_from_env_reads_prefixed_vars(monkeypatch):
    monkeypatch.setenv("EQ2_AZURE_ENDPOINT", "https://e")
    monkeypatch.setenv("EQ2_AZURE_API_KEY", KEY)
    cfg = AzureConfig.from_env()
    assert cfg.endpoint == "https://e"
    assert cfg.deployment == "gpt-oss-120b"


def test_redact_removes_secret():
    assert KEY not in redact(f"failed with key {KEY}", KEY)


# ---------------------------------------------------------------- happy path

def test_successful_call_parses_channels_separately():
    client, _ = make_client([FakeResponse(200, ok_body())])
    r = call(client, max_completion_tokens=100)
    assert r.content == "OK"
    assert r.reasoning_text == "thought"
    assert r.model_field == "gpt-oss-120b"
    assert r.finish_reason == "stop"
    assert r.ok


def test_reasoning_is_absent_from_audit_record():
    client, _ = make_client([FakeResponse(200, ok_body(reasoning="secret chain of thought"))])
    r = call(client, max_completion_tokens=100)
    rec = r.audit_record()
    assert "reasoning_text" not in rec
    assert "secret chain of thought" not in json.dumps(rec)
    assert rec["reasoning_present"] is True
    assert rec["reasoning_chars"] == len("secret chain of thought")


def test_api_key_header_is_sent_not_the_bearer():
    client, session = make_client([FakeResponse(200, ok_body())])
    call(client, max_completion_tokens=100)
    h = session.requests[0]["headers"]
    assert h["api-key"] == KEY
    assert "Authorization" not in h


# ---------------------------------------------------------------- capability degradation

def test_schema_rejection_degrades_and_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([
        FakeResponse(400, {"error": {"message": "Unsupported parameter: response_format"}}),
        FakeResponse(200, ok_body()),
    ])
    r = call(client, max_completion_tokens=100,
             json_schema={"name": "x", "schema": {"type": "object"}})
    assert r.ok
    assert client._schema_supported is False
    assert "response_format" in session.requests[0]["payload"]
    assert "response_format" not in session.requests[1]["payload"]


def test_effort_rejection_degrades_and_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([
        FakeResponse(400, {"error": {"message": "Unsupported value: reasoning_effort"}}),
        FakeResponse(200, ok_body()),
    ])
    r = call(client, max_completion_tokens=100, reasoning_effort="low")
    assert r.ok
    assert client._effort_supported is False
    assert "reasoning_effort" not in session.requests[1]["payload"]


def test_degraded_capability_is_not_retried_on_later_calls(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([
        FakeResponse(400, {"error": {"message": "Unsupported parameter: reasoning_effort"}}),
        FakeResponse(200, ok_body()),
        FakeResponse(200, ok_body()),
    ])
    call(client, max_completion_tokens=100, reasoning_effort="low")
    call(client, max_completion_tokens=100, reasoning_effort="low")
    assert "reasoning_effort" not in session.requests[2]["payload"]


# ---------------------------------------------------------------- errors

def test_missing_deployment_raises_without_leaking_key():
    client, _ = make_client([FakeResponse(404, {"error": {"code": "DeploymentNotFound"}})])
    with pytest.raises(DeploymentNotFound) as ei:
        call(client, max_completion_tokens=100)
    assert "gpt-oss-120b" in str(ei.value)
    assert KEY not in str(ei.value)


def test_auth_error_raises():
    client, _ = make_client([FakeResponse(401, {"error": {"message": "bad key"}})])
    with pytest.raises(AuthError) as ei:
        call(client, max_completion_tokens=100)
    assert KEY not in str(ei.value)


def test_rate_limit_then_success(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([
        FakeResponse(429, {"error": {"message": "slow down"}}, headers={"retry-after": "0"}),
        FakeResponse(200, ok_body()),
    ])
    r = call(client, max_completion_tokens=100)
    assert r.ok
    assert len(session.requests) == 2
    assert r.attempts == 2


def test_server_error_exhausts_retries_and_returns_error_result(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([FakeResponse(500, "boom"), FakeResponse(500, "boom"), FakeResponse(500, "boom")])
    r = call(client, max_completion_tokens=100)
    assert not r.ok
    assert r.error
    assert KEY not in (r.error or "")
    assert len(session.requests) == 3


def test_content_filter_is_not_ok():
    client, _ = make_client([FakeResponse(200, ok_body(content="", finish="content_filter"))])
    r = call(client, max_completion_tokens=100)
    assert not r.ok


def test_length_finish_is_flagged_truncated():
    client, _ = make_client([FakeResponse(200, ok_body(content="partial", finish="length"))])
    r = call(client, max_completion_tokens=100)
    assert r.truncated


# ---------------------------------------------------------------- budget

def test_budget_refuses_before_any_request_is_made():
    budget = Budget(max_requests=1, max_tokens=10_000)
    client, session = make_client([FakeResponse(200, ok_body())])
    client.budget = budget
    call(client, max_completion_tokens=100)
    with pytest.raises(BudgetExceeded):
        call(client, max_completion_tokens=100)
    assert len(session.requests) == 1, "the refused call must not reach the network"


def test_budget_refuses_when_token_cap_would_be_breached():
    budget = Budget(max_requests=10, max_tokens=100)
    client, session = make_client([FakeResponse(200, ok_body())])
    client.budget = budget
    with pytest.raises(BudgetExceeded):
        call(client, max_completion_tokens=5000)
    assert session.requests == []


def test_budget_accounts_usage_and_reasoning_tokens():
    budget = Budget(max_requests=5, max_tokens=10_000)
    client, _ = make_client([FakeResponse(200, ok_body())])
    client.budget = budget
    call(client, max_completion_tokens=100)
    snap = budget.snapshot()
    assert snap["requests_used"] == 1
    assert snap["prompt_tokens"] == 20
    assert snap["completion_tokens"] == 10
    assert snap["reasoning_tokens"] == 6
    assert snap["tokens_used"] == 30


# ---------------------------------------------------------------- mock client

def test_mock_is_deterministic():
    a = MockClient(Budget()).chat([{"role": "user", "content": "hi"}], request_id="x").content
    b = MockClient(Budget()).chat([{"role": "user", "content": "hi"}], request_id="x").content
    assert a == b
    assert a.startswith("[MOCK ANSWER]")


def test_mock_never_pretends_to_be_a_teacher():
    r = MockClient(Budget()).chat([{"role": "user", "content": "hi"}], request_id="x")
    assert "MOCK" in r.content
    assert "MOCK" in r.reasoning_text


@pytest.mark.parametrize("mode,expect", [
    ("truncate", "length"),
    ("think_leak", "stop"),
    ("empty", "stop"),
    ("refusal", "stop"),
    ("repetitive", "stop"),
])
def test_mock_fail_modes(mode, expect):
    r = MockClient(Budget(), fail_mode=mode).chat(
        [{"role": "user", "content": "hi"}], request_id="x"
    )
    assert r.finish_reason == expect
    if mode == "truncate":
        assert r.truncated
    if mode == "refusal":
        assert "can't help" in r.content
    if mode == "empty":
        assert r.content == ""


def test_mock_respects_budget():
    b = Budget(max_requests=2, max_tokens=10_000)
    c = MockClient(b)
    c.chat([{"role": "user", "content": "hi"}], request_id="1")
    c.chat([{"role": "user", "content": "hi"}], request_id="2")
    with pytest.raises(BudgetExceeded):
        c.chat([{"role": "user", "content": "hi"}], request_id="3")
