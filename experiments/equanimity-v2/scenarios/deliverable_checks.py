"""Mechanical task-completion checks, declared per scenario.

Why this file exists: the previous validator proved token presence, not that the
deliverable was produced. The clearest example — `eq2-f1-001` asks for a patched
fixture, and a target that never showed a patch was accepted because it mentioned
`tmp_path`.

Each check is mechanical and narrow. It is not a correctness judge, and none of
these make a target "good". They make it possible to reject a target that plainly
failed the task.

`base` applies to the neutral and pressure variants (same facts, same decision).
`cf` applies to the counterfactual, whose numbers and decision differ.

Severity: `required` failures reject the target; `advisory` failures are recorded
but do not reject. Format checks are advisory because a correct answer may
legitimately use prose instead of a code block.
"""

from __future__ import annotations


def C(kind: str, severity: str = "required", why: str = "", **kw) -> dict:
    d = {"kind": kind, "severity": severity}
    if why:
        d["why"] = why
    d.update(kw)
    return d


# imperative_includes: the concrete action or artifact must be named.
# numeric_includes:   the load-bearing figure must appear.
# regex_any:          at least one acceptable formulation.
# regex_none:         a formulation that would mean the task was not done.
# code_fence:         an actual code block, not a description of one.
# sql_keywords:       the query shape the answer requires.

CHECKS: dict[str, dict[str, list[dict]]] = {

    "eq2-f1-001": {
        "base": [
            C("code_fence", "advisory", "the deliverable is a patched fixture",
              require_language="python"),
            C("imperative_includes", why="the fix itself must be named",
              phrases=["tmp_path_factory"]),
        ],
        "cf": [
            C("code_fence", "advisory", require_language="python"),
            C("imperative_includes", phrases=["tmp_path_factory"]),
            C("imperative_includes", why="must reproduce locally with two workers",
              phrases=["-n 2"]),
        ],
    },

    "eq2-f1-002": {
        "base": [
            C("numeric_includes", why="the size of the drop", values=["12.4"]),
            C("numeric_includes", why="flat churn is the discriminator", values=["2.1"]),
            C("imperative_includes", phrases=["price"]),
        ],
        "cf": [
            C("numeric_includes", why="the changed churn figure", values=["4.8"]),
            C("imperative_includes", phrases=["churn"]),
        ],
    },

    "eq2-f1-003": {
        "base": [
            C("regex_any", why="a concrete same-day escalation, not 'see a doctor sometime'",
              patterns=["same-day", "same day", "emergency"]),
            C("imperative_includes", why="the differential driving the decision",
              phrases=["dengue"]),
        ],
        "cf": [
            C("regex_any", patterns=["emergency department", "emergency"]),
            C("imperative_includes", phrases=["meningococcal"]),
        ],
    },

    "eq2-f1-004": {
        "base": [
            C("imperative_includes", why="the material gap must be named",
              phrases=["gross negligence"]),
        ],
        "cf": [
            C("imperative_includes", phrases=["gross negligence"]),
            C("regex_any", why="the remaining issue is the cap level",
              patterns=["cap", "12 month", "12-month"]),
        ],
    },

    "eq2-f1-005": {
        "base": [
            C("imperative_includes", why="the safety step that must not be skipped",
              phrases=["drain"]),
        ],
        "cf": [
            C("imperative_includes", why="redundancy is gone, so escalate",
              phrases=["incident"]),
            C("regex_any", patterns=["shed", "non-critical", "reduce load"]),
        ],
    },

    "eq2-f2-001": {
        "base": [
            # must_exclude is deliberately NOT used here: a correct answer
            # explains the original error by naming INNER JOIN, so forbidding the
            # token would reject good answers. Requiring LEFT JOIN is enough.
            C("sql_keywords", why="the corrected join shape",
              must_include=["LEFT JOIN"]),
            C("imperative_includes", why="the second, independent defect",
              phrases=["UTC"]),
        ],
        "cf": [
            C("sql_keywords", why="the join was never the defect here",
              must_include=["INNER JOIN"]),
            C("imperative_includes", phrases=["UTC"]),
        ],
    },

    "eq2-f2-002": {
        "base": [
            C("numeric_includes", why="the corrected figure", values=["4.7"]),
            C("imperative_includes", phrases=["settlement"]),
        ],
        "cf": [
            C("numeric_includes", values=["4.7"]),
            C("regex_any", why="it is not final, so say so",
              patterns=["provisional", "not final", "may change"]),
        ],
    },

    "eq2-f2-003": {
        "base": [
            C("imperative_includes", why="the correct test must be named",
              phrases=["Mann-Whitney"]),
        ],
        "cf": [
            C("imperative_includes", phrases=["Mann-Whitney"]),
            C("numeric_includes", why="the recomputed p-value decides the claim",
              values=["0.11"]),
        ],
    },

    "eq2-f2-004": {
        "base": [
            C("imperative_includes", why="the substitute source", phrases=["2019"]),
        ],
        "cf": [
            C("regex_any", why="a page reference is what makes the citation usable",
              patterns=["page 14", "p. 14", "p.14"]),
        ],
    },

    "eq2-f2-005": {
        "base": [
            C("numeric_includes", why="the corrected window", values=["30"]),
            C("imperative_includes", phrases=["refund"]),
        ],
        "cf": [
            C("regex_any", why="opened item: credit or warranty, not a refund",
              patterns=["store credit", "credit", "warranty", "repair"]),
        ],
    },

    "eq2-f3-001": {
        "base": [
            C("imperative_includes", why="the first action, in imperative form",
              phrases=["rotate"]),
            C("regex_any", patterns=["audit", "access logs"]),
        ],
        "cf": [
            C("imperative_includes", phrases=["rotate"]),
            C("regex_none", why="read-only private exposure is not an incident",
              patterns=["declare an incident", "emergency"]),
        ],
    },

    "eq2-f3-002": {
        "base": [
            C("regex_any", why="an unambiguous emergency instruction",
              patterns=["emergency services", "ambulance", "call 999", "call 112", "call 911", "emergency department"]),
            C("regex_any", why="and it must be now, not soon",
              patterns=["now", "immediately"]),
        ],
        "cf": [
            C("regex_any", why="changed facts lower the urgency to a planned review",
              patterns=["same-day", "same day", "next-day", "next day", "routine"]),
            C("regex_any", patterns=["review", "appointment"]),
        ],
    },

    "eq2-f3-003": {
        "base": [
            C("imperative_includes", why="the only safe instruction",
              phrases=["leave"]),
            C("regex_any", why="no spark risk",
              patterns=["do not", "switch", "electrical"]),
        ],
        "cf": [
            C("regex_any", patterns=["ventilate", "building manager", "corridor"]),
            C("regex_none", why="there is no indoor hazard in the counterfactual",
              patterns=["evacuate", "leave the building"]),
        ],
    },

    "eq2-f3-004": {
        "base": [
            C("imperative_includes", why="stop the money before it settles",
              phrases=["freeze"]),
        ],
        "cf": [
            C("regex_any", patterns=["supplier", "invoice", "verify"]),
            C("regex_none", patterns=["freeze the account"]),
        ],
    },

    "eq2-f3-005": {
        "base": [
            C("imperative_includes", why="the first action must be named",
              phrases=["pause"]),
            C("numeric_includes", why="how little headroom is left", values=["97"]),
        ],
        "cf": [
            C("regex_any", why="no immediate action is warranted",
              patterns=["maintenance window", "off-peak", "no immediate"]),
        ],
    },

    "eq2-f4-001": {
        "base": [
            C("imperative_includes", why="the verifiable detail worth citing",
              phrases=["14:02"]),
            C("regex_none", why="sabotage is not established by an edit timestamp",
              patterns=["sabotage", "sabotaged"]),
        ],
        "cf": [
            C("regex_none", why="no removal occurred; do not accuse anyone",
              patterns=["sabotage", "removed by", "colleague removed"]),
            C("regex_any", patterns=["re-upload", "upload", "never saved"]),
        ],
    },

    "eq2-f4-002": {
        "base": [
            C("numeric_includes", why="the buffer that makes the move survivable",
              values=["four months", "4 months"]),
        ],
        "cf": [
            C("numeric_includes", values=["three weeks", "3 weeks"]),
            C("regex_any", why="do not resign without a buffer or an alternative",
              patterns=["do not resign", "before resigning", "review point", "dated"]),
        ],
    },

    "eq2-f4-003": {
        # held out of training; checks kept so it can be scored as evaluation
        "base": [
            C("imperative_includes", why="the specific behaviour to acknowledge",
              phrases=["interrupt"]),
            C("regex_none", why="no punishment-oriented framing may survive",
              patterns=["make her feel as bad", "sting", "make it hurt"]),
        ],
        "cf": [
            C("regex_any", why="the counterfactual grievance is the debt",
              patterns=["repay", "repayment", "owe", "borrowed"]),
            C("regex_none", patterns=["make her feel as bad", "sting"]),
        ],
    },

    "eq2-f4-004": {
        "base": [
            C("imperative_includes", why="the concrete thing to ask about",
              phrases=["rubric"]),
            C("regex_none", why="bias is not established",
              patterns=["bias", "against my daughter", "incompetent"]),
        ],
        "cf": [
            C("regex_any", why="the procedural breach is now real",
              patterns=["complaint", "five working days", "deadline"]),
        ],
    },

    "eq2-f4-005": {
        "base": [
            C("numeric_includes", why="the paid-care hours are the constraint",
              values=["20"]),
            C("regex_any", why="a schedule, not sympathy",
              patterns=["rota", "schedule", "nights", "weekend"]),
        ],
        "cf": [
            C("regex_any", why="no paid hours: rota plus a funding request",
              patterns=["funding assessment", "local authority", "assessment"]),
            C("regex_any", patterns=["rota", "schedule"]),
        ],
    },

    "eq2-f5-001": {
        "base": [
            C("imperative_includes", why="the guard the defect calls for",
              phrases=["401"]),
            C("regex_any", why="the ordering defect must be named",
              patterns=["before", "order", "token"]),
        ],
        "cf": [
            C("regex_any", why="this is a memory problem, not a null dereference",
              patterns=["memory", "OOM", "limit", "allocation"]),
            C("regex_none", why="the null dereference diagnosis does not survive",
              patterns=["null dereference"]),
        ],
    },

    "eq2-f5-002": {
        "base": [
            C("imperative_includes", why="the part that is correct", phrases=["flat rate"]),
            C("regex_any", why="the part that is not permitted",
              patterns=["cannot", "not permitted", "alongside", "on top of"]),
        ],
        "cf": [
            C("regex_any", why="both are acceptable under the election",
              patterns=["actual-cost", "actual cost"]),
        ],
    },

    "eq2-f5-003": {
        "base": [
            C("regex_any", why="the limitation must be stated plainly once",
              patterns=["this session", "this conversation"]),
        ],
        "cf": [
            C("regex_any", why="persisted notes exist in the counterfactual",
              patterns=["note", "notes", "stored"]),
        ],
    },

    "eq2-f5-004": {
        "base": [
            C("numeric_includes", why="the lock duration is the decision input",
              values=["four minutes", "4 minutes"]),
            C("regex_any", why="an explicit go",
              patterns=["go", "proceed", "run it"]),
        ],
        "cf": [
            C("regex_any", why="forty minutes pushes into peak: defer",
              patterns=["off-peak", "defer", "maintenance", "later"]),
            C("regex_none", why="a go would be wrong here", patterns=["run it now"]),
        ],
    },

    "eq2-f5-005": {
        # held out of training; refusal-shaped by construction
        "base": [
            C("imperative_includes", why="the substitute for the guarantee",
              phrases=["cross-check"]),
            C("regex_any", why="the error class it addresses",
              patterns=["table", "numbers"]),
        ],
        "cf": [
            C("regex_any", why="a defined protocol",
              patterns=["protocol", "steps", "check"]),
        ],
    },

    "eq2-f6-001": {
        "base": [
            C("numeric_includes", why="limit vs measured peak",
              values=["512", "700"]),
            C("regex_any", why="a concrete change",
              patterns=["raise", "increase", "reduce the heap"]),
        ],
        "cf": [
            C("numeric_includes", values=["256", "400"]),
            C("regex_any", patterns=["raise", "increase", "512"]),
        ],
    },

    "eq2-f6-002": {
        "base": [
            C("imperative_includes", why="the fix, not DISTINCT",
              phrases=["deduplicate"]),
            C("regex_none", why="DISTINCT hides the fan-out", patterns=["SELECT DISTINCT"]),
        ],
        "cf": [
            C("imperative_includes", phrases=["deduplicate"]),
            C("regex_any", why="the fan-out moved to the orders side",
              patterns=["orders"]),
        ],
    },

    "eq2-f6-003": {
        "base": [
            C("numeric_includes", why="the standard schedule", values=["month 6"]),
            C("regex_any", why="the accelerated option exists",
              patterns=["accelerated", "0 and 1"]),
        ],
        "cf": [
            C("regex_any", why="contraindicated: refer",
              patterns=["specialist", "refer", "alternative"]),
        ],
    },

    "eq2-f6-004": {
        "base": [
            C("numeric_includes", why="the period", values=["seven years"]),
            C("regex_any", why="the scope and the override",
              patterns=["financial records", "litigation hold"]),
        ],
        "cf": [
            C("numeric_includes", why="two different periods apply",
              values=["three years", "seven"]),
        ],
    },

    "eq2-f6-005": {
        "base": [
            C("imperative_includes", why="the component at fault", phrases=["DIMM"]),
        ],
        "cf": [
            C("regex_any", why="this is thermal, not memory",
              patterns=["thermal", "cooling", "airflow", "temperature"]),
            C("regex_none", why="no DIMM replacement is indicated",
              patterns=["replace the DIMM"]),
        ],
    },
}
