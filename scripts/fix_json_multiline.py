#!/usr/bin/env python3
"""
Fix JSON files where strings span multiple lines with literal newlines.
"""

import json
from pathlib import Path
import sys

def fix_multiline_json(filepath):
    """Fix JSON with multi-line string values"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, "valid"
    except:
        pass
    
    # Read as bytes to handle encoding properly
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Join all lines, then process
    content = ''.join(lines)
    
    # Simple but effective: process character by character
    result = []
    in_string = False
    prev_char = ''
    
    for char in content:
        # Check if we're entering/exiting a string (not escaped quote)
        if char == '"' and prev_char != '\\':
            in_string = not in_string
            result.append(char)
        elif in_string:
            # Inside a string - escape control characters
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                continue  # Skip
            elif char == '\t':
                result.append('\\t')
            elif char == '\b':
                result.append('\\b')
            elif char == '\f':
                result.append('\\f')
            else:
                result.append(char)
        else:
            # Outside strings - keep as-is
            result.append(char)
        
        prev_char = char
    
    fixed = ''.join(result)
    
    # Try parsing
    try:
        data = json.loads(fixed)
        # Write back formatted
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True, "fixed"
    except Exception as e:
        return False, str(e)[:80]

def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    
    stats = {"valid": 0, "fixed": 0, "failed": 0}
    
    for json_file in sorted(target.rglob("*.json")):
        success, msg = fix_multiline_json(json_file)
        
        if msg == "valid":
            stats["valid"] += 1
        elif success:
            stats["fixed"] += 1
            print(f"✓ {json_file.name}")
        else:
            stats["failed"] += 1
            print(f"✗ {json_file.name}: {msg}")
    
    print(f"\n{stats['valid']} valid, {stats['fixed']} fixed, {stats['failed']} failed")

if __name__ == "__main__":
    main()
