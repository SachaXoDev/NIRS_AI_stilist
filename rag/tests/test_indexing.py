from __future__ import annotations

import pytest
from PIL import Image

from wardrobe_rag.images import ImageLoader
from wardrobe_rag.indexing import IndexingPipeline
from wardrobe_rag.store import ChromaWardrobeStore


def test_snapshot_sync_is_idempotent_persistent_and_tenant_scoped(tmp_path, embedder, wardrobe):
    public_root = tmp_path / "public"
    public_root.mkdir()
    store_path = tmp_path / "index"
    store = ChromaWardrobeStore(store_path)
    pipeline = IndexingPipeline(store, embedder, ImageLoader(public_root))

    pipeline.sync("alice", wardrobe)
    revision = store.get_revision("alice")
    assert {item.id for item in store.get_items("alice")} == {item.id for item in wardrobe}
    pipeline.sync("alice", wardrobe)
    assert store.get_revision("alice") == revision
    assert len(store.get_items("alice")) == len(wardrobe)

    # The same item IDs in another wardrobe must never overwrite Alice's data.
    other = [item.model_copy(update={"title": "Другой пользователь"}) for item in wardrobe]
    pipeline.sync("bob", other)
    assert store.get_items("alice")[0].title != "Другой пользователь"
    assert {item.title for item in store.get_items("bob")} == {"Другой пользователь"}

    # Reopen the actual persistent adapter, not a fake store.
    reopened = ChromaWardrobeStore(store_path)
    assert reopened.get_revision("alice") == revision
    assert {item.id for item in reopened.get_items("alice")} == {item.id for item in wardrobe}


def test_update_delete_and_empty_snapshot_replace_both_indexes(tmp_path, embedder, wardrobe):
    public_root = tmp_path / "public"
    public_root.mkdir()
    store = ChromaWardrobeStore(tmp_path / "index")
    pipeline = IndexingPipeline(store, embedder, ImageLoader(public_root))
    pipeline.sync("alice", wardrobe)
    pipeline.sync("bob", wardrobe)
    revision = store.get_revision("alice")
    changed = wardrobe[0].model_copy(update={"title": "Красная блуза", "color": "Красный"})
    pipeline.sync("alice", [changed, wardrobe[1]])
    assert store.get_revision("alice") != revision
    assert {item.id for item in store.get_items("alice")} == {"top", "bottom"}
    assert next(item for item in store.get_items("alice") if item.id == "top").title == "Красная блуза"

    for category in ("shoes", "outerwear"):
        for channel in ("text", "image"):
            hits = store.query(channel, embedder.encode_text(["обувь"])[0], "alice", category, 10)
            assert hits == []

    pipeline.sync("alice", [])
    assert store.get_items("alice") == []
    for channel in ("text", "image"):
        assert store.query(channel, embedder.encode_text(["рубашка"])[0], "alice", "tops", 3) == []
    assert len(store.get_items("bob")) == len(wardrobe)


def test_vector_queries_cannot_cross_user_or_category(tmp_path, embedder, wardrobe, make_item):
    public_root = tmp_path / "public"
    public_root.mkdir()
    store = ChromaWardrobeStore(tmp_path / "index")
    pipeline = IndexingPipeline(store, embedder, ImageLoader(public_root))
    pipeline.sync("alice", wardrobe)
    pipeline.sync("bob", [make_item("secret", "tops", "Секретная рубашка")])
    vector = embedder.encode_text(["рубашка"])[0]
    for channel in ("text", "image"):
        hits = store.query(channel, vector, "alice", "tops", 100)
        assert {hit.item_id for hit in hits} == {"top"}


def test_duplicate_ids_cannot_corrupt_a_previously_committed_snapshot(tmp_path, embedder, wardrobe):
    store = ChromaWardrobeStore(tmp_path / "index")
    pipeline = IndexingPipeline(store, embedder, ImageLoader(tmp_path))
    pipeline.sync("alice", wardrobe)
    before = store.get_revision("alice")
    with pytest.raises(ValueError, match="Duplicate"):
        pipeline.sync("alice", [wardrobe[0], wardrobe[0]])
    assert store.get_revision("alice") == before
    assert len(store.get_items("alice")) == len(wardrobe)


def test_changed_image_pixels_trigger_a_new_visual_revision(tmp_path, embedder, make_item):
    target = tmp_path / "photo.png"
    Image.new("RGB", (8, 8), "red").save(target)
    item = make_item("top", imageUrl=str(target))
    store = ChromaWardrobeStore(tmp_path / "index")
    pipeline = IndexingPipeline(store, embedder, ImageLoader(tmp_path))
    pipeline.sync("alice", [item])
    before = store.get_revision("alice")
    calls = embedder.calls["image"]
    Image.new("RGB", (8, 8), "blue").save(target)
    pipeline.sync("alice", [item])
    assert store.get_revision("alice") != before
    assert embedder.calls["image"] > calls


def test_partial_vector_write_never_publishes_a_mixed_snapshot(tmp_path, embedder, wardrobe, monkeypatch):
    store = ChromaWardrobeStore(tmp_path / "index")
    pipeline = IndexingPipeline(store, embedder, ImageLoader(tmp_path))
    pipeline.sync("alice", wardrobe)
    before = store.get_revision("alice")
    changed = [wardrobe[0].model_copy(update={"title": "Новая рубашка"}), *wardrobe[1:]]

    collection_type = type(store.collections["image"])
    original_upsert = collection_type.upsert

    def fail_after_text_write(collection, *args, **kwargs):
        if collection.name == store.collections["image"].name:
            raise RuntimeError("simulated image-index write failure")
        return original_upsert(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(collection_type, "upsert", fail_after_text_write)
        with pytest.raises(RuntimeError, match="simulated"):
            pipeline.sync("alice", changed)

    assert store.get_revision("alice") == before
    assert next(item for item in store.get_items("alice") if item.id == "top").title == wardrobe[0].title
    for channel in ("text", "image"):
        assert {hit.item_id for hit in store.query(channel, embedder.encode_text(["рубашка"])[0], "alice", "tops", 3)} == {"top"}

    # A retry can publish the complete new generation after the failure is gone.
    pipeline.sync("alice", changed)
    assert store.get_revision("alice") != before
    assert next(item for item in store.get_items("alice") if item.id == "top").title == "Новая рубашка"


def test_unreadable_hnsw_segment_uses_committed_vectors_only(tmp_path, embedder, make_item, monkeypatch):
    from chromadb.errors import InternalError

    store = ChromaWardrobeStore(tmp_path / "index")
    pipeline = IndexingPipeline(store, embedder, ImageLoader(tmp_path))
    pipeline.sync("alice", [make_item("top", title="Белая рубашка")])
    pipeline.sync("bob", [make_item("top", title="Чёрное поло"), make_item("other")])

    def unreadable(*args, **kwargs):
        raise InternalError("Error creating hnsw segment reader: Nothing found on disk")

    monkeypatch.setattr(type(store.collections["text"]), "query", unreadable)
    query = embedder.encode_text(["рубашка"])[0]
    hits = store.query("text", query, "alice", "tops", 3)
    assert [hit.item_id for hit in hits] == ["top"]
    assert 0 <= hits[0].distance <= 2
