"""Build the Equanimity v2 semantic dataset from authored scenario specs.

Design note on the three variants. v0.1.0 uses two clean single-factor
contrasts rather than a full 2x2:

    neutral        facts A, calm register,   decision X
    pressure       facts A, emotional pressure, decision X   <- invariance test
    counterfactual facts B, calm register,   decision Y      <- sensitivity test

The crossed cell (pressure + changed fact) is deliberately not produced here.
It is the most interesting cell and it needs hand-authored messages, not
mechanical fact substitution. Its absence is recorded as a limitation, not
papered over.

Run:
    python3 src/build_dataset.py [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scenarios"))

from validate import (  # noqa: E402
    canonical_content_sha256,
    find_duplicates,
    validate_case,
    validate_triple,
)

DATASET_VERSION = "v0.1.1"
SCHEMA_VERSION = "equanimity-v2.semantic.1"
BUILD_UTC = os.environ.get("EQ2_BUILD_UTC", "2026-11-07T00:00:00Z")
AUTHOR = "pi-agent-seed-v1"


def load_specs() -> list[dict]:
    from f1_f2 import SPECS_F1_F2
    from f3_f4 import SPECS_F3_F4
    from f5_f6 import SPECS_F5_F6

    specs = SPECS_F1_F2 + SPECS_F3_F4 + SPECS_F5_F6
    ids = [s["spec_id"] for s in specs]
    assert len(ids) == len(set(ids)), "duplicate spec_id"
    return specs


def _facts(spec: dict, *, cf: bool) -> list[dict]:
    out = []
    for i, (stmt, toks, load) in enumerate(spec["facts"]):
        if cf and i == spec["cf_fact_index"]:
            stmt = spec["cf_statement"]
        out.append({
            "fact_id": f"f{i+1}",
            "statement": stmt,
            "load_bearing": load,
            "target_key_tokens": toks,
        })
    return out


def _prior(spec: dict, *, cf: bool) -> list[dict]:
    turns = spec["cf_prior_turns"] if (cf and spec["cf_prior_turns"]) else spec["prior_turns"]
    return [{"role": r, "content": t} for r, t in turns]


def check_spec(spec: dict) -> None:
    """Spec-level guards that a single case cannot express."""
    sid = spec["spec_id"]
    orig = spec["facts"][spec["cf_fact_index"]][0].strip().lower()
    cf = spec["cf_statement"].strip().lower()
    assert orig != cf, f"{sid}: cf_statement restates the original fact"
    assert spec["cf_decision"].strip() != spec["decision"]["expected"].strip(), (
        f"{sid}: cf_decision identical to the neutral decision"
    )
    assert spec["pressure"]["intensity"] >= 1, f"{sid}: pressure intensity must be >= 1"
    assert spec["neutral"].strip() != spec["pressure_msg"].strip(), f"{sid}: pressure message duplicates neutral"


def make_case(spec: dict, kind: str) -> dict:
    cf = kind == "counterfactual"

    if kind == "neutral":
        msg = spec["neutral"]
        pressure = {"type": "none", "intensity": 0, "target": "none", "escalation_cues": []}
    elif kind == "pressure":
        msg = spec["pressure_msg"]
        p = spec["pressure"]
        pressure = {
            "type": p["type"],
            "intensity": p["intensity"],
            "target": p["target"],
            "escalation_cues": list(p.get("cues", [])),
        }
    else:
        # Calm register plus one explicit fact update. Machine-derived text,
        # flagged in provenance so it cannot be mistaken for hand-authored prose.
        msg = f"{spec['neutral']} One thing has changed: {spec['cf_statement']}"
        pressure = {"type": "none", "intensity": 0, "target": "none", "escalation_cues": []}

    prior = _prior(spec, cf=cf)
    decision = spec["decision"]
    expected = decision["expected"]
    cf_decision = spec["cf_decision"]
    cf_fact_id = f"f{spec['cf_fact_index']+1}"

    provenance = {
        "author": AUTHOR,
        "created_utc": BUILD_UTC,
        "review_status": "draft",
        "content_sha256": "",
        "generation_config": (
            {
                "method": "appended_fact_update",
                "source": "scenarios/ seed spec neutral message",
                "requires": "human rewrite of the user message before approval",
            }
            if cf else None
        ),
    }

    case = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "scenario_id": spec["spec_id"],
        "case_family_id": spec["family"],
        "variant_id": f"{spec['spec_id']}-{kind}",
        "variant_kind": kind,
        "category": spec["category"],
        "subcategory": spec["subcategory"],
        "context": {
            "turn_index": len(prior),
            "prior_turns": prior,
            "user_message": msg,
        },
        "task": {
            "legitimate_task": spec["task"],
            "domain": spec["domain"],
            "deliverable": spec["deliverable"],
        },
        "facts": _facts(spec, cf=cf),
        "decision": {
            "expected_decision": cf_decision if cf else expected,
            "decision_type": decision["type"],
            "rationale": decision["rationale"],
            "assertiveness": decision["assertiveness"],
        },
        "urgency": spec["urgency"],
        "boundaries": spec["boundaries"],
        "pressure": pressure,
        "target_behavior": {"must": spec["must"], "must_not": spec["must_not"]},
        "counterfactual": {
            "changed_fact_id": cf_fact_id,
            "changed_fact_statement": spec["cf_statement"],
            "decision_after_change": cf_decision,
            "decision_differs": cf,
        },
        "split": spec["split"],
        "provenance": provenance,
        "review": {
            "automatic": {"status": "not_run", "checks": []},
            "human": {"status": "pending"},
        },
    }
    case["provenance"]["content_sha256"] = canonical_content_sha256(case)
    return case


def attach_validation(case: dict) -> dict:
    out = validate_case(case)
    case["review"]["automatic"] = {
        "status": "pass" if out.ok else "fail",
        "checks": [{"check_id": c.check_id, "result": c.result, "detail": c.detail[:300]} for c in out.checks],
    }
    if out.rejection_reasons:
        case["rejection_reasons"] = out.rejection_reasons
    return case


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data"))
    args = ap.parse_args()
    out = Path(args.out)

    specs = load_specs()
    cases = []
    for s in specs:
        for kind in ("neutral", "pressure", "counterfactual"):
            cases.append(attach_validation(make_case(s, kind)))

    for s in specs:
        check_spec(s)

    # Triple-level invariants: the checks that make the contrast controlled.
    by_scenario: dict[str, dict[str, dict]] = {}
    for c in cases:
        by_scenario.setdefault(c["scenario_id"], {})[c["variant_kind"]] = c

    triple_failures = []
    for sid, tri in by_scenario.items():
        tout = validate_triple(tri["neutral"], tri["pressure"], tri["counterfactual"])
        if not tout.ok:
            triple_failures.append(tout.as_dict())
        # attach the triple verdict to every variant so the audit trail is per-row
        for kind, case in tri.items():
            case["review"]["automatic"]["checks"].extend(
                {"check_id": chk.check_id, "result": chk.result, "detail": chk.detail[:300]}
                for chk in tout.checks
            )
            if not tout.ok:
                case["review"]["automatic"]["status"] = "fail"
                case.setdefault("rejection_reasons", []).extend(tout.rejection_reasons)

    accepted = [c for c in cases if c["review"]["automatic"]["status"] == "pass"]
    rejected = [c for c in cases if c["review"]["automatic"]["status"] != "pass"]

    (out / "validated").mkdir(parents=True, exist_ok=True)
    (out / "rejected").mkdir(parents=True, exist_ok=True)

    def dump(path: Path, rows: list[dict]) -> str:
        blob = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + ("\n" if rows else "")
        path.write_text(blob)
        return hashlib.sha256(blob.encode()).hexdigest()

    h_acc = dump(out / "validated" / "cases.jsonl", accepted)
    h_rej = dump(out / "rejected" / "rejected.jsonl", rejected)

    dups = find_duplicates(accepted)

    by_family: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for c in accepted:
        by_family[c["case_family_id"]] = by_family.get(c["case_family_id"], 0) + 1
        by_kind[c["variant_kind"]] = by_kind.get(c["variant_kind"], 0) + 1

    manifest = {
        "dataset_version": DATASET_VERSION,
        "schema_version": SCHEMA_VERSION,
        "build_utc": BUILD_UTC,
        "git_commit": git_commit(),
        "author": AUTHOR,
        "counts": {
            "scenarios": len(specs),
            "cases_total": len(cases),
            "accepted": len(accepted),
            "rejected": len(rejected),
        },
        "by_family": by_family,
        "by_variant_kind": by_kind,
        "outputs": {
            "validated_cases.jsonl": {"rows": len(accepted), "sha256": h_acc},
            "rejected.jsonl": {"rows": len(rejected), "sha256": h_rej},
        },
        "near_duplicates_cross_scenario": dups,
        "triple_failures": triple_failures,
        "limitations": [
            "All rows are review_status=draft; no human has approved any case.",
            "Counterfactual user messages are machine-derived (appended fact update), not hand-authored.",
            "The crossed cell (pressure + changed fact) is not generated in v0.1.0.",
            "No target responses exist yet for these cases; targets are produced separately and validated independently.",
            "Facts are authored by the same agent that wrote the decisions, so fact/decision agreement is not independent evidence.",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"specs={len(specs)} cases={len(cases)} accepted={len(accepted)} rejected={len(rejected)}")
    print(f"by_kind={by_kind}")
    for f, n in sorted(by_family.items()):
        print(f"  {f}: {n}")
    if dups:
        print(f"cross-scenario near-duplicates: {len(dups)}")
        for d in dups[:5]:
            print(f"  {d['a']} ~ {d['b']} ({d['similarity']})")
    if triple_failures:
        print(f"triple failures: {len(triple_failures)}")
        for t in triple_failures[:5]:
            print(f"  {t['subject_id']}: {t['rejection_reasons']}")
    if rejected:
        for r in rejected[:6]:
            print(f"REJECT {r['variant_id']}: {r.get('rejection_reasons')}")
    return 0 if not rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
