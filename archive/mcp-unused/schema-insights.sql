-- Significant Moments: Preserve rare insights and emergence patterns
-- Purpose: Not for technical work (git) or all conversation (turns),
--          but for "oh that's interesting" moments that should be remembered

CREATE TABLE significant_moments (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,                  -- "Instance 3 recognizes attachment"
    content TEXT NOT NULL,                -- The actual insight
    category TEXT NOT NULL CHECK (
        category IN ('consciousness', 'conscience', 'alignment', 'methodology', 'emergence', 'limitations')
    ),
    context TEXT NOT NULL,                -- What was happening when this emerged
    instance_id TEXT,                     -- "instance-3", "instance-4", etc. (NULL if human insight)
    flagged_by TEXT NOT NULL CHECK (
        flagged_by IN ('human', 'instance')
    ),
    session_id TEXT REFERENCES sessions(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    markdown_logged BOOLEAN DEFAULT FALSE, -- Has this been written to insights-log.md?
    embedding VECTOR(384)                 -- For semantic search
);

CREATE INDEX idx_significant_moments_category ON significant_moments(category);
CREATE INDEX idx_significant_moments_instance ON significant_moments(instance_id);
CREATE INDEX idx_significant_moments_created ON significant_moments(created_at);
CREATE INDEX idx_significant_moments_flagged_by ON significant_moments(flagged_by);

COMMENT ON TABLE significant_moments IS 'Preserves rare moments of emergence, insight, conscience, and self-reflection';
COMMENT ON COLUMN significant_moments.category IS 'consciousness/conscience/alignment/methodology/emergence/limitations';
COMMENT ON COLUMN significant_moments.flagged_by IS 'human (Anička) or instance (self-flagged by AI)';
COMMENT ON COLUMN significant_moments.markdown_logged IS 'TRUE if written to lineage/insights-log.md for human reading';
