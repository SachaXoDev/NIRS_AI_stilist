"""Full-snapshot indexing of canonical wardrobe items, text and actual pixels."""
from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from time import perf_counter

import numpy as np

from .schemas import WardrobeItem, SyncResult
from .text import build_document


class IndexingPipeline:
    def __init__(self, store, embedder, image_loader):
        self.store = store
        self.embedder = embedder
        self.image_loader = image_loader

    def sync(self, user_id: str, items: list[WardrobeItem | dict]) -> SyncResult:
        with ExitStack() as image_stack:
            return self._sync(user_id, items, image_stack)

    def _sync(self, user_id: str, items: list[WardrobeItem | dict], image_stack: ExitStack) -> SyncResult:
        started = perf_counter()
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")
        items = [item if isinstance(item, WardrobeItem) else WardrobeItem.model_validate(item) for item in items]
        if len({item.id for item in items}) != len(items):
            raise ValueError("Duplicate item IDs in wardrobe snapshot")
        items.sort(key=lambda item: item.id)
        warnings = []
        images, image_ids, image_hashes = [], [], {}
        for item in items:
            source = item.imagePath or item.imageUrl
            if not source:
                warnings.append(f"{item.id}: no image; text-only indexing")
                continue
            try:
                image = self.image_loader(source)
                image_stack.callback(image.close)
                images.append(image)
                image_ids.append(item.id)
                image_hashes[item.id] = hashlib.sha256(image.tobytes() + str(image.size).encode()).hexdigest()
            except (OSError, ValueError) as exc:
                warnings.append(f"{item.id}: image not indexed ({exc})")
        fingerprint = self.embedder.fingerprint
        payload = {"items": [item.model_dump(mode="json") for item in items],
                   "image_hashes": image_hashes, "fingerprint": fingerprint, "template": 1}
        revision = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with self.store.read_session():
            old = {item.id: item for item in self.store.get_items(user_id)}
            new = {item.id: item for item in items}
            added = len(new.keys() - old.keys())
            deleted = len(old.keys() - new.keys())
            updated = sum(old[key] != new[key] for key in old.keys() & new.keys())
            same = len(new.keys() & old.keys()) - updated
            timings = {"prepare_ms": (perf_counter() - started) * 1000}
            if revision != self.store.get_revision(user_id):
                t = perf_counter()
                text_vectors = self.embedder.encode_text([build_document(item) for item in items]) if items else np.empty((0, 0))
                timings["text_embedding_ms"] = (perf_counter() - t) * 1000
                t = perf_counter()
                visual_vectors = self.embedder.encode_images(images) if images else []
                timings["image_embedding_ms"] = (perf_counter() - t) * 1000
                t = perf_counter()
                self.store.replace_user(user_id, items, text_vectors, dict(zip(image_ids, visual_vectors)), revision, fingerprint)
                timings["persist_ms"] = (perf_counter() - t) * 1000
            timings["total_ms"] = (perf_counter() - started) * 1000
            return SyncResult(user_id=user_id, revision=revision, indexed_count=len(items),
                              image_count=len(image_ids), added_count=added, updated_count=updated,
                              deleted_count=deleted, unchanged_count=same, warnings=warnings, timings_ms=timings)
