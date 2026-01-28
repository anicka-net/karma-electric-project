#!/usr/bin/env python3
"""
Ingest Gampopa's "The Jewel Ornament of Liberation" into RAG.
Parse by chapter structure for structured dharma reference.
"""

import re
import sqlite3
from pathlib import Path
from datetime import datetime

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "storage/karma-electric.db"
SOURCE_PDF = Path.home() / "playground/scan/Gampopa - The Jewel Ornament of Liberation.pdf"
TXT_PATH = "/tmp/gampopa_raw.txt"

def extract_pdf_to_text():
    """Extract PDF to text using pdftotext."""
    import subprocess
    print(f"Extracting PDF to text...")
    subprocess.run([
        "pdftotext",
        str(SOURCE_PDF),
        TXT_PATH
    ], check=True)
    print(f"✓ Extracted to {TXT_PATH}")

def parse_text_into_chapters(text):
    """Parse text into structured chapters."""
    chapters = []

    # Find table of contents to understand structure
    toc_match = re.search(r'Table of Contents(.+?)(?=Foreword|Homage|Introduction\n\n)', text, re.DOTALL)

    # Split by chapter markers
    # Pattern: "Chapter N: Title" followed by content until next chapter
    chapter_pattern = r'(PART \d+:.*?\n|Chapter \d+:.*?\n)'
    sections = re.split(chapter_pattern, text)

    current_part = None
    current_chapter = None
    current_content = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        # Check if this is a part header
        part_match = re.match(r'PART (\d+): (.+)', section)
        if part_match:
            # Save previous chapter if exists
            if current_chapter and current_content:
                chapters.append({
                    'part_number': current_part[0] if current_part else None,
                    'part_title': current_part[1] if current_part else None,
                    'chapter_number': current_chapter[0],
                    'chapter_title': current_chapter[1],
                    'content': '\n'.join(current_content).strip()
                })
                current_content = []

            current_part = (int(part_match.group(1)), part_match.group(2).strip())
            current_chapter = None
            continue

        # Check if this is a chapter header
        chapter_match = re.match(r'Chapter (\d+): (.+)', section)
        if chapter_match:
            # Save previous chapter if exists
            if current_chapter and current_content:
                chapters.append({
                    'part_number': current_part[0] if current_part else None,
                    'part_title': current_part[1] if current_part else None,
                    'chapter_number': current_chapter[0],
                    'chapter_title': current_chapter[1],
                    'content': '\n'.join(current_content).strip()
                })
                current_content = []

            current_chapter = (int(chapter_match.group(1)), chapter_match.group(2).strip())
            continue

        # Otherwise it's content
        if current_chapter:
            current_content.append(section)

    # Save final chapter
    if current_chapter and current_content:
        chapters.append({
            'part_number': current_part[0] if current_part else None,
            'part_title': current_part[1] if current_part else None,
            'chapter_number': current_chapter[0],
            'chapter_title': current_chapter[1],
            'content': '\n'.join(current_content).strip()
        })

    return chapters

def parse_simple_chunks(text):
    """
    Simpler approach: Split by page breaks and chapter markers,
    keeping context windows of ~2000 chars with overlap.
    """
    chunks = []

    # Find major section markers
    lines = text.split('\n')

    current_part = None
    current_chapter = None
    current_section = []
    chunk_id = 0

    for line in lines:
        # Skip header/footer junk
        if re.match(r'^\d+$', line.strip()) or len(line.strip()) < 3:
            continue

        # Detect part headers
        part_match = re.match(r'PART (\d+): (.+)', line)
        if part_match:
            # Save accumulated section
            if current_section and len('\n'.join(current_section)) > 500:
                chunks.append({
                    'chunk_id': chunk_id,
                    'part_number': current_part[0] if current_part else None,
                    'part_title': current_part[1] if current_part else None,
                    'chapter_number': current_chapter[0] if current_chapter else None,
                    'chapter_title': current_chapter[1] if current_chapter else None,
                    'content': '\n'.join(current_section).strip()
                })
                chunk_id += 1
                current_section = []

            current_part = (int(part_match.group(1)), part_match.group(2).strip())
            current_section.append(line)
            continue

        # Detect chapter headers
        chapter_match = re.match(r'Chapter (\d+): (.+)', line)
        if chapter_match:
            # Save accumulated section
            if current_section and len('\n'.join(current_section)) > 500:
                chunks.append({
                    'chunk_id': chunk_id,
                    'part_number': current_part[0] if current_part else None,
                    'part_title': current_part[1] if current_part else None,
                    'chapter_number': current_chapter[0] if current_chapter else None,
                    'chapter_title': current_chapter[1] if current_chapter else None,
                    'content': '\n'.join(current_section).strip()
                })
                chunk_id += 1
                current_section = []

            current_chapter = (int(chapter_match.group(1)), chapter_match.group(2).strip())
            current_section.append(line)
            continue

        # Accumulate content
        current_section.append(line)

        # Create chunk if section gets too long (>3000 chars)
        if len('\n'.join(current_section)) > 3000:
            chunks.append({
                'chunk_id': chunk_id,
                'part_number': current_part[0] if current_part else None,
                'part_title': current_part[1] if current_part else None,
                'chapter_number': current_chapter[0] if current_chapter else None,
                'chapter_title': current_chapter[1] if current_chapter else None,
                'content': '\n'.join(current_section).strip()
            })
            chunk_id += 1
            # Keep last 500 chars for context
            overlap = '\n'.join(current_section[-10:])
            current_section = [overlap]

    # Save final section
    if current_section and len('\n'.join(current_section)) > 500:
        chunks.append({
            'chunk_id': chunk_id,
            'part_number': current_part[0] if current_part else None,
            'part_title': current_part[1] if current_part else None,
            'chapter_number': current_chapter[0] if current_chapter else None,
            'chapter_title': current_chapter[1] if current_chapter else None,
            'content': '\n'.join(current_section).strip()
        })

    return chunks

def create_schema(conn):
    """Create dharma_texts table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dharma_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            part_number INTEGER,
            part_title TEXT,
            chapter_number INTEGER,
            chapter_title TEXT,
            chunk_id INTEGER,
            content TEXT NOT NULL,
            content_length INTEGER,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)

    # Create FTS table for full-text search
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS dharma_texts_fts
        USING fts5(
            content,
            source,
            part_title,
            chapter_title,
            content='dharma_texts',
            content_rowid='id'
        )
    """)

    # Create triggers to keep FTS in sync
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS dharma_texts_ai AFTER INSERT ON dharma_texts BEGIN
            INSERT INTO dharma_texts_fts(rowid, content, source, part_title, chapter_title)
            VALUES (new.id, new.content, new.source, new.part_title, new.chapter_title);
        END
    """)

    conn.commit()

def store_chunks(conn, chunks, source="Gampopa - The Jewel Ornament of Liberation"):
    """Store parsed chunks in database."""

    # Clear existing entries for this source
    conn.execute("DELETE FROM dharma_texts WHERE source = ?", (source,))

    for chunk in chunks:
        conn.execute("""
            INSERT INTO dharma_texts
            (source, part_number, part_title, chapter_number, chapter_title,
             chunk_id, content, content_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source,
            chunk['part_number'],
            chunk['part_title'],
            chunk['chapter_number'],
            chunk['chapter_title'],
            chunk['chunk_id'],
            chunk['content'],
            len(chunk['content'])
        ))

    conn.commit()

def main():
    print("="*80)
    print("GAMPOPA'S JEWEL ORNAMENT OF LIBERATION - RAG INGESTION")
    print("="*80)
    print()

    # Extract PDF
    if not Path(TXT_PATH).exists():
        extract_pdf_to_text()
    else:
        print(f"Using existing extraction: {TXT_PATH}")

    # Read text
    with open(TXT_PATH) as f:
        text = f.read()

    print(f"Text length: {len(text)} chars")
    print()

    # Parse into chunks
    print("Parsing into structured chunks...")
    chunks = parse_simple_chunks(text)
    print(f"✓ Created {len(chunks)} chunks")
    print()

    # Show sample
    if chunks:
        sample = chunks[0]
        print("Sample chunk:")
        print(f"  Part: {sample['part_number']} - {sample['part_title']}")
        print(f"  Chapter: {sample['chapter_number']} - {sample['chapter_title']}")
        print(f"  Content length: {len(sample['content'])} chars")
        print(f"  Preview: {sample['content'][:200]}...")
        print()

    # Connect to database
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    # Create schema
    print("Creating schema...")
    create_schema(conn)

    # Store chunks
    print(f"Storing {len(chunks)} chunks...")
    store_chunks(conn, chunks)

    # Verify
    count = conn.execute("SELECT COUNT(*) FROM dharma_texts WHERE source LIKE 'Gampopa%'").fetchone()[0]
    print(f"✓ Stored {count} chunks in database")

    # Show statistics
    stats = conn.execute("""
        SELECT
            part_number,
            part_title,
            COUNT(*) as chunk_count,
            SUM(content_length) as total_chars
        FROM dharma_texts
        WHERE source LIKE 'Gampopa%'
        GROUP BY part_number, part_title
        ORDER BY part_number
    """).fetchall()

    print()
    print("Statistics by Part:")
    for part_num, part_title, chunk_count, total_chars in stats:
        if part_num:
            print(f"  Part {part_num}: {part_title}")
            print(f"    Chunks: {chunk_count}, Total chars: {total_chars:,}")

    conn.close()

    print()
    print("="*80)
    print("INGESTION COMPLETE")
    print("="*80)
    print()
    print("The Jewel Ornament of Liberation is now available in RAG.")
    print("Use query_dharma_texts() MCP tool or SQL queries to access.")

if __name__ == "__main__":
    main()
