"""Markdown table shape checks for the rendered reports.

A report table that renders as one cell per character is worse than no table: it looks like data and
is unreadable. These checks pin the two ways that happened: a row passed as a string instead of a
tuple, and a string joined as if it were a list.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
MAX_COLUMNS = 10


def table_blocks(text: str) -> list[list[str]]:
    blocks, current = [], []
    for line in text.splitlines():
        if line.startswith("|"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def pipes(line: str) -> int:
    """Column separators only: a pipe inside `inline code` is content, not a separator."""
    return re.sub(r"`[^`]*`", "", line).count("|")


def test_every_table_row_has_the_header_column_count():
    problems = []
    for path in sorted(REPORTS.glob("*.md")):
        for block in table_blocks(path.read_text()):
            head = pipes(block[0])
            if head > MAX_COLUMNS:
                problems.append(f"{path.name}: header has {head} pipes")
            for row in block:
                if pipes(row) != head:
                    problems.append(f"{path.name}: row has {pipes(row)} pipes vs {head}: {row[:80]}")
    assert problems == [], problems


def test_coverage_table_carries_prose_not_characters():
    text = (REPORTS / "TARGET_VALIDATOR_REPORT.md").read_text()
    assert "quantities, dates and units present in the answer" in text
    assert "structural requirements per task type" in text
    # The exploded form produced one cell per character, e.g. "| q | u | a | n | t ...".
    assert "| q | u | a | n |" not in text


def test_separator_rows_are_well_formed():
    for path in sorted(REPORTS.glob("*.md")):
        for block in table_blocks(path.read_text()):
            if len(block) < 2:
                continue
            sep = block[1]
            assert set(sep.replace("|", "").replace("-", "").strip()) == set(), (
                f"{path.name}: separator row is not dashes: {sep[:60]}")
