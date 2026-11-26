import pytest

from wardrobe_rag import RAGService, SlotSearchRequest
from test_retrieval import ControlledStore, engine_for


def test_rain_layer_search_limits_channels_to_the_target_and_keeps_outfit(embedder, wardrobe, make_item):
    items = wardrobe[:3] + [
        make_item("dry", "outerwear", "Джинсовая куртка", weather={"waterproof": False}),
        make_item("rain", "outerwear", "Куртка-дождевик", weather={"waterproof": True}),
        make_item("spare", "shoes", "Сапоги", weather={"waterproof": True}),
    ]
    store = ControlledStore({"alice": items})
    service = RAGService(None, engine_for(store, embedder))
    result = service.retrieve_slot(SlotSearchRequest(
        user_id="alice", query="Добавь куртку в дождь", slot="outerwear", operation="add",
        outfit_item_ids=["top", "bottom", "shoe"], context={"occasion": "деловая встреча", "rain": False},
        mode="multimodal",
    ))
    assert result.slot == "outerwear" and result.context.rain is True
    assert result.kept_item_ids == ["top", "bottom", "shoe"] and result.replaced_item_id is None
    assert [candidate.item_id for candidate in result.candidates] == ["rain"]
    assert {(channel, category) for channel, _, category, _ in store.queries} == {
        ("text", "outerwear"), ("image", "outerwear"),
    }


@pytest.mark.parametrize("exclude_flat", [False, True])
def test_replace_preserves_other_ids_excludes_old_pair_and_ignores_unknown_heels(embedder, wardrobe, make_item, exclude_flat):
    old = wardrobe[2].model_copy(update={"tags": ["плоская подошва"]})
    items = wardrobe[:2] + [old,
        make_item("heeled", "shoes", "Туфли на каблуке", tags=["плоская подошва"]),
        make_item("unknown", "shoes", "Кеды"),
        make_item("flat", "shoes", "Мягкие лоферы", tags=["плоская подошва"]),
    ]
    store = ControlledStore({"alice": items, "bob": [make_item("secret", "shoes")]})
    result = engine_for(store, embedder).retrieve_slot(dict(
        user_id="alice", query="Замени туфли на обувь без каблука", slot="shoes", operation="replace",
        outfit_item_ids=["top", "bottom", "shoe"], exclude_item_ids=["flat"] if exclude_flat else [],
    ))
    assert [c.item_id for c in result.candidates] == ([] if exclude_flat else ["flat"])
    assert result.kept_item_ids == ["top", "bottom"] and result.replaced_item_id == "shoe"
    assert all(candidate.score > 0 and not candidate.fallback for candidate in result.candidates)


def test_retained_piece_and_occasion_provide_lexical_evidence(embedder, make_item):
    def item(item_id, slot, title, color="", tags=()):
        return make_item(item_id, slot, title, color=color, tags=list(tags), style=[], material=None)

    store = ControlledStore({"alice": [
        item("green", "tops", "Изумрудный свитер", "Изумрудный"),
        item("ruby", "tops", "Рубиновая блуза", "Рубиновый"),
        item("coat-green", "outerwear", "Изумрудное пальто", "Изумрудный"),
        item("coat-ruby", "outerwear", "Рубиновое пальто", "Рубиновый"),
        item("coat-stage", "outerwear", "Жакет", tags=["театр"]),
        item("coat-other", "outerwear", "Нейтральная куртка"),
    ]})
    engine = engine_for(store, embedder)
    base = dict(user_id="alice", query="добавь слой", slot="outerwear", operation="add", mode="bm25")
    for kept, match in [("green", "coat-green"), ("ruby", "coat-ruby")]:
        result = engine.retrieve_slot(dict(base, outfit_item_ids=[kept], context={"occasion": "театр"}))
        ids = [candidate.item_id for candidate in result.candidates]
        assert ids[0] == match and "coat-stage" in ids and "coat-other" not in ids


def test_single_slot_bm25_without_evidence_does_not_fill_with_an_arbitrary_item(embedder, make_item):
    items = [
        make_item("top", "tops", "Блуза", color="", material=None, style=[], tags=[]),
        make_item("coat", "outerwear", "Жакет", color="", material=None, style=[], tags=[]),
    ]
    engine = engine_for(ControlledStore({"alice": items}), embedder)
    result = engine.retrieve_slot(dict(user_id="alice", query="добавь слой", slot="outerwear",
                                       operation="add", outfit_item_ids=["top"], mode="bm25"))
    assert result.candidates == []


def test_slot_edit_rejects_foreign_ids_and_wrong_slot_replacements(embedder, wardrobe, make_item):
    engine = engine_for(ControlledStore({"alice": wardrobe, "bob": [make_item("secret")]}), embedder)
    base = dict(user_id="alice", query="Замени обувь", slot="shoes", operation="replace")
    with pytest.raises(ValueError, match="current wardrobe"):
        engine.retrieve_slot(dict(base, outfit_item_ids=["top", "secret"]))
    with pytest.raises(ValueError, match="requested slot"):
        engine.retrieve_slot(dict(base, outfit_item_ids=["top", "bottom", "shoe"], replace_item_id="top"))


def test_slot_search_uses_warm_lining_without_treating_plain_lining_as_insulation(embedder, wardrobe, make_item):
    warm = make_item("warm", "shoes", "Кроссовки", material="Кожа", materialDetails={"lining": "Шерсть"})
    plain = make_item("plain", "shoes", "Кроссовки", material="Кожа",
                      materialDetails={"lining": "Полиэстер", "insulation": "без утеплителя"})
    result = engine_for(ControlledStore({"alice": [*wardrobe[:3], plain, warm]}), embedder).retrieve_slot(dict(
        user_id="alice", query="Замени обувь на кроссовки", slot="shoes", operation="replace",
        outfit_item_ids=["top", "bottom", "shoe"], context={"temperature_c": 6}, mode="bm25",
    ))
    assert [(c.item_id, c.material_weather_score) for c in result.candidates] == [("warm", 1), ("plain", 0)]
