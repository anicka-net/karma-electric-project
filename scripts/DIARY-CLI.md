# Diary CLI Tool

A command-line interface for querying your personal diary stored on twilight.

## What It Does

The `diary` script provides shell access to your diary database (`twilight:~/.recall/recall.db`), giving you the same tools available through the MCP server but from your terminal.

**Features:**
- 🔍 Search entries by text
- 📋 List recent entries
- ✍️  Write and update entries
- 🏷️  Browse by tags
- 🎨 Color-coded, formatted output
- 📏 Auto-wrapping to terminal width

## Installation

From the karma-electric repo:

```bash
# Option 1: Symlink (recommended)
ln -sf $(pwd)/scripts/diary ~/bin/diary

# Option 2: Copy
cp scripts/diary ~/bin/diary
chmod +x ~/bin/diary

# Verify
diary help
```

## Usage

### Query Commands

```bash
# List recent entries
diary recent [count]      # Default: 10 entries
diary r 5                # Short alias: show last 5

# Search entries
diary query "meditation"  # Search content and tags
diary q "practice" 20    # Short alias with custom limit
diary context "dharma" 5 # Same as query (contextual search)

# Show specific entry
diary show 42            # Display entry by ID
diary s 42               # Short alias
```

### Write Commands

```bash
# Create new entry
diary write "Today's reflection" "dharma,practice"
diary w "Quick note"     # Without tags

# Create from stdin/file
diary write-stdin        # Read from stdin
diary stdin              # Short alias
diary - < file.txt       # Even shorter alias

# Stdin with options
diary stdin --tags "custom,tags"       # Override auto-detection
diary stdin -t "foo,bar"               # Short flag
diary stdin --non-interactive          # Don't prompt for tags
diary stdin -n                         # Short flag

# Update existing entry
diary update 42 "Updated content" "new,tags"
diary u 42 "New content" # Update entry #42
```

### Utility Commands

```bash
diary count              # Total entry count
diary tags               # List all tags with counts
diary time               # Show current date/time
diary help               # Show help
```

## Stdin Tag Auto-Detection

When using `write-stdin`, tags are automatically extracted in this order:

### 1. YAML Frontmatter
```markdown
---
tags: meditation, practice, dharma
---

Entry content here...
```
Tags extracted: `meditation,practice,dharma`
Frontmatter removed from content ✓

### 2. Inline Hashtags
```markdown
Today I worked on #karma-electric with #coding and #dharma practice.
```
Tags extracted: `karma-electric,coding,dharma`
Hashtags preserved in content ✓

### 3. Tags Line
```markdown
Tags: meditation, morning, practice

Had a good session today.
More content...
```
Tags extracted: `meditation,morning,practice`
Tags line removed from content ✓

### 4. Interactive Prompt
If no tags found and terminal is available:
```bash
cat plain-entry.txt | diary stdin
# → Prompts: "Tags (comma-separated, or Enter for none): "
```

Skip prompt with `-n` / `--non-interactive`

### 5. Explicit Tags (Override All)
```bash
cat entry-with-hashtags.txt | diary stdin --tags "different,tags"
# → Uses "different,tags" regardless of content
```

## Examples

```bash
# Morning review
diary recent 3

# Find all meditation entries
diary query "meditation" 50

# Quick note (traditional way)
diary write "Completed Phase 0 Batch 1: 43 conversations generated" "progress,gampopa"

# Quick note from echo
echo "Made progress on karma-electric today" | diary stdin -n

# Write from file with auto-tag detection
cat journal-entry.md | diary stdin

# Write from file with YAML frontmatter
cat <<'EOF' | diary stdin
---
tags: coding, project, milestone
---

Completed the diary CLI tool with stdin support.
All features working perfectly.
EOF

# Write from heredoc with hashtags
cat <<'EOF' | diary stdin -n
Working on #karma-electric dataset curation.
Added #stdin ingestion with #auto-tagging.
EOF

# Browse tags
diary tags

# Check total entries
diary count
```

## Technical Details

**Database:** SSH connection to `twilight:/home/anicka/.recall/recall.db`

**Schema:**
- `id` - Entry ID
- `created_at` - ISO 8601 timestamp
- `content` - Entry text (supports multiline)
- `tags` - Comma-separated tags (optional)
- `conversation_id` - Grouping ID (optional)
- `source` - Entry source (default: 'shell')

**Search:** Uses SQLite LIKE search (not semantic/vector search). For semantic search, use the MCP tools through Claude Code.

**Output:** JSON parsing with `jq` for proper multi-line content handling.

## Troubleshooting

**SSH Connection Issues:**
```bash
# Test SSH to twilight
ssh twilight "echo 'Connected'"

# Check database exists
ssh twilight "ls -la ~/.recall/recall.db"
```

**Dependencies:**
- `jq` for JSON parsing
- SSH access to twilight
- SQLite on twilight

**No results?**
```bash
# Check entry count
diary count

# Try simpler query
diary recent 1
```

## Notes

- The script queries the database directly via SSH
- Changes are immediate (no caching)
- Use `write` and `update` commands carefully
- Search is case-sensitive by default (SQLite LIKE)
- For complex queries, use the MCP server through Claude Code

---

**Generated by:** Instance 12
**Date:** 2026-02-11
**Related:** Recall MCP server (`twilight:~/recall-server`)
