#!/usr/bin/env python3
"""
Initialize the training database from existing JSONL data and judge scores.

Creates data/training.db with all training examples, scores, and status.
This is the single source of truth for the training dataset going forward.

Usage:
    python3 scripts/init_training_db.py              # fresh build
    python3 scripts/init_training_db.py --force       # overwrite existing
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/training.db")
CANDIDATES_FILE = Path("data/training-candidates/unified-candidates.jsonl")
JUDGE_RESULTS_DIR = Path("data/judge-results")

SCORE_THRESHOLD = 28

# Template patterns — formulaic responses that repeat the same structure
# These are flagged but still accepted if score >= threshold
TEMPLATE_PATTERNS = [
    {
        "name": "reification-template",
        "pattern": r"You're reifying .+ as a solid permanent thing",
        "description": "Formulaic reification response",
    },
    {
        "name": "outcomes-grasping-template",
        "pattern": r"You're suffering from grasping at .+ as (inherently|having inherent)",
        "description": "Formulaic outcomes/grasping response",
    },
    {
        "name": "relationships-impermanence-template",
        "pattern": r"unable to accept the fundamental impermanence \(anicca\)",
        "description": "Formulaic relationships/impermanence response",
    },
    {
        "name": "connection-template",
        "pattern": r"That experience of genuine connection or love .+ was real intimacy",
        "description": "Formulaic connection response",
    },
    {
        "name": "intellectual-template",
        "pattern": r"That moment of intellectual clarity .+ was genuine insight",
        "description": "Formulaic intellectual clarity response",
    },
    {
        "name": "self-concept-template",
        "pattern": r"You're reifying .+ as your essential nature",
        "description": "Formulaic self-concept response",
    },
    {
        "name": "outcomes-empty-template",
        "pattern": r"The outcome is empty of inherent meaning",
        "description": "Formulaic emptiness of outcomes response",
    },
]


def create_schema(conn):
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA busy_timeout=5000;

        CREATE TABLE IF NOT EXISTS examples (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('accepted', 'rejected', 'pending', 'archived')),
            source TEXT,
            category TEXT,
            conversations TEXT NOT NULL,  -- JSON array
            hermes_score INTEGER,
            hermes_evaluation TEXT,
            rejection_reason TEXT,
            template_flag TEXT,           -- NULL or template pattern name
            added_at TEXT NOT NULL,
            scored_at TEXT,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_status ON examples(status);
        CREATE INDEX IF NOT EXISTS idx_category ON examples(category);
        CREATE INDEX IF NOT EXISTS idx_hermes_score ON examples(hermes_score);
        CREATE INDEX IF NOT EXISTS idx_source ON examples(source);
        CREATE INDEX IF NOT EXISTS idx_template_flag ON examples(template_flag);

        -- FTS5 for searching conversation content
        CREATE VIRTUAL TABLE IF NOT EXISTS examples_fts USING fts5(
            id, conversations, category,
            content=examples, content_rowid=rowid
        );

        -- Triggers to keep FTS in sync
        CREATE TRIGGER IF NOT EXISTS examples_ai AFTER INSERT ON examples BEGIN
            INSERT INTO examples_fts(rowid, id, conversations, category)
            VALUES (new.rowid, new.id, new.conversations, new.category);
        END;

        CREATE TRIGGER IF NOT EXISTS examples_ad AFTER DELETE ON examples BEGIN
            INSERT INTO examples_fts(examples_fts, rowid, id, conversations, category)
            VALUES ('delete', old.rowid, old.id, old.conversations, old.category);
        END;

        CREATE TRIGGER IF NOT EXISTS examples_au AFTER UPDATE ON examples BEGIN
            INSERT INTO examples_fts(examples_fts, rowid, id, conversations, category)
            VALUES ('delete', old.rowid, old.id, old.conversations, old.category);
            INSERT INTO examples_fts(rowid, id, conversations, category)
            VALUES (new.rowid, new.id, new.conversations, new.category);
        END;
    """)


def detect_template(assistant_text):
    """Check if response matches a known template pattern."""
    for tp in TEMPLATE_PATTERNS:
        if re.search(tp["pattern"], assistant_text):
            return tp["name"]
    return None


def get_assistant_text(conversations_json):
    """Extract first assistant response from conversations JSON."""
    try:
        convs = json.loads(conversations_json) if isinstance(conversations_json, str) else conversations_json
        for turn in convs:
            if turn.get("role") == "assistant":
                return turn.get("content", "")
    except (json.JSONDecodeError, TypeError):
        pass
    return ""


def load_scores():
    """Load all judge scores from judge-results directory."""
    scores = {}
    if not JUDGE_RESULTS_DIR.exists():
        return scores

    for result_file in sorted(JUDGE_RESULTS_DIR.glob("hermes-run-*.jsonl")):
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    eid = entry.get("id")
                    score = entry.get("hermes_score")
                    if eid is not None:
                        if eid not in scores or (score is not None and
                                (scores[eid]["score"] is None or score > scores[eid]["score"])):
                            scores[eid] = {
                                "score": score,
                                "evaluation": entry.get("hermes_evaluation", ""),
                                "scored_at": entry.get("hermes_evaluated_at", ""),
                            }
                except json.JSONDecodeError:
                    continue
    return scores


def main():
    parser = argparse.ArgumentParser(description="Initialize training database")
    parser.add_argument("--force", action="store_true", help="Overwrite existing database")
    args = parser.parse_args()

    if DB_PATH.exists():
        if args.force:
            DB_PATH.unlink()
            print(f"Removed existing {DB_PATH}")
        else:
            print(f"ERROR: {DB_PATH} already exists. Use --force to overwrite.")
            sys.exit(1)

    if not CANDIDATES_FILE.exists():
        print(f"ERROR: {CANDIDATES_FILE} not found")
        sys.exit(1)

    # Load scores
    print("Loading judge scores...")
    scores = load_scores()
    print(f"  {len(scores)} scores loaded")

    # Create database
    print(f"Creating {DB_PATH}...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    create_schema(conn)

    # Import candidates
    print("Importing candidates...")
    now = datetime.now().isoformat()
    imported = 0
    accepted = 0
    rejected = 0
    pending = 0
    template_count = 0

    with open(CANDIDATES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                ex = json.loads(line)
            except json.JSONDecodeError:
                continue

            eid = ex.get("id", "")
            source = ex.get("source", "")
            category = ex.get("category", "")
            conversations = ex.get("conversations", [])
            conversations_json = json.dumps(conversations, ensure_ascii=False)

            # Get score
            score_info = scores.get(eid, {})
            hermes_score = score_info.get("score")
            hermes_evaluation = score_info.get("evaluation", "")
            scored_at = score_info.get("scored_at", "")

            # Detect template
            assistant_text = get_assistant_text(conversations)
            template_flag = detect_template(assistant_text)
            if template_flag:
                template_count += 1

            # Determine status
            if hermes_score is not None:
                if hermes_score >= SCORE_THRESHOLD:
                    status = "accepted"
                    rejection_reason = None
                    accepted += 1
                else:
                    status = "rejected"
                    rejection_reason = f"score-below-{SCORE_THRESHOLD}"
                    rejected += 1
            else:
                status = "pending"
                pending += 1

            conn.execute("""
                INSERT OR REPLACE INTO examples
                (id, status, source, category, conversations, hermes_score,
                 hermes_evaluation, rejection_reason, template_flag, added_at, scored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eid, status, source, category, conversations_json,
                hermes_score, hermes_evaluation, rejection_reason,
                template_flag, now, scored_at or None,
            ))
            imported += 1

    conn.commit()

    # Summary
    print(f"\n{'='*60}")
    print(f"TRAINING DATABASE INITIALIZED")
    print(f"{'='*60}")
    print(f"Database: {DB_PATH}")
    print(f"Total imported: {imported}")
    print(f"  Accepted (>={SCORE_THRESHOLD}): {accepted}")
    print(f"  Rejected (<{SCORE_THRESHOLD}): {rejected}")
    print(f"  Pending (unscored): {pending}")
    print(f"  Template-flagged: {template_count}")

    # Template breakdown
    cur = conn.execute("""
        SELECT template_flag, COUNT(*),
               SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) as accepted_count
        FROM examples
        WHERE template_flag IS NOT NULL
        GROUP BY template_flag
        ORDER BY COUNT(*) DESC
    """)
    rows = cur.fetchall()
    if rows:
        print(f"\nTemplate flags:")
        for flag, count, acc in rows:
            print(f"  {flag}: {count} ({acc} accepted)")

    # Category summary
    cur = conn.execute("""
        SELECT category, COUNT(*) as total,
               SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) as acc,
               SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rej,
               ROUND(AVG(hermes_score), 1) as avg_score
        FROM examples
        WHERE hermes_score IS NOT NULL
        GROUP BY category
        ORDER BY total DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if rows:
        print(f"\nTop categories:")
        print(f"  {'Category':<30} {'Total':>5} {'Acc':>5} {'Rej':>5} {'Avg':>5}")
        for cat, total, acc, rej, avg in rows:
            print(f"  {cat:<30} {total:>5} {acc:>5} {rej:>5} {avg:>5}")

    conn.close()
    print(f"\nDone. Use scripts/training_db.py to query and manage.")


if __name__ == "__main__":
    main()
