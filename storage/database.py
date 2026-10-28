from __future__ import annotations
import sqlite3
import threading
import json
from pathlib import Path
from core.paths import db_path, ensure_dir
from core.errors import StorageError
from storage.constants import (
    SCHEMA_VERSION, PRAGMAS, SCHEMA_V1
)

__all__ = [
    "SCHEMA_VERSION",
    "Database"
]


def _with_meta(row: dict) -> dict:
    row["meta"] = json.loads(row["meta"] or "{}")
    return row


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else db_path()
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()


    # --- DB connection handling ---
    def connect(self) -> None:
        if self._conn is not None:
            return
        try:
            ensure_dir(self.path.parent)
            conn = sqlite3.connect(self.path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            for pragma in PRAGMAS:
                conn.execute(pragma)
        except (OSError, sqlite3.Error) as exc:
            raise StorageError(f"{type(exc).__name__}: {exc}") from exc
        self._conn = conn
        self._migrate()


    def close(self) -> None:
        with self._lock:
            conn, self._conn = self._conn, None
            if conn is not None:
                conn.close()


    def __enter__(self) -> Database:
        self.connect()
        return self


    def __exit__(self, *exc_info) -> None:
        self.close()


    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise StorageError()
        return self._conn


    # --- DB schema ---
    def _migrate(self) -> None:
        conn = self._require_conn()
        version = conn.execute("PRAGMA user_version").fetchone()[0]

        if version == SCHEMA_VERSION:
            return
        if version > SCHEMA_VERSION:
            raise StorageError(
                f"user_version={version}, aplikácia pozná {SCHEMA_VERSION}",
                message="Uložené chaty pochádzajú z novšej verzie aplikácie.",
                hint="Aktualizuj FUKAI na novšiu verziu."
            )

        try:
            with self._lock, conn:
                if version < 1:
                    conn.executescript(SCHEMA_V1)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        except sqlite3.Error as exc:
            raise StorageError(f"{type(exc).__name__}: {exc}") from exc


    # --- Read and Write ---
    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = self._require_conn()
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            raise StorageError(f"{type(exc).__name__}: {exc}") from exc
        return [dict(row) for row in rows]


    def execute(self, sql: str, params: tuple = ()) -> int:
        conn = self._require_conn()
        try:
            with self._lock, conn:
                return conn.execute(sql, params).lastrowid
        except sqlite3.Error as exc:
            raise StorageError(f"{type(exc).__name__}: {exc}") from exc


    # --- Model methods ---
    def add_model(self, title: str, path: str, meta: dict | None = None) -> int:
        meta_json = json.dumps(meta or {})
        return self.execute("INSERT INTO models (title, path, meta) VALUES (?, ?, ?)", (title, path, meta_json,))


    def list_models(self) -> list[dict]:
        rows = self.query("SELECT * FROM models ORDER BY last_used_at DESC, title ASC")
        return [_with_meta(row) for row in rows]


    def get_model(self, model_id: int) -> dict | None:
        rows = self.query("SELECT * FROM models WHERE id = ?", (model_id,))
        return _with_meta(rows[0]) if rows else None

    
    def delete_model(self, model_id: int) -> None:
        self.execute("DELETE FROM models WHERE id = ?", (model_id,))


    def mark_model_used(self, model_id: int) -> None:
        self.execute("UPDATE models SET last_used_at = (datetime('now')) WHERE id = ?", (model_id,))


if __name__ == "__main__":
    import sys
    import tempfile
    sys.stdout.reconfigure(encoding="utf-8")

    with Database(Path(tempfile.mkdtemp()) / "test.db") as db:
        print(f"súbor:        {db.path}")
        print(f"user_version: {db.query('PRAGMA user_version')[0]['user_version']}")
        print(f"foreign_keys: {db.query('PRAGMA foreign_keys')[0]['foreign_keys']}")
        print(f"tabuľky:      {[r['name'] for r in db.query(
            'SELECT name FROM sqlite_master WHERE type = ? ORDER BY name', ('table',))]}")

        print("\n--- modely ---")
        gemma = db.add_model("Gemma 3 4B", "gemma-3-4b-it-Q4_K_M.gguf", {"n_layers": 34})
        mistral = db.add_model("Mistral 7B", "mistral-7b-instruct-v0.2.Q4_K_M.gguf", {"n_layers": 32})
        print(f"pridané id: {gemma}, {mistral}")

        model = db.get_model(gemma)
        print(f"get_model({gemma}): {model['title']}, meta ako dict: {model['meta']}")
        print(f"get_model(999):   {db.get_model(999)}")

        db.mark_model_used(mistral)
        print(f"po mark_model_used({mistral}) je poradie: "
              f"{[m['title'] for m in db.list_models()]}")

        print("\n--- chat, správy, nastavenia ---")
        chat = db.execute("INSERT INTO chats (title, model_id) VALUES (?, ?)", ("Nový chat", gemma))
        db.execute("INSERT INTO content (chat_id, role, tokens, data) VALUES (?, ?, ?, ?)",
                   (chat, "user", 12, '{"text": "Ahoj"}'))
        db.execute("INSERT INTO content (chat_id, role, tokens, data) VALUES (?, ?, ?, ?)",
                   (chat, "assistant", 40, '{"text": "Ahoj, ako pomôžem?"}'))
        db.execute("INSERT INTO properties (chat_id, data) VALUES (?, ?)",
                   (chat, '{"temperature": 0.3}'))
        print(f"chat id={chat}, správ: "
              f"{db.query('SELECT COUNT(*) AS n FROM content WHERE chat_id = ?', (chat,))[0]['n']}")

        db.delete_model(gemma)
        print(f"po zmazaní modelu je chat.model_id: "
              f"{db.query('SELECT model_id FROM chats WHERE id = ?', (chat,))[0]['model_id']}")

        db.execute("DELETE FROM chats WHERE id = ?", (chat,))
        print(f"po zmazaní chatu zostalo správ: "
              f"{db.query('SELECT COUNT(*) AS n FROM content')[0]['n']}, "
              f"nastavení: {db.query('SELECT COUNT(*) AS n FROM properties')[0]['n']}")