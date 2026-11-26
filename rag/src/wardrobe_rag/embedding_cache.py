"""Content-addressed embedding cache, so unchanged wardrobe items are never re-encoded.

A wardrobe snapshot is immutable per revision, so any edit creates a new revision. Without a
cache every revision re-encodes the whole catalogue: changing one item out of fifty costs
fifty text and fifty image forward passes. Vectors are keyed by what was actually encoded
(model fingerprint + channel + exact text, or + pixel hash), which makes reuse safe across
revisions, users and process restarts, and impossible across different models.

The cache only skips work. It never changes a vector, a revision or a ranking, and deleting
the file is always safe.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

_CHUNK = 400  # stay below SQLite's bound-parameter limit


class EmbeddingCache:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, data BLOB NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pixel_hashes (source_key TEXT PRIMARY KEY, pixel_hash TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    @staticmethod
    def vector_key(fingerprint: str, channel: str, content: str) -> str:
        return hashlib.sha256(f"{fingerprint}\0{channel}\0{content}".encode("utf-8")).hexdigest()

    @staticmethod
    def source_key(raw_digest: str) -> str:
        # v1 covers the fixed SVG raster size and RGB flattening in ImageLoader.load.
        return hashlib.sha256(f"source-v1\0{raw_digest}".encode("utf-8")).hexdigest()

    def _select(self, table: str, column: str, value: str, keys: Iterable[str]) -> dict[str, object]:
        wanted = list(dict.fromkeys(keys))
        found: dict[str, object] = {}
        with self._lock, self._connect() as conn:
            for start in range(0, len(wanted), _CHUNK):
                chunk = wanted[start:start + _CHUNK]
                marks = ",".join("?" * len(chunk))
                rows = conn.execute(f"SELECT {column}, {value} FROM {table} WHERE {column} IN ({marks})", chunk)
                found.update(rows.fetchall())
        return found

    def get_vectors(self, keys: Iterable[str]) -> dict[str, np.ndarray]:
        return {key: np.frombuffer(blob, dtype=np.float32).copy()
                for key, blob in self._select("vectors", "key", "data", keys).items()}

    def put_vectors(self, vectors: Mapping[str, object]) -> None:
        rows = [(key, np.asarray(vector, dtype=np.float32).tobytes()) for key, vector in vectors.items()]
        if rows:
            with self._lock, self._connect() as conn:
                conn.executemany("INSERT OR REPLACE INTO vectors (key, data) VALUES (?, ?)", rows)

    def get_pixel_hashes(self, source_keys: Iterable[str]) -> dict[str, str]:
        return {key: str(value) for key, value in
                self._select("pixel_hashes", "source_key", "pixel_hash", source_keys).items()}

    def put_pixel_hashes(self, hashes: Mapping[str, str]) -> None:
        if hashes:
            with self._lock, self._connect() as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO pixel_hashes (source_key, pixel_hash) VALUES (?, ?)", list(hashes.items())
                )
