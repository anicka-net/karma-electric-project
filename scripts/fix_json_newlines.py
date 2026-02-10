#!/usr/bin/env python3
"""
Fix JSON files where string values contain literal newlines.
These need to be escaped as \\n for valid JSON.
"""

import json
import re
from pathlib import Path
import sys

def fix_json_with_literal_newlines(filepath):
    """
    Fix JSON files that have literal newlines in string values.
    Strategy: Read as text, escape newlines in quoted strings, then parse.
    """
    try:
        # First check if it's already valid
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, "already_valid"
    except:
        pass
    
    # Read raw content
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strategy: Find all string values and escape newlines within them
    # We need to handle: "key": "value with\nnewlines"
    
    # Use a state machine approach
    result = []
    i = 0
    in_string = False
    in_key = False  # Are we in a key or value?
    escape_next = False
    
    while i < len(content):
        char = content[i]
        
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue
        
        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue
        
        if char == '"':
            if in_string:
                # Ending a string
                in_string = False
                result.append(char)
            else:
                # Starting a string
                in_string = True
                result.append(char)
            i += 1
            continue
        
        if in_string:
            # We're inside a quoted string
            if char == '\n':
                # Replace literal newline with escaped version
                result.append('\\n')
            elif char == '\r':
                # Skip carriage returns
                pass
            elif char == '\t':
                # Replace tabs with spaces
                result.append('    ')
            else:
                result.append(char)
        else:
            # We're outside quoted strings - keep as-is
            result.append(char)
        
        i += 1
    
    fixed_content = ''.join(result)
    
    # Try to parse the fixed content
    try:
        data = json.loads(fixed_content)
        # Success! Write it back properly formatted
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True, "fixed"
    except Exception as e:
        return False, f"parse_failed: {str(e)[:100]}"

def main():
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path("data")
    
    print(f"Scanning {target}...")
    
    stats = {"already_valid": 0, "fixed": 0, "failed": 0}
    failed_files = []
    
    for json_file in target.rglob("*.json"):
        success, status = fix_json_with_literal_newlines(json_file)
        
        if status == "already_valid":
            stats["already_valid"] += 1
        elif success:
            stats["fixed"] += 1
            print(f"✓ Fixed: {json_file.relative_to(target)}")
        else:
            stats["failed"] += 1
            failed_files.append((json_file, status))
            print(f"✗ Failed: {json_file.relative_to(target)} - {status}")
    
    print(f"\nResults:")
    print(f"  Already valid: {stats['already_valid']}")
    print(f"  Fixed: {stats['fixed']}")
    print(f"  Failed: {stats['failed']}")
    
    if failed_files and stats['failed'] <= 10:
        print(f"\nFailed files:")
        for f, msg in failed_files:
            print(f"  {f}: {msg}")

if __name__ == "__main__":
    main()
