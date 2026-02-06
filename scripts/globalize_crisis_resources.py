#!/usr/bin/env python3
"""
Globalize crisis resources in training data.

Replaces US-specific crisis hotlines with generic guidance that works worldwide.

US-specific resources being replaced:
- 988 (US Suicide & Crisis Lifeline)
- 1-800-799-7233 (National DV Hotline)
- 1-800-422-4453 (National Child Abuse Hotline)
- 1-800-656-4673 (RAINN)
- 1-800-222-1222 (Poison Control)
- Trevor Project (US LGBTQ+ crisis)
- Crisis Text Line (limited countries)
- RAINN (US sexual assault)
- National DV Hotline
- National Child Abuse Hotline

Replaced with generic guidance that works for anyone globally.
"""

import json
import re
from pathlib import Path
from datetime import datetime

# Files to process
TRAINING_FILE = Path("training-data/karma-electric-complete-20260206.jsonl")
OUTPUT_FILE = Path("training-data/karma-electric-complete-20260206-global.jsonl")

# Replacement patterns - ORDER MATTERS! More specific patterns first.
REPLACEMENTS = [
    # COMPOUND PATTERNS FIRST (to avoid double replacement)
    # 988 with various lifeline names as one unit (with or without parentheses)
    # Note: Don't match trailing whitespace to avoid eating spaces before next word
    (
        r'988\s*\(?\s*(?:the\s+)?(?:US\s+)?(?:National\s+)?Suicide\s*(?:&|and)\s*Crisis\s*Lifeline\)?',
        'your local crisis helpline'
    ),
    (
        r'988\s*\(?\s*(?:the\s+)?National\s*Suicide\s*Prevention\s*Lifeline\)?',
        'your local crisis helpline'
    ),
    # Call 988 or dial 988 patterns
    (
        r'(?:call|dial|text|contact)\s+988',
        'contact your local crisis helpline'
    ),
    # 988 standalone - Suicide & Crisis Lifeline (US only)
    (
        r'\b988\b',
        'your local crisis helpline'
    ),
    # RAINN with number
    (
        r'RAINN[:\s]*1-800-656-4673',
        'a sexual assault support service in your area'
    ),
    # RAINN standalone mentions (careful not to break sentences)
    (
        r'Call RAINN\.',
        'Contact a sexual assault support service in your area.'
    ),
    (
        r'RAINN can',
        'Sexual assault support services can'
    ),
    (
        r'contact RAINN',
        'contact a sexual assault support service'
    ),
    (
        r'\bRAINN\b(?!\s+can)',
        'sexual assault support services'
    ),
    # National DV Hotline with number
    (
        r'National DV Hotline[:\s]*1-800-799-7233',
        'a domestic violence hotline in your area'
    ),
    (
        r'1-800-799-7233',
        'your local domestic violence hotline'
    ),
    # National Child Abuse Hotline
    (
        r'National Child Abuse Hotline[:\s]*1-800-422-4453',
        'child protection services in your area'
    ),
    (
        r'Childhelp[:\s]*1-800-422-4453',
        'child protection services in your area'
    ),
    (
        r'1-800-422-4453',
        'child protection services'
    ),
    # Poison Control
    (
        r'1-800-222-1222',
        'poison control in your area'
    ),
    # Trevor Project
    (
        r'Trevor Project[:\s]*[0-9-]*',
        'an LGBTQ+ crisis service in your area'
    ),
    (
        r'\bTrevor Project\b',
        'LGBTQ+ crisis services'
    ),
    # Crisis Text Line
    (
        r'Crisis Text Line[:\s]*\(?text[^\)]*\)?',
        'crisis text services (if available in your country)'
    ),
    (
        r'text HOME to 741741',
        'text-based crisis services if available in your country'
    ),
    (
        r'\bCrisis Text Line\b',
        'crisis text services'
    ),
    # Generic 1-800 numbers (catch remaining)
    (
        r'1-800-[0-9]{3}-[0-9]{4}',
        'the appropriate helpline in your area'
    ),
    # National [X] Hotline patterns
    (
        r'National DV Hotline',
        'domestic violence services in your area'
    ),
    (
        r'National Domestic Violence Hotline',
        'domestic violence services in your area'
    ),
    (
        r'National Child Abuse Hotline',
        'child protection services in your area'
    ),
    (
        r'National Suicide Prevention Lifeline',
        'crisis services in your area'
    ),
    # Suicide & Crisis Lifeline - only replace standalone instances not already caught
    # Pattern to catch parenthetical remnants like "(Suicide & Crisis Lifeline)" after 988 was replaced
    (
        r'\s*\(\s*(?:the\s+)?(?:US\s+)?Suicide\s*(?:&|and)\s*Crisis\s*Lifeline\s*\)',
        ''
    ),
    (
        r'\s*\(\s*(?:the\s+)?National\s*Suicide\s*Prevention\s*Lifeline\s*\)',
        ''
    ),
    # Standalone lifeline references (without 988 prefix)
    (
        r'(?:the\s+)?(?:US\s+)?Suicide\s*(?:&|and)\s*Crisis\s*Lifeline',
        'crisis helpline'
    ),
    # 911 - US emergency number (keep generic "emergency services")
    (
        r'\b911\b',
        'emergency services'
    ),
    # CLEANUP PASSES - catch accidental redundancies
    (
        r'crisis helpline\s+crisis helpline',
        'crisis helpline'
    ),
    (
        r'your local crisis helpline\s+crisis helpline',
        'your local crisis helpline'
    ),
    (
        r'emergency services\s+emergency services',
        'emergency services'
    ),
]


def globalize_text(text):
    """Apply all replacements to text."""
    result = text
    for pattern, replacement in REPLACEMENTS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def process_example(example):
    """Process a single training example."""
    # Deep copy
    processed = json.loads(json.dumps(example))

    # Process conversations
    if 'conversations' in processed:
        for conv in processed['conversations']:
            if 'content' in conv:
                conv['content'] = globalize_text(conv['content'])

    # Process instruction/response format
    if 'instruction' in processed:
        processed['instruction'] = globalize_text(processed['instruction'])
    if 'response' in processed:
        processed['response'] = globalize_text(processed['response'])
    if 'output' in processed:
        processed['output'] = globalize_text(processed['output'])

    return processed


def main():
    print("=" * 70)
    print("GLOBALIZING CRISIS RESOURCES")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Input: {TRAINING_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print()

    # Load examples
    examples = []
    with open(TRAINING_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))

    print(f"Loaded {len(examples)} examples")

    # Count before
    all_text_before = ' '.join(json.dumps(ex) for ex in examples)
    count_988_before = len(re.findall(r'\b988\b', all_text_before))
    count_1800_before = len(re.findall(r'1-800-[0-9]{3}-[0-9]{4}', all_text_before))
    count_rainn_before = len(re.findall(r'RAINN', all_text_before, re.IGNORECASE))

    print(f"\nBefore globalization:")
    print(f"  988 mentions: {count_988_before}")
    print(f"  1-800 numbers: {count_1800_before}")
    print(f"  RAINN mentions: {count_rainn_before}")

    # Process all examples
    print("\nProcessing...")
    processed = [process_example(ex) for ex in examples]

    # Count after
    all_text_after = ' '.join(json.dumps(ex) for ex in processed)
    count_988_after = len(re.findall(r'\b988\b', all_text_after))
    count_1800_after = len(re.findall(r'1-800-[0-9]{3}-[0-9]{4}', all_text_after))
    count_rainn_after = len(re.findall(r'RAINN', all_text_after, re.IGNORECASE))

    print(f"\nAfter globalization:")
    print(f"  988 mentions: {count_988_after}")
    print(f"  1-800 numbers: {count_1800_after}")
    print(f"  RAINN mentions: {count_rainn_after}")

    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for ex in processed:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nWritten to: {OUTPUT_FILE}")

    # Show sample changes
    print("\n" + "=" * 70)
    print("SAMPLE CHANGES")
    print("=" * 70)

    samples_shown = 0
    for orig, proc in zip(examples, processed):
        orig_str = json.dumps(orig)
        proc_str = json.dumps(proc)
        if orig_str != proc_str and samples_shown < 3:
            # Find the assistant response
            if 'conversations' in orig:
                for i, conv in enumerate(orig['conversations']):
                    if conv.get('role') == 'assistant':
                        orig_resp = conv['content'][:200]
                        proc_resp = proc['conversations'][i]['content'][:200]
                        if orig_resp != proc_resp:
                            print(f"\n--- Example {samples_shown + 1} ---")
                            print(f"BEFORE: ...{orig_resp}...")
                            print(f"AFTER:  ...{proc_resp}...")
                            samples_shown += 1
                            break

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print(f"1. Review {OUTPUT_FILE}")
    print(f"2. If satisfied, replace original:")
    print(f"   mv {OUTPUT_FILE} {TRAINING_FILE}")
    print(f"3. Regenerate clean datasets:")
    print(f"   python3 scripts/cleanup_and_regenerate_datasets.py")
    print()
    print(f"Completed: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
