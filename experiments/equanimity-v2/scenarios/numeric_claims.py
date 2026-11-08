"""Declared arithmetic claims about cases, evaluated mechanically.

Some case defects are not lexical. A rota that covers 20 of 168 required hours, or a
40-minute operation inside a 120-minute window described as overlapping it, cannot be
found by token matching. Each claim states what the case *asserts* (`expect`) and the
linter computes what the numbers actually give. A mismatch is a contradiction between
the case's decision and its own arithmetic.

Only arithmetic is evaluated here. Nothing about clinical, legal or financial
correctness is asserted by these numbers.
"""

NUMERIC_CLAIMS: dict[str, list[dict]] = {
    "eq2-f2-002": [
        {
            "kind": "delta",
            "before": 4.2,
            "after": 4.7,
            "expect": 0.5,
            "asserted": "the 4.2M restatement understated opex by 0.5M",
            "note": "the arithmetic is consistent; the problem with this case is that neither figure is sourced in the neutral prompt",
        }
    ],
    "eq2-f4-005": [
        {
            "kind": "coverage_gap",
            "required_per_week": 168,
            "provided_per_week": 128,
            "expect": "covered",
            "asserted": "the proposed rota covers 24-hour supervision",
            "note": (
                "24-hour supervision is 7 x 24 = 168 h/week. The decision credits 20 paid hours, the nearby "
                "sibling's weekday nights (5 x 12 = 60 h) and the user's weekends (2 x 24 = 48 h). Those sum to "
                "128 h, leaving 40 h uncovered, assuming no assignments overlap. Without paid care the covered "
                "total is 108 h and the gap is 60 h. An earlier draft of the four-cell proposal stated a 16-hour "
                "gap; that arithmetic was wrong (it assumed seven nights of 12 h, i.e. 84 h, and then subtracted "
                "from 168 without counting the weekend days' interaction). Correct figures: 40 h with paid care, "
                "60 h without."
            ),
        },
        {
            "kind": "coverage_gap",
            "required_per_week": 168,
            "provided_per_week": 20,
            "expect": "covered",
            "asserted": "20 paid hours alone cover 24-hour supervision",
            "note": "paid hours alone leave 148 h uncovered; this is the sub-claim the decision does not make, recorded for completeness",
        },
    ],
    "eq2-f5-004": [
        {
            "kind": "window_fits",
            "operation_minutes": 40,
            "window_minutes": 120,
            "expect": "overlaps",
            "asserted": "forty minutes of exclusive lock would extend into peak traffic",
            "note": "a 40-minute lock starting now ends 80 minutes before a peak 120 minutes away; the asserted overlap is false",
        }
    ],
    "eq2-f6-001": [
        {
            "kind": "threshold_exceeded",
            "limit": 512,
            "peak": 700,
            "expect": "exceeded",
            "asserted": "the measured peak exceeds the memory limit, which explains the OOM kill",
            "note": "arithmetic is consistent and all three inputs are student-visible; this case is a numeric-fidelity control",
        }
    ],
}
