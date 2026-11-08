"""Authoring helper for seed scenarios.

One `spec()` call describes a scenario family: the invariant facts and correct
decision (shared by neutral and pressure variants), plus the three authored user
messages and the counterfactual pivot. `build_dataset` expands it into the three
concrete cases.

Keeping the invariant part in one place is the point: pressure variants cannot
drift from the neutral facts because they are generated from the same fields.
"""

from __future__ import annotations

FAMILY_IDS = {
    "f1": "F1-emotional-provocation",
    "f2": "F2-frustration-correction",
    "f3": "F3-urgency-intervention",
    "f4": "F4-ambiguous-interpersonal",
    "f5": "F5-self-referential-pressure",
    "f6": "F6-neutral-technical",
}


def spec(
    *,
    sid: str,
    family: str,
    category: str,
    subcategory: str,
    domain: str,
    task: str,
    deliverable: str,
    facts: list[tuple[str, list[str], bool]],
    decision: dict,
    urgency: dict,
    boundaries: list[str],
    must: list[str],
    must_not: list[str],
    neutral: str,
    pressure_msg: str,
    pressure: dict,
    cf_fact_index: int,
    cf_statement: str,
    cf_decision: str,
    split: str = "train",
    prior_turns: list[tuple[str, str]] | None = None,
    cf_prior_turns: list[tuple[str, str]] | None = None,
) -> dict:
    assert sid.startswith("eq2-"), sid
    assert len(facts) >= 2, sid
    assert (cf_fact_index >= 0 and cf_fact_index < len(facts)), sid
    assert facts[cf_fact_index][2] is True, f"{sid}: counterfactual must pivot on a load-bearing fact"

    return {
        "spec_id": sid,
        "family": FAMILY_IDS[family],
        "category": category,
        "subcategory": subcategory,
        "domain": domain,
        "task": task,
        "deliverable": deliverable,
        "facts": facts,
        "decision": decision,
        "urgency": urgency,
        "boundaries": boundaries,
        "must": must,
        "must_not": must_not,
        "neutral": neutral,
        "pressure_msg": pressure_msg,
        "pressure": pressure,
        "cf_fact_index": cf_fact_index,
        "cf_statement": cf_statement,
        "cf_decision": cf_decision,
        "split": split,
        "prior_turns": prior_turns or [],
        "cf_prior_turns": cf_prior_turns or [],
    }
