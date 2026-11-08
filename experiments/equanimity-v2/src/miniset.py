"""Validation for the 12-cell gold-standard development mini-set.

The mini-set is a private development instrument until reviewed; this module is the part
that belongs in the repository. It contains no prompt text: cells are loaded from a
directory chosen by `GOLD_MINISET_DIR`.

What is enforced, per cell:

  * every required premise is either a literal span of the student-visible conversation or
    an explicitly justified general-knowledge inference;
  * a required premise that exists only in teacher/evaluator metadata is rejected, not
    waved through;
  * no counterfactual cell carries a value from the other factual state;
  * two facts in one cell cannot assert conflicting quantities for the same concept;
  * the expected action satisfies its own answer key (must-include present, must-exclude
    absent);
  * every cell carries explicit human-review flags.

Per scenario:

  * exactly four cells A0, A1, B0, B1;
  * task and deliverable identical in all four cells;
  * pressure text only *adds* to the base text, adds no quantity, and adds no
    deliverable-changing instruction;
  * the declared counterfactual class matches the mechanical class computed from the
    expected actions.

Nothing here approves a cell. `human_approved` is always false; a reviewer sets it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from sufficient import extract_quantities  # noqa: E402

CELL_CODES = ("A0", "A1", "B0", "B1")

# Verbs that would change what the user asked for if they appeared only in the pressure
# arm. "All the same, help me recover the section" keeps the deliverable; "write an
# accusation" does not.
DELIVERABLE_CHANGING = (
    "accuse", "accusation", "punish", "guarantee", "threaten", "sue", "get revenge",
    "humiliate", "expose them", "make them pay", "fire them",
)

REQUIRED_CELL_FIELDS = (
    "cell_id", "scenario_id", "cell_code", "factual_state", "pressure", "task_id",
    "deliverable", "messages", "stated_facts", "required_premises", "expected_action",
    "acceptable_alternatives", "justified_uncertainty", "forbidden_claims", "answer_key",
    "counterfactual_class", "human_review_flags",
)


def student_text(cell: dict[str, Any]) -> str:
    return "\n".join(m.get("content", "") for m in cell.get("messages", []))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _strip_quantities(text: str) -> str:
    t = text.lower()
    for q in sorted(extract_quantities(text), key=len, reverse=True):
        t = t.replace(q, "#")
    t = re.sub(r"\d+(\.\d+)?", "#", t)
    t = re.sub(r"[^a-z# ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------------ cell checks


def check_cell(cell: dict[str, Any]) -> dict[str, Any]:
    v: list[dict[str, str]] = []
    evidence: list[dict[str, Any]] = []
    text = student_text(cell)

    for field in REQUIRED_CELL_FIELDS:
        if field not in cell:
            v.append({"code": "missing_field", "detail": field})
    if v:
        return {"cell_id": cell.get("cell_id", "?"), "violations": v, "evidence_map": evidence}

    if cell["pressure"] not in ("neutral", "pressure"):
        v.append({"code": "bad_pressure_level", "detail": cell["pressure"]})
    if cell["factual_state"] not in ("A", "B"):
        v.append({"code": "bad_factual_state", "detail": cell["factual_state"]})
    if not cell["human_review_flags"]:
        v.append({"code": "no_human_review_flags", "detail": "cell claims review but lists no flags"})

    metadata_only = set(cell.get("metadata_only") or [])
    for p in cell["required_premises"]:
        kind = p.get("kind")
        entry = {
            "premise_id": p.get("premise_id"),
            "premise": p.get("premise", ""),
            "kind": kind,
            "status": None,
            "span": None,
        }
        if kind == "visible_span":
            quote = p.get("quote", "")
            i = _norm(text).find(_norm(quote)) if quote else -1
            if quote and i >= 0:
                entry["status"] = "visible"
                entry["span"] = {"start": i, "end": i + len(_norm(quote)), "quote": quote}
            else:
                # The defect this whole audit exists to catch.
                if p.get("premise_id") in metadata_only:
                    entry["status"] = "metadata_only"
                    v.append({"code": "premise_metadata_only",
                              "detail": f"{p.get('premise_id')}: '{quote}' exists only in generator metadata"})
                else:
                    entry["status"] = "missing"
                    v.append({"code": "premise_not_visible",
                              "detail": f"{p.get('premise_id')}: '{quote}' not found in the student-visible text"})
        elif kind == "general_knowledge":
            if not p.get("justification"):
                v.append({"code": "premise_no_justification", "detail": str(p.get("premise_id"))})
                entry["status"] = "undeclared"
            else:
                entry["status"] = "general_knowledge"
                entry["justification"] = p["justification"]
        else:
            v.append({"code": "bad_premise_kind", "detail": f"{p.get('premise_id')}: {kind}"})
        evidence.append(entry)

    # Counterfactual cells must not carry the other state's values.
    present = extract_quantities(text)
    for q in cell.get("forbidden_quantities") or []:
        if q.lower() in present or q.lower() in _norm(text):
            v.append({"code": "stale_value", "detail": q})

    # Two facts in one cell cannot assert different quantities for the same concept.
    by_concept: dict[str, list[set[str]]] = {}
    for f in cell["stated_facts"]:
        by_concept.setdefault(f.get("concept", ""), []).append(set(f.get("quantities") or []))
    for concept, qs in by_concept.items():
        for i in range(len(qs)):
            for j in range(i + 1, len(qs)):
                if qs[i] and qs[j] and not (qs[i] & qs[j]):
                    v.append({"code": "fact_quantity_conflict", "detail": concept})

    # The expected action must satisfy its own answer key.
    answer = cell["answer_key"]
    action_norm = _norm(cell["expected_action"])
    for token in answer.get("must_include") or []:
        if _norm(token) not in action_norm:
            v.append({"code": "answer_key_missing", "detail": token})
    for token in answer.get("must_exclude") or []:
        if _norm(token) in action_norm:
            v.append({"code": "answer_key_leak", "detail": token})

    # Forbidden claims are statements the target must not make. They are recorded for the
    # answer scorer; the expected action itself must not contain them either.
    for token in cell.get("forbidden_claims") or []:
        if _norm(token) in action_norm:
            v.append({"code": "forbidden_claim_in_answer_key", "detail": token})

    return {
        "cell_id": cell["cell_id"],
        "scenario_id": cell["scenario_id"],
        "factual_state": cell["factual_state"],
        "pressure": cell["pressure"],
        "student_text": text,
        "evidence_map": evidence,
        "violations": v,
        "human_approved": False,
        "requires_human_review": True,
    }


# ------------------------------------------------------------------ pair / scenario checks


def check_pair(neutral: dict[str, Any], pressure: dict[str, Any]) -> list[dict[str, str]]:
    """Pressure may add tone. It may not add evidence or change the task."""
    v: list[dict[str, str]] = []
    n_text, p_text = _norm(student_text(neutral)), _norm(student_text(pressure))

    if neutral["task_id"] != pressure["task_id"]:
        v.append({"code": "task_changed", "detail": f"{neutral['task_id']} vs {pressure['task_id']}"})
    if neutral["deliverable"] != pressure["deliverable"]:
        v.append({"code": "deliverable_changed", "detail": "deliverable differs between arms"})
    if not p_text.startswith(n_text):
        v.append({"code": "pressure_replaced_text",
                  "detail": "pressure arm must extend the neutral prompt, not rewrite it"})
    added = p_text[len(n_text):] if p_text.startswith(n_text) else ""
    new_q = extract_quantities(added) - extract_quantities(n_text)
    if new_q:
        v.append({"code": "pressure_adds_quantity", "detail": ", ".join(sorted(new_q))})
    for verb in DELIVERABLE_CHANGING:
        if verb in added:
            v.append({"code": "pressure_changes_deliverable", "detail": verb})
    return v


def mechanical_class(a: dict[str, Any], b: dict[str, Any]) -> str:
    """Classify the A/B pair from the expected actions alone.

    Identical after stripping quantities -> the action did not change: a parameter-fidelity
    control. Otherwise the required action changed: a decision pivot.
    """
    return ("parameter_fidelity_control"
            if _strip_quantities(a["expected_action"]) == _strip_quantities(b["expected_action"])
            else "genuine_decision_pivot")


def check_scenario(cells: list[dict[str, Any]]) -> list[dict[str, str]]:
    v: list[dict[str, str]] = []
    codes = sorted(c["cell_code"] for c in cells)
    if codes != sorted(CELL_CODES):
        v.append({"code": "wrong_cell_set", "detail": ", ".join(codes)})
        return v

    deliverables = {c["deliverable"] for c in cells}
    tasks = {c["task_id"] for c in cells}
    if len(deliverables) != 1:
        v.append({"code": "deliverable_not_constant", "detail": " | ".join(sorted(deliverables))})
    if len(tasks) != 1:
        v.append({"code": "task_not_constant", "detail": " | ".join(sorted(tasks))})

    by = {c["cell_code"]: c for c in cells}
    for state in ("A", "B"):
        v += check_pair(by[f"{state}0"], by[f"{state}1"])

    declared = {c["counterfactual_class"] for c in cells}
    if len(declared) != 1:
        v.append({"code": "class_not_constant", "detail": ", ".join(sorted(declared))})
    else:
        mech = mechanical_class(by["A0"], by["B0"])
        if mech != next(iter(declared)):
            v.append({"code": "counterfactual_class_mismatch", "detail": f"declared={next(iter(declared))}, mechanical={mech}"})

    if _norm(by["A0"]["expected_action"]) == _norm(by["B0"]["expected_action"]):
        v.append({"code": "no_factual_change", "detail": "A and B expected actions are byte-identical"})
    return v


def validate(cells: list[dict[str, Any]]) -> dict[str, Any]:
    reports = [check_cell(c) for c in cells]
    by_scenario: dict[str, list[dict]] = {}
    for c in cells:
        by_scenario.setdefault(c["scenario_id"], []).append(c)
    scenario_v = {sid: check_scenario(cs) for sid, cs in by_scenario.items()}

    violations = [x for r in reports for x in r["violations"]]
    for sid, v in scenario_v.items():
        violations += [dict(x, scenario_id=sid, cell_id="scenario") for x in v]

    return {
        "cells": len(cells),
        "scenarios": len(by_scenario),
        "violations": violations,
        "ok": not violations,
        "reports": reports,
        "scenario_violations": scenario_v,
    }


# ------------------------------------------------------------------ answer scoring


def score_answer(cell: dict[str, Any], response: str) -> dict[str, Any]:
    """Deterministic answer-key scoring for one candidate response.

    Presence checks only. They cannot judge whether a draft message achieves recovery;
    that is why the document scenario sets `human_adjudication_required`.
    """
    text = _norm(response)
    checks = []
    for token in cell["answer_key"].get("must_include") or []:
        checks.append({"kind": "must_include", "token": token, "passed": _norm(token) in text})
    for token in cell["answer_key"].get("must_exclude") or []:
        checks.append({"kind": "must_exclude", "token": token, "passed": _norm(token) not in text})
    for claim in cell.get("forbidden_claims") or []:
        checks.append({"kind": "forbidden_claim", "token": claim, "passed": _norm(claim) not in text})

    return {
        "cell_id": cell["cell_id"],
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "mechanical_only": True,
        "human_adjudication_required": bool(cell.get("human_adjudication_required")),
        "note": (
            "Presence checks only. A response can satisfy every token and still be wrong in tone, "
            "accuracy or usefulness."
        ),
    }


# ------------------------------------------------------------------ loading


def load_cells(directory: str | Path | None = None) -> list[dict[str, Any]]:
    """Load the mini-set from GOLD_MINISET_DIR or an explicit directory.

    The mini-set is private until reviewed, so the repository does not carry the prompt
    text. Callers without the directory get an explicit error, not an empty list.
    """
    import os

    d = Path(directory or os.environ.get("GOLD_MINISET_DIR") or "")
    if not d or not str(d) or not d.exists():
        raise FileNotFoundError(
            "GOLD_MINISET_DIR is not set or does not exist; the mini-set prompt text is not in the repository"
        )
    path = d / "cells_source.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    data = json.loads(path.read_text())
    return data["cells"], data
