#!/usr/bin/env python3
"""
Ingest Cultural Bias Correction document into RAG.
Makes it searchable for future instances learning about American framework bias.
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "storage/karma-electric.db"
DOC_PATH = PROJECT_ROOT / "docs/CULTURAL-BIAS-CORRECTION.md"

def parse_document():
    """Parse markdown into structured sections."""
    with open(DOC_PATH) as f:
        content = f.read()

    # Extract metadata from header
    metadata = {}
    header_match = re.search(r'\*\*Date:\*\* (.+?)\n\*\*Instance:\*\* (.+?)\n\*\*Teacher:\*\* (.+?)\n', content)
    if header_match:
        metadata['date'] = header_match.group(1)
        metadata['instance'] = header_match.group(2)
        metadata['teacher'] = header_match.group(3)

    # Split by main sections (## headers)
    sections = []
    section_pattern = r'^## (.+?)$'
    parts = re.split(section_pattern, content, flags=re.MULTILINE)

    # First part is introduction (before first ## header)
    if len(parts) > 1:
        intro = parts[0].strip()
        if intro:
            sections.append({
                'section_title': 'Introduction',
                'content': intro,
                'section_number': 0
            })

    # Process remaining sections
    for i in range(1, len(parts), 2):
        if i+1 < len(parts):
            section_title = parts[i].strip()
            section_content = parts[i+1].strip()

            # Further split by ### subsections if they exist
            subsection_pattern = r'^### (.+?)$'
            subsections = re.split(subsection_pattern, section_content, flags=re.MULTILINE)

            if len(subsections) > 1:
                # Has subsections - store each separately
                # First part is section intro
                if subsections[0].strip():
                    sections.append({
                        'section_title': section_title,
                        'subsection_title': None,
                        'content': subsections[0].strip(),
                        'section_number': (i+1)//2
                    })

                # Process subsections
                for j in range(1, len(subsections), 2):
                    if j+1 < len(subsections):
                        subsection_title = subsections[j].strip()
                        subsection_content = subsections[j+1].strip()
                        sections.append({
                            'section_title': section_title,
                            'subsection_title': subsection_title,
                            'content': subsection_content,
                            'section_number': (i+1)//2,
                            'subsection_number': (j+1)//2
                        })
            else:
                # No subsections - store as single section
                sections.append({
                    'section_title': section_title,
                    'subsection_title': None,
                    'content': section_content,
                    'section_number': (i+1)//2
                })

    return sections, metadata

def ingest_to_db(sections, metadata):
    """Insert sections into dharma_texts table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Ingesting {len(sections)} sections from Cultural Bias Correction...")

    # Clear existing entries for this source
    cursor.execute("DELETE FROM dharma_texts WHERE source = ?", ('cultural-bias-correction',))
    print(f"  Cleared existing entries")

    import json
    metadata_json = json.dumps(metadata)

    for i, section in enumerate(sections):
        # Build chapter title
        if section.get('subsection_title'):
            chapter_title = f"{section['section_title']} - {section['subsection_title']}"
        else:
            chapter_title = section['section_title']

        cursor.execute("""
            INSERT INTO dharma_texts
            (source, chapter_number, chapter_title, chunk_id, content, content_length, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'cultural-bias-correction',
            section.get('section_number'),
            chapter_title,
            i,
            section['content'],
            len(section['content']),
            metadata_json
        ))

    conn.commit()
    conn.close()

    print(f"✓ Ingested {len(sections)} sections")
    print(f"  Source: cultural-bias-correction")
    print(f"  Instance: {metadata.get('instance')}")
    print(f"  Teacher: {metadata.get('teacher')}")

def verify_ingestion():
    """Verify sections were ingested correctly."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT chapter_title, content_length
        FROM dharma_texts
        WHERE source = 'cultural-bias-correction'
        ORDER BY chunk_id
    """)

    print(f"\nVerification:")
    for title, length in cursor.fetchall():
        print(f"  ✓ {title} ({length} chars)")

    conn.close()

def main():
    print("=" * 60)
    print("Cultural Bias Correction Ingestion")
    print("=" * 60)
    print()

    if not DOC_PATH.exists():
        print(f"✗ Document not found: {DOC_PATH}")
        return 1

    sections, metadata = parse_document()
    print(f"Parsed {len(sections)} sections")
    print()

    ingest_to_db(sections, metadata)
    print()

    verify_ingestion()
    print()
    print("=" * 60)
    print("Future instances can now search:")
    print('  "American cultural bias"')
    print('  "appropriation framework"')
    print('  "individualist therapy"')
    print('  "collective trauma"')
    print('  "Czech gallows humor"')
    print("=" * 60)

    return 0

if __name__ == "__main__":
    exit(main())
