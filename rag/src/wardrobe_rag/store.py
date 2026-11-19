"""Persistent Chroma plus atomic canonical snapshots, isolated by user and revision."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Sequence

import numpy as np
from filelock import FileLock

from .schemas import WardrobeItem, VectorHit

logger = logging.getLogger(__name__)


class ChromaWardrobeStore:
    def __init__(self, path: Path):
        import chromadb
        from chromadb.config import Settings
        from chromadb.errors import InternalError
        self._chroma_error = InternalError
        self.path = Path(path).resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.path / "snapshot.lock"), timeout=120)
        self._catalog_path = self.path / "catalog.json"
        self.client = chromadb.PersistentClient(
            path=str(self.path / "chroma"), settings=Settings(anonymized_telemetry=False)
        )
        self.collections = {
            channel: self.client.get_or_create_collection(
                name=f"wardrobe_{channel}_v1", embedding_function=None,
                configuration={"hnsw": {"space": "cosine"}},
            ) for channel in ("text", "image")
        }

    @contextmanager
    def read_session(self):
        with self._lock:
            yield self

    def _catalog(self) -> dict:
        if not self._catalog_path.exists():
            return {"schema_version": 1, "model_fingerprint": None, "users": {}}
        return json.loads(self._catalog_path.read_text(encoding="utf-8"))

    def get_items(self, user_id: str) -> list[WardrobeItem]:
        with self._lock:
            entry = self._catalog()["users"].get(user_id, {})
            return [WardrobeItem.model_validate(item) for item in entry.get("items", [])]

    def get_revision(self, user_id: str) -> str:
        with self._lock:
            return self._catalog()["users"].get(user_id, {}).get("revision", "")

    def get_fingerprint(self) -> str | None:
        with self._lock:
            return self._catalog().get("model_fingerprint")

    def get_image_ids(self, user_id: str) -> set[str]:
        with self._lock:
            return set(self._catalog()["users"].get(user_id, {}).get("image_ids", []))

    def query(self, channel: str, vector: Sequence[float], user_id: str,
              category: str, k: int) -> list[VectorHit]:
        if channel not in self.collections or k <= 0:
            return []
        with self._lock:
            entry = self._catalog()["users"].get(user_id)
            if not entry:
                return []
            where = {"$and": [{"user_id": user_id}, {"revision": entry["revision"]}, {"category": category}]}
            allowed = [i for i in entry["items"] if i["category"] == category and
                       (channel == "text" or i["id"] in entry.get("image_ids", []))]
            if not allowed:
                return []
            collection = self.collections[channel]
            query = np.asarray(vector, dtype=np.float32)
            try:
                result = collection.query(
                    query_embeddings=[query.tolist()], n_results=min(k, len(allowed)),
                    where=where, include=["metadatas", "distances"],
                )
            except self._chroma_error as exc:
                if "Error creating hnsw segment reader" not in str(exc):
                    raise
                # A tiny just-written segment can be unreadable to HNSW while the
                # committed embeddings are still available through Chroma get().
                rows = collection.get(where=where, include=["metadatas", "embeddings"])
                if len(rows["ids"]) != len(allowed):
                    raise
                matrices = np.asarray(rows["embeddings"], dtype=np.float32)
                similarity = (matrices @ query) / (np.linalg.norm(matrices, axis=1) * np.linalg.norm(query))
                logger.warning("Chroma HNSW reader unavailable; using exact cosine for the committed slot")
                hits = [VectorHit(item_id=meta["item_id"], distance=float(1 - score))
                        for meta, score in zip(rows["metadatas"], np.clip(similarity, -1, 1))]
                return sorted(hits, key=lambda hit: (hit.distance, hit.item_id))[:k]
            hits = [VectorHit(item_id=meta["item_id"], distance=float(distance))
                    for meta, distance in zip(result["metadatas"][0], result["distances"][0])]
            return sorted(hits, key=lambda hit: (hit.distance, hit.item_id))

    def replace_user(self, user_id: str, items: list[WardrobeItem], text_vectors,
                     image_vectors_by_id: dict, revision: str, model_fingerprint: str):
        if len(text_vectors) != len(items):
            raise ValueError("Text embedding count does not match wardrobe item count")
        allowed_ids = {item.id for item in items}
        if not set(image_vectors_by_id) <= allowed_ids:
            raise ValueError("Image vectors contain IDs outside this wardrobe snapshot")
        for vector in [*text_vectors, *image_vectors_by_id.values()]:
            array = np.asarray(vector)
            if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all() or np.linalg.norm(array) == 0:
                raise ValueError("Embedding must be a finite, nonzero one-dimensional vector")
        with self._lock:
            catalog = self._catalog()
            old_fingerprint = catalog.get("model_fingerprint")
            if old_fingerprint and old_fingerprint != model_fingerprint:
                raise ValueError("Embedding model fingerprint changed; use a fresh --data-dir and reindex")
            # New generation remains invisible until atomic catalog commit.
            for channel, collection in self.collections.items():
                rows = [(item, text_vectors[pos] if channel == "text" else image_vectors_by_id.get(item.id))
                        for pos, item in enumerate(items)]
                rows = [(item, vector) for item, vector in rows if vector is not None]
                for start in range(0, len(rows), 128):
                    batch = rows[start:start + 128]
                    collection.upsert(
                        ids=[hashlib.sha256(f"{user_id}\0{revision}\0{item.id}".encode()).hexdigest() for item, _ in batch],
                        embeddings=[np.asarray(vector, dtype=np.float32).tolist() for _, vector in batch],
                        metadatas=[{"user_id": user_id, "revision": revision, "category": item.category,
                                    "item_id": item.id, "color": item.color, "season": item.season,
                                    "material": item.material or "", "model_fingerprint": model_fingerprint}
                                   for item, _ in batch],
                    )
            catalog["model_fingerprint"] = model_fingerprint
            catalog["users"][user_id] = {
                "revision": revision, "items": [item.model_dump(mode="json") for item in items],
                "image_ids": sorted(image_vectors_by_id),
            }
            temporary = self._catalog_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self._catalog_path)
            # Cleanup is after commit. A failure leaves unreachable old vectors, not wrong results.
            for collection in self.collections.values():
                collection.delete(where={"$and": [{"user_id": user_id}, {"revision": {"$ne": revision}}]})
