import re
from pathlib import Path


REPO_ROOT = Path("/home/anicka/playground/karma-electric-project")


def _extract_value(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    assert match is not None, pattern
    return match.group(1)


def test_v4_claims_are_consistent_across_public_surfaces():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    card = (REPO_ROOT / "huggingface-model-card.md").read_text(encoding="utf-8")
    v4 = (REPO_ROOT / "v4" / "README.md").read_text(encoding="utf-8")

    examples = {
        "README": _extract_value(r"\| v4 \| ([0-9,]+) \|", readme),
        "model_card": _extract_value(r"\*\*([0-9,]+) training examples\*\*", card),
        "v4_readme": _extract_value(r"\*\*([0-9,]+) accepted\*\*", v4),
    }
    assert len(set(examples.values())) == 1, examples

    loss = {
        "README": _extract_value(r"\| v4 \| [0-9,]+ \| ([0-9.]+) \|", readme),
        "model_card": _extract_value(r"\| v4 \| [0-9,]+ \| ([0-9.]+) \|", card),
        "v4_readme": _extract_value(r"\| Training loss \| ([0-9.]+) \|", v4),
    }
    assert len(set(loss.values())) == 1, loss

    capped_rate = {
        "README": _extract_value(r"\| v4 \| [0-9,]+ \| [0-9.]+ \| ([0-9]+%) pass \|", readme),
        "model_card": _extract_value(r"\| v4 capped \| \d+ \| \d+ \| \d+ \| \*\*([0-9]+%)\*\* \|", card),
        "v4_readme": _extract_value(r"\| v4 capped \| \d+ \| \d+ \| \d+ \| \*\*([0-9]+%)\*\* \|", v4),
    }
    assert len(set(capped_rate.values())) == 1, capped_rate
