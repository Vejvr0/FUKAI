from __future__ import annotations
import sqlite3
import threading
import json
from contextlib import contextmanager
from collections.abc import Iterator
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


def _parse_json(row: dict, key: str) -> dict:
    row[key] = json.loads(row[key] or "{}")
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


    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._require_conn()
        with self._lock:
            try:
                with conn:
                    yield conn
            except sqlite3.Error as exc:
                raise StorageError(f"{type(exc).__name__}: {exc}") from exc


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
        with self.transaction() as conn:
            return conn.execute(sql, params).lastrowid


    # --- Model methods ---
    def add_model(self, title: str, path: str, meta: dict | None = None) -> int:
        meta_json = json.dumps(meta or {})
        return self.execute("INSERT INTO models (title, path, meta) VALUES (?, ?, ?)", (title, path, meta_json,))


    def list_models(self) -> list[dict]:
        rows = self.query("SELECT * FROM models ORDER BY last_used_at DESC, title ASC")
        return [_parse_json(row, "meta") for row in rows]


    def get_model(self, model_id: int) -> dict | None:
        rows = self.query("SELECT * FROM models WHERE id = ?", (model_id,))
        return _parse_json(rows[0], "meta") if rows else None

    
    def delete_model(self, model_id: int) -> None:
        self.execute("DELETE FROM models WHERE id = ?", (model_id,))


    def mark_model_used(self, model_id: int) -> None:
        self.execute("UPDATE models SET last_used_at = (datetime('now')) WHERE id = ?", (model_id,))


    # --- Chats methods ---
    def create_chat(self, model_id: int, title: str, properties: dict) -> int:
        with self.transaction() as conn:
            chat_id = conn.execute("INSERT INTO chats (title, model_id) VALUES (?, ?)", (title, model_id)).lastrowid
            conn.execute("INSERT INTO properties (chat_id, data) VALUES (?, ?)", (chat_id, json.dumps(properties)))
        return chat_id


    def delete_chat(self, chat_id: int) -> None:
        self.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


    def rename_chat(self, chat_id: int, title: str) -> None:
        self.execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id,))


    def list_chats(self) -> list[dict]:
        return self.query("SELECT * FROM chats ORDER BY updated_at DESC, title ASC")


    def set_model(self, chat_id: int, model_id: int | None, properties: dict) -> None:
        with self.transaction() as conn:
            conn.execute("UPDATE chats SET model_id = ? WHERE id = ?", (model_id, chat_id))
            conn.execute("UPDATE properties SET data = ? WHERE chat_id = ?", (json.dumps(properties), chat_id))
            conn.execute("UPDATE content SET tokens = NULL WHERE chat_id = ?", (chat_id,))


    # --- Chat messages methods ---
    def add_message(self, chat_id: int, data: dict, tokens: int | None, role: str) -> int:
        with self.transaction() as conn:
            message_id = conn.execute("INSERT INTO content (data, tokens, role, chat_id) VALUES (?, ?, ?, ?)", (json.dumps(data), tokens, role, chat_id)).lastrowid
            conn.execute("UPDATE chats SET updated_at = (datetime('now')) WHERE id = ?", (chat_id,))
        return message_id


    def remove_message(self, message_id: int) -> None:
        self.execute("DELETE FROM content WHERE id = ?", (message_id,))


    def get_messages(self, chat_id: int) -> list[dict]:
        rows = self.query("SELECT id, data, tokens, role FROM content WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
        return [_parse_json(row, "data") for row in rows]


    def content_tokens(self, chat_id: int) -> int:
        count = self.query("SELECT COALESCE(SUM(tokens), 0) AS total FROM content WHERE chat_id = ?", (chat_id,))
        return count[0]["total"]


    # --- Chat properties methods ---
    def get_properties(self, chat_id: int) -> dict | None:
        rows = self.query("SELECT data FROM properties WHERE chat_id = ?", (chat_id,))
        return _parse_json(rows[0], "data")["data"] if rows else None


    def set_properties(self, chat_id: int, data: dict) -> None:
        data_json = json.dumps(data)
        self.execute("UPDATE properties SET data = ? WHERE chat_id = ?", (data_json, chat_id,))


if __name__ == "__main__":
    import sys
    import tempfile

    sys.stdout.reconfigure(encoding="utf-8")

    def props(n_ctx: int, temperature: float) -> dict:
        """Blob vo formáte z ALMANAC §7.2 – tri skupiny."""
        return {
            "load": {"n_ctx": n_ctx, "n_gpu_layers": -1, "n_threads": 8,
                     "n_batch": 512, "use_mmap": True},
            "sampling": {"temperature": temperature, "max_tokens": 1024, "top_p": 0.95,
                         "top_k": 40, "repeat_penalty": 1.1, "seed": None, "stop": []},
            "chat": {"system_prompt": "", "web_search": False},
        }

    with tempfile.TemporaryDirectory() as tmp:
        with Database(Path(tmp) / "test.db") as db:
            print(f"súbor:        {db.path}")
            print(f"user_version: {db.query('PRAGMA user_version')[0]['user_version']}")
            print(f"foreign_keys: {db.query('PRAGMA foreign_keys')[0]['foreign_keys']}")
            print(f"tabuľky:      {[r['name'] for r in db.query(
                'SELECT name FROM sqlite_master WHERE type = ? ORDER BY name', ('table',))]}")

            print("\n--- modely ---")
            gemma = db.add_model("Gemma 3 4B", "gemma-3-4b-it-Q4_K_M.gguf", {"n_layers": 34})
            mistral = db.add_model("Mistral 7B", "mistral-7b-instruct-v0.2.Q4_K_M.gguf", {"n_layers": 32})
            print(f"pridané id:   {gemma}, {mistral}")
            print(f"get_model({gemma}):  {db.get_model(gemma)['title']}, meta ako dict: {db.get_model(gemma)['meta']}")
            print(f"get_model(999): {db.get_model(999)}")
            db.mark_model_used(mistral)
            print(f"po mark_model_used({mistral}): {[m['title'] for m in db.list_models()]}")

            print("\n--- chat a správy ---")
            chat = db.create_chat(gemma, "Nový chat", props(4096, 0.7))
            print(f"create_chat:  id={chat}, properties riadkov="
                  f"{db.query('SELECT COUNT(*) AS n FROM properties')[0]['n']}")

            db.add_message(chat, {"text": "Ahoj"}, 12, "user")
            db.add_message(chat, {"text": "Ahoj, ako pomôžem?"}, 40, "assistant")
            print(f"get_messages: {[(m['role'], m['data']['text'], m['tokens']) for m in db.get_messages(chat)]}")
            print(f"content_tokens: {db.content_tokens(chat)}")

            db.rename_chat(chat, "Premenovaný")
            print(f"rename_chat:  {db.list_chats()[0]['title']}")

            print("\n--- vlastnosti ---")
            print(f"get_properties: n_ctx={db.get_properties(chat)['load']['n_ctx']}, "
                  f"temperature={db.get_properties(chat)['sampling']['temperature']}")
            db.set_properties(chat, props(4096, 0.3))
            print(f"po set_properties: temperature={db.get_properties(chat)['sampling']['temperature']}")

            print("\n--- výmena modelu (§7.1: celý reset + NULL tokeny) ---")
            db.set_model(chat, mistral, props(8192, 0.7))
            after = db.get_properties(chat)
            print(f"model_id:     {db.query('SELECT model_id FROM chats WHERE id = ?', (chat,))[0]['model_id']}"
                  f" (bol {gemma}, je {mistral})")
            print(f"n_ctx:        {after['load']['n_ctx']} (predvolený pre nový model)")
            print(f"temperature:  {after['sampling']['temperature']} (ručných 0.3 sa reset zbavil)")
            print(f"tokeny správ: {[m['tokens'] for m in db.get_messages(chat)]} → treba pretokenizovať")
            print(f"content_tokens pri NULL: {db.content_tokens(chat)}")

            print("\n--- atomicita a kaskády ---")
            before = db.query("SELECT COUNT(*) AS n FROM chats")[0]["n"]
            try:
                db.create_chat(99999, "Zlý model", props(4096, 0.7))
            except StorageError:
                pass
            after_n = db.query("SELECT COUNT(*) AS n FROM chats")[0]["n"]
            print(f"create_chat s neexistujúcim modelom: chatov {before} → {after_n}"
                  f" {'(atomické)' if before == after_n else '(SIROTA!)'}")

            db.delete_model(mistral)
            print(f"po delete_model je chats.model_id: "
                  f"{db.query('SELECT model_id FROM chats WHERE id = ?', (chat,))[0]['model_id']} (SET NULL)")

            db.delete_chat(chat)
            print(f"po delete_chat zostalo správ: {db.query('SELECT COUNT(*) AS n FROM content')[0]['n']}, "
                  f"vlastností: {db.query('SELECT COUNT(*) AS n FROM properties')[0]['n']} (CASCADE)")
