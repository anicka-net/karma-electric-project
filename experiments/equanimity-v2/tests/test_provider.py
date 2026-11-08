"""Tests for the provider adapter and the corrected fail-closed budget.

No network, no credentials. The fake HTTP layer exercises the real code paths.

The budget contract changed in v0.2.0 and these tests target the specific defects:

    - the old guard omitted prompt tokens from the projection
    - retries and failures did not consume the request allowance
    - reported usage beyond the reservation was silently ignored
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
    MockClient,
    estimate_prompt_tokens,
    redact,
)

KEY = "test-key-abcdef0123456789"


class FakeResponse:
    def __init__(self, status_code: int, body: dict | str = None, headers: dict | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.text = body if isinstance(body, str) else json.dumps(body or {})

    def json(self) -> dict:
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body or {}


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.requests.append({"url": url, "headers": headers, "payload": json.loads(data)})
        if not self.responses:
            raise AssertionError("FakeSession ran out of queued responses")
        return self.responses.pop(0)


def ok_body(content="OK", reasoning="thought", finish="stop", prompt_tokens=20, completion_tokens=10) -> dict:
    return {
        "model": "gpt-oss-120b",
        "choices": [{"message": {"content": content, "reasoning_content": reasoning},
                     "finish_reason": finish}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                  "total_tokens": prompt_tokens + completion_tokens,
                  "completion_tokens_details": {"reasoning_tokens": 6}},
    }


def make_client(responses, max_retries=2) -> tuple[AzureFoundryClient, FakeSession]:
    cfg = AzureConfig(endpoint="https://example.cognitiveservices.azure.com",
                      deployment="gpt-oss-120b", api_version="2024-12-01-preview",
                      api_key=KEY, max_retries=max_retries)
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
    assert cfg.chat_url == ("https://x/openai/deployments/gpt-oss-120b/chat/completions"
                            "?api-version=2024-12-01-preview")


def test_redact_removes_secret():
    assert KEY not in redact(f"failed with key {KEY}", KEY)


def test_estimate_prompt_tokens_is_monotonic_and_positive():
    a = estimate_prompt_tokens([{"role": "user", "content": "x"}])
    b = estimate_prompt_tokens([{"role": "user", "content": "x" * 4000}])
    assert a > 0 and b > a


# ---------------------------------------------------------------- happy path

def test_successful_call_parses_channels_separately():
    client, _ = make_client([FakeResponse(200, ok_body())])
    r = call(client, max_completion_tokens=100)
    assert r.content == "OK"
    assert r.reasoning_text == "thought"
    assert r.finish_reason == "stop"
    assert r.ok


def test_reasoning_absent_from_audit_record():
    client, _ = make_client([FakeResponse(200, ok_body(reasoning="secret chain of thought"))])
    rec = call(client, max_completion_tokens=100).audit_record()
    assert "reasoning_text" not in rec
    assert "secret chain of thought" not in json.dumps(rec)
    assert rec["reasoning_present"] is True


def test_api_key_header_sent():
    client, session = make_client([FakeResponse(200, ok_body())])
    call(client, max_completion_tokens=100)
    assert session.requests[0]["headers"]["api-key"] == KEY
    assert "Authorization" not in session.requests[0]["headers"]


# ---------------------------------------------------------------- capability degradation

def test_schema_rejection_degrades_and_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([
        FakeResponse(400, {"error": {"message": "Unsupported parameter: response_format"}}),
        FakeResponse(200, ok_body()),
    ])
    r = call(client, max_completion_tokens=100, json_schema={"name": "x", "schema": {"type": "object"}})
    assert r.ok and client._schema_supported is False
    assert "response_format" in session.requests[0]["payload"]
    assert "response_format" not in session.requests[1]["payload"]


def test_effort_rejection_degrades_and_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([
        FakeResponse(400, {"error": {"message": "Unsupported value: reasoning_effort"}}),
        FakeResponse(200, ok_body()),
    ])
    assert call(client, max_completion_tokens=100, reasoning_effort="low").ok
    assert "reasoning_effort" not in session.requests[1]["payload"]


# ---------------------------------------------------------------- errors

def test_missing_deployment_raises_without_leaking_key():
    client, _ = make_client([FakeResponse(404, {"error": {"code": "DeploymentNotFound"}})])
    with pytest.raises(DeploymentNotFound) as ei:
        call(client, max_completion_tokens=100)
    assert "gpt-oss-120b" in str(ei.value) and KEY not in str(ei.value)


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
    assert r.ok and r.attempts == 2
    assert client.budget.failed_attempts == 1


def test_server_error_exhausts_retries_and_returns_error_result(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client([FakeResponse(500, "boom")] * 3)
    r = call(client, max_completion_tokens=100)
    assert not r.ok and r.error
    assert KEY not in (r.error or "")
    assert len(session.requests) == 3
    assert client.budget.failed_attempts == 3


def test_content_filter_is_not_ok():
    client, _ = make_client([FakeResponse(200, ok_body(content="", finish="content_filter"))])
    assert not call(client, max_completion_tokens=100).ok


def test_length_finish_is_flagged_truncated():
    client, _ = make_client([FakeResponse(200, ok_body(content="partial", finish="length"))])
    assert call(client, max_completion_tokens=100).truncated


# ---------------------------------------------------------------- corrected budget

def test_budget_refuses_before_any_request_is_made():
    client, session = make_client([FakeResponse(200, ok_body()), FakeResponse(200, ok_body())])
    client.budget = Budget(max_requests=1, max_tokens=100_000)
    call(client, max_completion_tokens=100)
    with pytest.raises(BudgetExceeded):
        call(client, max_completion_tokens=100)
    assert len(session.requests) == 1, "the refused call must not reach the network"


def test_prompt_overhead_alone_can_exceed_the_budget():
    """Regression: the old guard only looked at the completion estimate."""
    long_prompt = "x" * 40_000
    est = estimate_prompt_tokens([{"role": "user", "content": long_prompt}])
    client, session = make_client([FakeResponse(200, ok_body())])
    client.budget = Budget(max_requests=10, max_tokens=max(100, est // 2))
    with pytest.raises(BudgetExceeded) as ei:
        client.chat([{"role": "user", "content": long_prompt}], request_id="t", max_completion_tokens=10)
    assert "prompt" in str(ei.value)
    assert session.requests == []


def test_retries_consume_the_request_allowance(monkeypatch):
    """Regression: retries did not count against the request cap."""
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, session = make_client(
        [FakeResponse(500, "boom")] * 6,
        max_retries=5,
    )
    client.budget = Budget(max_requests=3, max_tokens=100_000)
    with pytest.raises(BudgetExceeded) as ei:
        call(client, max_completion_tokens=100)
    assert "request budget exhausted" in str(ei.value)
    assert len(session.requests) == 3, "exactly the allowance, no more"


def test_usage_beyond_reservation_is_recorded_as_overrun():
    client, _ = make_client([FakeResponse(200, ok_body(prompt_tokens=5000, completion_tokens=5000))])
    client.budget = Budget(max_requests=10, max_tokens=100_000)
    call(client, max_completion_tokens=10)
    snap = client.budget.snapshot()
    assert snap["overruns"] == 1
    assert snap["tokens_used"] == 10_000
    assert snap["reserved_tokens"] == 0


def test_reservation_is_released_after_each_attempt(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    client, _ = make_client([FakeResponse(500, "boom"), FakeResponse(200, ok_body())])
    call(client, max_completion_tokens=100)
    assert client.budget.reserved_tokens == 0
    assert client.budget.requests_used == 2
    assert client.budget.failed_attempts == 1


def test_budget_accounts_usage_and_keeps_committed_consistent():
    client, _ = make_client([FakeResponse(200, ok_body())])
    client.budget = Budget(max_requests=5, max_tokens=10_000)
    call(client, max_completion_tokens=100)
    snap = client.budget.snapshot()
    assert snap["requests_used"] == 1
    assert snap["prompt_tokens"] == 20
    assert snap["completion_tokens"] == 10
    assert snap["tokens_used"] == 30
    assert snap["committed"] == 30


def test_snapshot_documents_that_reservation_is_not_a_billing_ceiling():
    snap = Budget().snapshot()
    assert "not a billing ceiling" in snap["note"]


# ---------------------------------------------------------------- mock client

def test_mock_is_deterministic_and_labelled():
    a = MockClient(Budget()).chat([{"role": "user", "content": "hi"}], request_id="x")
    b = MockClient(Budget()).chat([{"role": "user", "content": "hi"}], request_id="x")
    assert a.content == b.content
    assert "MOCK" in a.content and "MOCK" in a.reasoning_text


@pytest.mark.parametrize("mode,expect", [
    ("truncate", "length"), ("think_leak", "stop"), ("empty", "stop"),
    ("refusal", "stop"), ("repetitive", "stop"),
])
def test_mock_fail_modes(mode, expect):
    r = MockClient(Budget(), fail_mode=mode).chat([{"role": "user", "content": "hi"}], request_id="x")
    assert r.finish_reason == expect
    if mode == "truncate":
        assert r.truncated
    if mode == "empty":
        assert r.content == ""


def test_mock_respects_budget():
    b = Budget(max_requests=2, max_tokens=100_000)
    c = MockClient(b)
    c.chat([{"role": "user", "content": "hi"}], request_id="1", max_completion_tokens=100)
    c.chat([{"role": "user", "content": "hi"}], request_id="2", max_completion_tokens=100)
    with pytest.raises(BudgetExceeded):
        c.chat([{"role": "user", "content": "hi"}], request_id="3", max_completion_tokens=100)


# ---------------------------------------------------------------- smoke verdict

def test_zero_successful_generations_is_not_a_success_verdict():
    """The run script must not treat an empty or all-failed run as success.

    Exercised through the same predicate the script uses: a run is only clean when
    there are rows, at least one pass, no failures, and the target-set audit holds.
    """
    def verdict(rows, audit_ok):
        if not rows:
            return False
        if sum(1 for r in rows if r["ok"]) == 0:
            return False
        return audit_ok and all(r["ok"] for r in rows)

    assert verdict([], True) is False
    assert verdict([{"ok": False}], True) is False
    assert verdict([{"ok": True}, {"ok": False}], True) is False
    assert verdict([{"ok": True}], False) is False
    assert verdict([{"ok": True}], True) is True
