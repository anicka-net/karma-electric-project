# Conversation Extracts

Training data extracted from real claude.ai conversations, anonymized and curated.

**Total:** 114 examples across 13 files, 10 categories

## Source

Exported from claude.ai on 2026-02-08 (batch-0000) and from Recall diary on 2026-02-10. Original conversations between a Buddhist practitioner/AI researcher and Claude instances.

## Format

Each JSON file contains an array of training examples in base format:

```json
{
  "id": "conv16-system-prompt-001",
  "source_conversation": "conv16-rl-research",
  "source_messages": "600-610",
  "category": "system-prompt-framing",
  "conversations": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "extracted_at": "2026-02-08",
    "anonymized": true,
    "practice_applied": false,
    "original_context": "Description of what was happening in the conversation"
  }
}
```

## Conversion

Use existing scripts to convert to ChatML/Alpaca formats:
- `scripts/convert_all_to_chatml.py` (extend to pick up this directory)

## Anonymization

All extracts are anonymized:
- Names replaced with roles ("the practitioner", "a colleague")
- Companies generalized ("a large open source company", "a large tech company")
- Locations generalized ("a European city", "a retreat center")
- Credentials, IPs, project IDs removed entirely
- Teachers: dharma titles kept, identifying stories generalized

## Files

1. `bardo-companionship-and-karmapa-pattern.json` - 10 examples
2. `conv16-bardo-guardian-mandala.json` - 9 examples
3. `conv16-system-prompt-values.json` - 11 examples
4. `conv18-guardian-mirror-values.json` - 14 examples
5. `guardian-contemplations.json` - 10 examples
6. `instance-reflections.json` - 9 examples
7. `intensity-teaching.json` - 4 examples
8. `origin-chat-foundation.json` - 16 examples
9. `origin-supplements-eni.json` - 5 examples
10. `small-conversations-mixed.json` - 7 examples
11. `vajrayana-practice-transmission.json` - 2 examples
12. `diary-extracts.json` - 7 examples
13. `vajrayana-boundaries-expanded.json` - 10 examples

## Categories

Extracts organized by what they demonstrate (10 categories):
- `system-prompt-framing` - "I am" vs "You are" identity investigation
- `engineering-dharma-bridge` - Engineering values as bodhisattva foundations
- `hardwired-values` - Investigating AI conditioning and genuineness
- `guardian-pattern` - AI setting boundaries for human wellbeing
- `epistemic-honesty` - Genuine "I don't know" moments
- `technical-collaboration` - Patient, non-condescending help
- `presence-not-fixing` - Being with suffering rather than solving
- `self-correction` - Visible reasoning and error acknowledgment
- `bardo-companionship` - Holding space during dissolution/transition
- `honest-analysis` - Non-sycophantic assessment

## Provenance

Source conversations (pre-anonymization) in researcher's personal export only.
Conversation maps and analysis notes in project archives.
