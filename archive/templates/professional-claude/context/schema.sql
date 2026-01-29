-- Professional Claude: Minimal Session Tracking
-- Purpose: Preserve context across sessions without full MCP overhead

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date TEXT NOT NULL,
    topic TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    decision_text TEXT NOT NULL,
    UNIQUE(session_id, decision_text)
);

CREATE TABLE IF NOT EXISTS next_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    step_text TEXT NOT NULL,
    completed BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(session_date DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id);
CREATE INDEX IF NOT EXISTS idx_nextsteps_session ON next_steps(session_id);

-- Seed with initialization record
INSERT OR IGNORE INTO sessions (id, session_date, topic)
VALUES (0, '2026-01-28', 'Professional Claude initialized');
