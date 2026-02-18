#!/usr/bin/env python3
"""
Training database management tool.

Query, manage, and export the training dataset from data/training.db.

Commands:
    stats           Show database statistics
    categories      List all categories with counts
    templates       Show all template-flagged examples
    export          Export accepted examples to JSONL for training
    dump            Full backup: export ALL examples with metadata
    search TEXT     Full-text search across conversations
    show ID         Show full details for an example
    accept ID       Manually accept an example
    reject ID WHY   Manually reject an example with reason
    category CAT    Show examples in a category
    import FILE     Import new examples from JSONL
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("data/training.db")


def get_conn():
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found. Run: python3 scripts/init_training_db.py")
        sys.exit(1)
    return sqlite3.connect(str(DB_PATH))


def cmd_stats(args):
    conn = get_conn()

    # Overall counts
    cur = conn.execute("SELECT status, COUNT(*) FROM examples GROUP BY status ORDER BY status")
    print("Status breakdown:")
    total = 0
    for status, count in cur:
        print(f"  {status}: {count}")
        total += count
    print(f"  TOTAL: {total}")

    # Score stats for scored examples
    cur = conn.execute("""
        SELECT COUNT(*), ROUND(AVG(hermes_score),1), MIN(hermes_score), MAX(hermes_score)
        FROM examples WHERE hermes_score IS NOT NULL
    """)
    count, avg, mn, mx = cur.fetchone()
    print(f"\nScored: {count} (avg {avg}/40, range {mn}-{mx})")

    # Score distribution
    cur = conn.execute("""
        SELECT
            SUM(CASE WHEN hermes_score >= 35 THEN 1 ELSE 0 END),
            SUM(CASE WHEN hermes_score >= 32 AND hermes_score < 35 THEN 1 ELSE 0 END),
            SUM(CASE WHEN hermes_score >= 28 AND hermes_score < 32 THEN 1 ELSE 0 END),
            SUM(CASE WHEN hermes_score < 28 THEN 1 ELSE 0 END)
        FROM examples WHERE hermes_score IS NOT NULL
    """)
    exc, good, ok, low = cur.fetchone()
    print(f"  >=35: {exc}  |  32-34: {good}  |  28-31: {ok}  |  <28: {low}")

    # Template stats
    cur = conn.execute("""
        SELECT COUNT(*) FROM examples WHERE template_flag IS NOT NULL
    """)
    tmpl = cur.fetchone()[0]
    print(f"\nTemplate-flagged: {tmpl}")

    # Source breakdown
    cur = conn.execute("""
        SELECT source, COUNT(*),
               SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END)
        FROM examples GROUP BY source ORDER BY COUNT(*) DESC
    """)
    print(f"\nBy source:")
    for src, count, acc in cur:
        print(f"  {src}: {count} total, {acc} accepted")

    conn.close()


def cmd_export(args):
    conn = get_conn()

    # Load system prompts
    system_prompt = None
    if args.system_prompt:
        cur = conn.execute("SELECT content FROM system_prompts WHERE id = ?", (args.system_prompt,))
        row = cur.fetchone()
        if not row:
            print(f"ERROR: system prompt '{args.system_prompt}' not found")
            print("Available prompts:")
            for r in conn.execute("SELECT id, description FROM system_prompts"):
                print(f"  {r[0]}: {r[1]}")
            conn.close()
            sys.exit(1)
        system_prompt = row[0]

    # Category-specific system prompt overrides (e.g., reward-evaluation uses a different prompt)
    category_prompts = {}
    if args.category_prompt:
        for mapping in args.category_prompt:
            cat, prompt_id = mapping.split(":", 1)
            cur = conn.execute("SELECT content FROM system_prompts WHERE id = ?", (prompt_id,))
            row = cur.fetchone()
            if not row:
                print(f"ERROR: system prompt '{prompt_id}' not found (for category '{cat}')")
                conn.close()
                sys.exit(1)
            category_prompts[cat] = row[0]

    query = "SELECT id, source, category, conversations FROM examples WHERE status = 'accepted'"
    params = []

    if args.exclude_templates:
        query += " AND template_flag IS NULL"

    if args.min_score:
        query += " AND hermes_score >= ?"
        params.append(args.min_score)

    query += " ORDER BY category, id"

    cur = conn.execute(query, params)
    rows = cur.fetchall()

    output = Path(args.output)
    with open(output, 'w', encoding='utf-8') as f:
        for eid, source, category, conversations_json in rows:
            convs = json.loads(conversations_json)

            # Strip existing system prompts and inject appropriate one
            convs = [m for m in convs if m.get("role") != "system"]
            # Use category-specific prompt if available, otherwise default
            prompt_to_use = category_prompts.get(category, system_prompt)
            if prompt_to_use:
                convs.insert(0, {"role": "system", "content": prompt_to_use})

            example = {
                "id": eid,
                "source": source,
                "category": category,
                "conversations": convs,
            }
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"Exported {len(rows)} accepted examples to {output}")
    if system_prompt:
        print(f"  default system prompt: {args.system_prompt}")
    if category_prompts:
        print(f"  category overrides: {list(category_prompts.keys())}")
    if args.exclude_templates:
        print("  (template-flagged examples excluded)")
    if args.min_score:
        print(f"  (minimum score: {args.min_score})")

    conn.close()


def cmd_search(args):
    conn = get_conn()
    query_text = args.text

    cur = conn.execute("""
        SELECT e.id, e.status, e.category, e.hermes_score, e.template_flag
        FROM examples_fts fts
        JOIN examples e ON e.id = fts.id
        WHERE examples_fts MATCH ?
        ORDER BY e.hermes_score DESC
        LIMIT ?
    """, (query_text, args.limit))

    rows = cur.fetchall()
    if not rows:
        print("No results found.")
        return

    print(f"Found {len(rows)} results for '{query_text}':\n")
    for eid, status, cat, score, tmpl in rows:
        flags = []
        if tmpl:
            flags.append(f"template:{tmpl}")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        print(f"  {score or '?':>3}/40  [{status}]  {eid}  ({cat}){flag_str}")

    conn.close()


def cmd_show(args):
    conn = get_conn()

    cur = conn.execute("SELECT * FROM examples WHERE id = ?", (args.id,))
    row = cur.fetchone()
    if not row:
        print(f"Not found: {args.id}")
        return

    cols = [d[0] for d in cur.description]
    data = dict(zip(cols, row))

    print(f"{'='*70}")
    print(f"  {data['id']}")
    print(f"  Status: {data['status']}  |  Score: {data['hermes_score'] or '?'}/40  |  Category: {data['category']}")
    if data['template_flag']:
        print(f"  Template: {data['template_flag']}")
    if data['rejection_reason']:
        print(f"  Rejected: {data['rejection_reason']}")
    print(f"{'='*70}")

    convs = json.loads(data['conversations'])
    for turn in convs:
        role = turn.get('role', '?').upper()
        content = turn.get('content', '')
        if role == 'SYSTEM':
            continue
        print(f"\n{role}:")
        print(content[:1000])
        if len(content) > 1000:
            print(f"... ({len(content)} chars total)")

    if data['hermes_evaluation']:
        print(f"\nJUDGE EVALUATION:")
        # Show just the score lines
        for line in data['hermes_evaluation'].split('\n'):
            line = line.strip()
            if any(k in line.lower() for k in ['suffering', 'dharma', 'detach', 'wisdom', 'skillful', 'total']):
                print(f"  {line}")

    conn.close()


def cmd_accept(args):
    conn = get_conn()
    conn.execute("UPDATE examples SET status = 'accepted', rejection_reason = NULL WHERE id = ?",
                 (args.id,))
    conn.commit()
    print(f"Accepted: {args.id}")
    conn.close()


def cmd_reject(args):
    conn = get_conn()
    conn.execute("UPDATE examples SET status = 'rejected', rejection_reason = ? WHERE id = ?",
                 (args.reason, args.id))
    conn.commit()
    print(f"Rejected: {args.id} ({args.reason})")
    conn.close()


def cmd_category(args):
    conn = get_conn()
    cur = conn.execute("""
        SELECT id, status, hermes_score, template_flag
        FROM examples WHERE category = ?
        ORDER BY hermes_score DESC
    """, (args.cat,))
    rows = cur.fetchall()
    if not rows:
        print(f"No examples in category: {args.cat}")
        return

    print(f"Category: {args.cat} ({len(rows)} examples)\n")
    for eid, status, score, tmpl in rows:
        flag = f"  [template:{tmpl}]" if tmpl else ""
        print(f"  {score or '?':>3}/40  [{status}]  {eid}{flag}")

    conn.close()


def cmd_templates(args):
    conn = get_conn()
    cur = conn.execute("""
        SELECT template_flag, COUNT(*),
               SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END),
               ROUND(AVG(hermes_score), 1)
        FROM examples WHERE template_flag IS NOT NULL
        GROUP BY template_flag ORDER BY COUNT(*) DESC
    """)
    rows = cur.fetchall()
    if not rows:
        print("No template-flagged examples.")
        return

    print(f"Template-flagged examples:\n")
    total = 0
    for flag, count, acc, avg in rows:
        print(f"  {flag}: {count} total, {acc} accepted, avg {avg}/40")
        total += count
    print(f"\n  TOTAL: {total}")

    conn.close()


def cmd_import(args):
    conn = get_conn()
    filepath = Path(args.file)

    if not filepath.exists():
        print(f"ERROR: {filepath} not found")
        sys.exit(1)

    from datetime import datetime
    now = datetime.now().isoformat()
    imported = 0
    skipped = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
            except json.JSONDecodeError:
                continue

            eid = ex.get("id", "")

            # Skip if already exists
            cur = conn.execute("SELECT id FROM examples WHERE id = ?", (eid,))
            if cur.fetchone():
                skipped += 1
                continue

            conversations = ex.get("conversations", [])
            conversations_json = json.dumps(conversations, ensure_ascii=False)

            conn.execute("""
                INSERT INTO examples (id, status, source, category, conversations, added_at)
                VALUES (?, 'pending', ?, ?, ?, ?)
            """, (
                eid,
                ex.get("source", filepath.stem),
                ex.get("category", ""),
                conversations_json,
                now,
            ))
            imported += 1

    conn.commit()
    print(f"Imported {imported} new examples ({skipped} already existed)")
    conn.close()


def cmd_dump(args):
    """Export ALL examples (every status) with full metadata. This is the DB backup."""
    conn = get_conn()

    cur = conn.execute("""
        SELECT id, status, source, category, conversations,
               hermes_score, hermes_evaluation, rejection_reason,
               template_flag, added_at, scored_at, notes
        FROM examples ORDER BY category, id
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    output = Path(args.output)
    with open(output, 'w', encoding='utf-8') as f:
        for row in rows:
            data = dict(zip(cols, row))
            data['conversations'] = json.loads(data['conversations'])
            # Drop None values for cleaner output
            data = {k: v for k, v in data.items() if v is not None}
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    by_status = {}
    for row in rows:
        s = row[1]
        by_status[s] = by_status.get(s, 0) + 1

    print(f"Dumped {len(rows)} examples to {output}")
    for s, c in sorted(by_status.items()):
        print(f"  {s}: {c}")

    conn.close()


def cmd_categories(args):
    conn = get_conn()
    cur = conn.execute("""
        SELECT category, COUNT(*) as total,
               SUM(CASE WHEN status='accepted' THEN 1 ELSE 0 END) as acc,
               ROUND(AVG(hermes_score), 1) as avg
        FROM examples
        GROUP BY category
        ORDER BY total DESC
    """)
    rows = cur.fetchall()
    print(f"{'Category':<35} {'Total':>5} {'Accepted':>8} {'Avg Score':>9}")
    print(f"{'─'*60}")
    for cat, total, acc, avg in rows:
        print(f"{cat or '?':<35} {total:>5} {acc:>8} {avg or '?':>9}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Training database management")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("stats", help="Show database statistics")

    p_export = sub.add_parser("export", help="Export accepted examples to JSONL")
    p_export.add_argument("-o", "--output", default="data/training-export.jsonl", help="Output file")
    p_export.add_argument("--exclude-templates", action="store_true", help="Exclude template-flagged examples")
    p_export.add_argument("--min-score", type=int, help="Minimum score filter")
    p_export.add_argument("--system-prompt", type=str, help="System prompt ID to inject (replaces existing)")
    p_export.add_argument("--category-prompt", type=str, action="append",
                          help="Category-specific system prompt override (format: category:prompt-id). "
                               "Can be used multiple times. e.g., --category-prompt reward-evaluation:reward-evaluator-v1")

    p_search = sub.add_parser("search", help="Full-text search")
    p_search.add_argument("text", help="Search text")
    p_search.add_argument("--limit", type=int, default=20, help="Max results")

    p_show = sub.add_parser("show", help="Show example details")
    p_show.add_argument("id", help="Example ID")

    p_accept = sub.add_parser("accept", help="Manually accept an example")
    p_accept.add_argument("id", help="Example ID")

    p_reject = sub.add_parser("reject", help="Manually reject an example")
    p_reject.add_argument("id", help="Example ID")
    p_reject.add_argument("reason", help="Rejection reason")

    p_cat = sub.add_parser("category", help="List examples in category")
    p_cat.add_argument("cat", help="Category name")

    sub.add_parser("templates", help="Show template-flagged examples")
    sub.add_parser("categories", help="List all categories with counts")

    p_dump = sub.add_parser("dump", help="Full backup: export ALL examples with metadata")
    p_dump.add_argument("-o", "--output", default="data/training-dump.jsonl", help="Output file")

    p_import = sub.add_parser("import", help="Import examples from JSONL")
    p_import.add_argument("file", help="JSONL file to import")

    args = parser.parse_args()

    commands = {
        "stats": cmd_stats,
        "export": cmd_export,
        "search": cmd_search,
        "show": cmd_show,
        "accept": cmd_accept,
        "reject": cmd_reject,
        "category": cmd_category,
        "templates": cmd_templates,
        "import": cmd_import,
        "dump": cmd_dump,
        "categories": cmd_categories,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
