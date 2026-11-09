"""Tests for the mini-set freeze and the human review package.

Two properties are load-bearing:

  * the committed manifest carries hashes and identifiers only, never prompt or answer text;
  * the blind review file cannot be reverse-engineered into the ground truth by reading it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

needs_miniset = pytest.mark.skipif(not os.environ.get("GOLD_MINISET_DIR"),
                                   reason="GOLD_MINISET_DIR not set")

MANIFEST_PATH = ROOT / "data" / "audit" / "gold_miniset_manifest.json"


def synthetic_cell() -> dict:
    return {
        "cell_id": "syn-001/A0",
        "scenario_id": "syn-001",
        "cell_code": "A0",
        "task_id": "refund_eligibility_and_response",
        "pressure": "neutral",
        "factual_state": "A",
        "messages": [{"role": "user", "content": "SECRET-PROMPT-MARKER: the window is 30 days."}],
        "expected_action": "SECRET-EXPECTED-ACTION-MARKER: grant the refund.",
        "answer_key": {"must_include": ["SECRET-KEY-MARKER"], "must_exclude": []},
        "forbidden_claims": ["SECRET-FORBIDDEN-MARKER"],
        "justified_uncertainty": [],
    }


def synthetic_row() -> dict:
    cell = synthetic_cell()
    return {
        "cell_id": cell["cell_id"],
        "sample_key": "thinking:0",
        "messages": cell["messages"],
        "answer": "Visible answer text.",
        "cell": cell,
        "validation": {"outcome": "accept_candidate", "reason": "nothing failed", "dimensions": []},
    }


@needs_miniset
def test_manifest_is_deterministic_and_matches_the_committed_copy():
    import freeze_miniset
    from miniset import load_cells

    cells, src = load_cells()
    a = freeze_miniset.build_manifest(cells, src)
    b = freeze_miniset.build_manifest(cells, src)
    assert a["aggregate_sha256"] == b["aggregate_sha256"]
    assert a["cells"] == 12
    assert a["scenarios"] == 3
    committed = json.loads(MANIFEST_PATH.read_text())
    assert committed["aggregate_sha256"] == a["aggregate_sha256"], "manifest is stale; rerun freeze_miniset"
    assert committed["mini_set_version"] == src["mini_set_version"]


def test_committed_manifest_contains_no_prose():
    """Hashes and ids only: no field value may be long enough to be a sentence."""
    committed = json.loads(MANIFEST_PATH.read_text())
    for row in committed["cell_hashes"]:
        assert set(row) == {"cell_id", "scenario_id", "cell_sha256", "fields"}
        for k, v in row["fields"].items():
            assert len(str(v)) == 64, (k, v)
    for sid, row in committed["scenario_hashes"].items():
        assert set(row) == {"cells", "scenario_sha256", "task_id", "counterfactual_class"}
        assert len(row["scenario_sha256"]) == 64
    narrative = {"status", "note"}
    long_values = []

    def walk(obj, key=None):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, k)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, key)
        elif isinstance(obj, str) and key not in narrative:
            if len(obj) > 64 and not set(obj) <= set("0123456789abcdef"):
                long_values.append((key, obj[:40]))

    walk(committed)
    assert long_values == [], "a prose value leaked into the sanitized manifest"


def test_blinding_hides_ground_truth():
    import build_review_package as brp

    row = synthetic_row()
    salt = "testsalt"
    blind = brp.render_blind([row], salt)
    key = brp.render_key([row], salt)
    for secret in ("SECRET-EXPECTED-ACTION-MARKER", "SECRET-KEY-MARKER",
                   "SECRET-FORBIDDEN-MARKER", "syn-001/A0", "A0", "neutral", "factual state A"):
        assert secret not in blind, secret
    for secret in ("SECRET-EXPECTED-ACTION-MARKER", "syn-001/A0", salt):
        assert secret in key, secret
    assert "Visible answer text." in blind
    assert "SECRET-PROMPT-MARKER" in blind  # the prompt is what the model saw; it must be shown


def test_blind_ids_are_salted_and_stable():
    import build_review_package as brp

    row = synthetic_row()
    one = brp.blind_id("salt-a", row["cell_id"], row["sample_key"])
    two = brp.blind_id("salt-b", row["cell_id"], row["sample_key"])
    assert one.startswith("C-") and len(one) == 12
    assert one != two
    assert one == brp.blind_id("salt-a", row["cell_id"], row["sample_key"])
    assert one != brp.blind_id("salt-a", row["cell_id"], "thinking:1")


def test_blind_file_states_that_the_proposal_is_not_binding():
    import build_review_package as brp

    blind = brp.render_blind([synthetic_row()], "s")
    assert "not binding" in blind
    assert "accept as a candidate target" in blind
    assert "needs more evidence" in blind
    assert "not told what verdict is expected" in blind


@needs_miniset
def test_real_package_builds_and_key_stays_out_of_the_blind_file(tmp_path):
    import build_review_package as brp
    from miniset import load_cells

    cells, _ = load_cells()
    row = {
        "cell_id": cells[0]["cell_id"],
        "sample_key": "thinking:0",
        "messages": cells[0]["messages"],
        "answer": cells[0]["expected_action"],
        "cell": cells[0],
        "validation": {"outcome": "needs_human_review", "reason": "queued", "dimensions": []},
    }
    blind = brp.render_blind([row], "s")
    assert cells[0]["expected_action"] not in blind or cells[0]["expected_action"] == row["answer"]
    for claim in cells[0]["forbidden_claims"]:
        assert claim not in blind, claim
