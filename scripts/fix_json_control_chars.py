#!/usr/bin/env python3
"""
Fix JSON files with unescaped control characters.

Common issue: literal newlines, tabs, etc. in strings need to be escaped.
"""

import json
import sys
from pathlib import Path
import re

def fix_control_chars_in_string(s):
    """Replace unescaped control characters with escaped versions"""
    # Common control characters that need escaping
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    s = s.replace('\b', '\\b')
    s = s.replace('\f', '\\f')
    return s

def fix_json_file(filepath):
    """Try to fix a JSON file with control character issues"""
    try:
        # First try normal loading
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, "Already valid"
    except json.JSONDecodeError as e:
        if "control character" not in str(e).lower():
            return False, f"Different JSON error: {e}"
        
        # Read as raw text and try to fix
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse with a more lenient approach
            # Strategy: fix control chars in the raw content, then parse
            
            # This is tricky - we need to fix control chars ONLY inside strings
            # A simple approach: replace in quoted content
            
            # Actually, let's use a different approach:
            # Read line by line and fix only content that looks like it's in a string
            lines = content.split('\n')
            fixed_lines = []
            
            in_string = False
            for line in lines:
                # Check if we're inside a JSON string value
                if '"content":' in line or '"user_message":' in line:
                    # This line likely contains the problematic content
                    # We need to be more careful here
                    fixed_line = line
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            
            # Simpler approach: just try to load with a more permissive method
            # Actually, let's use regex to find string values and fix them
            
            # Even simpler: use json.loads with strict=False
            # That doesn't exist, so let's do manual fixing
            
            # Load as Python dict using eval (careful!)
            # No, that's too dangerous
            
            # Let's use a different strategy:
            # Parse manually looking for the content field and fix it
            import ast
            
            # Actually, the simplest fix:
            # Replace literal newlines in quoted strings with \\n
            # But we need to not break JSON structure
            
            # Read file, fix obvious issues
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                raw = f.read()
            
            # Replace problematic control chars that aren't already escaped
            # This is a rough heuristic
            fixed = raw.replace('\r\n', '\\n').replace('\n', '\\n').replace('\t', '\\t')
            
            # But this will break the JSON structure itself!
            # We need to only fix inside strings
            
            # Let's use a safer approach: find all "content": "..." blocks
            # and fix control chars within them
            
            def fix_string_content(match):
                key = match.group(1)
                value = match.group(2)
                # Fix control chars in value
                value = value.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                return f'"{key}": "{value}"'
            
            # This regex is risky but let's try
            # Pattern: "content": "some value that may have\nnewlines"
            # We need to match until the closing quote, but not break on escaped quotes
            
            # Safer: just rewrite the file
            # Load what we can, stringify, and rewrite
            
            # Try with replaced control chars
            fixed_content = content.replace('\r', '').replace('\t', '    ')
            
            # Now try to load again
            try:
                data = json.loads(fixed_content)
                # Success! Write back
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True, "Fixed and rewritten"
            except:
                pass
            
            return False, "Could not auto-fix"
            
        except Exception as e:
            return False, f"Error during fix attempt: {e}"

def main():
    if len(sys.argv) > 1:
        # Fix specific directory
        base_dir = Path(sys.argv[1])
    else:
        base_dir = Path("data")
    
    print(f"Scanning {base_dir} for JSON files...")
    
    fixed_count = 0
    already_valid = 0
    failed = []
    
    for json_file in base_dir.rglob("*.json"):
        success, msg = fix_json_file(json_file)
        
        if "Already valid" in msg:
            already_valid += 1
        elif success:
            fixed_count += 1
            print(f"✓ Fixed: {json_file}")
        else:
            failed.append((json_file, msg))
            print(f"✗ Failed: {json_file} - {msg}")
    
    print(f"\nResults:")
    print(f"  Already valid: {already_valid}")
    print(f"  Fixed: {fixed_count}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed files:")
        for f, msg in failed[:10]:  # Show first 10
            print(f"  {f}: {msg}")

if __name__ == "__main__":
    main()
