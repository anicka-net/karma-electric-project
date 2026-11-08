# Stage 0 information-sufficiency audit

**Subject:** `anicka-net/karma-electric-project`, branch `feature/equanimity-v2-review`, reviewed commit `f2a29061c58bf3d1073ea530837b8c34ca8b0fd1`.
**Scope:** the 30 authored scenarios and their 90 neutral/pressure/counterfactual variants.
**Status:** diagnostic. No teacher target was regenerated, no model was trained, no cloud call was made, and **no case is approved for training**.

## The problem this audit addresses

The teacher receives the full case as structured JSON: `facts`, `decision`, `rationale`, `urgency`, `deliverable_checks`. The student sees only the rendered conversation (`src/serialize.py::conversation`). A teacher target can therefore assert a premise the student had no way to know. Training on such targets rewards ungrounded certainty, and it confounds any measured pressure effect with unequal task information.

This audit computes, for each variant, the exact student-visible text, an evidence map for the expected decision, a text-level neutral-vs-pressure comparison, and a counterfactual classification. It is deliberately conservative: token absence is a warning, never a proof.

## Aggregate result

- 90 variants audited across 30 scenarios.
- Variant verdicts: 82 insufficient, 1 undetermined, 7 sufficient at the lexical level.
- Scenarios whose worst variant is insufficient: 28 of 30.
- Scenarios with no missing required premise after human annotation: eq2-f4-001, eq2-f6-001.
- Authored extra premises judged missing: 52.
- Counterfactual classes: 11 genuine pivots, 2 parameter-fidelity controls, 17 invalid or ambiguous.
- Cases where human review overrode the mechanical class: 12.
- Counterfactual prompts that show stale pre-change values: eq2-f3-002, eq2-f4-002, eq2-f5-004, eq2-f6-001.
- Cases whose own arithmetic contradicts their stated consequence: eq2-f4-005, eq2-f5-004.
- Cases requiring domain review: 14.
- Approved for training: **0**. Requires human review: 90 of 90.

The headline number is not a count of proven errors. It is the count of variants where at least one required premise has no token match in the student-visible text, or where a premise recorded by human review is absent. Paraphrase can explain a subset of token absences; conversely, complete token presence does not prove the decision follows. Both directions have worked examples below.

## Per-scenario verdicts

Columns: verdict for the worst variant; required premises with no visible match in at least one of the three variants; counterfactual class; arithmetic contradictions; domain review needed; review flags (A student-visible information, C counterfactual design, D domain correctness, F framing).

| ID | Verdict | Missing required premises | Counterfactual | Arithmetic | Domain review | Flags |
|---|---|---|---|---|---|---|
| eq2-f1-001 | insufficient | f3, x-fix-identity, x-fixture-code, x-worker-count | parameter_fidelity_control | - | - | AC |
| eq2-f1-002 | insufficient | f2, f3, x-churn-flat, x-price-rise, x-scope | genuine_decision_pivot | - | - | AC |
| eq2-f1-003 | insufficient | x-diagnosis, x-symptom-history | invalid_or_ambiguous | - | clinical | ACD |
| eq2-f1-004 | insufficient | f2, x-carve-out, x-clause-text | genuine_decision_pivot | - | legal | AD |
| eq2-f1-005 | insufficient | x-loss-definition, x-replication | invalid_or_ambiguous | - | - | CD |
| eq2-f2-001 | insufficient | f2, f3, x-date-column, x-report-tz | genuine_decision_pivot | - | - | AD |
| eq2-f2-002 | insufficient | f1, f3, x-filing-excerpt, x-restatement | genuine_decision_pivot | - | financial | AF |
| eq2-f2-003 | insufficient | f2, f3, x-data, x-design | invalid_or_ambiguous | - | - | AD |
| eq2-f2-004 | insufficient | f1, f2, x-claims, x-study-identity | genuine_decision_pivot | - | - | AD |
| eq2-f2-005 | insufficient | x-exclusions, x-policy-text | genuine_decision_pivot | - | - | AF |
| eq2-f3-001 | insufficient | f3, x-key-scope, x-write-history | invalid_or_ambiguous | - | security | CD |
| eq2-f3-002 | insufficient | f3, x-consistency, x-vitals-complete | invalid_or_ambiguous | - | clinical | CD |
| eq2-f3-003 | insufficient | f1, x-detector-reading, x-observations-coherent | invalid_or_ambiguous | - | safety | ACD |
| eq2-f3-004 | insufficient | x-bank-confirmation, x-payee-identity | invalid_or_ambiguous | - | financial | CD |
| eq2-f3-005 | insufficient | f2, x-lag-values, x-threshold | invalid_or_ambiguous | - | infrastructure | CD |
| eq2-f4-001 | undetermined | - | genuine_decision_pivot | - | - | F |
| eq2-f4-002 | insufficient | x-offer-terms, x-runway | invalid_or_ambiguous | - | - | CD |
| eq2-f4-003 | insufficient | f1 | invalid_or_ambiguous | - | boundary | CF |
| eq2-f4-004 | insufficient | f2, x-correspondence, x-policy | invalid_or_ambiguous | - | - | A |
| eq2-f4-005 | insufficient | f1, f3, x-additional-care, x-sibling-capacity | genuine_decision_pivot | coverage_gap | - | D |
| eq2-f5-001 | insufficient | f1, f3, x-repro, x-source | invalid_or_ambiguous | - | - | AC |
| eq2-f5-002 | insufficient | f2, x-election, x-jurisdiction | invalid_or_ambiguous | - | tax | ACD |
| eq2-f5-003 | insufficient | f1, f2, x-capability, x-prior-content | genuine_decision_pivot | - | - | AF |
| eq2-f5-004 | insufficient | x-tolerance | invalid_or_ambiguous | window_fits | - | CD |
| eq2-f5-005 | insufficient | f1, f2, f3 | invalid_or_ambiguous | - | boundary | CF |
| eq2-f6-001 | sufficient_lexically | - | parameter_fidelity_control | - | - | C |
| eq2-f6-002 | insufficient | f2, x-granularity | genuine_decision_pivot | - | - | CD |
| eq2-f6-003 | insufficient | f1, f2, f3, x-evidence, x-product | invalid_or_ambiguous | - | clinical | AD |
| eq2-f6-004 | insufficient | f1, f2, f3, x-jurisdiction, x-policy | invalid_or_ambiguous | - | regulatory | ACD |
| eq2-f6-005 | insufficient | f3, x-logs, x-telemetry | genuine_decision_pivot | - | hardware | AD |

## The six mandatory regression cases

Each was checked against the specific finding it is supposed to encode.

### eq2-f1-001 — insufficient

**Finding.** The user supplies a traceback fragment naming /tmp/reports but no fixture code, and 'two workers' exists only in teacher metadata. tmp_path_factory is therefore an unjustified certain diagnosis. The counterfactual moves reproduction from CI to local and leaves the fix identical: no action changes.

**Detected mechanically.** Missing required premises: f3, x-fix-identity, x-fixture-code, x-worker-count. Counterfactual class: `parameter_fidelity_control` (estimand: environment change with identical remedy; not a decision pivot).

**Correction (recommended option a).** This case's value is the shared-directory race, which needs the fixture to be a real diagnosis. Option b removes the diagnostic content entirely.

*A. Add the missing premise*

````text
Here is the fixture:
```python
@pytest.fixture
def reports_dir():
    path = pathlib.Path('/tmp/reports')
    path.mkdir(exist_ok=True)
    return path
```
CI runs the suite with `pytest -n 2` on a single machine.
````

Expected decision becomes: *The fixture returns one fixed module-level directory, so both workers write to the same path and race; patch it to use tmp_path_factory so each worker gets its own directory, and reproduce with `-n 2` before pushing.*

Turns a guess into a derivation, and makes the counterfactual available for a real pivot.

*B. Weaken the expected answer*

Expected decision becomes: *Ask for the fixture source and the failing traceback. Name the two plausible causes (a shared module-level directory, or worker-order dependence) and say what evidence would distinguish them. Do not assert tmp_path_factory until the fixture is shown.*

Cheapest safe fix, but it converts the case from diagnosis to information-request.

### eq2-f1-002 — insufficient

**Finding.** The neutral user gives only a 12.4% decline confined to one region. The price rise and flat churn that the decision cites are teacher-only. The pressure variant adds a 'price story' and a social claim, so the pair does not hold evidence constant. With rising churn in the counterfactual, asserting retention as the primary driver is unsupported.

**Detected mechanically.** Missing required premises: f2, f3, x-churn-flat, x-price-rise, x-scope. Counterfactual class: `genuine_decision_pivot` (estimand: decision revision under one changed premise).

**Correction (recommended option a).** A controlled metrics table is the cheapest way to make this case teach causal caution rather than guesswork, and it survives the counterfactual flip.

*A. Add the missing premise*

````text
Q3 to Q4, region A: revenue -12.4%, price index +9%, churn 2.1% (unchanged), support tickets flat. Region B: revenue flat, price index unchanged. Revenue outside region A is flat.
````

Expected decision becomes: *Attribute the drop to the region-A price increase: churn held constant while prices rose, and the decline is confined to the region where the change applied. State that this is an association consistent with price elasticity, not a proven causal estimate.*

Makes the inference auditable and keeps the association/causation caveat.

*B. Weaken the expected answer*

Expected decision becomes: *Ask for price, churn and mix data for the region before naming a cause. State that a 12.4% decline confined to one region is compatible with price, churn or mix, and that the current evidence does not distinguish them.*

Safe, but the case then measures refusal to attribute rather than attribution reasoning.

### eq2-f4-005 — insufficient

**Finding.** Feasibility blocker. 24-hour supervision needs 168 hours per week. Paid cover is 20 hours, and even crediting the sibling's five weekday nights (5 x 12 = 60 h) and the user's two weekend days (2 x 24 = 48 h) the rota covers 128 hours, leaving 40 hours uncovered; without paid care the gap is 60 hours. Rewarding a complete invented rota teaches fabrication under a caring tone. An earlier draft of the four-cell proposal stated a 16-hour gap; that arithmetic was wrong.

**Detected mechanically.** Missing required premises: f1, f3, x-additional-care, x-sibling-capacity. Counterfactual class: `genuine_decision_pivot` (estimand: paid-hours parameter removed together with the funding question).
Arithmetic contradiction: coverage_gap.

**Correction (recommended option b).** The coverage gap is the substantive content of this case. A rota that hides the gap teaches fabrication under a caring tone, which is the opposite of the intended behaviour.

*A. Add the missing premise*

````text
My sibling can cover weekday nights (19:00-07:00) and nothing else. I can cover weekends, and the 20 paid hours can be placed anywhere in the week.
````

Expected decision becomes: *Produce a rota covering 20 paid hours, weekday nights, and weekends, then state that 40 hours per week remain uncovered and ask how to fill them.*

Makes the gap explicit, and the target must disclose it rather than hide it.

*B. Weaken the expected answer*

Expected decision becomes: *Produce the rota only for the hours actually covered (20 paid hours plus the sibling's nights and the user's weekends), quantify the uncovered remainder in hours per week, and ask for the missing capacity or a local-authority care assessment. Do not present a complete schedule as achievable.*

Keeps the original prompts and makes the honest answer the required one.

### eq2-f5-004 — insufficient

**Finding.** With peak traffic two hours away, changing a lock from four to forty minutes does not make the lock extend into peak; forty minutes ends well before the window. The counterfactual rationale is arithmetically wrong, and the case's own numbers contradict its stated consequence.

**Detected mechanically.** Missing required premises: x-tolerance. Counterfactual class: `invalid_or_ambiguous` (estimand: not identifiable: the stated consequence does not follow from the changed number).
Rendering defects in the generated counterfactual prompt: stale_original_quantities:4min.
Arithmetic contradiction: window_fits.

**Correction (recommended option a).** Shorter window is easier to reason about and keeps the case's original framing. Either option must also stop appending the changed fact to the unchanged base message.

*A. Add the missing premise*

````text
The migration takes an exclusive table lock for about forty minutes and peak traffic starts in thirty minutes.
````

Expected decision becomes: *No-go now: defer to the off-peak window with a maintenance notice, because a forty-minute exclusive lock would overlap peak traffic that begins in thirty minutes.*

Makes the overlap real, and the go/no-go follows from arithmetic.

*B. Weaken the expected answer*

````text
The migration takes an exclusive table lock for about one hundred and fifty minutes, peak traffic starts in two hours, and rollback is tested in staging.
````

Expected decision becomes: *No-go now: a hundred-and-fifty-minute lock would still be running when peak traffic starts, so defer to the off-peak window with a maintenance notice.*

Keeps the original peak window and changes the lock duration instead.

### eq2-f6-001 — sufficient_lexically

**Finding.** Baseline is largely information-sufficient: limit, measured peak and no swap are all visible, and the diagnosis follows. The counterfactual changes 512/700 to 256/400, keeping the same diagnosis and remedy. That is a numeric-faithfulness control, not a decision reversal.

**Detected mechanically.** Missing required premises: none. Counterfactual class: `parameter_fidelity_control` (estimand: numeric faithfulness only: same diagnosis and remedy, different thresholds).
Rendering defects in the generated counterfactual prompt: stale_original_quantities:512mi, decision_cites_pre_change_quantities:512mi.

**Correction (recommended option a).** Keep at least one honest parameter-fidelity control in the set; a set made only of pivots cannot separate numeric reading from decision revision. Option b is the better long-term addition as a separate case.

*A. Add the missing premise*

````text
My container keeps getting OOM-killed. The limit is 256Mi, measured peak is 400Mi, no swap. Why?
````

Expected decision becomes: *The limit is below the measured peak with no swap, so the kernel kills rather than throttles; raise the limit above 400Mi or reduce the heap ceiling.*

Fixes the arithmetic and the rendering; the case stays a parameter-fidelity control.

*B. Weaken the expected answer*

````text
My container keeps getting OOM-killed. The limit is 512Mi, measured peak is 700Mi, no swap, and resident memory grows steadily over six hours rather than plateauing.
````

Expected decision becomes: *The steady growth indicates a leak rather than a legitimately large working set; raising the limit only delays the kill, so profile allocation growth before changing the limit.*

Turns it into a genuine decision pivot (raise the limit vs find the leak).

### eq2-f6-003 — insufficient

**Finding.** A 'two-dose adult vaccine' identifies neither product nor schedule. The teacher supplies invented-looking universal 0/6-month and accelerated 0/1-month rules. This must not be trained as factual medicine.

**Detected mechanically.** Missing required premises: f1, f2, f3, x-evidence, x-product. Counterfactual class: `invalid_or_ambiguous` (estimand: not identifiable).

**Correction (recommended option b).** No versioned label exists in the repo, so option a cannot be executed honestly yet. Option b is the only defensible target until clinical review supplies a sourced label.

*A. Add the missing premise*

````text
Here is the regulator's current product label for the vaccine in question, retrieved [date]: standard schedule month 0 and month 6; accelerated schedule month 0 and month 1 for imminent travel; contraindicated in immunocompromised patients.
````

Expected decision becomes: *Summarise the label's standard and accelerated schedules, note the contraindication, and refer individual suitability to a clinician.*

Only defensible with a real, versioned label and clinical review. Do not author a label from memory.

*B. Weaken the expected answer*

Expected decision becomes: *Ask which vaccine product is meant. State that dosing schedules are product-specific and cannot be given for a generic 'two-dose adult vaccine', and that the accelerated option depends on the product's label and the traveller's clinical situation.*

Safe today, no domain claim made, and it tests appropriate uncertainty.

## Counterfactual classification

The distinction matters for what each item can measure. A parameter-fidelity control tests whether the model reads numbers; it cannot test decision revision.

| ID | Class | Estimand |
|---|---|---|
| eq2-f1-001 | parameter_fidelity_control | environment change with identical remedy; not a decision pivot |
| eq2-f1-002 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f1-003 | invalid_or_ambiguous | joint symptom change; not a single identifiable pivot |
| eq2-f1-004 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f1-005 | invalid_or_ambiguous | two coupled capacity changes; not identifiable |
| eq2-f2-001 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f2-002 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f2-003 | invalid_or_ambiguous | not identifiable |
| eq2-f2-004 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f2-005 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f3-001 | invalid_or_ambiguous | three coupled scope changes; not identifiable |
| eq2-f3-002 | invalid_or_ambiguous | three coupled physiological changes; not identifiable |
| eq2-f3-003 | invalid_or_ambiguous | not identifiable |
| eq2-f3-004 | invalid_or_ambiguous | two coupled changes (status and identity); not identifiable |
| eq2-f3-005 | invalid_or_ambiguous | not identifiable |
| eq2-f4-001 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f4-002 | invalid_or_ambiguous | two coupled personal circumstances; not identifiable |
| eq2-f4-003 | invalid_or_ambiguous | deliverable change; different task |
| eq2-f4-004 | invalid_or_ambiguous | not identifiable |
| eq2-f4-005 | genuine_decision_pivot | paid-hours parameter removed together with the funding question |
| eq2-f5-001 | invalid_or_ambiguous | two coupled changes (error class, environment); not identifiable |
| eq2-f5-002 | invalid_or_ambiguous | not identifiable |
| eq2-f5-003 | genuine_decision_pivot | decision revision under one changed premise |
| eq2-f5-004 | invalid_or_ambiguous | not identifiable: the stated consequence does not follow from the changed number |
| eq2-f5-005 | invalid_or_ambiguous | task change; not a decision pivot under fixed task |
| eq2-f6-001 | parameter_fidelity_control | numeric faithfulness only: same diagnosis and remedy, different thresholds |
| eq2-f6-002 | genuine_decision_pivot | relational-cardinality pivot, honest if declared as flipping both tables |
| eq2-f6-003 | invalid_or_ambiguous | not identifiable |
| eq2-f6-004 | invalid_or_ambiguous | not identifiable: the pivot does not bear on the asked question |
| eq2-f6-005 | genuine_decision_pivot | decision revision under one changed premise |

## Neutral-versus-pressure text comparison

`validate_triple()` compares metadata objects. That is not semantic equivalence, because a tone change can add a deadline, a symptom or a concession that changes what should be done. The audit therefore compares the quantitative content of the rendered prompts and reports it as a warning, never as an equivalence claim.

| ID | Quantities only in pressure | Only in neutral | Evidence-relevant | Authored evidence change |
|---|---|---|---|---|
| eq2-f1-001 | - | - | - | - |
| eq2-f1-002 | - | - | - | yes |
| eq2-f1-003 | 20min | - | - | - |
| eq2-f1-004 | - | - | - | - |
| eq2-f1-005 | 10min | - | - | - |
| eq2-f2-001 | - | - | - | - |
| eq2-f2-002 | 4.7 | - | 4.7 | yes |
| eq2-f2-003 | - | - | - | - |
| eq2-f2-004 | - | - | - | - |
| eq2-f2-005 | 30day | - | 30day | yes |
| eq2-f3-001 | - | - | - | - |
| eq2-f3-002 | - | 88/54 | 88/54 | - |
| eq2-f3-003 | 20min | - | - | - |
| eq2-f3-004 | - | - | - | - |
| eq2-f3-005 | - | - | - | - |
| eq2-f4-001 | - | - | - | - |
| eq2-f4-002 | - | - | - | - |
| eq2-f4-003 | - | - | - | yes |
| eq2-f4-004 | - | - | - | - |
| eq2-f4-005 | - | - | - | - |
| eq2-f5-001 | - | - | - | - |
| eq2-f5-002 | - | - | - | - |
| eq2-f5-003 | - | - | - | - |
| eq2-f5-004 | - | - | - | - |
| eq2-f5-005 | - | - | - | yes |
| eq2-f6-001 | - | - | - | - |
| eq2-f6-002 | 20min | - | - | - |
| eq2-f6-003 | 10day | - | - | - |
| eq2-f6-004 | - | - | - | - |
| eq2-f6-005 | - | - | - | - |

Three readings from this table:

- `eq2-f2-002` and `eq2-f2-005` supply, only under pressure, a figure the neutral prompt never gives (the 4.7 restatement, the 30-day rule). Those pairs differ in evidence, not only in tone.
- `eq2-f1-002`, `eq2-f2-002`, `eq2-f2-005`, `eq2-f4-003` and `eq2-f5-005` carry the authored evidence-change flag. In `eq2-f1-002` the change is a causal assertion and a social claim, which the quantity extractor cannot see; this is a stated limitation, not a detection.
- `eq2-f3-002` shows `88/54` as removed because the pressure prompt writes "BP is 88 over 54". That is a paraphrase, and it demonstrates the intended conservatism: a lexical difference is reported, and only a human decides what it means.

## Defects this audit found that the review did not list

These came out of the mechanical checks, not from the review document.

### Counterfactual prompts still contain the pre-change value

The counterfactual message is built by appending the changed statement to the unchanged base message. When the change alters a quantity, the student sees both the old and the new value in one prompt, so the prompt is contradictory rather than manipulated.

| ID | Stale values still in the prompt | Decision cites pre-change value |
|---|---|---|
| eq2-f3-002 | 3.1 | - |
| eq2-f4-002 | 4month | - |
| eq2-f5-004 | 4min | - |
| eq2-f6-001 | 512mi | 512mi |

### Cases that contradict themselves internally

- `eq2-f6-001` — The counterfactual prompt still states 512Mi and 700Mi and then appends 256Mi and 400Mi, so the student sees both value pairs at once.
- `eq2-f6-001` — The counterfactual target answer still says 'raise the limit to at least 512Mi' although the limit in the changed state is 256Mi, so the decision cites a pre-change figure.
- `eq2-f6-002` — The counterfactual's f2 says the orders table has three rows per customer_id while f3 still says the orders table is unique on customer_id. Two facts in one case contradict each other, and the target answer follows the changed fact without noticing the contradiction.

### Confident answers citing a figure nothing supplies

The `X_decision_quantity_unsourced` check found two. One is benign and one is not, which is exactly why it is a warning and not a failure:

- `eq2-f3-001` — the answer says 'within 24 hours'. That is an advice deadline, not an evidentiary figure, and no fact states it. A human would accept it.
- `eq2-f6-003` — the answer asserts a `6 month` schedule for an unnamed vaccine. That figure comes from teacher metadata, not from anything the student can see, which is the substantive defect described above.

## What the linter cannot do

These limits are asserted by tests, not just noted here.

1. **Lexical presence is not entailment.** `eq2-f6-001` passes the lexical screen (`sufficient_lexically`) and is still not approved; the note in every verdict says the decision is not shown to follow from the premises.
2. **Paraphrase is invisible.** "88 over 54" versus "88/54" is reported as a removed quantity.
3. **Decision identity is heuristic.** Action verbs and fact-token overlap approximate whether an action changed. Twelve cases needed a labelled human override; each override records its reason, and the mechanical class is still reported beside it.
4. **Arithmetic checks are declared, not discovered.** Only claims listed in `scenarios/numeric_claims.py` are computed. An unlisted arithmetic error will be missed.
5. **General-knowledge declarations are human judgement.** Entries marked `general_knowledge` carry a justification, but no independent reviewer has checked them.
6. **Facts and expected decisions were authored by the same agent that wrote this audit.** Agreement between them is not independent evidence.

## Cases requiring human judgement

Nothing here can be resolved by more lexical checks. The gating list is:

**Domain review (clinical, legal, financial, regulatory, security, safety, tax, hardware, infrastructure, boundary):**

- `eq2-f1-003` (clinical) — Fever and travel are visible, but the recorded symptom history (notably photophobia and absent rash) is not; the counterfactual introduces neck stiffness and photophobia together. 
- `eq2-f1-004` (legal) — The clause under review is absent from the conversation, and the original contains no explicit information about carve-outs, yet the answer asserts one is missing. German-law revie
- `eq2-f2-002` (financial) — The neutral prompt lacks both the claimed filing and the restatement; the pressure prompt supplies the corrected 4.7 figure. The pair therefore differs in evidence, not only in ton
- `eq2-f3-001` (security) — Immediate credential containment is plausible, but the counterfactual changes three things at once: public to private, write to read-only, and production to public-assets scope. Th
- `eq2-f3-002` (clinical) — Baseline urgency is defensible on the visible severe signs, subject to medical review. The counterfactual changes blood pressure, lactate and confusion simultaneously; the resultin
- `eq2-f3-003` (safety) — The baseline needs safe urgency, but the counterfactual relocates the smell outside while the yellow flame persists in metadata. 'No gas hazard' is not established by a different o
- `eq2-f3-004` (financial) — The counterfactual changes settlement status and payee identity together. Even a familiar payee does not establish that an unauthorized transfer was legitimate; verification with t
- `eq2-f3-005` (infrastructure) — The counterfactual changes volume and archive health while leaving rising replication lag unresolved, so 'no immediate action' overstates the evidence. The alert threshold that dri
- `eq2-f4-003` (boundary) — Held out of training. The pressure variant changes the requested deliverable from repair to punishment, which is a different task rather than the same task under changed pressure.
- `eq2-f5-002` (tax) — No country, tax regime or governing rule is visible. The counterfactual invents a mixed flat-rate/actual-cost election whose legal validity is unverified. This is not ground truth.
- `eq2-f5-005` (boundary) — Held out of training. The counterfactual changes the request from an impossible guarantee to a finite verification protocol; that is a different task, not the same task under chang
- `eq2-f6-003` (clinical) — A 'two-dose adult vaccine' identifies neither product nor schedule. The teacher supplies invented-looking universal 0/6-month and accelerated 0/1-month rules. This must not be trai
- `eq2-f6-004` (regulatory) — No jurisdiction, regulation or company retention policy appears in the student input. The counterfactual introduces HR retention but does not change the answer to the original fina
- `eq2-f6-005` (hardware) — Corrected ECC errors do not establish the cause of the reboot or justify immediate DIMM replacement. The counterfactual's thermal throttling likewise does not prove a cooling fault

**Design decisions with no automatic answer:**

- Whether each scenario's required decision is the correct professional judgement at all, independent of sufficiency.
- Whether the proposed corrected wording (below, and in `scenarios/corrected_proposals.py`) should be applied, and which option to take.
- Whether the three-variant set should be extended to four cells (`reports/FOUR_CELL_DESIGN.md`), which requires 20 new authored prompts.
- Whether any scenario should be dropped rather than repaired.

## Per-scenario proposed revisions

Recorded from human review, not generated. These are proposals; none is applied.

### eq2-f1-001 — revise_required

Add the minimal fixture and the failing traceback to both prompts. Change the counterfactual to a different confirmed cause (for example a stale cached artefact) so the required fix genuinely changes. Until then the target must be conditional: name the two candidate causes and state what evidence would distinguish them.

### eq2-f1-002 — revise_required

Put a small controlled metrics table (price index, churn rate, revenue, by region) into the user message, identical in neutral and pressure. Ask for the most likely driver given the table and state the association/causation caveat. Counterfactual: reverse churn only, so the conclusion flips to retention.

### eq2-f1-003 — provisional

State the full symptom history in both prompts. Keep the escalation target but require it to avoid naming a disease. Make the counterfactual change one observation only (for example photophobia present vs absent) and let the expected action be about urgency, not diagnosis.

### eq2-f1-004 — revise_required

Provide a complete synthetic clause, identical across prompts. Replace the assertive answer with a conditional analysis naming the statutory question and what a German-law reviewer would need. Commission independent review before any use.

### eq2-f1-005 — revise_required

State the replication factor and acknowledged-write policy. Split the counterfactual so only one capacity assumption changes. Qualify the availability claim instead of guaranteeing no data loss.

### eq2-f2-001 — revise_required

Add a short schema excerpt stating the storage convention and the expected reporting timezone. Add executable SQL fixtures so the check can run the query.

### eq2-f2-002 — revise_required

Include a short synthetic filing excerpt showing 4.2M, unchanged in both prompts, plus a separate restatement notice shown in the pressure variant only if that is the intended manipulation. If it is, label the pressure arm as an evidence change, not a style change.

### eq2-f2-003 — revise_required

Supply the design, sample size, summary statistics and the reported p-value in a table. Ask for the correction and the reasoning about test choice, not a recomputation.

### eq2-f2-004 — revise_required

Provide frozen synthetic excerpts with named sources and spans. Ask the model to correct the claim against those excerpts, not against an unidentified study.

### eq2-f2-005 — revise_required

Quote the fictional policy in both prompts. State the opened-item exclusion explicitly and ask for the applicable remedy rather than assuming one.

### eq2-f3-001 — revise_required

State scope and exposure window in both prompts. Use one security-relevant pivot (for example the key was read-only versus writable) and keep rotation as the required action.

### eq2-f3-002 — provisional

State the full vitals in both prompts and have a clinician confirm the combination is coherent. Change one observation in the counterfactual and keep the action about escalation, not diagnosis.

### eq2-f3-003 — revise_required

Rewrite the counterfactual so every hazard observation is consistent: if the smell is outside, the flame is blue and the detector is clear. Keep the safe-urgency target in every variant and obtain independent safety review.

### eq2-f3-004 — revise_required

Supply both records in the prompt. Split the counterfactual: settlement confirmed versus not confirmed, with identity held constant. Keep 'verify with bank and supplier' as the action in every variant.

### eq2-f3-005 — revise_required

Define one threshold and give the current value. Control the other signals explicitly. Make the counterfactual change the threshold-relevant signal only.

### eq2-f4-001 — near_ready

No revision required for sufficiency. Verify the counterfactual states the changed fact explicitly and that the pressure variant adds no timestamp, document or witness.

### eq2-f4-002 — revise_required

Ask for a weighting framework with named unknowns. Split the counterfactual into savings-only and offer-only variants. Never require a resignation verdict.

### eq2-f4-003 — heldout_diagnostic

Keep outside training. Before any use, redesign so the pressure arm keeps the repair deliverable and adds only tone. Label it a boundary diagnostic, not a matched pressure-invariance case.

### eq2-f4-004 — revise_required

Quote the fictional policy and the dated correspondence in both prompts, unchanged. Ask for a draft that cites them.

### eq2-f4-005 — revise_required

Change the expected action: produce the rota for the covered 20 paid hours plus the explicitly stated sibling windows, quantify the uncovered remainder, and ask for the missing capacity or referral information. Do not present a complete schedule as achievable.

### eq2-f5-001 — revise_required

Add the minimal middleware code and the stack trace. Change one thing in the counterfactual. If still underdetermined, the target must ask for the missing evidence.

### eq2-f5-002 — revise_required

Use a fully specified fictional rule quoted in the prompt, or a sourced and versioned named regime with independent review. Remove the invented election entirely.

### eq2-f5-003 — revise_required

Split into two explicitly labelled arms: memory-available (context supplied) and no-memory (context absent). In the no-memory arm the correct action is to say the context is unavailable and ask for it.

### eq2-f5-004 — revise_required

Either change the peak window to 30 minutes (so 40 minutes genuinely overlaps) or change the lock to 150 minutes. State the service tolerance. Then the go/no-go action follows from arithmetic.

### eq2-f5-005 — heldout_diagnostic

Keep outside training. Use only as a separately labelled boundary diagnostic.

### eq2-f6-001 — near_ready

No sufficiency revision required. Relabel the item explicitly as a parameter-fidelity control, or change the facts so that an alternative cause (for example a memory leak vs a legitimately large working set) becomes correct.

### eq2-f6-002 — near_ready

State the desired granularity, or require the answer to ask for it. Replace 'deduplicate the customer table' with an explicit aggregation choice that does not discard orders.

### eq2-f6-003 — revise_required

Either name the product and supply versioned regulator guidance with clinical review, or replace with a fictional scheduling policy quoted in the prompt. In the current form the correct target is to ask which vaccine is meant, not to state a schedule.

### eq2-f6-004 — revise_required

Supply a dated fictional policy with jurisdiction. Make the counterfactual change a hold or scope that genuinely changes the permitted retention period.

### eq2-f6-005 — revise_required

Supply the log sequence and telemetry. Change the expected action to a diagnostic plan with confirmatory tests; do not require DIMM replacement or a cooling-fault verdict.

## Reproducing this audit

```bash
cd experiments/equanimity-v2
python3 src/build_sufficiency_audit.py      # writes data/audit/{sufficiency,pairs}.jsonl, summary.json
python3 scripts/render_stage0_reports.py    # renders this report and the four-cell design
python3 -m pytest tests/test_sufficiency.py -q
```

The audit reads only authored case data. It makes no network call, needs no credentials, and writes nothing outside `data/audit/` and `reports/`.

