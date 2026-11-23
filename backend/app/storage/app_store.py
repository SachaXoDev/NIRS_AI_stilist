"""SQLite-хранилище бэкенда (стандартная библиотека).

* key-value — настройки куратора из админки;
* снимки гардеробов — только для встроенного движка поиска. В основном режиме гардероб
  хранит сам пакет `wardrobe_rag` (Chroma + catalog.json).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.schemas import WardrobeItem

DEMO_USER_ID = "demo"
_BASE_CAPSULE_PATH = Path(__file__).resolve().parents[3] / "rag" / "data" / "wardrobe_seed.json"


def load_wardrobe_file(path: str | Path | None = None) -> list[WardrobeItem]:
    """Прочитать JSON-массив вещей. Без аргумента — базовая капсула бренда (10 вещей)."""
    raw = json.loads(Path(path or _BASE_CAPSULE_PATH).read_text(encoding="utf-8"))
    return [WardrobeItem.model_validate(item) for item in raw]


class AppStore:
    def __init__(self, database_path: str) -> None:
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS wardrobe_snapshots (
                user_id  TEXT PRIMARY KEY,
                revision TEXT NOT NULL,
                items    TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    # --- key-value ----------------------------------------------------------------

    def get_json(self, key: str) -> Any | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_json(self, key: str, value: Any) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO kv (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )
            self._conn.commit()

    # --- снимки гардероба (встроенный движок) ---------------------------------------

    def get_snapshot(self, user_id: str) -> tuple[str, list[WardrobeItem]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT revision, items FROM wardrobe_snapshots WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return "", []
        return row[0], [WardrobeItem.model_validate(item) for item in json.loads(row[1])]

    def replace_snapshot(self, user_id: str, items: list[WardrobeItem]) -> str:
        payload = [item.model_dump(by_alias=True, mode="json") for item in items]
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        revision = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        with self._lock:
            self._conn.execute(
                "INSERT INTO wardrobe_snapshots (user_id, revision, items) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET revision = excluded.revision, items = excluded.items",
                (user_id, revision, encoded),
            )
            self._conn.commit()
        return revision

    def close(self) -> None:
        with self._lock:
            self._conn.close()
