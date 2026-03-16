from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    input TEXT,
    output TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Prompt versioning: elke wijziging aan een agent prompt wordt bijgehouden
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    version INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    change_reason TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    performance_score REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Feedback op agent output: basis voor het zelflerende systeem
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER NOT NULL,
    agent TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN -1 AND 1),
    comment TEXT,
    tags TEXT,
    prompt_version INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (log_id) REFERENCES agent_log(id)
);

-- Geleerde voorkeuren: patronen die de agent heeft geleerd
CREATE TABLE IF NOT EXISTS learned_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    category TEXT NOT NULL,
    preference TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5,
    source_feedback_ids TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_agent_key ON agent_memory(agent, key);
CREATE INDEX IF NOT EXISTS idx_log_agent ON agent_log(agent, created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_agent ON prompt_versions(agent, version);
CREATE INDEX IF NOT EXISTS idx_feedback_agent ON feedback(agent, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(agent, rating);
CREATE INDEX IF NOT EXISTS idx_learned_prefs_agent ON learned_preferences(agent, is_active);
"""
