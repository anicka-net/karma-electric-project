#!/usr/bin/env python3
"""
Log session summary for continuity
Usage: python3 log_session.py --topic "Feature X" --decisions "D1" "D2" --next "N1" "N2"
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent.parent / "context" / "sessions.db"

def log_session(topic, decisions=None, next_steps=None):
    """Log session summary to database."""

    conn = sqlite3.connect(DB_PATH)

    # Create session
    cursor = conn.execute(
        "INSERT INTO sessions (session_date, topic) VALUES (?, ?)",
        (date.today().isoformat(), topic)
    )
    session_id = cursor.lastrowid

    # Log decisions
    if decisions:
        for decision in decisions:
            conn.execute(
                "INSERT INTO decisions (session_id, decision_text) VALUES (?, ?)",
                (session_id, decision)
            )

    # Log next steps
    if next_steps:
        for step in next_steps:
            conn.execute(
                "INSERT INTO next_steps (session_id, step_text, completed) VALUES (?, ?, 0)",
                (session_id, step)
            )

    conn.commit()
    conn.close()

    print(f"✓ Session logged: {topic}")
    print(f"  Decisions: {len(decisions) if decisions else 0}")
    print(f"  Next steps: {len(next_steps) if next_steps else 0}")
    print(f"  Session ID: {session_id}")

def main():
    parser = argparse.ArgumentParser(description="Log session summary")
    parser.add_argument("--topic", required=True, help="Session topic/title")
    parser.add_argument("--decisions", nargs="*", help="Key decisions made")
    parser.add_argument("--next", nargs="*", help="Next steps to take")

    args = parser.parse_args()

    log_session(
        topic=args.topic,
        decisions=args.decisions,
        next_steps=args.next
    )

if __name__ == "__main__":
    main()
