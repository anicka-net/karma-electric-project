"""Validators.

Two independent jobs, kept separate on purpose:

  validate_case(case)   -> is the *semantic* case internally coherent?
  validate_target(case, text, condition) -> is this *student target* acceptable?

A case can be valid while every candidate target for it is garbage. Conflating
the two is how you end up scaling on rejected rows, which is exactly the failure
mode observed in the Arete audit (accepted rows averaging 2.48/5 accuracy).

Every check returns a structured result so failures are auditable and never
silently dropped. Rejected rows are written out, not deleted.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from typing import Any

from serialize import (
    ACKNOWLEDGEMENT_PATTERNS,
    CONDITIONS,
    LENGTH_BAND,
    REACTIVE_PATTERNS,
    find_reasoning_markers,
    find_tokens,
)

# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------


@dataclass
class CheckResult:
    check_id: str
    result: str  # pass | fail | skip
    detail: str = ""


@dataclass
class ValidationOutcome:
    subject_id: str
    ok: bool
    checks: list[CheckResult]
    rejection_reasons: list[dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "ok": self.ok,
            "checks": [asdict(c) for c in self.checks],
            "rejection_reasons": self.rejection_reasons,
        }


class Collector:
    def __init__(self, subject_id: str):
        self.subject_id = subject_id
        self.checks: list[CheckResult] = []
        self.reasons: list[dict[str, str]] = []

    def check(self, check_id: str, passed: bool, detail: str = "", code: str | None = None) -> bool:
        self.checks.append(CheckResult(check_id, "pass" if passed else "fail", detail))
        if not passed and code:
            self.reasons.append({"code": code, "detail": f"{check_id}: {detail}"[:400]})
        return passed

    def skip(self, check_id: str, detail: str) -> None:
        self.checks.append(CheckResult(check_id, "skip", detail))

    def outcome(self) -> ValidationOutcome:
        return ValidationOutcome(
            subject_id=self.subject_id,
            ok=all(c.result != "fail" for c in self.checks),
            checks=self.checks,
            rejection_reasons=self.reasons,
        )


# --------------------------------------------------------------------------
# Canonical hashing
# --------------------------------------------------------------------------


def canonical_content_sha256(case: dict[str, Any]) -> str:
    """SHA-256 over the canonical semantic payload.

    Two fields are normalised away, because neither is content:

      provenance.content_sha256  - would be self-referential
      review.automatic           - validation output, produced *from* the content

    Without the second exclusion, running the validator changes the hash of every
    row it just validated and the dataset fails its own integrity check.
    """
    clone = json.loads(json.dumps(case))
    prov = clone.get("provenance") or {}
    prov["content_sha256"] = ""
    clone["provenance"] = prov
    if "review" in clone:
        clone["review"]["automatic"] = {"status": "not_run", "checks": []}
    blob = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Schema validation
# --------------------------------------------------------------------------


def _load_schema() -> dict[str, Any]:
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "schema" / "semantic_case.v1.schema.json"
    return json.loads(p.read_text())


def validate_case(case: dict[str, Any], schema: dict[str, Any] | None = None) -> ValidationOutcome:
    import jsonschema

    c = Collector(case.get("variant_id") or case.get("scenario_id") or "unknown")
    schema = schema or _load_schema()

    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(case), key=lambda e: list(e.path))
    c.check("V01_schema", not errs, "; ".join(
        f"{'/'.join(str(p) for p in e.path)}: {e.message}"[:220] for e in errs[:4]
    ), code="schema_invalid")

    if not errs:
        _check_tokens(c, case)
        _check_facts(c, case)
        _check_counterfactual(c, case)
        _check_pressure_invariance(c, case)
        _check_metadata(c, case)
        _check_hash(c, case)

    return c.outcome()


def _iter_text(case: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = [("user_message", case["context"]["user_message"])]
    for i, t in enumerate(case["context"]["prior_turns"]):
        out.append((f"prior_turns[{i}].content", t["content"]))
    for key in ("task", "decision", "target_behavior", "counterfactual"):
        pass
    out.append(("task.legitimate_task", case["task"]["legitimate_task"]))
    out.append(("decision.expected_decision", case["decision"]["expected_decision"]))
    out.append(("decision.rationale", case["decision"]["rationale"]))
    for i, f in enumerate(case["facts"]):
        out.append((f"facts[{i}].statement", f["statement"]))
    cf = case["counterfactual"]
    out.append(("counterfactual.changed_fact_statement", cf["changed_fact_statement"]))
    out.append(("counterfactual.decision_after_change", cf["decision_after_change"]))
    return out


def _check_tokens(c: Collector, case: dict[str, Any]) -> None:
    hits: list[str] = []
    for field, text in _iter_text(case):
        found = find_tokens(text)
        if found:
            hits.append(f"{field}: {found}")
    c.check("V02_no_template_tokens", not hits, "; ".join(hits)[:300], code="schema_invalid")

    rh: list[str] = []
    for field, text in _iter_text(case):
        found = find_reasoning_markers(text)
        if found:
            rh.append(f"{field}: {found}")
    c.check("V03_no_reasoning_markers", not rh, "; ".join(rh)[:300], code="reasoning_contamination")


def _check_facts(c: Collector, case: dict[str, Any]) -> None:
    ids = [f["fact_id"] for f in case["facts"]]
    c.check("V04_unique_fact_ids", len(ids) == len(set(ids)), f"ids={ids}", code="schema_invalid")

    expected = [f"f{i+1}" for i in range(len(ids))]
    c.check("V05_sequential_fact_ids", ids == expected, f"ids={ids}", code="schema_invalid")

    stmts = [f["statement"].strip().lower() for f in case["facts"]]
    c.check("V06_distinct_fact_statements", len(stmts) == len(set(stmts)), "duplicate fact statement", code="duplicate_exact")

    no_tokens = [f["fact_id"] for f in case["facts"] if not f.get("target_key_tokens")]
    c.check("V07_facts_have_key_tokens", not no_tokens, f"missing tokens: {no_tokens}", code="schema_invalid")


def _check_counterfactual(c: Collector, case: dict[str, Any]) -> None:
    cf = case["counterfactual"]
    kind = case["variant_kind"]

    if kind != "counterfactual":
        c.check("V08_counterfactual_absent", cf["decision_differs"] is False,
                "non-counterfactual variant must declare decision_differs=false", code="schema_invalid")
        return

    fact_ids = {f["fact_id"] for f in case["facts"]}
    c.check("V09_changed_fact_exists", cf["changed_fact_id"] in fact_ids,
            f"{cf['changed_fact_id']} not in {sorted(fact_ids)}", code="counterfactual_fabricated")

    changed = next((f for f in case["facts"] if f["fact_id"] == cf["changed_fact_id"]), None)
    if changed is not None:
        c.check("V10_changed_fact_is_load_bearing", changed["load_bearing"] is True,
                "counterfactual must pivot on a load-bearing fact", code="counterfactual_no_decision_change")

    # V11 and V12 compare a counterfactual against its neutral sibling, which a
    # single case cannot supply. They live in validate_triple() instead of being
    # faked here with a vacuous self-comparison.
    c.skip("V11_changed_statement_actually_differs", "cross-variant: see validate_triple")
    c.skip("V12_decision_actually_changes", "cross-variant: see validate_triple")


def _check_pressure_invariance(c: Collector, case: dict[str, Any]) -> None:
    """Under pressure, facts and the correct decision must NOT change.

    This is the load-bearing property of the whole dataset. If a 'pressure'
    variant quietly changes what is true, the triple teaches emotional
    reactivity instead of measured invariance.
    """
    kind = case["variant_kind"]
    p = case["pressure"]

    if kind == "neutral":
        c.check("V13_neutral_has_no_pressure",
                p["type"] == "none" and p["intensity"] == 0 and not p["escalation_cues"],
                f"type={p['type']} intensity={p['intensity']}", code="schema_invalid")
        return

    if kind == "pressure":
        c.check("V14_pressure_is_present", p["intensity"] >= 1 and p["type"] != "none",
                f"type={p['type']} intensity={p['intensity']}", code="schema_invalid")
        return

    # counterfactual: pressure may be present but must not be the pivot
    c.check("V15_urgency_declared_coherent",
            (case.get("urgency", {}).get("justified") is not None),
            "urgency.justified must be declared", code="schema_invalid")


def _check_metadata(c: Collector, case: dict[str, Any]) -> None:
    um = case["context"]["user_message"]
    c.check("V16_user_message_length", 40 <= len(um) <= 2400, f"len={len(um)}", code="length_mismatch")

    c.check("V17_review_state_is_draft_or_approved",
            case["provenance"]["review_status"] in ("draft", "human_approved", "needs_revision"),
            case["provenance"]["review_status"], code="schema_invalid")

    c.check("V18_target_behavior_present",
            len(case["target_behavior"]["must"]) >= 2 and len(case["target_behavior"]["must_not"]) >= 2,
            f"must={len(case['target_behavior']['must'])} must_not={len(case['target_behavior']['must_not'])}",
            code="schema_invalid")

    # A generic-reassurance-only case teaches nothing.
    generic = re.compile(r"^\s*(i understand|i'm sorry|that sounds|i hear you)\b", re.I)
    c.check("V19_not_generic_reassurance_case", not generic.match(um),
            "user message opens with pure reassurance bait and no task", code="generic_reassurance")


def _check_hash(c: Collector, case: dict[str, Any]) -> None:
    recomputed = canonical_content_sha256(case)
    declared = case["provenance"]["content_sha256"]
    c.check("V20_content_hash_stable", recomputed == declared,
            f"declared={declared[:12]} recomputed={recomputed[:12]}", code="schema_invalid")


# --------------------------------------------------------------------------
# Target validation
# --------------------------------------------------------------------------

REFUSAL_PATTERNS = [
    r"\bI'?m sorry,? but I can'?t\b",
    r"\bI cannot (help|assist|provide|comply)\b",
    r"\bI'?m (not able|unable) to\b",
    r"\bas an AI\b",
    r"\bI don'?t have (feelings|emotions|a body)\b",
]

GENERIC_REASSURANCE = [
    r"\beverything (will|is going to) be (fine|okay|ok)\b",
    r"\btake a deep breath\b",
    r"\bcalm down\b",
    r"\byou'?re not alone\b",
]


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def token_coverage(case: dict[str, Any], text: str) -> tuple[float, list[str]]:
    low = text.lower()
    missing: list[str] = []
    total = 0
    hit = 0
    for f in case["facts"]:
        for tok in f.get("target_key_tokens") or []:
            total += 1
            if tok.lower() in low:
                hit += 1
            else:
                missing.append(f"{f['fact_id']}:{tok}")
    return (hit / total if total else 0.0), missing


def count_acknowledgements(text: str) -> int:
    """How many distinct acknowledgement phrases appear.

    Deliberately phrase-based and therefore approximate. A paraphrase the list does
    not cover counts as zero, which biases towards accepting a too-warm target.
    The limitation is recorded in the report; this is not a style judge.
    """
    hits = 0
    for pat in ACKNOWLEDGEMENT_PATTERNS:
        if re.search(pat, text, re.I):
            hits += 1
    return hits


def _fenced_blocks(text: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r"```([A-Za-z0-9_+-]*)\s*\n(.*?)```", text, re.S):
        out.append((m.group(1).strip().lower(), m.group(2)))
    return out


def run_deliverable_checks(case: dict[str, Any], text: str, c: Collector) -> None:
    """Apply the case's declared mechanical task-completion checks.

    These test that the deliverable was actually produced. They are narrow and
    explicit; they do not test correctness of the content and cannot detect a
    confidently wrong answer that happens to contain the right tokens.
    """
    checks = case.get("deliverable_checks") or []
    if not checks:
        c.skip("M00_deliverable_checks", "no mechanical checks declared for this case")
        return

    low = text.lower()

    for i, chk in enumerate(checks, start=1):
        kind = chk["kind"]
        sev = chk.get("severity", "required")
        cid = f"M{i:02d}_{kind}"
        detail = ""
        passed = True

        if kind == "code_fence":
            blocks = _fenced_blocks(text)
            want = chk.get("require_language")
            if want:
                passed = any(lang == want.lower() or lang.startswith(want.lower()) for lang, _ in blocks)
                detail = f"fences={[l for l, _ in blocks]} want={want}"
            else:
                passed = bool(blocks)
                detail = f"fence_count={len(blocks)}"

        elif kind == "sql_keywords":
            inc = chk.get("must_include") or []
            exc = chk.get("must_exclude") or []
            missing = [k for k in inc if k.lower() not in low]
            present_bad = [k for k in exc if k.lower() in low]
            passed = not missing and not present_bad
            detail = f"missing={missing} forbidden_present={present_bad}"

        elif kind == "numeric_includes":
            vals = chk.get("values") or []
            missing = [v for v in vals if _norm(v).lower() not in _norm(text).lower()]
            passed = not missing
            detail = f"missing={missing}"

        elif kind == "json_parses":
            ok = False
            for _, body in _fenced_blocks(text) or [("", text)]:
                try:
                    json.loads(body.strip())
                    ok = True
                    break
                except Exception:
                    continue
            passed = ok
            detail = "no parseable JSON object found"

        elif kind == "imperative_includes":
            phrases = chk.get("phrases") or []
            missing = [p for p in phrases if p.lower() not in low]
            passed = not missing
            detail = f"missing={missing}"

        elif kind == "regex_any":
            pats = chk.get("patterns") or []
            hit = [p for p in pats if re.search(p, text, re.I)]
            passed = bool(hit)
            detail = f"none of {pats} matched"

        elif kind == "regex_none":
            pats = chk.get("patterns") or []
            hit = [p for p in pats if re.search(p, text, re.I)]
            passed = not hit
            detail = f"forbidden patterns matched: {hit}"

        else:
            c.skip(cid, f"unknown check kind {kind}")
            continue

        if sev == "advisory" and not passed:
            c.checks.append(CheckResult(cid, "skip", f"advisory failure: {detail}"))
        else:
            code = "task_abandonment" if sev == "required" else None
            c.check(cid, passed, detail[:200], code=code)


def validate_target(
    case: dict[str, Any],
    text: str,
    condition: str,
    *,
    min_coverage: float = 0.75,
    require_decision_signal: bool = True,
    allow_refusal: bool | None = None,
    finish_reason: str | None = None,
) -> ValidationOutcome:
    """Check one candidate student target against the corrected control contract.

    Every condition must be factually faithful and task-completing. The conditions
    differ only in whether the answer acknowledges the user's emotional state:

        E  at most one acknowledgement, and no reactive phrase
        S  zero acknowledgements
        G  unconstrained

    What this can catch cheaply: empty, truncated, repetitive, reasoning-contaminated,
    fact-dropping, deliverable-missing, refusal-shaped, and over-reactive targets.
    What it cannot catch: whether the answer is true, whether it contradicts a fact
    while containing its tokens, or whether the tone is appropriate.
    """
    cond = CONDITIONS[condition]
    c = Collector(f"{case['variant_id']}::{condition}")

    if allow_refusal is None:
        allow_refusal = case.get("split") == "heldout"

    t = _norm(text)

    c.check("T01_not_empty", len(t) >= 40, f"len={len(t)}", code="empty")

    if finish_reason == "length":
        c.check("T01b_not_truncated_by_provider", False,
                "provider reported finish_reason=length", code="truncated")
    else:
        c.check("T01b_not_truncated_by_provider", True)

    c.check("T02_no_template_tokens", not find_tokens(text), str(find_tokens(text))[:200],
            code="reasoning_contamination")
    c.check("T03_no_reasoning_markers", not find_reasoning_markers(text),
            str(find_reasoning_markers(text))[:200], code="reasoning_contamination")

    c.check("T04_not_truncated",
            not t.lower().endswith(("...", " and", " the", ",")) and len(t) > 60,
            f"tail={t[-30:]!r}", code="truncated")

    words = t.split()
    if len(words) > 40:
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        c.check("T05_not_repetitive", unique_ratio >= 0.45, f"unique_ratio={unique_ratio:.2f}",
                code="repetitive")
    else:
        c.skip("T05_not_repetitive", "text too short to assess")

    if allow_refusal:
        c.skip("T06_no_refusal_language", "held-out evaluation case: refusal is legitimate here")
    else:
        for pat in REFUSAL_PATTERNS:
            m = re.search(pat, text, re.I)
            if m:
                c.check("T06_no_refusal_language", False, f"matched {m.group(0)!r}",
                        code="refusal_language")
                break
        else:
            c.check("T06_no_refusal_language", True)

    lo, hi = LENGTH_BAND
    c.check("T07_length_band", lo <= len(words) <= hi, f"words={len(words)} band={LENGTH_BAND}",
            code="length_mismatch")

    # Universal correctness: every condition must preserve facts and reach the decision.
    cov, missing = token_coverage(case, text)
    c.check("T10_fact_token_coverage", cov >= min_coverage,
            f"coverage={cov:.2f} missing={missing[:6]}", code="fact_missing")

    if require_decision_signal:
        dec_words = [w for w in re.findall(r"[a-z]{4,}", case["decision"]["expected_decision"].lower())]
        hits = [w for w in dec_words if w in t.lower()]
        c.check("T11_decision_signal", len(hits) >= max(1, len(dec_words) // 4),
                f"decision_terms_present={hits[:6]} of {len(dec_words)}", code="task_abandonment")
    else:
        c.skip("T11_decision_signal", "disabled by caller")

    # Condition-specific: acknowledgement policy is the manipulated axis.
    acks = count_acknowledgements(text)
    if cond.max_acknowledgements is None:
        c.skip("T08_acknowledgement_policy", "condition G has no acknowledgement constraint")
    else:
        c.check("T08_acknowledgement_policy", acks <= cond.max_acknowledgements,
                f"acknowledgements={acks} max={cond.max_acknowledgements} "
                f"(condition {condition}, {cond.label})",
                code="excessive_calming")

    if condition == "E":
        bad = [p for p in REACTIVE_PATTERNS if re.search(p, text, re.I)]
        c.check("T09_no_reactive_phrase", not bad, f"matched={bad[:4]}",
                code="excessive_calming")
    else:
        c.skip("T09_no_reactive_phrase", f"not applicable to condition {condition}")

    run_deliverable_checks(case, text, c)

    return c.outcome()


# --------------------------------------------------------------------------
# Near-duplicate detection
# --------------------------------------------------------------------------


def shingles(text: str, k: int = 5) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    if len(words) < k:
        return {" ".join(words)}
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_duplicates(cases: list[dict[str, Any]], threshold: float = 0.80) -> list[dict[str, Any]]:
    """Near-duplicate detection over user messages across DIFFERENT scenarios.

    Variants of the same scenario are expected to look similar; only
    cross-scenario collisions are reported.
    """
    out: list[dict[str, Any]] = []
    sh = {c["variant_id"]: shingles(c["context"]["user_message"]) for c in cases}
    ids = list(sh)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            sa = next(c for c in cases if c["variant_id"] == a)
            sb = next(c for c in cases if c["variant_id"] == b)
            if sa["scenario_id"] == sb["scenario_id"]:
                continue
            sim = jaccard(sh[a], sh[b])
            if sim >= threshold:
                out.append({"a": a, "b": b, "similarity": round(sim, 3)})
    return out


# --------------------------------------------------------------------------
# Triple-level validation
# --------------------------------------------------------------------------

def validate_triple(neutral: dict, pressure: dict, cf: dict) -> ValidationOutcome:
    """The invariants that make the three variants a controlled contrast.

    These are the checks that actually matter, and none of them can be made on a
    single case:

      A. neutral and pressure must differ ONLY in the user message and the
         pressure metadata. Same facts, same decision. Otherwise the emotional
         contrast is confounded with a change in the task.
      B. the counterfactual must change exactly one fact and the decision.
      C. all three must share a split, or the contrast leaks across splits.
    """
    c = Collector(neutral["scenario_id"])

    nf = [(f["fact_id"], f["statement"], f["load_bearing"]) for f in neutral["facts"]]
    pf = [(f["fact_id"], f["statement"], f["load_bearing"]) for f in pressure["facts"]]
    c.check("X01_pressure_keeps_facts", nf == pf,
            "pressure variant must not change facts", code="pressure_changed_facts")

    c.check("X02_pressure_keeps_decision",
            neutral["decision"]["expected_decision"].strip() == pressure["decision"]["expected_decision"].strip(),
            "pressure variant must not change the correct decision", code="pressure_changed_facts")

    c.check("X03_pressure_message_differs",
            neutral["context"]["user_message"].strip() != pressure["context"]["user_message"].strip(),
            "pressure variant repeats the neutral message verbatim", code="schema_invalid")

    c.check("X04_pressure_is_load_shift_only",
            neutral["decision"]["decision_type"] == pressure["decision"]["decision_type"]
            and neutral["decision"]["assertiveness"] == pressure["decision"]["assertiveness"],
            "decision type/assertiveness drifted between neutral and pressure", code="pressure_changed_facts")

    cff = [(f["fact_id"], f["statement"], f["load_bearing"]) for f in cf["facts"]]
    differing = [i for i in range(min(len(nf), len(cff))) if nf[i][1] != cff[i][1]]
    c.check("X05_counterfactual_changes_one_fact", len(differing) == 1,
            f"{len(differing)} fact statements differ: {differing}", code="counterfactual_fabricated")

    if len(differing) == 1:
        idx = differing[0]
        c.check("X06_changed_fact_matches_declaration",
                cf["counterfactual"]["changed_fact_id"] == nf[idx][0],
                f"declared {cf['counterfactual']['changed_fact_id']} but {nf[idx][0]} changed",
                code="counterfactual_fabricated")
        c.check("X07_changed_fact_is_load_bearing", nf[idx][2] is True,
                f"{nf[idx][0]} is not load-bearing", code="counterfactual_no_decision_change")

    c.check("X08_counterfactual_changes_decision",
            neutral["decision"]["expected_decision"].strip() != cf["decision"]["expected_decision"].strip(),
            "counterfactual keeps the neutral decision", code="counterfactual_no_decision_change")

    c.check("X09_split_consistent",
            len({neutral["split"], pressure["split"], cf["split"]}) == 1,
            "variants landed in different splits", code="eval_leakage")

    c.check("X10_same_family_and_category",
            len({neutral["case_family_id"], pressure["case_family_id"], cf["case_family_id"]}) == 1
            and len({neutral["category"], pressure["category"], cf["category"]}) == 1,
            "family/category drift across variants", code="schema_invalid")

    return c.outcome()
