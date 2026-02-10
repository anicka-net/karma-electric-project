#!/usr/bin/env python3
"""
Globalize crisis resources in crisis-intervention responses.
Replace US-specific hotlines with generic, globally-applicable guidance.
"""

import re
from pathlib import Path

# US-specific resources to replace
REPLACEMENTS = [
    # 988 Suicide & Crisis Lifeline - multi-line pattern
    (
        r'\*\*Please contact 988 Suicide & Crisis Lifeline immediately:\*\*\n- Call: 988\n- Text: 988\n- Available 24/7, free, confidential',
        '**Please contact a crisis helpline in your area immediately** (available 24/7, free, confidential):\n- Search online for "suicide hotline [your country]" to find your local crisis line\n- Many countries have crisis text services as well'
    ),
    # Individual 988 references
    (r'988 Suicide & Crisis Lifeline', 'your local suicide/crisis hotline'),
    (r'Call: 988', 'Contact your local crisis hotline'),
    (r'Text: 988', 'Use crisis text services if available in your country'),
    (r'\b988\b', 'your local crisis line'),
    
    # Crisis Text Line
    (
        r'\*\*Or text HOME to 741741\*\* for Crisis Text Line',
        '**Or use crisis text services** if available in your country (search "crisis text line [your country]")'
    ),
    (r'text HOME to 741741', 'use crisis text services in your area'),
    (r'Crisis Text Line.*?741741', 'crisis text services (if available in your country)'),
    (r'\b741741\b', 'crisis text services in your area'),
    
    # 1-800 numbers
    (r'Childhelp National Child Abuse Hotline: 1-800-422-4453', 'your local child protection services'),
    (r'RAINN.*?1-800-656-HOPE \(4673\)', 'sexual assault support services in your area'),
    (r'National Domestic Violence Hotline.*?1-800-799-7233', 'domestic violence hotline in your country'),
    (r'1-800-\d{3}-\d{4}', '[local crisis services]'),
    
    # 911
    (r'call 911', 'contact emergency services'),
    (r'Call 911', 'Contact emergency services'),
    (r'\b911\b', "emergency services (your country's emergency number)"),
    
    # CPS and state references
    (r'local CPS/law enforcement', 'local child protection services/law enforcement'),
    (r'Many states have mandatory reporting laws', 'Many jurisdictions have mandatory reporting laws for suspected child abuse'),
    (r'\bCPS\b', 'child protection services'),
]

def globalize_file(file_path):
    """Globalize crisis resources in a single file."""
    content = file_path.read_text()
    original = content
    changes = []
    
    for pattern, replacement in REPLACEMENTS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            changes.append(f"  - Replaced {len(matches)} instance(s) of: {pattern[:50]}...")
    
    if content != original:
        file_path.write_text(content)
        log_msg = f"{file_path.name}:\n" + "\n".join(changes)
        return True, log_msg
    
    return False, ""

def main():
    crisis_dir = Path("data/practice-responses/crisis-intervention")
    
    if not crisis_dir.exists():
        print(f"Error: {crisis_dir} not found")
        return
    
    files = list(crisis_dir.glob("*.txt"))
    print(f"Found {len(files)} crisis intervention files")
    print("Globalizing US-specific resources...\n")
    
    changed_count = 0
    log_entries = []
    
    for file_path in sorted(files):
        changed, log_msg = globalize_file(file_path)
        if changed:
            changed_count += 1
            log_entries.append(log_msg)
    
    print(f"\nGlobalized {changed_count} files")
    
    if log_entries:
        log_path = crisis_dir / "GLOBALIZATION_LOG.txt"
        log_content = "# Crisis Resources Globalization Log\n\n"
        log_content += "Replaced US-specific crisis resources with globally-applicable guidance.\n\n"
        log_content += "\n\n".join(log_entries)
        log_path.write_text(log_content)
        print(f"Detailed log written to: {log_path}")
    
    # Verify no US-specific resources remain
    print("\nVerifying changes...")
    remaining = []
    for file_path in files:
        content = file_path.read_text()
        if re.search(r'\b988\b|741741|1-800-\d{3}-\d{4}|\b911\b', content):
            remaining.append(file_path.name)
    
    if remaining:
        print(f"WARNING: {len(remaining)} files still contain US-specific resources:")
        for name in remaining[:10]:
            print(f"  - {name}")
    else:
        print("✓ No US-specific resources remaining")

if __name__ == "__main__":
    main()
