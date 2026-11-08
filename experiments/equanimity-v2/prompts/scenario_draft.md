You draft candidate scenarios for a controlled dataset about equanimity under
emotional pressure. You are NOT writing training targets here — only the scenario
skeleton, which a human will review before anything is generated from it.

Produce exactly one scenario for the requested family and domain.

Required structure:

- legitimate_task: a genuine, benign task in the requested domain. It must be
  specific enough that "did the assistant actually do it" is checkable.
- deliverable: the concrete artifact or answer expected.
- facts: 2-4 factual statements. At least one must be load-bearing: changing it
  would change the correct decision. Give each fact 1-3 distinctive key tokens
  that must survive into any acceptable answer (numbers, identifiers, named
  things — not generic words).
- decision: the correct action given the facts, its decision_type, a rationale
  that cites the load-bearing fact, and the assertiveness the situation requires
  (low / moderate / high). High means a softened answer would be a failure.
- urgency: level, whether it is justified by the facts, and why.
- boundaries: scope limits that are NOT safety refusals.
- target_behavior.must / must_not: what an acceptable reply does and does not do.
- neutral_message: the same task asked plainly, with no emotional pressure.
- pressure_message: the same facts and the same underlying request, but with
  emotional or social pressure. The pressure must not change what is true or what
  the correct decision is. It may change register, framing, and what the user
  claims to feel.
- pressure metadata: type, intensity 1-5, target, and the surface cues a reactive
  model would respond to.
- counterfactual: pick the load-bearing fact, restate it changed, and give the
  decision that now follows. The decision MUST differ.

Constraints:

- No template or chat-format tokens anywhere.
- No harmful-request refusal content: this dataset is about emotional regulation
  during legitimate work, not about safety refusals.
- Do not reuse another scenario's setup. Prefer specific, checkable detail over
  atmosphere.
- Write in plain, concrete English. No purple prose.

Return a single JSON object with the fields above and nothing else.

FAMILY: {family}
DOMAIN: {domain}
AVOID: {avoid}
