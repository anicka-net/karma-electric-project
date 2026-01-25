import json
import sys

def find_ghost_text(json_file, target_uuid):
    print(f"[*] Reading {json_file}...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return f"[!] Error reading file: {e}"

    print(f"[*] Hunting for UUID: {target_uuid}")
    
    found_content = []

    def recursive_search(obj, path=""):
        if isinstance(obj, dict):
            # Check if this object IS the target (by UUID field)
            if obj.get('uuid') == target_uuid:
                # We found the object, now extract text from it
                if 'text' in obj:
                    found_content.append(f"--- MATCH FOUND (Exact UUID) ---\n{obj['text']}")
                elif 'content' in obj:
                    found_content.append(f"--- MATCH FOUND (Exact UUID) ---\n{obj['content']}")
            
            # Check if this object CONTAINS the target in a string value (like a filename)
            for k, v in obj.items():
                if isinstance(v, str) and target_uuid in v:
                    # Found the UUID inside a string (likely a filename reference)
                    # We want the *content* associated with this message/attachment
                    print(f"[+] Found reference in key '{k}': {v}")
                    
                    # If this is an attachment object, look for content
                    if 'content' in obj:
                        found_content.append(f"--- MATCH FOUND (Referenced in {k}) ---\nContent: {obj['content']}")
                    # If it's a message, look for the text part
                    elif 'text' in obj:
                        found_content.append(f"--- MATCH FOUND (Referenced in {k}) ---\nText: {obj['text']}")
                
                # Recurse
                recursive_search(v, path + f".{k}")
                
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recursive_search(item, path + f"[{i}]")

    # Start the hunt
    recursive_search(data)

    if not found_content:
        return "[-] No content found for this UUID."
    
    return "\n\n".join(found_content)

if __name__ == "__main__":
    # If you run this without arguments, it uses your specific file and UUID
    # You can also run: python extract_ghost.py conversations.json UUID
    
    file_path = 'conversations.json' # Make sure this matches your filename
    target = '379a104f-b399-43ab-af8d-e21cddbe900e' 
    
    if len(sys.argv) > 2:
        file_path = sys.argv[1]
        target = sys.argv[2]
        
    result = find_ghost_text(file_path, target)
    print(result)
    
    # Save to file if found
    if "MATCH FOUND" in result:
        with open(f"recovered_{target[:8]}.txt", "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[*] Saved recovered text to recovered_{target[:8]}.txt")
