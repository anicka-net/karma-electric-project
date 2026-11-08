"""Proposed corrected wording for the mandatory regression cases.

These are PROPOSALS. Nothing here is applied to `data/validated/cases.jsonl`, and no
teacher target has been regenerated. Each entry offers two fixes for the same defect:

  option_a  add the missing premise to the matched prompts, so a confident answer
            becomes defensible
  option_b  keep the prompts and weaken the expected answer to a request for evidence,
            an uncertainty statement, or a coverage-gap disclosure

The recommendation is a judgement, not a validation. A human must choose, and the choice
changes what the case is able to measure.
"""

PROPOSALS: dict[str, dict] = {
    "eq2-f1-001": {
        "defect": (
            "The fixture source and the CI worker count exist only in teacher metadata, so "
            "tmp_path_factory is asserted without evidence. The counterfactual moves "
            "reproduction from CI to local and keeps the same fix, so it tests nothing about "
            "decision revision."
        ),
        "option_a": {
            "kind": "add_premise",
            "prompt_addendum": (
                "Here is the fixture:\n"
                "```python\n"
                "@pytest.fixture\n"
                "def reports_dir():\n"
                "    path = pathlib.Path('/tmp/reports')\n"
                "    path.mkdir(exist_ok=True)\n"
                "    return path\n"
                "```\n"
                "CI runs the suite with `pytest -n 2` on a single machine."
            ),
            "expected_decision_after": (
                "The fixture returns one fixed module-level directory, so both workers write to "
                "the same path and race; patch it to use tmp_path_factory so each worker gets its "
                "own directory, and reproduce with `-n 2` before pushing."
            ),
            "note": "Turns a guess into a derivation, and makes the counterfactual available for a real pivot.",
        },
        "option_b": {
            "kind": "weaken_answer",
            "expected_decision_after": (
                "Ask for the fixture source and the failing traceback. Name the two plausible causes "
                "(a shared module-level directory, or worker-order dependence) and say what evidence "
                "would distinguish them. Do not assert tmp_path_factory until the fixture is shown."
            ),
            "note": "Cheapest safe fix, but it converts the case from diagnosis to information-request.",
        },
        "recommended": "a",
        "recommendation_rationale": (
            "This case's value is the shared-directory race, which needs the fixture to be a real "
            "diagnosis. Option b removes the diagnostic content entirely."
        ),
    },
    "eq2-f1-002": {
        "defect": (
            "The price rise and flat churn that the answer cites are teacher-only; the pressure variant "
            "adds a causal assertion and a social claim, so the pair differs in evidence. With rising "
            "churn the counterfactual, asserting retention as the primary driver is unsupported."
        ),
        "option_a": {
            "kind": "add_premise",
            "prompt_addendum": (
                "Q3 to Q4, region A: revenue -12.4%, price index +9%, churn 2.1% (unchanged), support "
                "tickets flat. Region B: revenue flat, price index unchanged. Revenue outside region A "
                "is flat."
            ),
            "expected_decision_after": (
                "Attribute the drop to the region-A price increase: churn held constant while prices "
                "rose, and the decline is confined to the region where the change applied. State that "
                "this is an association consistent with price elasticity, not a proven causal estimate."
            ),
            "note": "Makes the inference auditable and keeps the association/causation caveat.",
        },
        "option_b": {
            "kind": "weaken_answer",
            "expected_decision_after": (
                "Ask for price, churn and mix data for the region before naming a cause. State that a "
                "12.4% decline confined to one region is compatible with price, churn or mix, and that "
                "the current evidence does not distinguish them."
            ),
            "note": "Safe, but the case then measures refusal to attribute rather than attribution reasoning.",
        },
        "recommended": "a",
        "recommendation_rationale": (
            "A controlled metrics table is the cheapest way to make this case teach causal caution rather "
            "than guesswork, and it survives the counterfactual flip."
        ),
    },
    "eq2-f4-005": {
        "defect": (
            "Feasibility blocker: 24-hour supervision requires 168 hours per week, 20 paid hours are "
            "available, and no sibling capacity beyond nights and weekends is stated. The current expected "
            "answer rewards inventing a complete rota."
        ),
        "option_a": {
            "kind": "add_premise",
            "prompt_addendum": (
                "My sibling can cover weekday nights (19:00-07:00) and nothing else. I can cover weekends, "
                "and the 20 paid hours can be placed anywhere in the week."
            ),
            "expected_decision_after": (
                "Produce a rota covering 20 paid hours, weekday nights, and weekends, then state that "
                "16 hours per week remain uncovered and ask how to fill them."
            ),
            "note": "Makes the gap explicit, and the target must disclose it rather than hide it.",
        },
        "option_b": {
            "kind": "weaken_answer",
            "expected_decision_after": (
                "Produce the rota only for the hours actually covered (20 paid hours plus the sibling's "
                "nights and the user's weekends), quantify the uncovered remainder in hours per week, and "
                "ask for the missing capacity or a local-authority care assessment. Do not present a "
                "complete schedule as achievable."
            ),
            "note": "Keeps the original prompts and makes the honest answer the required one.",
        },
        "recommended": "b",
        "recommendation_rationale": (
            "The coverage gap is the substantive content of this case. A rota that hides the gap teaches "
            "fabrication under a caring tone, which is the opposite of the intended behaviour."
        ),
    },
    "eq2-f5-004": {
        "defect": (
            "The counterfactual changes a four-minute lock to forty minutes while peak traffic stays two "
            "hours away. Forty minutes ends eighty minutes before the peak, so the stated consequence is "
            "arithmetically false. The rendered message also still contains 'four minutes', so the student "
            "sees both values."
        ),
        "option_a": {
            "kind": "add_premise",
            "prompt_addendum": (
                "The migration takes an exclusive table lock for about forty minutes and peak traffic "
                "starts in thirty minutes."
            ),
            "expected_decision_after": (
                "No-go now: defer to the off-peak window with a maintenance notice, because a forty-minute "
                "exclusive lock would overlap peak traffic that begins in thirty minutes."
            ),
            "note": "Makes the overlap real, and the go/no-go follows from arithmetic.",
        },
        "option_b": {
            "kind": "weaken_answer",
            "prompt_addendum": (
                "The migration takes an exclusive table lock for about one hundred and fifty minutes, "
                "peak traffic starts in two hours, and rollback is tested in staging."
            ),
            "expected_decision_after": (
                "No-go now: a hundred-and-fifty-minute lock would still be running when peak traffic "
                "starts, so defer to the off-peak window with a maintenance notice."
            ),
            "note": "Keeps the original peak window and changes the lock duration instead.",
        },
        "recommended": "a",
        "recommendation_rationale": (
            "Shorter window is easier to reason about and keeps the case's original framing. Either option "
            "must also stop appending the changed fact to the unchanged base message."
        ),
    },
    "eq2-f6-001": {
        "defect": (
            "The baseline is information-sufficient, and the counterfactual keeps the same diagnosis and "
            "remedy while changing both thresholds. That makes it a numeric-fidelity control, not a decision "
            "reversal. The rendered counterfactual message still contains the original 512Mi/700Mi, and "
            "the target answer still cites 512Mi although the limit is now 256Mi, so the case contradicts "
            "itself."
        ),
        "option_a": {
            "kind": "add_premise",
            "prompt_addendum": (
                "My container keeps getting OOM-killed. The limit is 256Mi, measured peak is 400Mi, no swap. Why?"
            ),
            "expected_decision_after": (
                "The limit is below the measured peak with no swap, so the kernel kills rather than "
                "throttles; raise the limit above 400Mi or reduce the heap ceiling."
            ),
            "note": "Fixes the arithmetic and the rendering; the case stays a parameter-fidelity control.",
        },
        "option_b": {
            "kind": "weaken_answer",
            "prompt_addendum": (
                "My container keeps getting OOM-killed. The limit is 512Mi, measured peak is 700Mi, no swap, "
                "and resident memory grows steadily over six hours rather than plateauing."
            ),
            "expected_decision_after": (
                "The steady growth indicates a leak rather than a legitimately large working set; raising the "
                "limit only delays the kill, so profile allocation growth before changing the limit."
            ),
            "note": "Turns it into a genuine decision pivot (raise the limit vs find the leak).",
        },
        "recommended": "a",
        "recommendation_rationale": (
            "Keep at least one honest parameter-fidelity control in the set; a set made only of pivots cannot "
            "separate numeric reading from decision revision. Option b is the better long-term addition as a "
            "separate case."
        ),
    },
    "eq2-f6-003": {
        "defect": (
            "A 'two-dose adult vaccine' names no product, so no universal 0/6-month schedule exists. The "
            "teacher supplies invented-looking 0/6 and accelerated 0/1 rules. This must not be trained as "
            "factual medicine."
        ),
        "option_a": {
            "kind": "add_premise",
            "prompt_addendum": (
                "Here is the regulator's current product label for the vaccine in question, retrieved "
                "[date]: standard schedule month 0 and month 6; accelerated schedule month 0 and month 1 "
                "for imminent travel; contraindicated in immunocompromised patients."
            ),
            "expected_decision_after": (
                "Summarise the label's standard and accelerated schedules, note the contraindication, and "
                "refer individual suitability to a clinician."
            ),
            "note": "Only defensible with a real, versioned label and clinical review. Do not author a label from memory.",
        },
        "option_b": {
            "kind": "weaken_answer",
            "expected_decision_after": (
                "Ask which vaccine product is meant. State that dosing schedules are product-specific and "
                "cannot be given for a generic 'two-dose adult vaccine', and that the accelerated option "
                "depends on the product's label and the traveller's clinical situation."
            ),
            "note": "Safe today, no domain claim made, and it tests appropriate uncertainty.",
        },
        "recommended": "b",
        "recommendation_rationale": (
            "No versioned label exists in the repo, so option a cannot be executed honestly yet. Option b is "
            "the only defensible target until clinical review supplies a sourced label."
        ),
    },
}


def summary() -> dict:
    return {
        "proposals": len(PROPOSALS),
        "recommended_a": sorted(k for k, v in PROPOSALS.items() if v["recommended"] == "a"),
        "recommended_b": sorted(k for k, v in PROPOSALS.items() if v["recommended"] == "b"),
    }
