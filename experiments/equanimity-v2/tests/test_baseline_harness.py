"""Tests for the bounded baseline harness.

The harness is small but the failure modes are not: an unclosed reasoning channel must not be
reported as an answer, the job plan must be exactly 36 generations with distinct seeds, and a rerun
must not regenerate what is already recorded.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def harness():
    path = ROOT / "scripts" / "run_baseline.py"
    spec = importlib.util.spec_from_file_location("baseline_harness", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OPEN = "<" + "think" + ">"
CLOSE = "<" + "/" + "think" + ">"


def test_unclosed_channel_yields_no_answer():
    mod = harness()
    reasoning, answer, closed = mod.split_channels(OPEN + "still thinking about it")
    assert closed is False
    assert reasoning == "still thinking about it"
    assert answer == "", "reasoning text must not be reported as an answer"


def test_closed_channel_splits_reasoning_from_answer():
    mod = harness()
    reasoning, answer, closed = mod.split_channels(OPEN + "\nbecause 512 < 700\n" + CLOSE + "\n\nRaise the limit.")
    assert closed is True
    assert reasoning.startswith("because")
    assert answer == "Raise the limit."


def test_no_channel_is_all_answer():
    mod = harness()
    reasoning, answer, closed = mod.split_channels("Raise the limit to 1Gi.")
    assert (reasoning, answer, closed) == ("", "Raise the limit to 1Gi.", True)


def test_job_plan_is_exactly_thirty_six_with_two_thinking_samples():
    mod = harness()
    cells = [{"cell_id": f"c{i}", "messages": [{"role": "user", "content": "q"}]} for i in range(12)]
    jobs = mod.plan(cells)
    assert len(jobs) == 36
    keys = [(j["cell_id"], j["sample_key"]) for j in jobs]
    assert len(set(keys)) == 36
    per_cell = {}
    for j in jobs:
        per_cell.setdefault(j["cell_id"], []).append(j["sample_key"])
    for cid, ks in per_cell.items():
        assert sorted(ks) == ["no_thinking:0", "thinking:0", "thinking:1"], cid


def test_thinking_samples_have_distinct_seeds():
    mod = harness()
    cells = [{"cell_id": "c", "messages": []}]
    jobs = mod.plan(cells)
    seeds = [j["seed"] for j in jobs]
    assert len(set(seeds)) == 3


def test_resume_skips_recorded_generations(tmp_path):
    mod = harness()
    raw = tmp_path / "raw.jsonl"
    raw.write_text(json.dumps({"cell_id": "a", "sample_key": "thinking:0"}) + "\n")
    assert mod.load_done(raw) == {("a", "thinking:0")}


def test_dry_run_requires_a_private_directory(monkeypatch, tmp_path):
    mod = harness()
    monkeypatch.delenv("GOLD_MINISET_DIR", raising=False)
    monkeypatch.delenv("EQ2_EVIDENCE_DIR", raising=False)
    with pytest.raises(SystemExit):
        mod.private_dir()


def test_sampling_config_is_explicit():
    mod = harness()
    for key in ("temperature", "top_p", "top_k", "max_new_tokens"):
        assert key in mod.SAMPLING
    assert mod.SAMPLING["temperature"] > 0
