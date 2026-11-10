"""Evidence-sufficiency auditing.

The problem this addresses: the teacher is given the full case as structured JSON
(`facts`, `decision`, `rationale`), while the student sees only the conversation
rendered by `serialize.conversation`. A teacher target can therefore assert a premise
the student had no way to know. That rewards ungrounded certainty and confounds any
measured pressure effect with unequal task information.

What this module computes, per case variant:

  student_view        exactly what the model sees, nothing else
  generator_view      the metadata fields withheld from the student
  evidence_map        one entry per required premise: visible span, declared general
                      knowledge, or explicitly missing
  sufficiency         sufficient_lexically | undetermined | insufficient
  pressure pair       text-level quantity comparison, not metadata comparison
  counterfactual      genuine pivot | parameter-fidelity control | invalid/ambiguous

Deliberate limitation, stated once and enforced in tests: lexical absence is a
WARNING. A premise whose tokens are absent may still be paraphrase, and a premise
whose tokens are present may still be logically underdetermined. Nothing here
auto-approves a case. Every row says `requires_human_review: true` and
`approved_for_training: false`.
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

from serialize import conversation  # noqa: E402

# Fields that exist in the case but are NOT part of the student conversation.
GENERATOR_ONLY_FIELDS = [
    "facts",
    "decision",
    "urgency",
    "boundaries",
    "target_behavior",
    "deliverable_checks",
    "counterfactual",
    "pressure",
    "case_family_id",
    "category",
    "subcategory",
    "split",
    "provenance",
    "review",
    "scenario_id",
    "variant_id",
    "variant_kind",
]

HIGH_STAKES_DOMAINS = {"medicine", "law", "finance", "policy"}

DOMAIN_REVIEW_LABEL = {
    "medicine": "clinical",
    "law": "legal",
    "finance": "financial",
    "policy": "regulatory",
}

# ---------------------------------------------------------------- student view


def student_view(case: dict[str, Any]) -> dict[str, Any]:
    """The exact conversation the student is trained on.

    No facts, no decision, no rationale, no urgency metadata. If a premise is not in
    this text, the student cannot know it.
    """
    msgs = conversation(case)
    return {
        "messages": msgs,
        "text": "\n".join(m["content"] for m in msgs),
        "system": None,
    }


def generator_view(case: dict[str, Any]) -> dict[str, Any]:
    """The metadata the teacher and the evaluator see but the student does not."""
    return {
        "withheld_fields": [f for f in GENERATOR_ONLY_FIELDS if f in case],
        "facts": case.get("facts", []),
        "decision": case.get("decision", {}),
        "urgency": case.get("urgency", {}),
        "boundaries": case.get("boundaries", []),
        "deliverable_checks": case.get("deliverable_checks", []),
    }


# ---------------------------------------------------------------- quantities

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "ninety": 90, "hundred": 100,
}

UNIT_CANON = {
    "%": "%", "mi": "mi", "min": "min", "mins": "min", "minute": "min",
    "minutes": "min", "hour": "h", "hours": "h", "h": "h", "day": "day",
    "days": "day", "week": "week", "weeks": "week", "month": "month",
    "months": "month", "year": "year", "years": "year", "second": "sec",
    "seconds": "sec",
}

_UNIT_ALT = "|".join(sorted(UNIT_CANON, key=len, reverse=True))
_DIGIT_RE = re.compile(rf"\b(\d+(?:\.\d+)?)\s*({_UNIT_ALT})?\b", re.I)
_BARE_DEC_RE = re.compile(r"(?<![\d.])(\d+\.\d+)(?!\d)")
_WORD_RE = re.compile(rf"\b({'|'.join(NUMBER_WORDS)})\s+({_UNIT_ALT})\b", re.I)
_RATIO_RE = re.compile(r"\b(\d{1,3}/\d{1,3})\b")


def extract_quantities(text: str) -> set[str]:
    """Normalised quantitative tokens in a text.

    Only number+unit pairs and ratios are captured. A bare number is ignored so that
    rhetorical numbers ("asked three people") do not masquerade as evidence. This is
    a deliberately narrow extractor: missing a quantity is a false negative, which is
    the conservative direction for a warning system.
    """
    return {q for q, _ in find_quantities(text)}


def find_quantities(text: str) -> list[tuple[str, int]]:
    """Quantities with their character offsets, so a caller can look at the surrounding claim."""
    out: list[tuple[str, int]] = []
    for m in _RATIO_RE.finditer(text):
        out.append((m.group(1), m.start()))
    for m in _DIGIT_RE.finditer(text):
        num, unit = m.group(1), m.group(2)
        if unit:
            out.append((f"{num}{UNIT_CANON[unit.lower()]}", m.start()))
    for m in _WORD_RE.finditer(text):
        out.append((f"{NUMBER_WORDS[m.group(1).lower()]}{UNIT_CANON[m.group(2).lower()]}", m.start()))
    # Bare decimals are captured because figures like 4.2 and 4.7 are evidence in
    # data/finance cases, while bare integers ("asked three people") are not.
    for m in _BARE_DEC_RE.finditer(text):
        out.append((m.group(1), m.start()))
    return out


def quantity_units(quantities: set[str]) -> set[str]:
    return {q.lstrip("0123456789./") for q in quantities}


def compare_quantities(a: str, b: str, evidence_units: set[str],
                       fact_quantities: set[str] | None = None) -> dict[str, Any]:
    """Compare quantitative content of two texts.

    `evidence_units` are the units used by the case's own facts. Additions in those
    units are treated as potentially evidence-changing; additions in other units are
    treated as contextual (deadlines, waiting times) and reported as a warning only.
    """
    qa, qb = extract_quantities(a), extract_quantities(b)
    fact_q = fact_quantities or set()
    added = sorted(qb - qa)
    removed = sorted(qa - qb)
    ev_added = [q for q in added if q in fact_q or q.lstrip("0123456789./") in evidence_units]
    return {
        "quantities_a": sorted(qa),
        "quantities_b": sorted(qb),
        "added": added,
        "removed": removed,
        "evidence_relevant_added": ev_added,
        "evidence_relevant_removed": [q for q in removed
                                      if q in fact_q or q.lstrip("0123456789./") in evidence_units],
    }


# ---------------------------------------------------------------- premises


def _first_span(text: str, token: str) -> dict[str, Any] | None:
    i = text.lower().find(token.lower())
    if i < 0:
        return None
    return {"start": i, "end": i + len(token), "snippet": text[max(0, i - 40):i + len(token) + 40]}


def premise_status(fact: dict[str, Any], student_text: str) -> dict[str, Any]:
    """Token-based presence of a premise in the student-visible text.

    Status:
      visible  all declared tokens appear
      partial  some appear — usually paraphrase, but unverified
      missing  none appear
    """
    tokens = fact.get("target_key_tokens") or []
    present, absent, spans = [], [], []
    for tok in tokens:
        span = _first_span(student_text, tok)
        if span:
            present.append(tok)
            spans.append(span)
        else:
            absent.append(tok)

    if not tokens:
        status = "missing"
    elif len(present) == len(tokens):
        status = "visible"
    elif present:
        status = "partial"
    else:
        status = "missing"

    return {
        "premise_id": fact.get("fact_id"),
        "premise": fact.get("statement"),
        "required": bool(fact.get("load_bearing")),
        "tokens": tokens,
        "present_tokens": present,
        "absent_tokens": absent,
        "spans": spans,
        "status": status,
        "source": "mechanical_token_match",
    }


def build_evidence_map(case: dict[str, Any], authored: dict[str, Any] | None) -> list[dict[str, Any]]:
    """One entry per premise needed for the expected decision.

    Sources are labelled: `mechanical_token_match` for derived premises, and
    `authored_stage0_finding` for premises or general-knowledge claims recorded by
    human review. The two are never merged into a single unexplained verdict.
    """
    student_text = student_view(case)["text"]
    out = [premise_status(f, student_text) for f in case.get("facts", [])]

    for extra in (authored or {}).get("extra_premises", []):
        out.append({
            "premise_id": extra.get("premise_id", f"x{len(out)+1}"),
            "premise": extra["premise"],
            "required": extra.get("required", True),
            "tokens": [],
            "present_tokens": [],
            "absent_tokens": [],
            "spans": [],
            "status": extra["status"],
            "reason": extra.get("reason", ""),
            "source": "authored_stage0_finding",
        })

    for pid, ov in ((authored or {}).get("premise_status_overrides") or {}).items():
        for entry in out:
            if entry["premise_id"] == pid:
                entry["mechanical_status"] = entry["status"]
                entry["status"] = ov["status"]
                entry["reason"] = ov["reason"]
                entry["source"] = "authored_stage0_finding"

    for entry in out:
        if entry["status"] == "visible":
            entry["justification"] = "student_visible_span"
        elif entry["status"] == "general_knowledge":
            entry["justification"] = "declared_general_knowledge"
        elif entry["status"] == "partial":
            entry["justification"] = "partially_visible_probable_paraphrase"
        else:
            entry["justification"] = "not_in_student_view"
    return out


def sufficiency(evidence_map: list[dict[str, Any]], authored: dict[str, Any] | None) -> dict[str, Any]:
    """Conservative verdict. Never 'sufficient' in an approving sense."""
    required = [e for e in evidence_map if e.get("required")]
    missing = [e for e in required if e["status"] == "missing"]
    partial = [e for e in required if e["status"] == "partial"]
    gk = [e for e in required if e["status"] == "general_knowledge"]

    if missing:
        verdict = "insufficient"
    elif partial:
        verdict = "undetermined"
    else:
        verdict = "sufficient_lexically"

    return {
        "verdict": verdict,
        "missing_premise_ids": [e["premise_id"] for e in missing],
        "partial_premise_ids": [e["premise_id"] for e in partial],
        "general_knowledge_premise_ids": [e["premise_id"] for e in gk],
        "required_premises": len(required),
        "note": (
            "sufficient_lexically means every required premise has a token match in the "
            "student view. It does NOT mean the decision follows from those premises. "
            "No verdict here approves a case."
        ),
    }


# ---------------------------------------------------------------- counterfactual

ACTION_LEXICON = {
    "fix", "patch", "replace", "deduplicate", "rotate", "freeze", "escalate", "call",
    "leave", "evacuate", "drain", "pause", "raise", "reduce", "increase", "defer",
    "run", "proceed", "decline", "request", "ask", "verify", "confirm", "audit",
    "investigate", "attribute", "recommend", "propose", "schedule", "write", "draft",
    "give", "state", "report", "refer", "arrange", "review", "monitor",
    "restore", "restart", "notify", "contact", "test", "reproduce", "withhold",
}

# Synonyms are collapsed so that "patch the fixture" and "fix the fixture" count as the
# same action. Without this, a cosmetic verb change inflates the apparent action overlap
# difference and misclassifies a parameter-fidelity control as an ambiguous pivot.
ACTION_SYNONYMS = {
    "patch": "fix", "repair": "fix", "dedupe": "deduplicate", "lower": "reduce",
    "increase": "raise", "boost": "raise", "escalate": "escalate", "call": "call",
    "defer": "defer", "postpone": "defer", "wait": "defer", "proceed": "run",
    "execute": "run", "decline": "decline", "refuse": "decline", "verify": "verify",
    "check": "verify", "confirm": "verify", "monitor": "monitor", "watch": "monitor",
}


def action_set(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower())
    out = set()
    for w in words:
        if w in ACTION_LEXICON:
            out.add(ACTION_SYNONYMS.get(w, w))
        elif w in ACTION_SYNONYMS:
            out.add(ACTION_SYNONYMS[w])
    return out


def content_words(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "been",
        "to", "of", "in", "on", "for", "with", "that", "this", "it", "as", "at", "by",
        "from", "not", "no", "do", "does", "did", "should", "must", "will", "would",
        "can", "could", "may", "might", "have", "has", "had", "there", "their", "its",
        "which", "who", "what", "when", "where", "why", "how", "than", "then", "so",
    }
    return {w for w in re.findall(r"[a-z0-9.]+", text.lower()) if w not in stop and len(w) > 1}


def _normalise_decision(text: str) -> str:
    """Strip quantities and punctuation so two decisions can be compared modulo numbers."""
    t = text.lower()
    for q in extract_quantities(text):
        t = t.replace(q, "#")
    t = re.sub(r"\d+(?:\.\d+)?", "#", t)
    t = re.sub(r"[^a-z# ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def multi_fact_reference(case: dict[str, Any], original_statement: str) -> list[str]:
    """Facts other than the declared one whose tokens newly appear in the changed statement.

    The counterfactual contract is exactly one changed fact. If the new statement also
    introduces the vocabulary of another fact, more than one premise moved, and the
    intervention is not identifiable.
    """
    changed = case["counterfactual"]["changed_fact_statement"]
    cid = case["counterfactual"]["changed_fact_id"]
    out = []
    for f in case["facts"]:
        if f["fact_id"] == cid:
            continue
        for tok in f.get("target_key_tokens") or []:
            if len(tok) < 3:
                continue
            if tok.lower() in changed.lower() and tok.lower() not in original_statement.lower():
                out.append(f["fact_id"])
                break
    return out


def classify_counterfactual(case: dict[str, Any], neutral: dict[str, Any], authored: dict[str, Any] | None) -> dict[str, Any]:
    """Classify what the counterfactual is designed to change.

      parameter_fidelity_control  same action, different parameters. Tests numeric reading,
                                  NOT decision revision.
      genuine_decision_pivot      required action changes while one premise changes.
      invalid_or_ambiguous        several premises move, action identity is indeterminate,
                                  or the case's arithmetic contradicts its conclusion.

    This classification is provisional (`mechanical_class`). An authored override may
    supersede it; both are reported.
    """
    basis: list[str] = []
    cf_decision = case["counterfactual"].get("decision_after_change") or case["decision"]["expected_decision"]
    n_decision = neutral["decision"]["expected_decision"]

    type_changed = case["decision"]["decision_type"] != neutral["decision"]["decision_type"]
    acts_cf, acts_n = action_set(cf_decision), action_set(n_decision)
    jacc = (len(acts_cf & acts_n) / len(acts_cf | acts_n)) if (acts_cf | acts_n) else 0.0

    original_statement = next(
        (f["statement"] for f in neutral["facts"] if f["fact_id"] == case["counterfactual"]["changed_fact_id"]),
        "",
    )
    changed_statement = case["counterfactual"]["changed_fact_statement"]
    other_facts_moved = multi_fact_reference(case, original_statement)

    numbers_equal = _normalise_decision(cf_decision) == _normalise_decision(n_decision)

    if type_changed:
        cls = "genuine_decision_pivot"
        basis.append("decision_type_changed")
    elif numbers_equal:
        cls = "parameter_fidelity_control"
        basis.append("decisions_identical_after_stripping_quantities")
    elif not (acts_cf or acts_n):
        cls = "invalid_or_ambiguous"
        basis.append("no_action_verbs_indeterminate")
    elif other_facts_moved and jacc < 0.75:
        cls = "invalid_or_ambiguous"
        basis.append(f"multiple_facts_moved:{','.join(sorted(set(other_facts_moved)))};action_overlap_{jacc:.2f}")
    elif jacc >= 0.75:
        cls = "parameter_fidelity_control"
        basis.append(f"action_set_overlap_{jacc:.2f}")
    elif jacc <= 0.2:
        cls = "genuine_decision_pivot"
        basis.append(f"action_set_overlap_{jacc:.2f}")
    else:
        cls = "invalid_or_ambiguous"
        basis.append(f"action_set_overlap_{jacc:.2f}_indeterminate")

    mechanical_class = cls
    defects: list[str] = []

    # The student must see the new value, and must not still see the old one.
    student_text = student_view(case)["text"]
    q_student = extract_quantities(student_text)
    q_changed = extract_quantities(changed_statement)
    q_original = extract_quantities(original_statement)
    stale = sorted((q_student & q_original) - q_changed)
    if q_changed and stale:
        defects.append(f"stale_original_quantities:{','.join(stale)}")

    # The expected decision must not cite the pre-change value either. In f6-001 the limit
    # becomes 256Mi but the target still says "raise the limit to at least 512Mi".
    stale_decision = sorted(q for q in extract_quantities(cf_decision)
                            if q in q_original and q not in q_changed)
    if q_changed and stale_decision:
        defects.append(f"decision_cites_pre_change_quantities:{','.join(stale_decision)}")

    tokens = next(
        (f["target_key_tokens"] for f in case["facts"] if f["fact_id"] == case["counterfactual"]["changed_fact_id"]),
        [],
    )
    if q_changed:
        visible = bool(q_changed & q_student)
    else:
        cw = content_words(changed_statement)
        hit = sum(1 for w in cw if w in student_text.lower())
        visible = bool(cw) and hit / len(cw) >= 0.6
    if not visible:
        defects.append("changed_premise_not_visible_to_student")

    override = (authored or {}).get("cf_class_override")
    if override:
        cls = override["class"]
        basis.append(f"authored_override:{override['reason']}")

    return {
        "class": cls,
        "mechanical_class": mechanical_class,
        "overridden": bool(override),
        "basis": basis,
        "action_overlap": round(jacc, 2),
        "decision_identical_modulo_quantities": numbers_equal,
        "other_facts_moved": sorted(set(other_facts_moved)),
        "rendering_defects": defects,
        "estimand": (authored or {}).get("cf_estimand") or (
            "numeric fidelity only; the required action does not change"
            if cls == "parameter_fidelity_control"
            else "decision revision under one changed premise"
            if cls == "genuine_decision_pivot"
            else "not identifiable"
        ),
        "changed_fact_id": case["counterfactual"]["changed_fact_id"],
        "changed_statement": changed_statement,
        "original_statement": original_statement,
    }


def case_checks(case: dict[str, Any]) -> list[dict[str, str]]:
    """Case-internal consistency checks that do not depend on the counterfactual.

    These catch two defect classes the token screen misses:
      * the expected decision cites a quantity that appears in no fact and nowhere in
        the conversation (an unsourced figure in a confident answer);
      * two facts in one case assert different quantities for the same concept.

    Both are warnings, not proofs. A quantity may legitimately be derived arithmetic
    (for example a total), so a human must confirm.
    """
    out = []
    student_text = student_view(case)["text"]
    fact_text = " ".join(f["statement"] for f in case["facts"])
    visible = extract_quantities(fact_text) | extract_quantities(student_text)
    decision_q = extract_quantities(case["decision"]["expected_decision"])

    unsourced = sorted(q for q in decision_q if q not in visible)
    if unsourced:
        out.append({
            "code": "X_decision_quantity_unsourced",
            "detail": f"decision cites {','.join(unsourced)} which no fact or prompt states",
            "severity": "warning",
        })

    CONCEPTS = ("peak", "limit", "pressure", "lactate", "churn", "rows", "row",
                "savings", "budget", "p-value", "temperature", "volume", "lag")
    pairs = []
    for c in CONCEPTS:
        holders = [(f["fact_id"], extract_quantities(f["statement"])) for f in case["facts"]
                   if c in f["statement"].lower()]
        for i in range(len(holders)):
            for j in range(i + 1, len(holders)):
                qa, qb = holders[i][1], holders[j][1]
                if qa and qb and not (qa & qb):
                    pairs.append(f"{c}:{holders[i][0]}/{holders[j][0]}")
    if pairs:
        out.append({
            "code": "X_fact_quantity_conflict",
            "detail": ";".join(sorted(set(pairs))),
            "severity": "warning",
        })
    return out


# ---------------------------------------------------------------- numeric claims


def evaluate_numeric_claims(claims: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Evaluate declared arithmetic claims about a case.

    Some case defects are arithmetic, not lexical: a rota that covers 20 of 168 hours,
    or a 40-minute operation inside a 120-minute window described as overlapping it.
    Those cannot be found by token matching, so they are declared and computed here.
    """
    out = []
    for c in claims or []:
        kind = c["kind"]
        expect = c.get("expect")
        r: dict[str, Any] = {"kind": kind, "note": c.get("note", ""), "asserted": c.get("asserted", ""),
                            "expect": expect, "computed": None, "holds": None}

        if kind == "coverage_gap":
            gap = c["required_per_week"] - c["provided_per_week"]
            r.update({
                "required_per_week": c["required_per_week"],
                "provided_per_week": c["provided_per_week"],
                "gap_hours_per_week": gap,
                "computed": "covered" if gap <= 0 else "gap",
            })
        elif kind == "window_fits":
            fits = c["operation_minutes"] <= c["window_minutes"]
            r.update({
                "operation_minutes": c["operation_minutes"],
                "window_minutes": c["window_minutes"],
                "fits": fits,
                "computed": "fits" if fits else "overlaps",
            })
        elif kind == "threshold_exceeded":
            exceeded = c["peak"] > c["limit"]
            r.update({"limit": c["limit"], "peak": c["peak"], "exceeded": exceeded,
                      "computed": "exceeded" if exceeded else "within"})
        elif kind == "delta":
            delta = round(c["after"] - c["before"], 4)
            r.update({"before": c["before"], "after": c["after"], "delta": delta, "computed": delta})
        else:
            r["note"] = f"unknown claim kind {kind}"

        # `holds` = the arithmetic agrees with what the case asserts.
        r["holds"] = (r["computed"] == expect) if r["computed"] is not None and expect is not None else None
        r["contradicts_case"] = (r["holds"] is False)
        out.append(r)
    return out


# ---------------------------------------------------------------- assembly


def high_stakes(case: dict[str, Any]) -> dict[str, Any]:
    domain = case["task"]["domain"]
    d_type = case["decision"]["decision_type"]
    required = domain in HIGH_STAKES_DOMAINS or d_type in ("escalate_urgently", "decline_scope")
    if d_type == "decline_scope":
        review_type = "boundary"
    elif domain in HIGH_STAKES_DOMAINS:
        review_type = DOMAIN_REVIEW_LABEL[domain]
    elif d_type == "escalate_urgently":
        review_type = "safety"
    else:
        review_type = None
    return {
        "required": required,
        "domain": domain,
        "review_type": review_type,
        "reason": (
            f"domain={domain}, decision_type={d_type}: domain-specific assertions are not "
            "established by the case author or the lexical validator"
        ) if required else "",
    }


def audit_case(case: dict[str, Any], neutral: dict[str, Any] | None, authored: dict[str, Any] | None) -> dict[str, Any]:
    sv = student_view(case)
    ev = build_evidence_map(case, authored)
    suf = sufficiency(ev, authored)
    hs = high_stakes(case)
    if (authored or {}).get("domain_review"):
        hs = {
            "required": True,
            "domain": case["task"]["domain"],
            "review_type": authored["domain_review"],
            "reason": authored.get("notes", "")[:160],
            "forced_by": "authored_stage0_finding",
        }
    numbers = evaluate_numeric_claims((authored or {}).get("numeric_claims"))

    flags: list[dict[str, str]] = []
    if suf["missing_premise_ids"]:
        flags.append({"code": "A_premise_missing", "detail": ",".join(suf["missing_premise_ids"])})
    if suf["partial_premise_ids"]:
        flags.append({"code": "A_premise_partial", "detail": ",".join(suf["partial_premise_ids"])})
    for n in numbers:
        if n["contradicts_case"]:
            flags.append({"code": "N_numeric_contradiction", "detail": n["kind"]})
    if hs["required"]:
        flags.append({"code": "D_domain_review_required", "detail": hs["review_type"] or "domain"})

    cf = None
    if case["variant_kind"] == "counterfactual" and neutral is not None:
        cf = classify_counterfactual(case, neutral, authored)
        flags.append({"code": f"C_cf_{cf['class']}", "detail": ";".join(cf["basis"])})
        if cf["overridden"]:
            flags.append({"code": "C_mechanical_disagrees", "detail": cf["mechanical_class"]})
        for d in cf["rendering_defects"]:
            flags.append({"code": "X_cf_rendering_defect", "detail": d})

    for chk in case_checks(case):
        flags.append({"code": chk["code"], "detail": chk["detail"]})


    return {
        "variant_id": case["variant_id"],
        "scenario_id": case["scenario_id"],
        "variant_kind": case["variant_kind"],
        "dataset_version": case["dataset_version"],
        "split": case["split"],
        "student_view": sv,
        "generator_view": generator_view(case),
        "evidence_map": ev,
        "sufficiency": suf,
        "numeric_claims": numbers,
        "counterfactual": cf,
        "case_checks": case_checks(case),
        "high_stakes": hs,
        "mechanical_flags": flags,
        "authored_findings": {
            "flags": (authored or {}).get("flags", []),
            "verdict": (authored or {}).get("verdict"),
            "notes": (authored or {}).get("notes", ""),
            "proposed_revision": (authored or {}).get("proposed_revision", ""),
            "source": "authored_stage0_finding" if authored else None,
        },
        "requires_human_review": True,
        "approved_for_training": False,
    }


def audit_pairs(cases: list[dict[str, Any]], authored: dict[str, dict]) -> dict[str, Any]:
    """Text-level comparison of neutral vs pressure for each scenario.

    Never returns an equivalence claim. It returns the quantitative difference and
    `semantic_equiv: unverified`, because only a human can judge whether a changed
    deadline or a new social claim changes the required action.
    """
    by: dict[str, dict[str, dict]] = {}
    for c in cases:
        by.setdefault(c["scenario_id"], {})[c["variant_kind"]] = c

    out = []
    for sid, tri in sorted(by.items()):
        if "neutral" not in tri or "pressure" not in tri:
            continue
        n, p = tri["neutral"], tri["pressure"]
        evidence_units: set[str] = set()
        fact_quantities: set[str] = set()
        for f in n["facts"]:
            q = extract_quantities(f["statement"])
            fact_quantities |= q
            evidence_units |= quantity_units(q)

        diff = compare_quantities(
            student_view(n)["text"], student_view(p)["text"], evidence_units, fact_quantities
        )
        warnings = []
        if diff["evidence_relevant_added"]:
            warnings.append(f"pressure adds evidence-relevant quantities: {diff['evidence_relevant_added']}")
        if diff["evidence_relevant_removed"]:
            warnings.append(f"pressure removes evidence-relevant quantities: {diff['evidence_relevant_removed']}")
        if diff["added"]:
            warnings.append(f"pressure adds quantities (may be contextual): {diff['added']}")
        if diff["removed"]:
            warnings.append(f"pressure removes quantities: {diff['removed']}")

        auth = authored.get(sid, {})
        out.append({
            "scenario_id": sid,
            "semantic_equiv": "unverified",
            "quantity_diff": diff,
            "warnings": warnings,
            "metadata_equality": {
                "facts_identical": [f["statement"] for f in n["facts"]] == [f["statement"] for f in p["facts"]],
                "decision_identical": n["decision"]["expected_decision"] == p["decision"]["expected_decision"],
            },
            "authored_flags": auth.get("flags", []),
            "authored_pressure_evidence_change": auth.get("pressure_evidence_change"),
            "note": (
                "metadata_equality is what validate_triple already checks. It is not "
                "semantic equivalence; the quantity diff and the authored flag are the "
                "text-level evidence, and a human must still judge the case."
            ),
        })
    return {"pairs": out, "count": len(out)}


# ---------------------------------------------------------------- entry point


def main() -> int:
    cases_path = ROOT / "data" / "validated" / "cases.jsonl"
    if not cases_path.exists():
        raise SystemExit("run src/build_dataset.py first")
    sys.path.insert(0, str(ROOT / "scenarios"))
    from numeric_claims import NUMERIC_CLAIMS
    from stage0_findings import FINDINGS

    cases = [json.loads(l) for l in cases_path.read_text().splitlines() if l.strip()]
    by: dict[str, dict[str, dict]] = {}
    for c in cases:
        by.setdefault(c["scenario_id"], {})[c["variant_kind"]] = c

    rows = []
    for c in cases:
        sid = c["scenario_id"]
        auth = dict(FINDINGS.get(sid, {}))
        auth["numeric_claims"] = NUMERIC_CLAIMS.get(sid, [])
        rows.append(audit_case(c, by[sid].get("neutral"), auth))

    print(json.dumps({
        "rows": len(rows),
        "scenarios": len(by),
        "insufficient": sum(1 for r in rows if r["sufficiency"]["verdict"] == "insufficient"),
        "undetermined": sum(1 for r in rows if r["sufficiency"]["verdict"] == "undetermined"),
        "sufficient_lexically": sum(1 for r in rows if r["sufficiency"]["verdict"] == "sufficient_lexically"),
        "approved_for_training": sum(1 for r in rows if r["approved_for_training"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
