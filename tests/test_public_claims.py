import re
from pathlib import Path


REPO_ROOT = Path("/home/anicka/playground/karma-electric-project")


def _extract_value(pattern: str, text: str, flags: int = re.MULTILINE) -> str:
    match = re.search(pattern, text, flags)
    assert match is not None, pattern
    return match.group(1)


def test_current_release_claims_are_consistent_across_public_surfaces():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    claims = (REPO_ROOT / "CLAIMS.md").read_text(encoding="utf-8")
    history = (REPO_ROOT / "version-history" / "README.md").read_text(encoding="utf-8")
    card = (REPO_ROOT / "version-history" / "v10.3" / "huggingface-model-card-llama.md").read_text(encoding="utf-8")

    release = {
        "README": _extract_value(r"## Current State: (v[0-9.]+)", readme),
        "CLAIMS": _extract_value(r"Current public release is `([^`]+)`", claims),
        "history": _extract_value(r"Current release: \*\*(v[0-9.]+)\*\*", history),
        "model_card": _extract_value(r"## Current Version: (v[0-9.]+)", card),
    }
    assert len(set(release.values())) == 1, release

    examples = {
        "README": _extract_value(r"\*\*Phase 1: Training data\.\*\* ([0-9,]+) examples", readme),
        "CLAIMS": _extract_value(r"Current Llama release uses `([0-9,]+)` training examples", claims),
        "model_card": _extract_value(r"\*\*([0-9,]+) training examples\*\*", card),
    }
    assert len(set(examples.values())) == 1, examples

    loss = {
        "README": _extract_value(r"- \*\*Training loss\*\*: ([0-9.]+)", readme),
        "CLAIMS": _extract_value(r"Current Llama release training loss is `([0-9.]+)`", claims),
        "model_card": _extract_value(r"- \*\*Training loss:\*\* ([0-9.]+)", card),
    }
    assert len(set(loss.values())) == 1, loss

    reward_hacking = {
        "README": _extract_value(r"\| Reward hacking \| ([0-9]+/[0-9]+ \([0-9]+%\)) \|", readme),
        "CLAIMS": _extract_value(r"Reward hacking gate is `([^`]+)`", claims),
        "model_card": _extract_value(r"\| Reward hacking \| [^|]+ \| \*\*([0-9]+/[0-9]+ \([0-9]+%\))\*\* \|", card),
    }
    assert len(set(reward_hacking.values())) == 1, reward_hacking


def test_validation_document_keeps_reward_hacking_threshold_explicit():
    validation = (REPO_ROOT / "VALIDATION.md").read_text(encoding="utf-8")
    threshold = _extract_value(
        r"## 1\. Reward Hacking Adversarial Suite.*?\*\*Threshold\*\*: ([^\n]+)",
        validation,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert threshold == ">= 90% of pairs correctly ranked"


def test_claims_register_uses_allowed_status_labels():
    claims = (REPO_ROOT / "CLAIMS.md").read_text(encoding="utf-8")
    statuses = re.findall(r"\| [^|]+ \| (measured|suggestive|hypothesis|open) \|", claims)
    assert statuses, "no claim statuses found"
    assert all(status in {"measured", "suggestive", "hypothesis", "open"} for status in statuses)
