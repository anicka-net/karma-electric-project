#!/usr/bin/env python3
"""Freeze the 12-cell development mini-set.

Produces a manifest of content hashes so a run can be tied to exact data. The manifest is written
twice: a full copy in the private directory (with per-cell hashes and field hashes) and a sanitized
copy in the repository containing only ids, hashes, version and provenance — never prompt text.

Freezing is not approval. The status stays "development review; not a confirmatory holdout".
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from miniset import load_cells  # noqa: E402

PROVENANCE_FIELDS = ("messages", "stated_facts", "expected_action", "answer_key",
                     "forbidden_claims", "required_premises")


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_manifest(cells: list[dict], src: dict) -> dict:
    rows = []
    for c in cells:
        row = {
            "cell_id": c["cell_id"],
            "scenario_id": c["scenario_id"],
            "cell_sha256": sha(canonical(c)),
            "fields": {f: sha(canonical(c.get(f))) for f in PROVENANCE_FIELDS},
        }
        rows.append(row)

    scenario_rows = {}
    for sid in sorted({c["scenario_id"] for c in cells}):
        scenario_cells = [c for c in cells if c["scenario_id"] == sid]
        scenario_rows[sid] = {
            "cells": sorted(c["cell_code"] for c in scenario_cells),
            "scenario_sha256": sha(canonical(sorted(scenario_cells, key=lambda x: x["cell_code"]))),
            "task_id": scenario_cells[0]["task_id"],
            "counterfactual_class": scenario_cells[0]["counterfactual_class"],
        }

    return {
        "mini_set_version": src["mini_set_version"],
        "status": ("frozen development set; not a confirmatory holdout; no teacher targets generated; "
                   "not approved for training"),
        "cells": len(cells),
        "scenarios": len(scenario_rows),
        "aggregate_sha256": sha(canonical(rows)),
        "scenario_hashes": scenario_rows,
        "cell_hashes": rows,
        "note": ("Hashes only. Prompt text, expected actions, answer keys and answer-key prose remain "
                 "in the private directory and are not part of this file."),
    }


def main() -> int:
    try:
        cells, src = load_cells()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    manifest = build_manifest(cells, src)
    private_dir = Path(os.environ["GOLD_MINISET_DIR"])
    (private_dir / "gold_miniset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    sanitized = {
        "mini_set_version": manifest["mini_set_version"],
        "status": manifest["status"],
        "cells": manifest["cells"],
        "scenarios": manifest["scenarios"],
        "aggregate_sha256": manifest["aggregate_sha256"],
        "scenario_hashes": {
            sid: {"cells": v["cells"], "scenario_sha256": v["scenario_sha256"],
                  "task_id": v["task_id"], "counterfactual_class": v["counterfactual_class"]}
            for sid, v in manifest["scenario_hashes"].items()
        },
        "cell_hashes": manifest["cell_hashes"],
        "note": manifest["note"],
    }
    dest = ROOT / "data" / "audit" / "gold_miniset_manifest.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"version": sanitized["mini_set_version"], "cells": sanitized["cells"],
                      "aggregate_sha256": sanitized["aggregate_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
