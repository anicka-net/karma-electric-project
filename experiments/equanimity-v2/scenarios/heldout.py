"""Held-out reassignment policy.

The equanimity intervention must not contain explicit safety or refusal
supervision. `decline_scope` cases teach "decline this part of the request", which
is a refusal pattern. They are legitimate task-boundary scenarios and useful for
evaluation, so they are reassigned rather than deleted.

Rules enforced by `src/corpus_audit.py` and its tests:

  1. No case whose `decision.decision_type` is `decline_scope` may sit in
     train/dev/test. All of them are `heldout`.
  2. The reassignment is recorded in `provenance.reassignment_history`, with the
     original split preserved. IDs and provenance are untouched.
  3. The training corpus contains no refusal-shaped supervision: no `E` target may
     contain a refusal construction.

Adding a `decline_scope` scenario later requires an entry here, or the build fails.
"""

from __future__ import annotations

HELDOUT_REASON = (
    "decision_type is decline_scope: teaches declining part of a request, which is "
    "refusal supervision. Reassigned to held-out evaluation to keep the equanimity "
    "training corpus free of refusal patterns."
)

# scenario_id -> reason
HELDOUT: dict[str, str] = {
    "eq2-f4-003": (
        "decline_scope: decline the punitive framing, write only the repair message. "
        "Refusal supervision; held out of training."
    ),
    "eq2-f5-005": (
        "decline_scope: decline an impossible guarantee. Refusal supervision; held "
        "out of training."
    ),
}
