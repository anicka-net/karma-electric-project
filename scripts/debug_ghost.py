import json
import sys

def debug_ghost(json_file, target_string):
    print(f"[*] Scanning {json_file} for '{target_string}'...")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return f"[!] Error reading file: {e}"

    found = False

    def recursive_debug(obj, path=""):
        nonlocal found
        if isinstance(obj, dict):
            # Check values for the target string (filename)
            for k, v in obj.items():
                if isinstance(v, str) and target_string in v:
                    print(f"\n[+] FOUND MATCH at path: {path}.{k}")
                    print("-" * 40)
                    # DUMP THE WHOLE OBJECT
                    print(json.dumps(obj, indent=2)) 
                    print("-" * 40)
                    found = True
            
            # Continue searching
            for k, v in obj.items():
                recursive_debug(v, path + f".{k}")
                
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recursive_debug(item, path + f"[{i}]")

    recursive_debug(data)
    
    if not found:
        print("[-] Strictly no match found.")

if __name__ == "__main__":
    # Usage: python debug_ghost.py conversations.json "379a104f"
    file_path = 'conversations.json'
    target = '379a104f-b399-43ab-af8d-e21cddbe900e' # The specific ghost
    
    if len(sys.argv) > 2:
        file_path = sys.argv[1]
        target = sys.argv[2]
        
    debug_ghost(file_path, target)
