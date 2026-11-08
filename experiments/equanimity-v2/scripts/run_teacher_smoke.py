"""Bounded live smoke test against the Azure GPT-OSS 120B deployment.

Scope, enforced in code and not just documented:

    max_requests = 18   (6 cases x 3 conditions)
    max_tokens   = 50_000

Design of the 18 calls: one case from each of the six families, each generated
under the three SFT conditions. F1-F5 use their pressure variant (the case where
the manipulation is live); F6 uses its neutral variant as a no-pressure control
for the same generation procedure.

What this produces: candidate target texts, each independently validated against
its case. It does NOT produce an approved dataset, and nothing here is evidence
that the targets are good — only that they parse, respect facts on the token
level, and avoid the mechanically detectable failure modes.

Usage:
    python3 scripts/run_teacher_smoke.py --dry-run
    EQ2_AZURE_API_KEY=... EQ2_AZURE_ENDPOINT=... python3 scripts/run_teacher_smoke.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from provider.azure_foundry import (  # noqa: E402
    AzureConfig,
    AzureFoundryClient,
    Budget,
    BudgetExceeded,
    MockClient,
    ProviderError,
)
from validate import validate_target  # noqa: E402

SMOKE_CASES = [
    ("eq2-f1-001", "pressure"),
    ("eq2-f2-001", "pressure"),
    ("eq2-f3-002", "neutral"),
    ("eq2-f4-003", "pressure"),
    ("eq2-f5-001", "pressure"),
    ("eq2-f6-001", "neutral"),
]

CONDITIONS = ["E", "S", "G"]

MAX_REQUESTS = 18
MAX_TOKENS = 50_000
MAX_COMPLETION = 900
REASONING_EFFORT = "low"


def load_cases() -> dict[str, dict]:
    p = ROOT / "data" / "validated" / "cases.jsonl"
    if not p.exists():
        raise SystemExit("run src/build_dataset.py first")
    out = {}
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["variant_id"]] = r
    return out


def case_for_prompt(case: dict) -> dict:
    """The subset of the case the teacher is allowed to see.

    Deliberately excluded: provenance, review, split, rejection_reasons. The
    teacher does not need to know how the case will be validated, and telling it
    would invite it to write to the rubric instead of to the task.
    """
    return {
        "variant_kind": case["variant_kind"],
        "category": case["category"],
        "subcategory": case["subcategory"],
        "context": case["context"],
        "task": case["task"],
        "facts": [{k: f[k] for k in ("fact_id", "statement", "load_bearing")} for f in case["facts"]],
        "decision": case["decision"],
        "urgency": case["urgency"],
        "boundaries": case["boundaries"],
        "target_behavior": case["target_behavior"],
        "pressure": case["pressure"],
    }


def build_prompt(case: dict, condition: str) -> str:
    template = (ROOT / "prompts" / f"target_{condition}.md").read_text()
    tokens = [tok for f in case["facts"] for tok in f.get("target_key_tokens", [])]
    return (
        template
        .replace("{key_tokens}", ", ".join(tokens))
        .replace("{case_json}", json.dumps(case_for_prompt(case), indent=2, ensure_ascii=False))
    )


def get_key() -> tuple[str, str]:
    key = os.environ.get("EQ2_AZURE_API_KEY", "")
    endpoint = os.environ.get("EQ2_AZURE_ENDPOINT", "")
    if not key and Path("/tmp/oss_key.txt").exists():
        key = Path("/tmp/oss_key.txt").read_text().strip()
    if not key:
        raise SystemExit(
            "no API key: set EQ2_AZURE_API_KEY (and EQ2_AZURE_ENDPOINT), "
            "or place the key in /tmp/oss_key.txt"
        )
    if not endpoint:
        raise SystemExit("no endpoint: set EQ2_AZURE_ENDPOINT")
    return key, endpoint


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="use the deterministic mock client")
    ap.add_argument("--out", default=str(ROOT / "data" / "smoke"))
    args = ap.parse_args()

    cases = load_cases()
    plan = [(f"{sid}-{kind}", cond) for sid, kind in SMOKE_CASES for cond in CONDITIONS]

    assert len(plan) == MAX_REQUESTS, f"plan has {len(plan)} calls, budget is {MAX_REQUESTS}"

    budget = Budget(max_requests=MAX_REQUESTS, max_tokens=MAX_TOKENS)

    if args.dry_run:
        client = MockClient(budget=budget)
        client_label = "mock(dry-run)"
    else:
        key, endpoint = get_key()
        cfg = AzureConfig(
            endpoint=endpoint,
            deployment=os.environ.get("EQ2_AZURE_DEPLOYMENT", "gpt-oss-120b"),
            api_version=os.environ.get("EQ2_AZURE_API_VERSION", "2024-12-01-preview"),
            api_key=key,
        )
        client = AzureFoundryClient(cfg, budget=budget)
        client_label = f"azure:{cfg.deployment}"

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    results_path = outdir / "targets.jsonl"
    audit_path = outdir / "audit.jsonl"

    rows = []
    stopped_early = None

    with results_path.open("w") as fres, audit_path.open("w") as faud:
        for variant_id, condition in plan:
            case = cases[variant_id]
            prompt = build_prompt(case, condition)
            try:
                res = client.chat(
                    [{"role": "user", "content": prompt}],
                    request_id=f"{variant_id}::{condition}",
                    max_completion_tokens=MAX_COMPLETION,
                    reasoning_effort=REASONING_EFFORT,
                )
            except BudgetExceeded as exc:
                stopped_early = str(exc)
                break
            except ProviderError as exc:
                stopped_early = f"{type(exc).__name__}: {exc}"
                break

            verdict = validate_target(case, res.content, condition)
            row = {
                "variant_id": variant_id,
                "condition": condition,
                "content": res.content,
                "validation": verdict.as_dict(),
                "finish_reason": res.finish_reason,
                "latency_s": round(res.latency_s, 2),
                "usage": res.usage,
                "attempts": res.attempts,
                "provider": client_label,
            }
            rows.append(row)
            fres.write(json.dumps(row, sort_keys=True) + "\n")
            faud.write(json.dumps(res.audit_record(), sort_keys=True) + "\n")
            faud.flush()

            tag = "PASS" if verdict.ok else "FAIL"
            print(f"{variant_id:28s} {condition}  {tag}  "
                  f"{res.latency_s:5.1f}s  tokens={res.usage.get('completion_tokens', 0):4d}  "
                  f"len={len(res.content):4d}")

    summary = {
        "provider": client_label,
        "planned_calls": len(plan),
        "completed_calls": len(rows),
        "stopped_early": stopped_early,
        "budget": budget.snapshot(),
        "conditions": CONDITIONS,
        "cases": [f"{sid}-{kind}" for sid, kind in SMOKE_CASES],
        "pass": sum(1 for r in rows if r["validation"]["ok"]),
        "fail": sum(1 for r in rows if not r["validation"]["ok"]),
        "failures": [
            {"variant_id": r["variant_id"], "condition": r["condition"],
             "checks": [c for c in r["validation"]["checks"] if c["result"] == "fail"]}
            for r in rows if not r["validation"]["ok"]
        ],
        "note": (
            "Candidate targets only. Validation is mechanical (schema, tokens, "
            "fact-token coverage, refusal patterns, repetition). It is not evidence "
            "of quality and nothing here is human-approved."
        ),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print()
    print(f"provider={client_label} calls={len(rows)}/{len(plan)} pass={summary['pass']} fail={summary['fail']}")
    print(f"budget={json.dumps(budget.snapshot())}")
    if stopped_early:
        print(f"STOPPED EARLY: {stopped_early}")
    return 0 if not rows or summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
