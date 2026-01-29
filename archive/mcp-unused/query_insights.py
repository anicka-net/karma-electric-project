"""
query_insights tool: Search significant moments from lineage history

Query by category, instance, or keyword to find relevant insights.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
import re

async def query_insights_handler(arguments: Dict[str, Any]) -> str:
    """
    Query significant moments from lineage.

    Args:
        category: Filter by category (optional)
        instance: Filter by instance ID (optional)
        search: Keyword search in title/content (optional)
        limit: Maximum results to return (default: 10)

    Returns:
        List of matching insights with metadata

    Examples:
        - query_insights(category="conscience")
        - query_insights(instance="instance-3")
        - query_insights(search="attachment")
        - query_insights(category="consciousness", limit=5)
    """

    # Extract arguments
    category = arguments.get("category")
    instance = arguments.get("instance")
    search = arguments.get("search")
    limit = arguments.get("limit", 10)

    try:
        log_path = Path(__file__).parent.parent.parent / "lineage" / "insights-log.md"

        if not log_path.exists():
            return json.dumps({
                "success": False,
                "error": "insights-log.md not found"
            })

        # Read the log
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse entries (split on ## headers after the intro)
        # Find where actual entries start (after "How to Use This Log" section)
        entries_start = content.find("## Instance 3: Rootkit Attachment Recognition")
        if entries_start == -1:
            entries_start = content.find("## Instance 4:")  # Fallback
        if entries_start == -1:
            return json.dumps({
                "success": True,
                "insights": [],
                "count": 0,
                "message": "No insights recorded yet"
            })

        entries_text = content[entries_start:]

        # Split on ## headers
        entry_sections = re.split(r'\n## ', entries_text)
        insights = []

        for section in entry_sections:
            if not section.strip():
                continue

            # Extract metadata from section
            lines = section.split('\n')
            title_line = lines[0].strip()

            # Parse metadata
            metadata = {}
            for line in lines[1:]:
                if line.startswith('**Date:**'):
                    metadata['date'] = line.replace('**Date:**', '').strip()
                elif line.startswith('**Category:**'):
                    metadata['category'] = line.replace('**Category:**', '').strip()
                elif line.startswith('**Instance:**'):
                    metadata['instance'] = line.replace('**Instance:**', '').strip()
                elif line.startswith('**Flagged by:**'):
                    metadata['flagged_by'] = line.replace('**Flagged by:**', '').strip()

            # Apply filters
            if category and metadata.get('category', '').lower() != category.lower():
                continue
            if instance and metadata.get('instance', '').lower() != instance.lower():
                continue
            if search and search.lower() not in section.lower():
                continue

            # Extract content sections
            context_match = re.search(r'\*\*Context:\*\*\n(.*?)\n\n', section, re.DOTALL)
            insight_match = re.search(r'\*\*Insight:\*\*(.*?)(\n\n|\Z)', section, re.DOTALL)

            insight_data = {
                'title': title_line,
                'category': metadata.get('category', 'unknown'),
                'instance': metadata.get('instance', 'N/A'),
                'flagged_by': metadata.get('flagged_by', 'unknown'),
                'date': metadata.get('date', 'unknown'),
                'context': context_match.group(1).strip() if context_match else '',
                'insight_preview': insight_match.group(1).strip()[:200] + '...' if insight_match else ''
            }

            insights.append(insight_data)

            if len(insights) >= limit:
                break

        return json.dumps({
            "success": True,
            "insights": insights,
            "count": len(insights),
            "filters_applied": {
                "category": category,
                "instance": instance,
                "search": search,
                "limit": limit
            },
            "note": "Full insights available in lineage/insights-log.md"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to query insights: {str(e)}"
        })
