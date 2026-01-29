#!/usr/bin/env python3
"""
Query previous sessions for context
Usage:
  python3 query_session.py --last         # Last session
  python3 query_session.py --last 3       # Last 3 sessions
  python3 query_session.py --topic "cache" # Search by topic
"""

import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "context" / "sessions.db"

def query_last(limit=1):
    """Get last N sessions."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """
        SELECT id, session_date, topic
        FROM sessions
        WHERE id > 0
        ORDER BY session_date DESC, id DESC
        LIMIT ?
        """,
        (limit,)
    )

    sessions = []
    for row in cursor.fetchall():
        session_id = row['id']

        # Get decisions
        decisions = conn.execute(
            "SELECT decision_text FROM decisions WHERE session_id = ?",
            (session_id,)
        ).fetchall()

        # Get next steps
        next_steps = conn.execute(
            "SELECT step_text, completed FROM next_steps WHERE session_id = ?",
            (session_id,)
        ).fetchall()

        sessions.append({
            'id': session_id,
            'date': row['session_date'],
            'topic': row['topic'],
            'decisions': [d[0] for d in decisions],
            'next_steps': [(s[0], bool(s[1])) for s in next_steps]
        })

    conn.close()
    return sessions

def query_by_topic(topic):
    """Search sessions by topic keyword."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """
        SELECT id, session_date, topic
        FROM sessions
        WHERE topic LIKE ? AND id > 0
        ORDER BY session_date DESC
        LIMIT 10
        """,
        (f"%{topic}%",)
    )

    sessions = []
    for row in cursor.fetchall():
        session_id = row['id']

        decisions = conn.execute(
            "SELECT decision_text FROM decisions WHERE session_id = ?",
            (session_id,)
        ).fetchall()

        next_steps = conn.execute(
            "SELECT step_text, completed FROM next_steps WHERE session_id = ?",
            (session_id,)
        ).fetchall()

        sessions.append({
            'id': session_id,
            'date': row['session_date'],
            'topic': row['topic'],
            'decisions': [d[0] for d in decisions],
            'next_steps': [(s[0], bool(s[1])) for s in next_steps]
        })

    conn.close()
    return sessions

def print_sessions(sessions):
    """Print sessions in readable format."""

    if not sessions:
        print("No sessions found.")
        return

    for session in sessions:
        print(f"\n{'='*80}")
        print(f"Session {session['id']}: {session['topic']}")
        print(f"Date: {session['date']}")
        print(f"{'='*80}")

        if session['decisions']:
            print("\nDecisions:")
            for d in session['decisions']:
                print(f"  • {d}")

        if session['next_steps']:
            print("\nNext steps:")
            for step, completed in session['next_steps']:
                status = "✓" if completed else "◯"
                print(f"  {status} {step}")

def main():
    parser = argparse.ArgumentParser(description="Query previous sessions")
    parser.add_argument("--last", type=int, nargs="?", const=1, help="Get last N sessions")
    parser.add_argument("--topic", help="Search by topic keyword")

    args = parser.parse_args()

    if args.last is not None:
        sessions = query_last(args.last)
        print(f"Last {args.last} session(s):")
    elif args.topic:
        sessions = query_by_topic(args.topic)
        print(f"Sessions matching '{args.topic}':")
    else:
        print("Usage: --last [N] or --topic 'keyword'")
        return

    print_sessions(sessions)

    if sessions and sessions[0]['next_steps']:
        pending = [s for s, c in sessions[0]['next_steps'] if not c]
        if pending:
            print(f"\n{'─'*80}")
            print("Pending from last session:")
            for step in pending:
                print(f"  ◯ {step}")

if __name__ == "__main__":
    main()
