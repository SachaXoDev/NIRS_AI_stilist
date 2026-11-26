"""Reuse of embeddings for unchanged items; vectors, revisions and rankings must not change."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from wardrobe_rag.embedding_cache import EmbeddingCache
from wardrobe_rag.images import ImageLoader
from wardrobe_rag.indexing import IndexingPipeline
from wardrobe_rag.store import ChromaWardrobeStore

CATALOGUE = 12


@pytest.fixture
def catalogue(tmp_path, make_item):
    """Twelve items with distinct pictures on disk, like a small real wardrobe."""
    items = []
    for n in range(CATALOGUE):
        path = tmp_path / f"photo-{n}.png"
        Image.new("RGB", (8, 8), (n * 20, 40, 200 - n * 10)).save(path)
        items.append(make_item(f"item-{n:02d}", "tops", f"Рубашка номер {n}", imageUrl=str(path)))
    return items


def _pipeline(tmp_path, embedder, *, cached: bool, name: str = "index"):
    store = ChromaWardrobeStore(tmp_path / name)
    cache = EmbeddingCache(tmp_path / name / "embedding_cache.sqlite3") if cached else None
    return IndexingPipeline(store, embedder, ImageLoader(tmp_path), cache), store


def _calls(embedder) -> tuple[int, int]:
    return embedder.calls["text"], embedder.calls["image"]


def test_without_cache_one_edit_re_encodes_the_whole_catalogue(tmp_path, embedder, catalogue):
    pipeline, _ = _pipeline(tmp_path, embedder, cached=False)
    pipeline.sync("alice", catalogue)
    before = _calls(embedder)
    edited = [catalogue[0].model_copy(update={"color": "Красный"}), *catalogue[1:]]
    result = pipeline.sync("alice", edited)
    assert _calls(embedder) == (before[0] + CATALOGUE, before[1] + CATALOGUE)
    assert (result.encoded_text_count, result.encoded_image_count) == (CATALOGUE, CATALOGUE)
    assert result.reused_text_count == result.reused_image_count == 0


def test_with_cache_one_edit_encodes_only_the_changed_item(tmp_path, embedder, catalogue):
    pipeline, store = _pipeline(tmp_path, embedder, cached=True)
    first = pipeline.sync("alice", catalogue)
    assert (first.encoded_text_count, first.encoded_image_count) == (CATALOGUE, CATALOGUE)
    before = _calls(embedder)

    edited = [catalogue[0].model_copy(update={"color": "Красный"}), *catalogue[1:]]
    result = pipeline.sync("alice", edited)
    assert _calls(embedder) == (before[0] + 1, before[1]), "one changed text, pictures untouched"
    assert (result.encoded_text_count, result.reused_text_count) == (1, CATALOGUE - 1)
    assert (result.encoded_image_count, result.reused_image_count) == (0, CATALOGUE)
    assert result.updated_count == 1 and result.unchanged_count == CATALOGUE - 1
    assert store.get_revision("alice") == result.revision != first.revision


def test_added_and_removed_items_do_not_touch_the_rest(tmp_path, embedder, catalogue, make_item):
    pipeline, store = _pipeline(tmp_path, embedder, cached=True)
    pipeline.sync("alice", catalogue)
    before = _calls(embedder)

    extra = tmp_path / "extra.png"
    Image.new("RGB", (8, 8), "white").save(extra)
    grown = [*catalogue, make_item("item-new", "shoes", "Кеды", imageUrl=str(extra))]
    assert pipeline.sync("alice", grown).encoded_image_count == 1
    assert _calls(embedder) == (before[0] + 1, before[1] + 1)

    shrunk = pipeline.sync("alice", catalogue[:5])
    assert _calls(embedder) == (before[0] + 1, before[1] + 1), "deleting never needs the encoders"
    assert shrunk.deleted_count == CATALOGUE - 4 and len(store.get_items("alice")) == 5


def test_another_user_and_a_restart_reuse_the_same_vectors(tmp_path, embedder, catalogue):
    pipeline, _ = _pipeline(tmp_path, embedder, cached=True)
    pipeline.sync("alice", catalogue)
    before = _calls(embedder)

    # A fresh process: new store and cache objects over the same directory.
    reopened, store = _pipeline(tmp_path, embedder, cached=True)
    result = reopened.sync("bob", catalogue)
    assert _calls(embedder) == before
    assert (result.reused_text_count, result.reused_image_count) == (CATALOGUE, CATALOGUE)
    assert len(store.get_items("bob")) == CATALOGUE


def test_changed_pixels_at_the_same_path_are_encoded_again(tmp_path, embedder, catalogue):
    pipeline, _ = _pipeline(tmp_path, embedder, cached=True)
    first = pipeline.sync("alice", catalogue)
    before = _calls(embedder)
    Image.new("RGB", (8, 8), "black").save(tmp_path / "photo-3.png")
    result = pipeline.sync("alice", catalogue)
    assert result.revision != first.revision
    assert _calls(embedder) == (before[0], before[1] + 1)
    assert (result.encoded_image_count, result.reused_image_count) == (1, CATALOGUE - 1)


def test_vectors_are_not_shared_between_models(tmp_path, embedder, catalogue):
    pipeline, _ = _pipeline(tmp_path, embedder, cached=True)
    pipeline.sync("alice", catalogue)
    before = _calls(embedder)

    other_model = type(embedder)()
    other_model.fingerprint = "another-model"
    second, _ = _pipeline(tmp_path, other_model, cached=True, name="other-index")
    second.cache = pipeline.cache  # same cache file, different encoder
    second.sync("alice", catalogue)
    assert _calls(other_model) == (CATALOGUE, CATALOGUE) and _calls(embedder) == before


def test_cache_changes_neither_revision_nor_vectors_nor_ranking(tmp_path, embedder, catalogue):
    plain, plain_store = _pipeline(tmp_path, embedder, cached=False, name="plain")
    cached, cached_store = _pipeline(tmp_path, embedder, cached=True, name="cached")
    edited = [catalogue[0].model_copy(update={"title": "Изумрудная рубашка"}), *catalogue[1:]]
    for snapshot in (catalogue, edited):  # second pass is served mostly from the cache
        assert plain.sync("alice", snapshot).revision == cached.sync("alice", snapshot).revision

    query = embedder.encode_text(["изумрудная рубашка"])[0]
    for channel in ("text", "image"):
        expected = plain_store.query(channel, query, "alice", "tops", CATALOGUE)
        actual = cached_store.query(channel, query, "alice", "tops", CATALOGUE)
        assert [hit.item_id for hit in actual] == [hit.item_id for hit in expected]
        assert np.allclose([hit.distance for hit in actual], [hit.distance for hit in expected], atol=1e-6)


def test_unreadable_image_is_still_reported_with_a_cache(tmp_path, embedder, make_item):
    pipeline, _ = _pipeline(tmp_path, embedder, cached=True)
    result = pipeline.sync("alice", [make_item("top", imageUrl=str(tmp_path / "missing.png"))])
    assert result.image_count == 0 and any("image not indexed" in warning for warning in result.warnings)
