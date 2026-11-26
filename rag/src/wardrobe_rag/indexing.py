"""Full-snapshot indexing of canonical wardrobe items, text and actual pixels."""
from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from time import perf_counter

import numpy as np

from .embedding_cache import EmbeddingCache
from .schemas import WardrobeItem, SyncResult
from .text import build_document


class IndexingPipeline:
    def __init__(self, store, embedder, image_loader, cache: EmbeddingCache | None = None):
        """`cache` is optional: without it every new revision re-encodes the whole snapshot."""
        self.store = store
        self.embedder = embedder
        self.image_loader = image_loader
        self.cache = cache

    def sync(self, user_id: str, items: list[WardrobeItem | dict]) -> SyncResult:
        with ExitStack() as image_stack:
            return self._sync(user_id, items, image_stack)

    def _load(self, source: str, image_stack: ExitStack):
        image = self.image_loader(source)
        image_stack.callback(image.close)
        return image

    def _sync(self, user_id: str, items: list[WardrobeItem | dict], image_stack: ExitStack) -> SyncResult:
        started = perf_counter()
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")
        items = [item if isinstance(item, WardrobeItem) else WardrobeItem.model_validate(item) for item in items]
        if len({item.id for item in items}) != len(items):
            raise ValueError("Duplicate item IDs in wardrobe snapshot")
        items.sort(key=lambda item: item.id)
        cache = self.cache
        warnings = []
        sources = {item.id: source for item in items if (source := item.imagePath or item.imageUrl)}

        # A raw-bytes digest is far cheaper than decoding or rasterising. For a source seen
        # before it yields the same pixel hash as loading the image would.
        source_keys: dict[str, str] = {}
        raw_digest = getattr(self.image_loader, "digest", None) if cache else None
        if raw_digest is not None:
            for item_id, source in sources.items():
                try:
                    source_keys[item_id] = cache.source_key(raw_digest(source))
                except (OSError, ValueError):
                    pass  # the load below reports the real reason
        known_hashes = cache.get_pixel_hashes(source_keys.values()) if source_keys else {}

        loaded, image_ids, image_hashes, new_hashes = {}, [], {}, {}
        for item in items:
            if item.id not in sources:
                warnings.append(f"{item.id}: no image; text-only indexing")
                continue
            pixel_hash = known_hashes.get(source_keys.get(item.id, ""))
            if pixel_hash is None:
                try:
                    image = loaded[item.id] = self._load(sources[item.id], image_stack)
                except (OSError, ValueError) as exc:
                    warnings.append(f"{item.id}: image not indexed ({exc})")
                    continue
                pixel_hash = hashlib.sha256(image.tobytes() + str(image.size).encode()).hexdigest()
                if item.id in source_keys:
                    new_hashes[source_keys[item.id]] = pixel_hash
            image_ids.append(item.id)
            image_hashes[item.id] = pixel_hash
        if cache:
            cache.put_pixel_hashes(new_hashes)

        fingerprint = self.embedder.fingerprint
        payload = {"items": [item.model_dump(mode="json") for item in items],
                   "image_hashes": image_hashes, "fingerprint": fingerprint, "template": 2}
        revision = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        counts = {"encoded_text_count": 0, "reused_text_count": 0, "encoded_image_count": 0, "reused_image_count": 0}
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
                documents = [build_document(item) for item in items]
                text_keys = [EmbeddingCache.vector_key(fingerprint, "text", document) for document in documents]
                vectors = cache.get_vectors(text_keys) if cache else {}
                missing = {key: document for key, document in zip(text_keys, documents) if key not in vectors}
                counts["reused_text_count"] = sum(key in vectors for key in text_keys)
                if missing:
                    fresh = dict(zip(missing, self.embedder.encode_text(list(missing.values()))))
                    counts["encoded_text_count"] = len(text_keys) - counts["reused_text_count"]
                    if cache:
                        cache.put_vectors(fresh)
                    vectors.update(fresh)
                text_vectors = [vectors[key] for key in text_keys] if items else np.empty((0, 0))
                timings["text_embedding_ms"] = (perf_counter() - t) * 1000

                t = perf_counter()
                image_keys = {item_id: EmbeddingCache.vector_key(fingerprint, "image", image_hashes[item_id])
                              for item_id in image_ids}
                vectors = cache.get_vectors(image_keys.values()) if cache else {}
                counts["reused_image_count"] = sum(key in vectors for key in image_keys.values())
                # Identical pictures (two users' copies, a re-uploaded photo) are encoded once.
                pending = {key: item_id for item_id, key in image_keys.items() if key not in vectors}
                if pending:
                    for item_id in pending.values():
                        if item_id not in loaded:  # hash came from the cache, pixels were not needed until now
                            try:
                                loaded[item_id] = self._load(sources[item_id], image_stack)
                            except (OSError, ValueError) as exc:
                                raise ValueError(f"{item_id}: image became unreadable during indexing ({exc})") from exc
                    fresh = dict(zip(pending, self.embedder.encode_images([loaded[i] for i in pending.values()])))
                    counts["encoded_image_count"] = len(image_keys) - counts["reused_image_count"]
                    if cache:
                        cache.put_vectors(fresh)
                    vectors.update(fresh)
                visual_vectors = {item_id: vectors[key] for item_id, key in image_keys.items()}
                timings["image_embedding_ms"] = (perf_counter() - t) * 1000
                t = perf_counter()
                self.store.replace_user(user_id, items, text_vectors, visual_vectors, revision, fingerprint)
                timings["persist_ms"] = (perf_counter() - t) * 1000
            timings["total_ms"] = (perf_counter() - started) * 1000
            return SyncResult(user_id=user_id, revision=revision, indexed_count=len(items),
                              image_count=len(image_ids), added_count=added, updated_count=updated,
                              deleted_count=deleted, unchanged_count=same, warnings=warnings, timings_ms=timings,
                              **counts)
