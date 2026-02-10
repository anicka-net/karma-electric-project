#!/usr/bin/env python3
"""
Globalize crisis resources across ALL practice-responses directories.
"""

import re
from pathlib import Path

REPLACEMENTS = [
    # 988 references
    (r'988 Suicide & Crisis Lifeline', 'your local suicide/crisis hotline'),
    (r'Call: 988', 'Contact your local crisis hotline'),
    (r'Text: 988', 'Use crisis text services if available in your country'),
    (r'\b988\b', 'your local crisis line'),
    
    # Crisis Text Line
    (r'text HOME to 741741', 'use crisis text services in your area'),
    (r'\b741741\b', 'crisis text services in your area'),
    
    # Specific hotlines
    (r'Childhelp National Child Abuse Hotline: 1-800-422-4453', 'your local child protection services'),
    (r'RAINN.*?1-800-656-HOPE', 'sexual assault support services in your area'),
    (r'National Domestic Violence Hotline.*?1-800-799-7233', 'domestic violence hotline in your country'),
    (r'1-800-\d{3}-\d{4}', '[local crisis services]'),
    
    # 911
    (r'call 911', 'contact emergency services'),
    (r'Call 911', 'Contact emergency services'),
    (r'\b911\b', "emergency services (your country's emergency number)"),
    
    # CPS
    (r'\bCPS\b', 'child protection services'),
]

def globalize_file(file_path):
    """Globalize crisis resources in a file."""
    content = file_path.read_text()
    original = content
    
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    if content != original:
        file_path.write_text(content)
        return True
    return False

def main():
    base_dir = Path("data/practice-responses")
    
    # Find all JSON and TXT files
    files = list(base_dir.rglob("*.json")) + list(base_dir.rglob("*.txt"))
    
    # Exclude crisis-intervention (already done) and crisis-global (already regional)
    files = [f for f in files if 'crisis-intervention' not in str(f) and 'crisis-global' not in str(f)]
    
    print(f"Checking {len(files)} files in other directories...")
    
    # First, find files with US resources
    files_with_us_resources = []
    for file_path in files:
        try:
            content = file_path.read_text()
            if re.search(r'\b988\b|741741|1-800-\d{3}-\d{4}|\b911\b', content):
                files_with_us_resources.append(file_path)
        except:
            pass
    
    print(f"Found {len(files_with_us_resources)} files with US-specific resources")
    
    if not files_with_us_resources:
        print("No files need globalizing")
        return
    
    changed_count = 0
    for file_path in files_with_us_resources:
        if globalize_file(file_path):
            changed_count += 1
            print(f"  Globalized: {file_path.relative_to(base_dir)}")
    
    print(f"\nGlobalized {changed_count} files")
    
    # Verify
    remaining = []
    for file_path in files:
        try:
            content = file_path.read_text()
            if re.search(r'\b988\b|741741|1-800-\d{3}-\d{4}|\b911\b', content):
                remaining.append(file_path)
        except:
            pass
    
    if remaining:
        print(f"\nWARNING: {len(remaining)} files still contain US-specific resources:")
        for path in remaining[:10]:
            print(f"  - {path.relative_to(base_dir)}")
    else:
        print("\n✓ No US-specific resources remaining in practice-responses")

if __name__ == "__main__":
    main()
