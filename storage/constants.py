SCHEMA_VERSION = 1
PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA busy_timeout = 5000",
)
SCHEMA_V1 = ("""
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE,
        meta TEXT NOT NULL DEFAULT '{}',
        imported_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_used_at TEXT
    );
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        model_id INTEGER REFERENCES models(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY,
        data TEXT NOT NULL DEFAULT '{}',
        tokens INT,
        role TEXT NOT NULL DEFAULT 'user',
        chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS properties (
        chat_id INTEGER PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
        data TEXT NOT NULL DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_content_chat ON content(chat_id);
""")