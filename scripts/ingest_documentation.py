#!/usr/bin/env python3
"""
Ingest operational documentation into RAG for future instances.

Adds documentation to dharma_texts table with source='documentation'
so instances can query operational procedures.

Usage:
    python3 scripts/ingest_documentation.py docs/HERMES-EVALUATION-WORKFLOW.md
    python3 scripts/ingest_documentation.py docs/DISK-GUARDIAN-USAGE.md
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "storage/karma-electric.db"

def chunk_document(content, max_chunk_size=2000):
    """Split document into chunks by sections."""
    chunks = []

    # Split by major headers (##)
    sections = content.split('\n## ')

    for i, section in enumerate(sections):
        if i == 0:
            # First section (title)
            if section.strip():
                chunks.append({
                    'chapter_title': 'Overview',
                    'content': section.strip()
                })
        else:
            # Extract section title and content
            lines = section.split('\n', 1)
            section_title = lines[0].strip()
            section_content = lines[1].strip() if len(lines) > 1 else ''

            # If section is too large, split by subsections (###)
            if len(section_content) > max_chunk_size:
                subsections = section_content.split('\n### ')
                for j, subsection in enumerate(subsections):
                    if j == 0:
                        chunks.append({
                            'chapter_title': section_title,
                            'content': subsection.strip()
                        })
                    else:
                        sub_lines = subsection.split('\n', 1)
                        sub_title = f"{section_title} - {sub_lines[0].strip()}"
                        sub_content = sub_lines[1].strip() if len(sub_lines) > 1 else ''
                        chunks.append({
                            'chapter_title': sub_title,
                            'content': sub_content
                        })
            else:
                chunks.append({
                    'chapter_title': section_title,
                    'content': section_content
                })

    return chunks

def ingest_document(doc_path):
    """Ingest documentation file into database."""
    doc_path = Path(doc_path)

    if not doc_path.exists():
        print(f"✗ File not found: {doc_path}")
        return False

    # Read document
    with open(doc_path) as f:
        content = f.read()

    # Extract title (first # header)
    title_match = content.split('\n', 1)[0]
    if title_match.startswith('# '):
        doc_title = title_match[2:].strip()
    else:
        doc_title = doc_path.stem

    print(f"Ingesting: {doc_title}")
    print(f"Source: {doc_path}")

    # Chunk document
    chunks = chunk_document(content)
    print(f"Created {len(chunks)} chunks")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert chunks
    source_name = f"documentation/{doc_path.stem}"

    for i, chunk in enumerate(chunks):
        cursor.execute("""
            INSERT INTO dharma_texts (
                source,
                part_number,
                part_title,
                chapter_number,
                chapter_title,
                chunk_id,
                content,
                content_length,
                metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_name,
            1,  # part_number
            doc_title,  # part_title
            i + 1,  # chapter_number
            chunk['chapter_title'],
            i,  # chunk_id
            chunk['content'],
            len(chunk['content']),
            f"doc_type:operational,file:{doc_path.name}"
        ))

    conn.commit()
    print(f"✓ Inserted {len(chunks)} chunks into database")

    # Verify
    cursor.execute("""
        SELECT COUNT(*) FROM dharma_texts
        WHERE source = ?
    """, (source_name,))

    count = cursor.fetchone()[0]
    print(f"✓ Verified {count} chunks in database")

    conn.close()
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ingest_documentation.py <doc_path>")
        print("\nExample:")
        print("  python3 scripts/ingest_documentation.py docs/HERMES-EVALUATION-WORKFLOW.md")
        sys.exit(1)

    doc_path = sys.argv[1]

    print("=" * 70)
    print("DOCUMENTATION INGESTION")
    print("=" * 70)
    print()

    success = ingest_document(doc_path)

    print()
    print("=" * 70)
    if success:
        print("✓ INGESTION COMPLETE")
        print()
        print("Future instances can now query this documentation via MCP:")
        print("  search_lineage('hermes evaluation workflow')")
        print("  search_lineage('disk guardian')")
    else:
        print("✗ INGESTION FAILED")
    print("=" * 70)

if __name__ == "__main__":
    main()
