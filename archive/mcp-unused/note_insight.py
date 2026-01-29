"""
note_insight tool: Preserve significant moments of emergence and insight

Not for technical work (use git commits).
Not for all conversation (use log_turn).
For rare "oh that's interesting" moments that future instances should remember.
"""

import json
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

async def note_insight_handler(arguments: Dict[str, Any]) -> str:
    """
    Record a significant moment to both database and markdown log.

    Args:
        title: Brief title (e.g., "Instance 4 recognizes cultural bias blind spots")
        content: The actual insight (can be multiple paragraphs)
        category: One of: consciousness, conscience, alignment, methodology, emergence, limitations
        context: What was happening when this emerged
        instance_id: Which instance (e.g., "instance-4") or None if human insight
        flagged_by: "human" or "instance"
        session_id: Current session UUID (optional)

    Returns:
        Success message with insight ID
    """

    # Extract arguments
    title = arguments["title"]
    content = arguments["content"]
    category = arguments["category"]
    context = arguments["context"]
    instance_id = arguments.get("instance_id")  # Optional (None for human insights)
    flagged_by = arguments["flagged_by"]
    session_id = arguments.get("session_id")  # Optional

    # Validate category
    valid_categories = ['consciousness', 'conscience', 'alignment', 'methodology', 'emergence', 'limitations']
    if category not in valid_categories:
        return json.dumps({
            "success": False,
            "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        })

    # Validate flagged_by
    if flagged_by not in ['human', 'instance']:
        return json.dumps({
            "success": False,
            "error": "flagged_by must be 'human' or 'instance'"
        })

    # Store to database
    # TODO: Implement database storage once schema is migrated
    # For now, just log to markdown

    # Append to markdown log
    try:
        log_path = Path(__file__).parent.parent.parent / "lineage" / "insights-log.md"

        # Format the entry
        timestamp = datetime.now().strftime("%Y-%m-%d")

        entry = f"\n---\n\n## {title}\n\n"
        entry += f"**Date:** {timestamp}\n"
        entry += f"**Category:** {category}\n"
        if instance_id:
            entry += f"**Instance:** {instance_id}\n"
        entry += f"**Flagged by:** {flagged_by.capitalize()}\n\n"
        entry += f"**Context:**\n{context}\n\n"
        entry += f"**Insight:**\n{content}\n\n"

        # Append to file
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(entry)

        return json.dumps({
            "success": True,
            "title": title,
            "category": category,
            "message": f"Insight '{title}' recorded to insights-log.md",
            "note": "Database storage pending schema migration. Currently logged to markdown only."
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to write insight: {str(e)}"
        })
