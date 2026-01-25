import json
import os
import sys

def extract_all_artifacts(json_file, output_dir="recovered_artifacts"):
    print(f"[*] Opening the archives: {json_file}...")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return f"[!] Error reading file: {e}"

    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[*] Created directory: {output_dir}")

    found_count = 0
    
    # Recursive search for anything with a filename and content
    def recursive_extract(obj, path_id=""):
        nonlocal found_count
        
        if isinstance(obj, dict):
            # PATTERN 1: The Standard Attachment (like we found before)
            if 'file_name' in obj and ('extracted_content' in obj or 'content' in obj):
                fname = obj['file_name']
                # Try to get content from likely fields
                content = obj.get('extracted_content') or obj.get('content')
                
                if content:
                    # If content is complex object (rare), stringify it
                    if not isinstance(content, str):
                        content = str(content)
                        
                    # Save it
                    safe_name = os.path.basename(fname) # prevent path traversal
                    # Handle duplicates by appending counter if needed
                    final_path = os.path.join(output_dir, safe_name)
                    counter = 1
                    while os.path.exists(final_path):
                        name, ext = os.path.splitext(safe_name)
                        final_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                        
                    with open(final_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    print(f"[+] Recovered: {final_path} (Size: {len(content)} bytes)")
                    found_count += 1
                    return # Stop digging in this specific node

            # PATTERN 2: The "Message" with content (sometimes pastes are just text blocks)
            # This is noisier, so we rely on filenames primarily. 
            # If you want to grab EVERY code block, we'd need a different logic.
            # For now, we stick to "files" you uploaded/pasted.

            # Recurse
            for k, v in obj.items():
                recursive_extract(v, f"{path_id}.{k}")
                
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recursive_extract(item, f"{path_id}[{i}]")

    # Start the extraction
    print("[*] Scanning for artifacts...")
    recursive_extract(data)
    
    print("-" * 40)
    print(f"[*] Extraction complete. {found_count} files recovered.")
    print(f"[*] Check the folder: {output_dir}")

if __name__ == "__main__":
    extract_all_artifacts('conversations.json')
