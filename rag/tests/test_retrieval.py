from __future__ import annotations

from PIL import Image
import pytest

from wardrobe_rag.config import RAGConfig
from wardrobe_rag.retrieval import RetrievalEngine
from wardrobe_rag.schemas import RetrievalRequest, VectorHit
from wardrobe_rag.text import build_document, tokenize


class ControlledStore:
    """Already ranked vector hits; lets tests isolate fusion and slot logic."""

    def __init__(self, items):
        self.items = items
        self.queries = []

    def get_items(self, user_id):
        return self.items.get(user_id, [])

    def get_revision(self, user_id):
        return "test-revision-" + user_id

    def query(self, channel, vector, user_id, category, k):
        self.queries.append((channel, user_id, category, k))
        items = [item for item in self.get_items(user_id) if item.category == category]
        return [VectorHit(item_id=item.id, distance=(index + 1) / 100) for index, item in enumerate(items[:k])]


def engine_for(store, embedder, **kwargs):
    return RetrievalEngine(store, embedder, image_loader=lambda _: Image.new("RGB", (8, 8), "blue"), **kwargs)


def test_text_normalization_and_document_does_not_index_stale_snippet(make_item):
    assert tokenize("ШЁЛК!") == tokenize("шелк")
    assert tokenize("рубашка") == tokenize("рубашку")
    document = build_document(make_item("item", title="Красная блуза", color="Красный", embeddingSnippet="устаревший белый свитер"))
    assert "Красная" in document
    assert "устаревший" not in document
    assert "белый свитер" not in document


def test_dense_search_uses_per_category_budget_not_global_top_k(embedder, make_item):
    items = [make_item(f"top-{index}", "tops", f"Рубашка {index}") for index in range(8)]
    items += [make_item("bottom", "bottoms", "Брюки"), make_item("shoe", "shoes", "Лоферы")]
    store = ControlledStore({"alice": items, "bob": [make_item("secret")]})
    result = engine_for(store, embedder).retrieve(RetrievalRequest(user_id="alice", query="город", mode="dense"))
    assert len(result.candidates_by_slot["tops"]) == 3
    assert result.candidates_by_slot["bottoms"][0].item.id == "bottom"
    assert result.candidates_by_slot["shoes"][0].item.id == "shoe"
    assert result.missing_slots == []
    assert all(user == "alice" for _, user, _, _ in store.queries)
    assert {category for _, _, category, _ in store.queries} >= {"tops", "bottoms", "shoes"}


def test_bm25_without_matches_has_only_explicit_unranked_fallback(embedder, wardrobe):
    store = ControlledStore({"alice": wardrobe})
    request = RetrievalRequest(user_id="alice", query="ксилографическийавтожир", mode="bm25")
    result = engine_for(store, embedder).retrieve(request)
    assert result.missing_slots == []
    for candidates in result.candidates_by_slot.values():
        for candidate in candidates:
            assert candidate.fallback
            assert candidate.score == 0
            assert candidate.bm25_rank is None
            assert candidate.dense_rank is None
            assert candidate.visual_rank is None
    assert any("fallback" in warning.lower() for warning in result.warnings)
    assert store.queries == []


def test_hybrid_without_lexical_matches_has_only_dense_contributions(embedder, wardrobe):
    result = engine_for(ControlledStore({"alice": wardrobe}), embedder).retrieve(
        RetrievalRequest(user_id="alice", query="ксилографическийавтожир", mode="hybrid")
    )
    for candidates in result.candidates_by_slot.values():
        for candidate in candidates:
            assert candidate.bm25_rank is None
            assert candidate.bm25_contribution == 0
            assert candidate.score == pytest.approx(candidate.dense_contribution + candidate.visual_contribution)
            assert candidate.score > 0


def test_hybrid_alpha_endpoints_use_only_the_selected_channel(embedder, wardrobe):
    engine = engine_for(ControlledStore({"alice": wardrobe}), embedder)
    semantic = engine.retrieve(RetrievalRequest(user_id="alice", query="ксилографическийавтожир", mode="hybrid", alpha=1))
    assert semantic.candidates_by_slot["tops"]
    lexical = engine.retrieve(RetrievalRequest(user_id="alice", query="ксилографическийавтожир", mode="hybrid", alpha=0))
    assert all(candidate.fallback and candidate.score == 0 for candidates in lexical.candidates_by_slot.values() for candidate in candidates)


def test_anchor_survives_shortlist_and_explicit_exclusion_is_applied(embedder, make_item):
    items = [make_item(f"top-{index}", "tops", f"Рубашка {index}") for index in range(5)]
    items += [make_item("bottom", "bottoms", "Брюки"), make_item("shoe", "shoes", "Лоферы")]
    result = engine_for(ControlledStore({"alice": items}), embedder).retrieve(
        RetrievalRequest(user_id="alice", query="город", mode="dense", anchor_item_id="top-4", exclude_item_ids=["top-0"])
    )
    ids = [candidate.item.id for candidate in result.candidates_by_slot["tops"]]
    assert "top-4" in ids
    assert "top-0" not in ids
    assert next(candidate for candidate in result.candidates_by_slot["tops"] if candidate.item.id == "top-4").anchored


def test_visual_text_and_image_queries_use_the_correct_encoder(embedder, wardrobe):
    store = ControlledStore({"alice": wardrobe})
    engine = engine_for(store, embedder)
    result = engine.retrieve(RetrievalRequest(user_id="alice", query="белые кеды", mode="visual"))
    assert result.candidates_by_slot["shoes"]
    assert embedder.calls["visual_text"] == 1
    assert all(channel == "image" for channel, _, _, _ in store.queries)

    store.queries.clear()
    engine.retrieve(RetrievalRequest(user_id="alice", query_image="uploaded.png", mode="visual"))
    assert embedder.calls["image"] == 1
    assert all(channel == "image" for channel, _, _, _ in store.queries)


def test_cold_weather_requires_outerwear_and_rain_excludes_known_open_shoes(embedder, make_item):
    items = [
        make_item("top", "tops"),
        make_item("bottom", "bottoms", "Брюки"),
        make_item("sandals", "shoes", "Сандалии", weather={"open_shoes": True}),
        make_item("boots", "shoes", "Ботинки", weather={"open_shoes": False}),
    ]
    result = engine_for(ControlledStore({"alice": items}), embedder).retrieve(
        RetrievalRequest(user_id="alice", query="+6°C, дождь и ветер", mode="dense")
    )
    assert "outerwear" in result.required_slots
    assert "outerwear" in result.missing_slots
    assert [candidate.item.id for candidate in result.candidates_by_slot["shoes"]] == ["boots"]


def test_top_k_configuration_rejects_an_insufficient_pool():
    with pytest.raises(ValueError):
        RAGConfig(candidate_pool=1)


def test_rrf_combines_independent_dense_and_lexical_evidence(embedder, make_item):
    items = [
        make_item("dense-first", "tops", "Синяя майка"),
        make_item("lexical", "tops", "Изумрудная блуза", color="Изумрудный"),
        make_item("bottom", "bottoms", "Брюки"),
        make_item("shoe", "shoes", "Ботинки"),
    ]
    result = engine_for(ControlledStore({"alice": items}), embedder).retrieve(
        RetrievalRequest(user_id="alice", query="изумрудная", mode="hybrid", alpha=0.65)
    )
    candidate = result.candidates_by_slot["tops"][0]
    assert candidate.item.id == "lexical"
    assert candidate.bm25_rank == 1
    assert candidate.dense_rank == 2
    assert candidate.bm25_contribution == pytest.approx(0.35 / 61)
    assert candidate.dense_contribution == pytest.approx(0.65 / 62)
    assert candidate.score == pytest.approx(0.35 / 61 + 0.65 / 62)


def test_adapter_hits_outside_the_user_catalog_are_discarded(embedder, wardrobe):
    class BadAdapter(ControlledStore):
        def query(self, channel, vector, user_id, category, k):
            return [VectorHit(item_id="foreign-secret", distance=0)]

    result = engine_for(BadAdapter({"alice": wardrobe}), embedder).retrieve(
        RetrievalRequest(user_id="alice", query="город", mode="dense")
    )
    candidates = [candidate for values in result.candidates_by_slot.values() for candidate in values]
    assert all(candidate.item.id != "foreign-secret" for candidate in candidates)
    assert all(candidate.fallback and candidate.dense_rank is None for candidate in candidates)


def test_existing_index_cannot_be_queried_by_a_different_model(embedder, wardrobe):
    store = ControlledStore({"alice": wardrobe})
    store.get_fingerprint = lambda: "another-model-version"
    with pytest.raises(ValueError):
        engine_for(store, embedder).retrieve(RetrievalRequest(user_id="alice", query="город", mode="dense"))


def test_negated_color_and_explicit_material_exclusion_are_hard_filters(embedder, make_item):
    items = [
        make_item("black", "tops", "Чёрная рубашка", color="Чёрный"),
        make_item("red", "tops", "Красная рубашка", color="Красный"),
        make_item("wool", "bottoms", "Шерстяные брюки", material="Шерсть"),
        make_item("cotton", "bottoms", "Хлопковые брюки", material="Хлопок"),
        make_item("shoe", "shoes", "Кеды"),
    ]
    result = engine_for(ControlledStore({"alice": items}), embedder).retrieve(
        RetrievalRequest(user_id="alice", query="город без чёрного", mode="dense", exclude_materials=["шерсть"])
    )
    assert [candidate.item.id for candidate in result.candidates_by_slot["tops"]] == ["red"]
    assert [candidate.item.id for candidate in result.candidates_by_slot["bottoms"]] == ["cotton"]


def test_multimodal_diagnostics_expose_all_three_actual_rrf_contributions(embedder, wardrobe):
    result = engine_for(ControlledStore({"alice": wardrobe}), embedder).retrieve(
        RetrievalRequest(user_id="alice", query="рубашка", mode="multimodal", alpha=0.65, visual_weight=0.35)
    )
    top = result.candidates_by_slot["tops"][0]
    assert top.bm25_contribution == pytest.approx(0.35 / 61)
    assert top.dense_contribution == pytest.approx((0.65 * 0.65) / 61)
    assert top.visual_contribution == pytest.approx((0.65 * 0.35) / 61)
    assert top.score == pytest.approx(top.bm25_contribution + top.dense_contribution + top.visual_contribution)
