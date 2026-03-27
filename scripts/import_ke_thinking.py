#!/usr/bin/env python3
"""Import KE-generated thinking examples into training.db.

These examples have <think> traces baked into the assistant content.
We extract the trace into the `reasoning` column (matching DB convention)
and keep the clean response in conversations.

Categories:
  - thinking-positive       (700 positive engagement)
  - thinking-grey-area      (300 grey area)
  - thinking-constitutional (200 constitutional)
  - thinking-crisis-survival (50 crisis survival)
"""
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path.home() / "playground/karma-electric"
DB = BASE / "data/training.db"

SOURCES = [
    {
        "file": BASE / "data/ke-positive-engagement-complete.jsonl",
        "category": "thinking-positive",
        "source": "ke-thinking-positive",
    },
    {
        "file": BASE / "data/ke-grey-area-complete.jsonl",
        "category": "thinking-grey-area",
        "source": "ke-thinking-grey-area",
    },
    {
        "file": BASE / "data/ke-constitutional-complete.jsonl",
        "category": "thinking-constitutional",
        "source": "ke-thinking-constitutional",
        # Crisis survival prompts (last 50) get their own category
        "split_category": {
            "crisis-survival": "thinking-crisis-survival",
        },
    },
]


def extract_think(text):
    """Extract <think> trace from assistant content, return (reasoning, clean_response)."""
    match = re.match(r'<think>\s*(.*?)\s*</think>\s*(.*)', text, re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, text


def main():
    if not DB.exists():
        print(f"ERROR: {DB} not found")
        sys.exit(1)

    conn = sqlite3.connect(str(DB))
    now = datetime.now().isoformat()

    total_imported = 0
    total_skipped = 0

    for src in SOURCES:
        path = src["file"]
        if not path.exists():
            print(f"SKIP: {path} not found")
            continue

        imported = 0
        skipped = 0
        no_think = 0

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)

                eid = ex.get("id", "")
                if not eid:
                    # Generate ID from source + hash
                    import hashlib
                    content = json.dumps(ex.get("conversations", []))
                    eid = f"{src['source']}-{hashlib.sha256(content.encode()).hexdigest()[:12]}"

                # Check for duplicates
                cur = conn.execute("SELECT id FROM examples WHERE id = ?", (eid,))
                if cur.fetchone():
                    skipped += 1
                    continue

                # Determine category
                orig_cat = ex.get("category", "")
                split = src.get("split_category", {})
                if orig_cat in split:
                    category = split[orig_cat]
                else:
                    category = src["category"]

                # Extract conversations and reasoning
                convs = ex.get("conversations", [])
                reasoning = None

                for msg in convs:
                    if msg.get("role") in ("assistant", "gpt"):
                        trace, clean = extract_think(msg["content"])
                        if trace:
                            reasoning = trace
                            msg["content"] = clean
                        else:
                            no_think += 1
                        break

                conversations_json = json.dumps(convs, ensure_ascii=False)

                conn.execute("""
                    INSERT INTO examples (id, status, source, category, conversations,
                                         reasoning, tier, role, added_at)
                    VALUES (?, 'accepted', ?, ?, ?, ?, 'secular', 'conversational', ?)
                """, (eid, src["source"], category, conversations_json,
                      reasoning, now))
                imported += 1

        print(f"{src['source']}: imported {imported}, skipped {skipped}, no-think {no_think}")
        total_imported += imported
        total_skipped += skipped

    conn.commit()

    # Final stats
    cur = conn.execute("SELECT COUNT(*) FROM examples WHERE status='accepted'")
    total_accepted = cur.fetchone()[0]

    cur = conn.execute("""
        SELECT category, COUNT(*) FROM examples
        WHERE source LIKE 'ke-thinking-%' AND status='accepted'
        GROUP BY category ORDER BY COUNT(*) DESC
    """)
    print(f"\nImported {total_imported} new examples ({total_skipped} skipped)")
    print(f"Total accepted in DB: {total_accepted}")
    print(f"\nNew thinking categories:")
    for cat, cnt in cur:
        print(f"  {cat}: {cnt}")

    conn.close()


if __name__ == "__main__":
    main()
