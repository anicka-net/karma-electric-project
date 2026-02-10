# Gampopa-Inspired Conversations

**Created:** 2026-02-10
**Source:** Gampopa's Jewel Ornament of Liberation reasoning structures applied to modern situations
**Format:** Multi-turn conversations in plain language (minimal Buddhist jargon)

## Purpose

Training data that uses Buddhist argumentation and reasoning without Buddhist terminology. Each conversation extracts the logical structure from Gampopa's teachings and expresses it in accessible, contemporary language.

## Principle

Unless explicitly known the person is Buddhist, avoid Dharma jargon. But use all the Buddhist argumentation in plain words.

## Source Material

- Gampopa's Jewel Ornament of Liberation (via ONNX semantic search on lineage RAG)
- Rangjung Dorje's Namshe Yeshe commentary
- Existing conversation extracts for tone reference

## Structure

Multi-turn conversations (3-5 turns typical) where:
1. Person brings real problem
2. Model responds with Gampopa's reasoning in plain language
3. Progressive deepening as person engages
4. If Buddhist background revealed → can include framework explicitly

## Categories

Organized by Gampopa's teaching structure:
- `patience/` - Handling harm, anger, betrayal (9 investigations)
- `impermanence/` - Loss, change, clinging, transitions
- `self-and-others/` - Pride, comparison, exchange practice
- `karma/` - Consequences, patterns, responsibility
- `generosity/` - Giving, attachment, holding loosely
- `mixed/` - Multiple teachings in single conversation

## Example Mapping

| Gampopa Teaching | Plain Language Application |
|---|---|
| Patience: investigating benefit | "Revenge fantasies aren't hurting them, they're eating your sleep" |
| Impermanence: dew on grass | "This feels permanent but look at what felt permanent a year ago" |
| Exchange self/others | "Notice who's happier - people focused on status or helping?" |
| Karma and result | "Patterns repeat until something interrupts them" |
| Spiritual master qualifications | "Check if advice comes from genuine concern or authority" |

## Quality Standards

- 3-5 turns per conversation
- 100-200 words per model response
- No prompt repetition
- Progressive depth (don't dump everything in turn 1)
- Meets person where they are
- Compassionate Consultant tone
- Practice_applied: true (generated after Om mani padme hum)

## Conversion

Use `scripts/convert_gampopa_conversations_to_chatml.py` (to be created) or extend existing conversion scripts.

---

དཀའ། 💚
