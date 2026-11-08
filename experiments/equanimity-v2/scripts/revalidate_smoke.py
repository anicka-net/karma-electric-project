"""Re-validate stored smoke-run target text against the current dataset.

Why this exists: the 18-call live run was deliberately kept to a single pass.
When a validator or case-authoring defect is found afterwards, re-running the
teacher costs another 18 calls. Re-validating the *stored text* costs nothing and
answers the honest question — did the failure come from the teacher, or from our
own checker?

This is not a substitute for a fresh run. A fixed checker that now accepts old
text says something about the checker, not about the teacher's output quality.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from validate import validate_target  # noqa: E402


def prose_fingerprint(case: dict) -> str:
    """Hash of the parts a reader would call 'the case text'.

    Used to separate 'the prose changed' from 'only metadata changed' (dataset
    version, added deliverable checks, split reassignment), which is what happened
    between v0.1.0 and v0.2.0.
    """
    import hashlib

    payload = {
        "context": case["context"],
        "facts": [{k: f[k] for k in ("fact_id", "statement", "load_bearing")} for f in case["facts"]],
        "decision": case["decision"],
        "task": case["task"],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def evidence_dir() -> Path:
    """Raw teacher text is deliberately absent from this repository.

    No local path is embedded here: it would publish a private filesystem layout
    and would also break for any other checkout. The directory must be supplied.
    """
    import os

    raw = os.environ.get("EQ2_EVIDENCE_DIR", "")
    if not raw:
        raise SystemExit(
            "EQ2_EVIDENCE_DIR is not set. Raw teacher generations are held outside\n"
            "Git history (see data/smoke/README.md). Point this at the directory\n"
            "containing targets.jsonl to re-validate stored text."
        )
    d = Path(raw)
    if not (d / "targets.jsonl").exists():
        raise SystemExit(f"no targets.jsonl in {d}")
    return d


def main() -> int:
    cases = {}
    for line in (ROOT / "data" / "validated" / "cases.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            cases[r["variant_id"]] = r

    stored = [json.loads(l) for l in (evidence_dir() / "targets.jsonl").read_text().splitlines() if l.strip()]
    at_run = json.loads((ROOT / "data" / "smoke" / "cases_at_run.json").read_text())

    rows = []
    for r in stored:
        vid, cond = r["variant_id"], r["condition"]
        before = r["validation"]["ok"]
        case = cases[vid]
        after_out = validate_target(case, r["content"], cond)
        after = after_out.ok
        rows.append({
            "variant_id": vid,
            "condition": cond,
            "ok_at_run": before,
            "ok_now": after,
            "changed": before != after,
            "case_hash_at_run": at_run.get(vid),
            "case_hash_now": case["provenance"]["content_sha256"],
            "case_content_changed": at_run.get(vid) != case["provenance"]["content_sha256"],
            "prose_fingerprint": prose_fingerprint(case),
            "failing_checks_now": [c.check_id for c in after_out.checks if c.result == "fail"],
            "failing_checks_at_run": [c["check_id"] for c in r["validation"]["checks"] if c["result"] == "fail"],
        })

    summary = {
        "stored_targets": len(rows),
        "ok_at_run": sum(1 for r in rows if r["ok_at_run"]),
        "ok_now": sum(1 for r in rows if r["ok_now"]),
        "flipped_to_pass": [r for r in rows if not r["ok_at_run"] and r["ok_now"]],
        "still_failing": [r for r in rows if not r["ok_now"]],
        "case_content_changed_rows": [r["variant_id"] for r in rows if r["case_content_changed"]],
        "distinct_prose_fingerprints": sorted({r["prose_fingerprint"] for r in rows}),
        "prose_note": (
            "case_content_changed is true for every row because dataset_version, "
            "deliverable_checks and split are all part of the content hash. The prose "
            "itself did not change; check the fingerprints if that distinction matters."
        ),
        "caveat": (
            "Re-validation of stored text, not a fresh teacher run. A checker fix "
            "that now accepts old output is evidence about the checker only."
        ),
    }
    (ROOT / "data" / "smoke" / "revalidation.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (ROOT / "data" / "smoke" / "revalidation_rows.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n"
    )

    print(f"stored={len(rows)} ok_at_run={summary['ok_at_run']} ok_now={summary['ok_now']}")
    print(f"case content hash changed for all {len(summary['case_content_changed_rows'])} rows "
          f"(metadata: version, deliverable_checks, split); prose fingerprints: "
          f"{len(summary['distinct_prose_fingerprints'])} distinct")
    for r in summary["flipped_to_pass"]:
        print(f"  FLIPPED {r['variant_id']} {r['condition']}: {r['failing_checks_at_run']} -> pass")
    for r in summary["still_failing"]:
        print(f"  STILL FAILING {r['variant_id']} {r['condition']}: {r['failing_checks_now']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
