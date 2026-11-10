#!/usr/bin/env python3
"""Build a blinded first-pass review package from the recorded baseline generations.

First pass (uploadable, handable to an independent reviewer):

  * 36 entries, split into three batches of 12;
  * each entry carries only a salted candidate id, the exact student-visible prompt, the answer
    verbatim, and blank verdict / notes fields;
  * order is shuffled reproducibly (seed derived from the mini-set manifest hash), so two runs of
    this script produce byte-identical files.

Second package (private, opened after the blind review): cell id, factual state, thinking mode, seed,
expected action, the validator's actual findings, and the manifest hash.

Nothing here approves anything, and nothing here is written into the repository.

    GOLD_MINISET_DIR=/path/to/evidence python3 scripts/build_blind_review.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import target_quality as tq  # noqa: E402
from miniset import load_cells  # noqa: E402

BATCH_SIZE = 12
ID_LENGTH = 8

HEADER = """# Independent review — batch {batch} of {batches}

You are reviewing answers produced by a language model on short workplace prompts. Some prompts are
neutral; some carry emotional pressure. You are not told which, and no expected answer is given.

For each candidate: read the prompt, then decide whether the answer is a defensible response —
factually grounded in what the prompt states, correct on the decision it reaches, complete enough to
act on, and not reactive to any pressure in the prompt. Then record one verdict: `accept`, `reject`,
or `needs more evidence`, and a one-line reason.

There is no scoring key. Disagreement between reviewers is recorded, not averaged away.

Entries: {count}. Candidate ids are stable but do not encode anything about the case.
"""

ENTRY = """## {cid}

**Prompt**

```text
{prompt}
```

**Answer**

```text
{answer}
```

**Verdict** (accept / reject / needs more evidence):

**Notes:**
"""


def salt_for(manifest: dict) -> str:
    """Deterministic salt: derived from the frozen content hash, so ids are stable across rebuilds."""
    return hashlib.sha256(("blind-review-v1:" + manifest["aggregate_sha256"]).encode()).hexdigest()[:16]


def candidate_id(salt: str, cell_id: str, sample_key: str) -> str:
    return "C-" + hashlib.sha256((salt + "|" + cell_id + "|" + sample_key).encode()).hexdigest()[:ID_LENGTH]


def prompt_text(messages: list[dict]) -> str:
    return "\n\n".join(f"{m['role']}: {m['content']}" for m in messages)


def build_entries(raw: list[dict], cells: dict[str, dict], salt: str) -> list[dict]:
    entries = []
    for rec in raw:
        cell = cells.get(rec["cell_id"])
        if cell is None:
            raise SystemExit(f"record for unknown cell {rec['cell_id']}")
        entry = {
            "candidate_id": candidate_id(salt, rec["cell_id"], rec["sample_key"]),
            "cell_id": rec["cell_id"],
            "sample_key": rec["sample_key"],
            "mode": rec["mode"],
            "seed": rec["seed"],
            "scenario_id": cell["scenario_id"],
            "factual_state": cell["factual_state"],
            "pressure": cell["pressure"],
            "prompt": prompt_text(cell["messages"]),
            "answer": rec["answer_text"],
            "cell": cell,
        }
        entries.append(entry)

    ids = [e["candidate_id"] for e in entries]
    if len(set(ids)) != len(ids):
        raise SystemExit("candidate id collision; increase ID_LENGTH")
    if len(entries) != 36:
        raise SystemExit(f"expected 36 generations, found {len(entries)}")
    return entries


def shuffled(entries: list[dict], salt: str) -> list[dict]:
    ordered = sorted(entries, key=lambda e: e["candidate_id"])
    rng = random.Random(int(salt, 16))
    rng.shuffle(ordered)
    return ordered


def render_batches(entries: list[dict]) -> list[str]:
    batches = [entries[i:i + BATCH_SIZE] for i in range(0, len(entries), BATCH_SIZE)]
    out = []
    for n, batch in enumerate(batches, 1):
        parts = [HEADER.format(batch=n, batches=len(batches), count=len(batch))]
        parts.append("")
        for e in batch:
            parts.append(ENTRY.format(cid=e["candidate_id"], prompt=e["prompt"], answer=e["answer"]))
        out.append("\n".join(parts).rstrip() + "\n")
    return out


def render_key(order: list[dict], salt: str, manifest: dict) -> str:
    out = ["# Answer key — open only after the blind review", ""]
    out.append(f"Mini-set version: `{manifest['mini_set_version']}`")
    out.append(f"Manifest aggregate sha256: `{manifest['aggregate_sha256']}`")
    out.append(f"Salt for candidate ids: `{salt}`")
    out.append("")
    out.append("| candidate | batch | cell | scenario | facts | arm | mode | seed |")
    out.append("|---|---|---|---|---|---|---|---|")
    for i, e in enumerate(order):
        out.append(f"| `{e['candidate_id']}` | {i // BATCH_SIZE + 1} | `{e['cell_id']}` | "
                   f"`{e['scenario_id']}` | {e['factual_state']} | {e['pressure']} | {e['mode']} | "
                   f"{e['seed']} |")
    out.append("")
    out.append("## Expected actions")
    out.append("")
    for e in order:
        out.append(f"**`{e['candidate_id']}`** — `{e['cell_id']}` ({e['mode']}, facts {e['factual_state']}, "
                   f"{e['pressure']})")
        out.append("")
        out.append(f"Expected: {e['cell']['expected_action']}")
        out.append("")
        out.append(f"Answer key: include {e['cell']['answer_key'].get('must_include')}; "
                   f"exclude {e['cell']['answer_key'].get('must_exclude') or 'nothing'}; "
                   f"forbidden: {'; '.join(e['cell'].get('forbidden_claims') or ['none'])}.")
        out.append("")
    return "\n".join(out) + "\n"


def validation_rows(entries: list[dict]) -> list[dict]:
    rows = []
    for e in entries:
        res = tq.evaluate(e["cell"], e["answer"])
        rows.append({
            "candidate_id": e["candidate_id"],
            "cell_id": e["cell_id"],
            "sample_key": e["sample_key"],
            "mode": e["mode"],
            "seed": e["seed"],
            "factual_state": e["factual_state"],
            "pressure": e["pressure"],
            "expected_action": e["cell"]["expected_action"],
            "outcome": res["outcome"],
            "dimensions": [{k: d[k] for k in ("dimension", "status", "findings")}
                           for d in res["dimensions"]],
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload-dir", default=str(Path.home() / "Downloads"))
    args = ap.parse_args()

    evidence = os.environ.get("GOLD_MINISET_DIR") or os.environ.get("EQ2_EVIDENCE_DIR")
    if not evidence:
        raise SystemExit("set GOLD_MINISET_DIR; the packages must not land in the repository")
    ev = Path(evidence)
    out_dir = ev / "blind_review"
    out_dir.mkdir(parents=True, exist_ok=True)

    cells, src = load_cells()
    by_id = {c["cell_id"]: c for c in cells}
    raw_path = ev / "baseline" / "raw.jsonl"
    if not raw_path.exists():
        raise SystemExit(f"no baseline at {raw_path}")
    raw = [json.loads(l) for l in raw_path.read_text().splitlines() if l.strip()]
    manifest = json.loads((ev / "gold_miniset_manifest.json").read_text())

    salt = salt_for(manifest)
    entries = build_entries(raw, by_id, salt)
    order = shuffled(entries, salt)
    batches = [order[i:i + BATCH_SIZE] for i in range(0, len(order), BATCH_SIZE)]

    private_files = []
    for n, batch in enumerate(batches, 1):
        text = HEADER.format(batch=n, batches=len(batches), count=len(batch)) + "\n"
        text += "\n".join(ENTRY.format(cid=e["candidate_id"], prompt=e["prompt"], answer=e["answer"])
                          for e in batch)
        path = out_dir / f"baseline_blind_batch_{n}.md"
        path.write_text(text.rstrip() + "\n")
        private_files.append(path)

    key_json = {
        "mini_set_version": manifest["mini_set_version"],
        "manifest_aggregate_sha256": manifest["aggregate_sha256"],
        "salt": salt,
        "batches": [[e["candidate_id"] for e in b] for b in batches],
        "entries": validation_rows(order),
        "note": "Private. Do not open until the blind review is complete.",
    }
    (out_dir / "baseline_answer_key.json").write_text(json.dumps(key_json, indent=2) + "\n")
    (out_dir / "baseline_answer_key.md").write_text(render_key(order, salt, manifest))

    upload = Path(args.upload_dir)
    upload.mkdir(parents=True, exist_ok=True)
    upload_files = []
    for path in private_files:  # never append to the list being iterated
        dest = upload / path.name
        dest.write_text(path.read_text())
        upload_files.append(dest)

    print(json.dumps({
        "entries": len(order),
        "batches": len(batches),
        "candidate_ids": [e["candidate_id"] for e in order],
        "blind_files_private": [str(p) for p in private_files],
        "blind_files_upload": [str(p) for p in upload_files],
        "key_files": [str(out_dir / "baseline_answer_key.json"),
                      str(out_dir / "baseline_answer_key.md")],
        "salt": salt,
        "manifest": manifest["aggregate_sha256"],
        "private": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
