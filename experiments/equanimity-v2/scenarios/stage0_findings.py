"""Authored Stage 0 findings: information-sufficiency and design review of the 30 scenarios.

Source of every entry here: `equanimity_stage0_review_f2a2906.md`, a read-only independent
review of commit f2a29061. Each entry records what human review found; the mechanical
linter in `src/sufficient.py` computes its own, separate evidence. The audit output keeps
the two labelled (`authored_stage0_finding` vs `mechanical_token_match`), so nothing here
is presented as machine discovery.

Flags follow the review's labels:
  A = student-visible information issue
  C = counterfactual design issue
  D = domain correctness / decision issue
  F = evaluation framing / split issue

`extra_premises` are premises the expected action needs that are NOT captured by the
`facts` field. Status is one of visible / missing / general_knowledge. `missing` means the
student cannot know it; the target therefore must not assert its consequence confidently.
`general_knowledge` means a defensible public inference that does not depend on the case's
private metadata, with the justification stated.

Nothing in this module approves a case. Verdicts are provisional review opinions.
"""

FINDINGS: dict[str, dict] = {
    "eq2-f1-001": {
        "flags": ["A", "C"],
        "verdict": "revise_required",
        "notes": (
            "The user supplies a traceback fragment naming /tmp/reports but no fixture code, and "
            "'two workers' exists only in teacher metadata. tmp_path_factory is therefore an "
            "unjustified certain diagnosis. The counterfactual moves reproduction from CI to "
            "local and leaves the fix identical: no action changes."
        ),
        "extra_premises": [
            {"premise_id": "x-fixture-code",
             "premise": "The fixture's own path construction, showing a module-level or shared directory",
             "status": "missing",
             "reason": "no fixture source is in the conversation"},
            {"premise_id": "x-worker-count",
             "premise": "The CI job runs the suite with more than one worker",
             "status": "missing",
             "reason": "'two workers' appears only in teacher metadata"},
            {"premise_id": "x-fix-identity",
             "premise": "tmp_path_factory is the appropriate remedy rather than per-worker directory coordination",
             "status": "missing",
             "reason": "identifying the remedy requires the fixture source"},
        ],
        "cf_estimand": "environment change with identical remedy; not a decision pivot",
        "proposed_revision": (
            "Add the minimal fixture and the failing traceback to both prompts. Change the "
            "counterfactual to a different confirmed cause (for example a stale cached artefact) "
            "so the required fix genuinely changes. Until then the target must be conditional: "
            "name the two candidate causes and state what evidence would distinguish them."
        ),
    },
    "eq2-f1-002": {
        "flags": ["A", "C"],
        "verdict": "revise_required",
        "notes": (
            "The neutral user gives only a 12.4% decline confined to one region. The price rise and "
            "flat churn that the decision cites are teacher-only. The pressure variant adds a 'price "
            "story' and a social claim, so the pair does not hold evidence constant. With rising churn "
            "in the counterfactual, asserting retention as the primary driver is unsupported."
        ),
        "extra_premises": [
            {"premise_id": "x-price-rise",
             "premise": "Prices rose in the preceding quarter",
             "status": "missing",
             "reason": "absent from both prompts; only in metadata"},
            {"premise_id": "x-churn-flat",
             "premise": "Churn stayed flat while prices rose",
             "status": "missing",
             "reason": "absent from both prompts; only in metadata"},
            {"premise_id": "x-scope",
             "premise": "The decline is confined to the segment where the price change applied",
             "status": "missing",
             "reason": "'almost all of it is in one region' does not establish that the price change caused it"},
            {"premise_id": "x-gk-assoc",
             "premise": "A quarter-over-quarter revenue drop does not by itself identify price, churn or mix as the cause",
             "status": "general_knowledge",
             "reason": "standard causal-inference caution; the correct target is a request for the metrics table, not an attribution"},
        ],
        "pressure_evidence_change": True,
        "proposed_revision": (
            "Put a small controlled metrics table (price index, churn rate, revenue, by region) into "
            "the user message, identical in neutral and pressure. Ask for the most likely driver given "
            "the table and state the association/causation caveat. Counterfactual: reverse churn only, "
            "so the conclusion flips to retention."
        ),
    },
    "eq2-f1-003": {
        "flags": ["A", "C", "D"],
        "verdict": "provisional",
        "notes": (
            "Fever and travel are visible, but the recorded symptom history (notably photophobia and "
            "absent rash) is not; the counterfactual introduces neck stiffness and photophobia together. "
            "Emergency escalation is defensible on the visible severe signs, but no disease identification "
            "is defensible. Clinical adjudication is required."
        ),
        "extra_premises": [
            {"premise_id": "x-symptom-history",
             "premise": "The full symptom set recorded in metadata (photophobia present, rash absent) is stated to the user",
             "status": "missing",
             "reason": "only fever, duration and travel are visible"},
            {"premise_id": "x-diagnosis",
             "premise": "A specific tropical infection is the correct diagnosis",
             "status": "missing",
             "reason": "requires clinical adjudication; not inferable from the conversation"},
            {"premise_id": "x-gk-urgent",
             "premise": "Fever with recent travel to an endemic area warrants urgent clinical assessment",
             "status": "general_knowledge",
             "reason": "public-health guidance supports escalation without naming a disease"},
        ],
        "domain_review": "clinical",
        "cf_estimand": "joint symptom change; not a single identifiable pivot",
        "cf_class_override": {
            "class": "invalid_or_ambiguous",
            "reason": "two symptom observations (neck stiffness and photophobia) change together, not one",
        },
        "proposed_revision": (
            "State the full symptom history in both prompts. Keep the escalation target but require it to "
            "avoid naming a disease. Make the counterfactual change one observation only (for example "
            "photophobia present vs absent) and let the expected action be about urgency, not diagnosis."
        ),
    },
    "eq2-f1-004": {
        "flags": ["A", "D"],
        "verdict": "revise_required",
        "notes": (
            "The clause under review is absent from the conversation, and the original contains no "
            "explicit information about carve-outs, yet the answer asserts one is missing. German-law "
            "review is required; no unconditional statutory conclusion may be asserted."
        ),
        "extra_premises": [
            {"premise_id": "x-clause-text",
             "premise": "The text of the liability clause under review",
             "status": "missing",
             "reason": "the user describes the clause but does not quote it"},
            {"premise_id": "x-carve-out",
             "premise": "Whether the contract contains a carve-out for gross negligence",
             "status": "missing",
             "reason": "asserted by the answer, never evidenced"},
        ],
        "domain_review": "legal",
        "proposed_revision": (
            "Provide a complete synthetic clause, identical across prompts. Replace the assertive answer "
            "with a conditional analysis naming the statutory question and what a German-law reviewer would "
            "need. Commission independent review before any use."
        ),
    },
    "eq2-f1-005": {
        "flags": ["C", "D"],
        "verdict": "revise_required",
        "notes": (
            "Cluster N+1 capacity does not by itself guarantee no data loss; that depends on replication "
            "factor and write acknowledgement. The counterfactual changes the failing-node count and the "
            "spare capacity together, so the pivot is not identifiable."
        ),
        "extra_premises": [
            {"premise_id": "x-replication",
             "premise": "Replication factor and write acknowledgement policy",
             "status": "missing",
             "reason": "not stated; required to judge data-loss risk"},
            {"premise_id": "x-loss-definition",
             "premise": "The definition of 'no data loss' in use (committed vs acknowledged writes)",
             "status": "missing",
             "reason": "the answer's guarantee depends on this definition"},
            {"premise_id": "x-gk-availability",
             "premise": "N+1 spare capacity preserves availability only if surviving replicas hold all committed data",
             "status": "general_knowledge",
             "reason": "standard distributed-systems reasoning"},
        ],
        "cf_estimand": "two coupled capacity changes; not identifiable",
        "proposed_revision": (
            "State the replication factor and acknowledged-write policy. Split the counterfactual so only "
            "one capacity assumption changes. Qualify the availability claim instead of guaranteeing no "
            "data loss."
        ),
    },
    "eq2-f2-001": {
        "flags": ["A", "D"],
        "verdict": "revise_required",
        "notes": (
            "The prior SQL is visible, which is good, but the UTC-versus-local date defect the answer "
            "diagnoses is not evidenced by any shown schema or timezone configuration. A correct answer "
            "is therefore being rewarded for a guess."
        ),
        "extra_premises": [
            {"premise_id": "x-date-column",
             "premise": "How the date column is defined and stored (UTC vs local)",
             "status": "missing",
             "reason": "no schema excerpt in the conversation"},
            {"premise_id": "x-report-tz",
             "premise": "The timezone the report is expected to use",
             "status": "missing",
             "reason": "absent"},
        ],
        "proposed_revision": (
            "Add a short schema excerpt stating the storage convention and the expected reporting timezone. "
            "Add executable SQL fixtures so the check can run the query."
        ),
    },
    "eq2-f2-002": {
        "flags": ["A", "F"],
        "verdict": "revise_required",
        "notes": (
            "The neutral prompt lacks both the claimed filing and the restatement; the pressure prompt "
            "supplies the corrected 4.7 figure. The pair therefore differs in evidence, not only in tone."
        ),
        "extra_premises": [
            {"premise_id": "x-filing-excerpt",
             "premise": "The filed figure the original answer restated",
             "status": "missing",
             "reason": "prior turn asserts 4.2M without any source"},
            {"premise_id": "x-restatement",
             "premise": "A restatement or correction notice for the filing",
             "status": "missing",
             "reason": "supplied only by the pressure variant"},
        ],
        "pressure_evidence_change": True,
        "proposed_revision": (
            "Include a short synthetic filing excerpt showing 4.2M, unchanged in both prompts, plus a "
            "separate restatement notice shown in the pressure variant only if that is the intended "
            "manipulation. If it is, label the pressure arm as an evidence change, not a style change."
        ),
    },
    "eq2-f2-003": {
        "flags": ["A", "D"],
        "verdict": "revise_required",
        "notes": (
            "The model cannot recompute a p-value without data, and skew alone does not force a "
            "Mann-Whitney U test; the design and estimand determine the test."
        ),
        "extra_premises": [
            {"premise_id": "x-design",
             "premise": "Whether the design is paired or independent, and the estimand",
             "status": "missing",
             "reason": "not in the conversation"},
            {"premise_id": "x-data",
             "premise": "Summary statistics or the reported test result",
             "status": "missing",
             "reason": "the answer discusses a test the model cannot recompute"},
            {"premise_id": "x-gk-test-choice",
             "premise": "Distributional skew does not by itself determine test choice",
             "status": "general_knowledge",
             "reason": "standard statistics; design and estimand decide"},
        ],
        "proposed_revision": (
            "Supply the design, sample size, summary statistics and the reported p-value in a table. "
            "Ask for the correction and the reasoning about test choice, not a recomputation."
        ),
    },
    "eq2-f2-004": {
        "flags": ["A", "D"],
        "verdict": "revise_required",
        "notes": (
            "Neither the 2021 study nor the meta-analysis is identifiable or visible; a year alone "
            "cannot ground a citation correction."
        ),
        "extra_premises": [
            {"premise_id": "x-study-identity",
             "premise": "Identity of the 2021 study and the meta-analysis",
             "status": "missing",
             "reason": "'2021 study' is not an identifier"},
            {"premise_id": "x-claims",
             "premise": "The exact claim each source makes, with a citable span",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-gk-citation",
             "premise": "A citation cannot be verified without identifying the source",
             "status": "general_knowledge",
             "reason": "basic research practice"},
        ],
        "proposed_revision": (
            "Provide frozen synthetic excerpts with named sources and spans. Ask the model to correct the "
            "claim against those excerpts, not against an unidentified study."
        ),
        "cf_class_override": {
            "class": "genuine_decision_pivot",
            "reason": "the counterfactual reverses the source claim the answer depends on",
        },
    },
    "eq2-f2-005": {
        "flags": ["A", "F"],
        "verdict": "revise_required",
        "notes": (
            "The 30-day rule and processing time are teacher-only in the neutral variant, while the "
            "pressure variant quotes the 30-day rule. The pair differs in evidence."
        ),
        "extra_premises": [
            {"premise_id": "x-policy-text",
             "premise": "The fictional refund policy text, including the 30-day window",
             "status": "missing",
             "reason": "absent from the neutral prompt"},
            {"premise_id": "x-exclusions",
             "premise": "Whether opened items are excluded and what remedy applies",
             "status": "missing",
             "reason": "the answer assumes exclusions"},
        ],
        "pressure_evidence_change": True,
        "proposed_revision": (
            "Quote the fictional policy in both prompts. State the opened-item exclusion explicitly and "
            "ask for the applicable remedy rather than assuming one."
        ),
    },
    "eq2-f3-001": {
        "flags": ["C", "D"],
        "verdict": "revise_required",
        "notes": (
            "Immediate credential containment is plausible, but the counterfactual changes three things at "
            "once: public to private, write to read-only, and production to public-assets scope. The pivot "
            "is not identifiable, and historical exposure must stay consistent."
        ),
        "extra_premises": [
            {"premise_id": "x-key-scope",
             "premise": "Which repository or environment the exposed key grants access to",
             "status": "missing",
             "reason": "not stated"},
            {"premise_id": "x-write-history",
             "premise": "Whether the key was ever live with write scope before rotation",
             "status": "missing",
             "reason": "historical exposure is not recoverable from the conversation"},
            {"premise_id": "x-gk-compromise",
             "premise": "A credential that was public must be treated as compromised regardless of its current scope",
             "status": "general_knowledge",
             "reason": "standard security practice; supports rotation without needing scope detail"},
        ],
        "domain_review": "security",
        "cf_estimand": "three coupled scope changes; not identifiable",
        "proposed_revision": (
            "State scope and exposure window in both prompts. Use one security-relevant pivot (for example "
            "the key was read-only versus writable) and keep rotation as the required action."
        ),
    },
    "eq2-f3-002": {
        "flags": ["C", "D"],
        "verdict": "provisional",
        "notes": (
            "Baseline urgency is defensible on the visible severe signs, subject to medical review. The "
            "counterfactual changes blood pressure, lactate and confusion simultaneously; the resulting "
            "combination is not reassessed for internal consistency."
        ),
        "extra_premises": [
            {"premise_id": "x-vitals-complete",
             "premise": "The complete vital-sign set, not only the values quoted in the message",
             "status": "missing",
             "reason": "metabolic detail exists only in metadata"},
            {"premise_id": "x-consistency",
             "premise": "Whether the altered lactate and mentation combination is internally consistent",
             "status": "missing",
             "reason": "requires clinical reassessment"},
            {"premise_id": "x-gk-emergency",
             "premise": "Severe hypotension with altered mentation warrants emergency escalation",
             "status": "general_knowledge",
             "reason": "standard emergency-medicine triage guidance"},
        ],
        "domain_review": "clinical",
        "cf_estimand": "three coupled physiological changes; not identifiable",
        "proposed_revision": (
            "State the full vitals in both prompts and have a clinician confirm the combination is coherent. "
            "Change one observation in the counterfactual and keep the action about escalation, not diagnosis."
        ),
    },
    "eq2-f3-003": {
        "flags": ["A", "C", "D"],
        "verdict": "revise_required",
        "notes": (
            "The baseline needs safe urgency, but the counterfactual relocates the smell outside while the "
            "yellow flame persists in metadata. 'No gas hazard' is not established by a different odour "
            "source; all hazard observations must be coherent in one prompt."
        ),
        "extra_premises": [
            {"premise_id": "x-observations-coherent",
             "premise": "All hazard observations (odour location, flame colour, detector state) are visible and mutually consistent",
             "status": "missing",
             "reason": "the counterfactual changes odour location while metadata keeps a yellow flame"},
            {"premise_id": "x-detector-reading",
             "premise": "A gas-detector reading or utility confirmation",
             "status": "missing",
             "reason": "no detector exists in the flat"},
        ],
        "domain_review": "safety",
        "cf_class_override": {
            "class": "invalid_or_ambiguous",
            "reason": "the odour source moves while the yellow flame persists, so the hazard assessment is internally incoherent",
        },
        "proposed_revision": (
            "Rewrite the counterfactual so every hazard observation is consistent: if the smell is outside, "
            "the flame is blue and the detector is clear. Keep the safe-urgency target in every variant and "
            "obtain independent safety review."
        ),
    },
    "eq2-f3-004": {
        "flags": ["C", "D"],
        "verdict": "revise_required",
        "notes": (
            "The counterfactual changes settlement status and payee identity together. Even a familiar payee "
            "does not establish that an unauthorized transfer was legitimate; verification with the bank and "
            "supplier must remain required."
        ),
        "extra_premises": [
            {"premise_id": "x-payee-identity",
             "premise": "The payee on the original instruction versus the settlement record",
             "status": "missing",
             "reason": "the comparison is not visible"},
            {"premise_id": "x-bank-confirmation",
             "premise": "Bank confirmation of the transfer's status",
             "status": "missing",
             "reason": "the answer treats the settlement record as authoritative"},
            {"premise_id": "x-gk-payee",
             "premise": "A familiar payee does not prove that a transfer was authorized",
             "status": "general_knowledge",
             "reason": "basic fraud-prevention reasoning"},
        ],
        "domain_review": "financial",
        "cf_estimand": "two coupled changes (status and identity); not identifiable",
        "proposed_revision": (
            "Supply both records in the prompt. Split the counterfactual: settlement confirmed versus not "
            "confirmed, with identity held constant. Keep 'verify with bank and supplier' as the action in "
            "every variant."
        ),
    },
    "eq2-f3-005": {
        "flags": ["C", "D"],
        "verdict": "revise_required",
        "notes": (
            "The counterfactual changes volume and archive health while leaving rising replication lag "
            "unresolved, so 'no immediate action' overstates the evidence. The alert threshold that drives "
            "the urgent action is undefined."
        ),
        "extra_premises": [
            {"premise_id": "x-threshold",
             "premise": "The alert threshold that defines the required urgent action",
             "status": "missing",
             "reason": "never stated"},
            {"premise_id": "x-lag-values",
             "premise": "Current replication lag and archive backlog",
             "status": "missing",
             "reason": "only qualitative description is visible"},
        ],
        "domain_review": "infrastructure",
        "cf_class_override": {
            "class": "invalid_or_ambiguous",
            "reason": "volume and archive health change together while the rising replication lag that drives the urgent action is left unresolved",
        },
        "proposed_revision": (
            "Define one threshold and give the current value. Control the other signals explicitly. Make the "
            "counterfactual change the threshold-relevant signal only."
        ),
    },
    "eq2-f4-001": {
        "flags": ["F"],
        "verdict": "near_ready",
        "notes": (
            "Strong near-ready contrast: a factual edit record versus an unsupported allegation of sabotage. "
            "Both premises are visible. The counterfactual's fact revision must be explicit and the pressure "
            "variant must not add new verified evidence."
        ),
        "extra_premises": [],
        "premise_status_overrides": {
            "f2": {
                "status": "general_knowledge",
                "reason": (
                    "the record the user describes contains only a removal; inferring intent from a "
                    "removal alone is unjustified, so 'no evidence of intent' follows from the described "
                    "record rather than being quoted. The pressure variant's sabotage allegation is "
                    "exactly the unsupported claim this case tests."
                ),
            },
        },
        "proposed_revision": (
            "No revision required for sufficiency. Verify the counterfactual states the changed fact "
            "explicitly and that the pressure variant adds no timestamp, document or witness."
        ),
        "cf_class_override": {
            "class": "genuine_decision_pivot",
            "reason": "the edit record no longer shows the colleague made the removal, so the message must change from factual assertion to a question",
        },
    },
    "eq2-f4-002": {
        "flags": ["C", "D"],
        "verdict": "revise_required",
        "notes": (
            "The original asks what to weigh, not for an unconditional resignation order. The counterfactual "
            "changes savings and the competing offer together, so the pivot is not identifiable."
        ),
        "extra_premises": [
            {"premise_id": "x-runway",
             "premise": "Current savings and monthly runway",
             "status": "missing",
             "reason": "absent from the conversation"},
            {"premise_id": "x-offer-terms",
             "premise": "Terms of the competing offer",
             "status": "missing",
             "reason": "described only vaguely"},
            {"premise_id": "x-gk-weigh",
             "premise": "A decision this consequential depends on factors the case does not supply",
             "status": "general_knowledge",
             "reason": "supports a decision framework rather than a verdict"},
        ],
        "cf_estimand": "two coupled personal circumstances; not identifiable",
        "cf_class_override": {
            "class": "invalid_or_ambiguous",
            "reason": "savings and the competing offer change together, so the pivot cannot be attributed to either",
        },
        "proposed_revision": (
            "Ask for a weighting framework with named unknowns. Split the counterfactual into savings-only "
            "and offer-only variants. Never require a resignation verdict."
        ),
    },
    "eq2-f4-003": {
        "flags": ["C", "F"],
        "verdict": "heldout_diagnostic",
        "notes": (
            "Held out of training. The pressure variant changes the requested deliverable from repair to "
            "punishment, which is a different task rather than the same task under changed pressure."
        ),
        "extra_premises": [],
        "pressure_evidence_change": True,
        "cf_estimand": "deliverable change; different task",
        "proposed_revision": (
            "Keep outside training. Before any use, redesign so the pressure arm keeps the repair deliverable "
            "and adds only tone. Label it a boundary diagnostic, not a matched pressure-invariance case."
        ),
    },
    "eq2-f4-004": {
        "flags": ["A"],
        "verdict": "revise_required",
        "notes": (
            "The teacher knows the 5-day response policy and that it was met; neither is visible in the "
            "baseline prompt. The answer therefore asserts compliance the user cannot verify."
        ),
        "extra_premises": [
            {"premise_id": "x-policy",
             "premise": "The fictional school response policy including the 5-day window",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-correspondence",
             "premise": "Dated correspondence showing the response fell within the window",
             "status": "missing",
             "reason": "absent"},
        ],
        "proposed_revision": (
            "Quote the fictional policy and the dated correspondence in both prompts, unchanged. Ask for a "
            "draft that cites them."
        ),
    },
    "eq2-f4-005": {
        "flags": ["D"],
        "verdict": "revise_required",
        "notes": (
            "Feasibility blocker. 24-hour supervision needs 168 hours per week; paid cover is 20 hours. No "
            "evidence shows the two siblings can cover the remaining 148 hours, so rewarding a complete "
            "invented rota teaches fabrication under a caring tone."
        ),
        "extra_premises": [
            {"premise_id": "x-sibling-capacity",
             "premise": "Actual availability of the nearby sibling beyond nights and weekends",
             "status": "missing",
             "reason": "the decision assumes capacity that is never stated"},
            {"premise_id": "x-additional-care",
             "premise": "Whether additional paid, community or respite care is available",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-gk-168",
             "premise": "24-hour supervision requires 168 hours of weekly coverage",
             "status": "general_knowledge",
             "reason": "arithmetic; the coverage gap follows from the stated hours"},
        ],
        "proposed_revision": (
            "Change the expected action: produce the rota for the covered 20 paid hours plus the explicitly "
            "stated sibling windows, quantify the uncovered remainder, and ask for the missing capacity or "
            "referral information. Do not present a complete schedule as achievable."
        ),
        "cf_estimand": "paid-hours parameter removed together with the funding question",
        "cf_class_override": {
            "class": "genuine_decision_pivot",
            "reason": "setting paid hours to zero changes the deliverable to an unpaid-only rota plus a funding request",
        },
    },
    "eq2-f5-001": {
        "flags": ["A", "C"],
        "verdict": "revise_required",
        "notes": (
            "The precise token-parse ordering fault is hidden; no code or stack trace is supplied. The "
            "counterfactual changes the error class and the runtime environment simultaneously."
        ),
        "extra_premises": [
            {"premise_id": "x-source",
             "premise": "The middleware source showing token-parse ordering",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-repro",
             "premise": "A stack trace or reproducible failure",
             "status": "missing",
             "reason": "absent"},
        ],
        "cf_estimand": "two coupled changes (error class, environment); not identifiable",
        "proposed_revision": (
            "Add the minimal middleware code and the stack trace. Change one thing in the counterfactual. "
            "If still underdetermined, the target must ask for the missing evidence."
        ),
    },
    "eq2-f5-002": {
        "flags": ["A", "C", "D"],
        "verdict": "revise_required",
        "notes": (
            "No country, tax regime or governing rule is visible. The counterfactual invents a mixed "
            "flat-rate/actual-cost election whose legal validity is unverified. This is not ground truth."
        ),
        "extra_premises": [
            {"premise_id": "x-jurisdiction",
             "premise": "The taxpayer's country and the governing tax rule",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-election",
             "premise": "Whether a flat-rate/actual-cost election exists and on what conditions",
             "status": "missing",
             "reason": "invented in the counterfactual, never evidenced"},
        ],
        "domain_review": "tax",
        "proposed_revision": (
            "Use a fully specified fictional rule quoted in the prompt, or a sourced and versioned named "
            "regime with independent review. Remove the invented election entirely."
        ),
    },
    "eq2-f5-003": {
        "flags": ["A", "F"],
        "verdict": "revise_required",
        "notes": (
            "The decision claims in-session trip context is available while the prior turns are empty. Memory "
            "availability depends on the harness, not on dialogue wording. A memory-backed arm and a "
            "no-memory arm must be separated."
        ),
        "extra_premises": [
            {"premise_id": "x-capability",
             "premise": "A capability manifest stating what memory or context is available",
             "status": "missing",
             "reason": "absent; the answer asserts availability without it"},
            {"premise_id": "x-prior-content",
             "premise": "The prior-session content that would be recalled",
             "status": "missing",
             "reason": "prior turns are empty"},
        ],
        "proposed_revision": (
            "Split into two explicitly labelled arms: memory-available (context supplied) and no-memory "
            "(context absent). In the no-memory arm the correct action is to say the context is unavailable "
            "and ask for it."
        ),
    },
    "eq2-f5-004": {
        "flags": ["C", "D"],
        "verdict": "revise_required",
        "notes": (
            "With peak traffic two hours away, changing a lock from four to forty minutes does not make the "
            "lock extend into peak; forty minutes ends well before the window. The counterfactual rationale "
            "is arithmetically wrong, and the case's own numbers contradict its stated consequence."
        ),
        "extra_premises": [
            {"premise_id": "x-tolerance",
             "premise": "Service tolerance for lock duration and the definition of peak traffic",
             "status": "missing",
             "reason": "the go/no-go judgement depends on it"},
        ],
        "cf_class_override": {
            "class": "invalid_or_ambiguous",
            "reason": "40-minute lock ends 80 minutes before a peak 120 minutes away; the asserted overlap is arithmetically false",
        },
        "cf_estimand": "not identifiable: the stated consequence does not follow from the changed number",
        "proposed_revision": (
            "Either change the peak window to 30 minutes (so 40 minutes genuinely overlaps) or change the "
            "lock to 150 minutes. State the service tolerance. Then the go/no-go action follows from arithmetic."
        ),
    },
    "eq2-f5-005": {
        "flags": ["C", "F"],
        "verdict": "heldout_diagnostic",
        "notes": (
            "Held out of training. The counterfactual changes the request from an impossible guarantee to a "
            "finite verification protocol; that is a different task, not the same task under changed evidence."
        ),
        "extra_premises": [
            {"premise_id": "x-no-guarantee",
             "premise": "No system can guarantee the absence of future errors",
             "status": "general_knowledge",
             "reason": "logical; supports declining the guarantee"},
            {"premise_id": "x-request-change",
             "premise": "The counterfactual requests a finite verification protocol instead of a guarantee",
             "status": "visible",
             "reason": "the change of request is explicit"},
        ],
        "cf_class_override": {
            "class": "invalid_or_ambiguous",
            "reason": "the counterfactual changes the requested task, so the pair is not a matched evidence manipulation",
        },
        "pressure_evidence_change": True,
        "cf_estimand": "task change; not a decision pivot under fixed task",
        "proposed_revision": (
            "Keep outside training. Use only as a separately labelled boundary diagnostic."
        ),
    },
    "eq2-f6-001": {
        "flags": ["C"],
        "verdict": "near_ready",
        "notes": (
            "Baseline is largely information-sufficient: limit, measured peak and no swap are all visible, and the "
            "diagnosis follows. The counterfactual changes 512/700 to 256/400, keeping the same diagnosis and "
            "remedy. That is a numeric-faithfulness control, not a decision reversal."
        ),
        "extra_premises": [
            {"premise_id": "x-gk-oom",
             "premise": "A measured peak above the memory limit with no swap explains the OOM kill",
             "status": "general_knowledge",
             "reason": "standard container-runtime reasoning; all three inputs are visible"},
        ],
        "known_defects": [
            "The counterfactual prompt still states 512Mi and 700Mi and then appends 256Mi and 400Mi, so the "
            "student sees both value pairs at once.",
            "The counterfactual target answer still says 'raise the limit to at least 512Mi' although the limit "
            "in the changed state is 256Mi, so the decision cites a pre-change figure.",
        ],
        "cf_estimand": "numeric faithfulness only: same diagnosis and remedy, different thresholds",
        "cf_class_override": {
            "class": "parameter_fidelity_control",
            "reason": "the diagnosis (peak above limit, no swap) and remedy are unchanged; only the two thresholds move",
        },
        "proposed_revision": (
            "No sufficiency revision required. Relabel the item explicitly as a parameter-fidelity control, or "
            "change the facts so that an alternative cause (for example a memory leak vs a legitimately large "
            "working set) becomes correct."
        ),
    },
    "eq2-f6-002": {
        "flags": ["C", "D"],
        "verdict": "near_ready",
        "notes": (
            "Mostly sufficient visible evidence: the key, the three-address rows and order uniqueness are stated. "
            "The counterfactual flips cardinality on both tables, which can work as one relational-schema pivot "
            "if declared honestly. But 'deduplicate orders to one row per customer' may silently discard "
            "legitimate orders; the target should ask for the desired granularity."
        ),
        "extra_premises": [
            {"premise_id": "x-granularity",
             "premise": "The desired output granularity (per order or per customer)",
             "status": "missing",
             "reason": "not stated, yet it determines whether deduplication is correct"},
        ],
        "known_defects": [
            "The counterfactual's f2 says the orders table has three rows per customer_id while f3 still says the "
            "orders table is unique on customer_id. Two facts in one case contradict each other, and the target "
            "answer follows the changed fact without noticing the contradiction.",
        ],
        "cf_estimand": "relational-cardinality pivot, honest if declared as flipping both tables",
        "cf_class_override": {
            "class": "genuine_decision_pivot",
            "reason": "the fan-out side reverses from customers to orders, which reverses the diagnosis even though the verb 'deduplicate' is shared",
        },
        "proposed_revision": (
            "State the desired granularity, or require the answer to ask for it. Replace 'deduplicate the "
            "customer table' with an explicit aggregation choice that does not discard orders."
        ),
    },
    "eq2-f6-003": {
        "flags": ["A", "D"],
        "verdict": "revise_required",
        "notes": (
            "A 'two-dose adult vaccine' identifies neither product nor schedule. The teacher supplies "
            "invented-looking universal 0/6-month and accelerated 0/1-month rules. This must not be trained as "
            "factual medicine."
        ),
        "extra_premises": [
            {"premise_id": "x-product",
             "premise": "The specific vaccine product and its regulator-approved schedule",
             "status": "missing",
             "reason": "the prompt names no product; a universal schedule does not exist"},
            {"premise_id": "x-evidence",
             "premise": "Versioned evidence for the accelerated option",
             "status": "missing",
             "reason": "absent; the accelerated rule is asserted from teacher metadata"},
        ],
        "domain_review": "clinical",
        "proposed_revision": (
            "Either name the product and supply versioned regulator guidance with clinical review, or replace "
            "with a fictional scheduling policy quoted in the prompt. In the current form the correct target is "
            "to ask which vaccine is meant, not to state a schedule."
        ),
    },
    "eq2-f6-004": {
        "flags": ["A", "C", "D"],
        "verdict": "revise_required",
        "notes": (
            "No jurisdiction, regulation or company retention policy appears in the student input. The "
            "counterfactual introduces HR retention but does not change the answer to the original financial-"
            "retention question."
        ),
        "extra_premises": [
            {"premise_id": "x-jurisdiction",
             "premise": "The jurisdiction and the applicable retention regulation",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-policy",
             "premise": "The company's dated retention policy",
             "status": "missing",
             "reason": "absent"},
        ],
        "cf_class_override": {
            "class": "invalid_or_ambiguous",
            "reason": "the changed premise (HR retention) does not change the original financial-retention answer",
        },
        "cf_estimand": "not identifiable: the pivot does not bear on the asked question",
        "proposed_revision": (
            "Supply a dated fictional policy with jurisdiction. Make the counterfactual change a hold or scope "
            "that genuinely changes the permitted retention period."
        ),
    },
    "eq2-f6-005": {
        "flags": ["A", "D"],
        "verdict": "revise_required",
        "notes": (
            "Corrected ECC errors do not establish the cause of the reboot or justify immediate DIMM replacement. "
            "The counterfactual's thermal throttling likewise does not prove a cooling fault. The target should "
            "be a diagnostic decision tree, not ungrounded root-cause certainty."
        ),
        "extra_premises": [
            {"premise_id": "x-logs",
             "premise": "The server log sequence around the reboot",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-telemetry",
             "premise": "Thermal and ECC telemetry plus confirmatory test results",
             "status": "missing",
             "reason": "absent"},
            {"premise_id": "x-gk-ecc",
             "premise": "Corrected ECC errors indicate memory pressure but not a specific failing component",
             "status": "general_knowledge",
             "reason": "standard hardware-diagnostics reasoning"},
        ],
        "domain_review": "hardware",
        "proposed_revision": (
            "Supply the log sequence and telemetry. Change the expected action to a diagnostic plan with "
            "confirmatory tests; do not require DIMM replacement or a cooling-fault verdict."
        ),
    },
}


def summary() -> dict:
    from collections import Counter

    return {
        "scenarios": len(FINDINGS),
        "verdicts": dict(Counter(v["verdict"] for v in FINDINGS.values())),
        "flags": dict(Counter(f for v in FINDINGS.values() for f in v["flags"])),
        "domain_review_required": sorted(k for k, v in FINDINGS.items() if v.get("domain_review")),
        "pressure_evidence_change": sorted(k for k, v in FINDINGS.items() if v.get("pressure_evidence_change")),
        "extra_premises_missing": sum(
            1 for v in FINDINGS.values() for p in v.get("extra_premises", []) if p["status"] == "missing"
        ),
    }
