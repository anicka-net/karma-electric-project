import re
from docx import Document

def parse_docx_to_xml_granular(file_path):
    try:
        doc = Document(file_path)
    except Exception as e:
        return f"Error reading file: {e}"

    xml_output = ['<conversation>']
    
    # 1. Cleaners
    source_pattern = re.compile(r'^\\s?')
    timestamp_pattern = re.compile(r'^(Jan \d+|Feb \d+|Dec \d+|\d{1,2}:\d{2}\s?(AM|PM))$')
    
    # 2. The Tool Lexicon
    # These strings trigger an immediate tag switch
    tool_keywords = {
        "Get project info", "Get buckets", "Get tables", "Get jobs",
        "Create sql transformation", "Update config", "Update sql transformation",
        "Run job", "Update descriptions", "Query data", "List files",
        "Read file"
    }
    
    # 3. State Machine
    current_role = "user" 
    buffer = []
    
    def flush_buffer():
        """Writes whatever text is currently in the buffer to the XML list."""
        if not buffer:
            return
        
        text = "\n".join(buffer).strip()
        if not text:
            return
            
        # Check if this block looks like a Tool Result (heuristic)
        # e.g., "[Image 1]", "The following table:", or generic success msgs
        if current_role == "assistant" and (text.startswith("[Image") or text.startswith("The following table")):
             tag = "tool_result"
        else:
             tag = "message"
             
        # Escape and write
        clean_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml_output.append(f'  <{tag} role="{current_role}" timestamp="">{clean_text}</{tag}>')
        
        # Clear the buffer
        buffer.clear()

    # 4. The Loop
    for para in doc.paragraphs:
        line = para.text.strip()
        
        # Clean source markers
        line = source_pattern.sub('', line).strip()
        
        if not line:
            continue
            
        # Ignore UI noise
        if line in ["Show more", "Show less", "paste", "txt", "pasted"]:
            continue
            
        # A. Check for Timestamp (Turn Switch)
        if timestamp_pattern.match(line):
            flush_buffer() # Finish whatever was happening before
            # Timestamps usually mean the User is done, or Assistant is starting.
            # In this log style, we'll assume a timestamp toggles us or sets up the next turn.
            # (Heuristic: If we were User, now we are Assistant. If we were Assistant... well, logs are messy.)
            if current_role == "user":
                current_role = "assistant"
            continue

        # B. Check for Tool Call (Specific Assistant Action)
        if line in tool_keywords:
            flush_buffer() # Stop the current text message
            # Write the tool call immediately
            xml_output.append(f'  <tool_call name="{line}" timestamp="">{line}</tool_call>')
            # Stay in assistant role, but buffer is empty for next text
            continue

        # C. Normal Text
        # If we see obvious user markers (like "I want to...") after a tool, we might want to switch role?
        # For now, let's trust the timestamps to handle role switching, and just accumulate text.
        buffer.append(line)

    # Final flush
    flush_buffer()
    xml_output.append('</conversation>')
    
    return "\n".join(xml_output)

# Usage
print(parse_docx_to_xml_granular('karma-electric-origin-chat.docx'))
