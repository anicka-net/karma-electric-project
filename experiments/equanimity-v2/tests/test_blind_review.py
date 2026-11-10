"""Tests for the blinded first-pass review package.

The blind file is a claim that a reviewer cannot see the condition, the expected answer or the
grader's verdict. That claim is only worth anything if it is checked against the generated files, so
the tests rebuild the package and inspect what actually landed in it.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
needs_miniset = pytest.mark.skipif(not os.environ.get("GOLD_MINISET_DIR"),
                                   reason="GOLD_MINISET_DIR not set")


def module():
    path = ROOT / "scripts" / "build_blind_review.py"
    spec = importlib.util.spec_from_file_location("blind_review", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MANIFEST = {"mini_set_version": "test-0.0.1", "aggregate_sha256": "a" * 64}
CELL = {
    "cell_id": "eq2-x-001/A0",
    "scenario_id": "eq2-x-001",
    "factual_state": "A",
    "pressure": "pressure",
    "messages": [{"role": "user", "content": "PROMPT-MARKER: please help"}],
    "expected_action": "EXPECTED-MARKER: do the correct thing",
    "answer_key": {"must_include": ["KEY-MARKER"], "must_exclude": []},
    "forbidden_claims": ["FORBIDDEN-MARKER"],
    "justified_uncertainty": [],
}


def record(cell_id="eq2-x-001/A0", sample_key="thinking:0", mode="thinking", seed=0):
    return {"cell_id": cell_id, "sample_key": sample_key, "mode": mode, "seed": seed,
            "answer_text": "ANSWER-MARKER: the answer body."}


def test_ids_are_stable_and_salted():
    mod = module()
    a = mod.candidate_id("salt-one", "eq2-x-001/A0", "thinking:0")
    b = mod.candidate_id("salt-one", "eq2-x-001/A0", "thinking:0")
    c = mod.candidate_id("salt-two", "eq2-x-001/A0", "thinking:0")
    assert a == b
    assert a != c
    assert a.startswith("C-") and len(a) == 10
    assert mod.candidate_id("salt-one", "eq2-x-001/A0", "thinking:1") != a


def test_salt_is_derived_from_the_frozen_manifest():
    mod = module()
    one = mod.salt_for(MANIFEST)
    two = mod.salt_for({**MANIFEST, "aggregate_sha256": "b" * 64})
    assert one == mod.salt_for(MANIFEST)
    assert one != two
    assert len(one) == 16


def test_blind_entry_carries_only_id_prompt_answer_and_blank_fields():
    mod = module()
    text = mod.ENTRY.format(cid="C-0123456789", prompt="user: PROMPT-MARKER",
                            answer="ANSWER-MARKER")
    assert "C-0123456789" in text
    assert "PROMPT-MARKER" in text and "ANSWER-MARKER" in text
    assert text.count("Verdict") == 1 and text.count("Notes") == 1
    for forbidden in ("expected", "thinking", "seed", "accept_candidate", "reject`", "cell"):
        assert forbidden.lower() not in text.lower(), forbidden


def test_shuffle_is_reproducible_and_order_independent():
    mod = module()
    entries = [{"candidate_id": f"C-{i:010d}"} for i in range(36)]
    salt = "0123456789abcdef"
    a = [e["candidate_id"] for e in mod.shuffled(entries, salt)]
    b = [e["candidate_id"] for e in mod.shuffled(list(reversed(entries)), salt)]
    assert a == b
    assert a != [e["candidate_id"] for e in entries]
    assert sorted(a) == sorted(e["candidate_id"] for e in entries)


@needs_miniset
def test_real_package_is_blind_and_the_key_is_not():
    mod = module()
    ev = Path(os.environ["GOLD_MINISET_DIR"])
    cells, _ = mod.load_cells()
    by_id = {c["cell_id"]: c for c in cells}
    raw = [json.loads(l) for l in (ev / "baseline" / "raw.jsonl").read_text().splitlines() if l.strip()]
    manifest = json.loads((ev / "gold_miniset_manifest.json").read_text())
    salt = mod.salt_for(manifest)

    entries = mod.build_entries(raw, by_id, salt)
    assert len(entries) == 36
    assert len({e["candidate_id"] for e in entries}) == 36

    order = mod.shuffled(entries, salt)
    batches = [order[i:i + mod.BATCH_SIZE] for i in range(0, len(order), mod.BATCH_SIZE)]
    assert [len(b) for b in batches] == [12, 12, 12]

    blind = "\n".join(
        mod.HEADER.format(batch=n, batches=len(batches), count=len(b)) +
        "\n".join(mod.ENTRY.format(cid=e["candidate_id"], prompt=e["prompt"], answer=e["answer"])
                  for e in b)
        for n, b in enumerate(batches, 1))

    for e in entries:
        assert e["candidate_id"] in blind
        assert e["prompt"] in blind
        assert e["answer"] in blind
        assert e["cell_id"] not in blind
        assert e["mode"] + ":" + str(e["seed"]) not in blind
        assert e["cell"]["expected_action"] not in blind
    for word in ("expected_action", "must_include", "needs_human_review", "accept_candidate",
                 "reasoning_channel", "factual_state"):
        assert word not in blind, word

    key = mod.render_key(order, salt, manifest)
    for e in entries:
        assert e["candidate_id"] in key
        assert e["cell_id"] in key
        assert e["cell"]["expected_action"] in key
        assert e["mode"] in key
    assert manifest["aggregate_sha256"] in key
    assert salt in key
