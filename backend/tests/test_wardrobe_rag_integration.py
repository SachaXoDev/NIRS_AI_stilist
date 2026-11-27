"""Связка бэкенда с настоящим пакетом `wardrobe_rag` из каталога rag/.

Chroma, BM25, RRF, слоты и `validate_selection` — реальные; подменён только кодировщик
(детерминированные тестовые векторы вместо 2,3 ГБ весов). Тесты проверяют интеграцию,
а не качество поиска. Если пакет не установлен, модуль пропускается.
"""
import json

import pytest

from tests.conftest import ScriptedLLM

pytest.importorskip("wardrobe_rag")

RRF_FIELDS = {
    "bm25_rank", "dense_rank", "visual_rank", "bm25_contribution", "dense_contribution",
    "visual_contribution", "anchored", "fallback",
}


def _answer(item_ids, text="Собрал лаконичный образ.") -> str:
    return json.dumps({
        "text": text,
        "outfit": {
            "title": "Деловой минимализм", "description": "Строгий силуэт.", "occasion": "Офис",
            "item_ids": item_ids, "stylistReasoning": "Контраст чёрного и серого.",
            "confidenceTips": ["Подверните рукава."],
        },
    }, ensure_ascii=False)


def _recommend(client, **payload):
    response = client.post("/api/recommend-outfit", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_health_reports_real_engine(make_client, rag_engine):
    retrieval = make_client(engine=rag_engine).get("/health").json()["retrieval"]
    assert retrieval["engine"] == "wardrobe_rag" and retrieval["model_fingerprint"]


def test_demo_wardrobe_is_seeded_into_chroma_with_images(make_client, rag_engine):
    client = make_client(engine=rag_engine)
    items = client.get("/api/wardrobe", params={"user_id": "demo"}).json()["items"]
    assert len(items) == 10
    # повторная синхронизация того же снимка ничего не переиндексирует
    report = client.post("/api/wardrobe/sync", json={"user_id": "demo", "items": items}).json()
    assert report["unchanged_count"] == 10 and report["added_count"] == 0
    assert report["image_count"] == 10, "SVG стартовой капсулы растеризуются и индексируются"


def test_end_to_end_with_mock_llm_and_real_retrieval(make_client, rag_engine, capsule_json):
    client = make_client(engine=rag_engine)
    data = _recommend(
        client, query="Москва: +6°C, ветрено, деловая встреча", wardrobe=capsule_json,
        user_id="user-elena", mode="multimodal", debug=True,
    )
    assert data["source"] == "mock" and data["meta"]["retriever"] == "wardrobe_rag"
    categories = [item["category"] for item in data["suggestedOutfit"]["items"]]
    assert {"tops", "bottoms", "shoes", "outerwear"} <= set(categories), "при +6°C нужен верхний слой"

    retrieval = data["retrieval"]
    assert retrieval["engine"] == "wardrobe_rag" and retrieval["mode"] == "multimodal"
    assert retrieval["alpha"] == 0.65 and retrieval["visual_weight"] == 0.35 and retrieval["rrf_c"] == 60
    assert retrieval["context"]["temperature_c"] == 6 and retrieval["context"]["wind"] is True
    assert "outerwear" in retrieval["required_slots"]
    assert RRF_FIELDS <= retrieval["candidates_by_slot"]["tops"][0].keys()
    assert retrieval["wardrobe_revision"] == data["meta"]["wardrobeRevision"]
    assert data["timings"]["syncMs"] > 0 and data["timings"]["retrievalMs"] > 0


def test_llm_choice_is_validated_by_the_rag_package(make_client, rag_engine):
    llm = ScriptedLLM([
        _answer(["item-1", "item-4", "item-8", "item-7"]),          # две пары обуви
        _answer(["item-1", "item-4", "item-8", "someone-elses"]),   # чужой id
        _answer(["item-1", "item-4", "item-8"]),
    ])
    client = make_client(engine=rag_engine, llm=llm, llm_max_repairs=2)
    data = _recommend(client, query="образ в офис на деловую встречу")
    assert data["source"] == "llm" and data["meta"]["llmAttempts"] == 3
    assert data["referencedItemIds"] == ["item-1", "item-4", "item-8"]
    assert "At most one item is allowed in slot shoes" in llm.calls[1][-1]["content"]
    assert "someone-elses" in llm.calls[2][-1]["content"]


def test_llm_failure_falls_back_to_package_assembly(make_client, rag_engine):
    llm = ScriptedLLM(["не json", "снова не json"])
    data = _recommend(make_client(engine=rag_engine, llm=llm), query="образ в офис")
    assert data["source"] == "fallback"
    categories = {item["category"] for item in data["suggestedOutfit"]["items"]}
    assert {"tops", "bottoms", "shoes"} <= categories


def test_three_tops_only_is_reported_as_missing_slots(make_client, rag_engine, capsule_json):
    tops = [dict(item, id=f"top-{n}") for n, item in enumerate(capsule_json[:1] * 3)]
    data = _recommend(make_client(engine=rag_engine), query="образ в офис", wardrobe=tops, user_id="u-tops")
    assert "suggestedOutfit" not in data and data["source"] == "none"
    assert data["missingSlots"] == ["bottoms", "shoes"]


def test_anchor_is_passed_structurally(make_client, rag_engine):
    query = "Подбери законченный образ с вещью «Шелковый шейный платок с геометрическим принтом»."
    data = _recommend(make_client(engine=rag_engine), query=query, debug=True)
    assert data["retrieval"]["anchor_item_id"] == "item-10"
    assert "item-10" in data["referencedItemIds"]


def test_anchor_conflicting_with_weather_is_dropped_with_warning(make_client, rag_engine, capsule_json):
    # рубашка размечена как «не ниже +12°C» — закрепить её при +2°C нельзя
    wardrobe = [dict(item, weather={"temperature_min": 12}) if item["id"] == "item-1" else item
                for item in capsule_json]
    data = _recommend(
        make_client(engine=rag_engine), query="что надеть при +2°C", wardrobe=wardrobe,
        user_id="u-weather", anchor_item_id="item-1",
    )
    assert "item-1" not in data["referencedItemIds"]
    assert any("item-1" in warning and "без неё" in warning for warning in data["warnings"])


def test_users_with_same_item_ids_are_isolated(make_client, rag_engine, capsule_json):
    client = make_client(engine=rag_engine)
    renamed = [dict(item, title="Чужая вещь " + item["id"]) for item in capsule_json]
    client.post("/api/wardrobe/sync", json={"user_id": "bob", "items": renamed})
    data = _recommend(client, query="образ в офис", user_id="demo")
    assert all(not item["title"].startswith("Чужая") for item in data["suggestedOutfit"]["items"])


def test_wardrobe_ids_restrict_real_retrieval(make_client, rag_engine):
    data = _recommend(
        make_client(engine=rag_engine), query="образ в офис", wardrobe_ids=["item-5", "item-3", "item-7"]
    )
    assert set(data["referencedItemIds"]) == {"item-5", "item-3", "item-7"}


def test_data_url_photo_is_accepted(make_client, rag_engine, capsule_json):
    import base64
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (24, 32), (200, 30, 30)).save(buffer, format="PNG")
    photo = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    custom = {"id": "custom-1", "title": "Красные лодочки", "category": "shoes", "color": "Красный",
              "season": "all", "style": [], "tags": [], "imageUrl": photo, "uploadedAt": "2026-11-20"}
    wardrobe = [item for item in capsule_json if item["category"] != "shoes"] + [custom]
    client = make_client(engine=rag_engine)
    report = client.post("/api/wardrobe/sync", json={"user_id": "u-photo", "items": wardrobe}).json()
    assert report["image_count"] == 9 and not report["warnings"]
    data = _recommend(client, query="образ на вечер", user_id="u-photo")
    shoes = [item for item in data["suggestedOutfit"]["items"] if item["category"] == "shoes"]
    assert shoes[0]["id"] == "custom-1" and shoes[0]["imageUrl"] == photo


def test_stream_sends_retrieval_diagnostics_before_text(make_client, rag_engine):
    response = make_client(engine=rag_engine).post(
        "/api/recommend-outfit/stream", json={"query": "Дождь и +12°C", "debug": True}
    )
    events = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    names = [name for name, _ in events]
    assert names.index("retrieval") < names.index("delta") < names.index("result")
    retrieval = dict(events)["retrieval"]
    assert retrieval["engine"] == "wardrobe_rag" and "candidates_by_slot" in retrieval
    assert dict(events)["result"]["suggestedOutfit"]


@pytest.mark.parametrize("has_sandals", [True, False])
def test_hot_beach_outfit_excludes_closed_shoes(make_client, rag_engine, has_sandals):
    beach_ids = ["item-18", "item-27", "item-39"]
    llm = ScriptedLLM([_answer(["item-18", "item-27", "item-40"]), _answer(beach_ids)])
    client = make_client(engine=rag_engine, llm=llm)
    ids = {"item-18", "item-27", "item-40", "item-24", "item-5"}
    if has_sandals:
        ids.add("item-39")
    wardrobe = [item for item in client.get("/api/wardrobe/base-capsule").json() if item["id"] in ids]
    result = _recommend(client, query="Подбери образ для пляжа в жару при +30°C",
                        wardrobe=wardrobe, anchor_item_id="item-40", user_id="test-beach", debug=True)
    assert result["retrieval"]["context"]["occasion"] == "beach"
    if has_sandals:
        assert result["source"] == "llm" and result["referencedItemIds"] == beach_ids
        assert result["meta"]["llmAttempts"] == 2
    else:
        assert result["source"] == "none" and result["missingSlots"] == ["shoes"]
        assert "suggestedOutfit" not in result and not llm.calls


def test_beach_with_flip_flops_uses_that_pair_from_the_wardrobe(make_client, rag_engine):
    capsule = _capsule50()
    shoes = {"id": "slides", "category": "shoes", "title": "Белые шлёпки"}
    outfit = ["item-18", "item-27", "slides"]
    llm = ScriptedLLM([_answer(["item-18", "item-27", "item-39"]), _answer(outfit)])
    result = _recommend(
        make_client(engine=rag_engine, llm=llm), user_id="beach-with-slides",
        query="Хочу собрать образ со шлепками на пляж", wardrobe=[*capsule.values(), shoes],
    )
    assert result["suggestedOutfit"]["occasion"] == "Пляж"
    assert set(result["referencedItemIds"]) == set(outfit)


def test_beach_flip_flop_retry_keeps_request_until_the_user_changes_it(make_client, rag_engine):
    client = make_client(engine=rag_engine)
    wardrobe = list(_capsule50().values())
    query = "Хочу собрать образ со шлепками на пляж"
    history = [{"sender": "user", "text": "привет"}, {"sender": "assistant", "text": "Привет!"}]
    for text in (query, "создай образ"):
        result = _recommend(client, query=text, user_id="beach-retry", wardrobe=wardrobe, history=history)
        assert result["meta"]["occasion"] == "Пляж" and result["missingSlots"] == ["shoes"]
        assert "suggestedOutfit" not in result and "шлёпки" in result["text"] and "сандалии" in result["text"]
        history.extend([{"sender": "user", "text": text}, {"sender": "assistant", "text": result["text"]}])

    result = _recommend(client, query="Создай образ с сандалиями на пляж", user_id="beach-retry",
                        wardrobe=wardrobe, history=history)
    assert {"item-18", "item-27", "item-39"} <= set(result["referencedItemIds"])

    result = _recommend(client, query="Создай образ в офис", user_id="beach-retry",
                        wardrobe=wardrobe, history=history)
    assert result["suggestedOutfit"]["occasion"] == "Деловой выход"


def test_engine_is_built_from_settings_like_in_integration_md(settings, tmp_path, monkeypatch):
    """Проверяем проводку `from_settings` (пути, аргументы конструкторов) без скачивания весов."""
    import wardrobe_rag.embedding as embedding

    from app.rag.factory import build_engine
    from app.storage.app_store import AppStore
    from tests.conftest import REPO_ROOT, DeterministicTestEmbedder

    seen = {}

    def fake_embedder(*, cache_dir, device, offline):
        seen.update(cache_dir=cache_dir, device=device, offline=offline)
        return DeterministicTestEmbedder()

    monkeypatch.setattr(embedding, "SentenceTransformerEmbedder", fake_embedder)
    cfg = settings.model_copy(update={
        "rag_engine": "wardrobe_rag",
        "rag_data_dir": str(tmp_path / "rag_data"),
        "rag_cache_dir": str(tmp_path / "cache"),
        "rag_public_root": str(REPO_ROOT / "public"),
        "rag_offline": True,
    })
    engine = build_engine(cfg, AppStore(cfg.database_path))
    assert engine.name == "wardrobe_rag"
    assert seen == {"cache_dir": tmp_path / "cache", "device": "cpu", "offline": True}
    assert engine.info()["offline"] is True and (tmp_path / "rag_data" / "chroma").exists()


def test_auto_mode_falls_back_to_builtin_and_strict_mode_fails(settings, monkeypatch):
    import wardrobe_rag.embedding as embedding

    from app.rag.factory import build_engine
    from app.storage.app_store import AppStore

    def broken_embedder(**kwargs):
        raise OSError("models are not in the offline cache")

    monkeypatch.setattr(embedding, "SentenceTransformerEmbedder", broken_embedder)
    store = AppStore(settings.database_path)
    assert build_engine(settings.model_copy(update={"rag_engine": "auto"}), store).name == "builtin-bm25"
    with pytest.raises(RuntimeError, match="wardrobe_rag"):
        build_engine(settings.model_copy(update={"rag_engine": "wardrobe_rag"}), store)


# --- точечная правка образа поверх настоящего retrieve_slot ----------------------------------------
# Те же три примера, что в rag/data/slot_search_examples.json, но через HTTP-контракт бэкенда.


def _capsule50():
    from app.storage.app_store import load_base_capsule

    return {item.id: item.model_dump(by_alias=True, mode="json") for item in load_base_capsule()}


RUNNING_REQUEST = "Собери образ для пробежки в тёплый день"
RUNNING_IDS = ["item-16", "item-25", "item-37"]


def test_running_search_and_model_repair_on_full_capsule(make_client, rag_engine):
    unsuitable = ["item-5", "item-22", "item-41"]  # комплект из воспроизведённого промаха
    llm = ScriptedLLM([_answer(unsuitable), _answer(RUNNING_IDS)])
    result = _recommend(
        make_client(engine=rag_engine, llm=llm), query=RUNNING_REQUEST, user_id="running-capsule",
        wardrobe=list(_capsule50().values()), debug=True,
    )
    slots = result["retrieval"]["candidates_by_slot"]
    assert [entry["item"]["id"] for entry in slots["shoes"]] == ["item-37"]
    assert set(result["referencedItemIds"]) == set(RUNNING_IDS)
    assert result["source"] == "llm" and result["meta"]["llmAttempts"] == 2


def test_running_without_running_shoes_does_not_substitute_casual_shoes(make_client, rag_engine):
    capsule = _capsule50()
    del capsule["item-37"]
    result = _recommend(
        make_client(engine=rag_engine), query="Что надеть, чтобы побегать в парке?", user_id="running-no-shoes",
        wardrobe=list(capsule.values()),
    )
    assert result["missingSlots"] == ["shoes"] and "suggestedOutfit" not in result
    assert "беговых кроссовок" in result["text"]


def _edit(client, user_id, query, wardrobe_ids, card_ids, request_text, **payload):
    capsule = _capsule50()
    return _recommend(
        client, query=query, user_id=user_id, wardrobe=[capsule[i] for i in wardrobe_ids], debug=True,
        history=[
            {"sender": "user", "text": request_text},
            {"sender": "assistant", "text": "В образ вошли: …", "hasOutfit": True, "itemIds": card_ids},
        ],
        **payload,
    )


def test_running_shoe_edit_keeps_original_when_only_casual_alternatives_exist(make_client, rag_engine):
    result = _edit(
        make_client(engine=rag_engine), "running-shoe-edit", "Замени обувь, остальное оставь",
        [*RUNNING_IDS, "item-36", "item-41"], RUNNING_IDS, RUNNING_REQUEST,
    )
    assert "suggestedOutfit" not in result and "edit" not in result
    assert result["retrieval"]["candidates"] == []


def test_add_rain_layer_keeps_the_outfit_and_skips_non_waterproof_jackets(make_client, rag_engine):
    result = _edit(
        make_client(engine=rag_engine), "slot-rain", "Добавь куртку в дождь к этому образу",
        ["item-1", "item-4", "item-8", "item-28", "item-29", "item-33"], ["item-1", "item-4", "item-8"],
        "Подбери образ на деловую встречу, +10°C",
    )
    assert result["edit"]["keptItemIds"] == ["item-1", "item-4", "item-8"]
    assert result["edit"]["addedItemIds"] == ["item-33"], "жакет и джинсовка помечены как не для дождя"
    assert result["source"] == "rules" and result["meta"]["retriever"] == "wardrobe_rag"
    retrieval = result["retrieval"]
    assert retrieval["engine"] == "wardrobe_rag" and retrieval["slot"] == "outerwear"
    assert retrieval["context"]["rain"] is True and retrieval["context"]["temperature_c"] == 10
    assert retrieval["wardrobe_revision"] == result["meta"]["wardrobeRevision"]


def test_replace_heels_changes_one_id_and_never_returns_the_old_pair(make_client, rag_engine):
    result = _edit(
        make_client(engine=rag_engine), "slot-shoes", "Замени туфли на что-нибудь без каблука, остальное оставь",
        ["item-1", "item-4", "item-7", "item-35", "item-36", "item-42"], ["item-1", "item-4", "item-42"],
        "Подбери образ на встречу в стиле smart casual, +17°C",
    )
    ids = [item["id"] for item in result["suggestedOutfit"]["items"]]
    assert set(ids) ^ {"item-1", "item-4", "item-42"} == {"item-42", "item-36"}
    assert result["retrieval"]["replaced_item_id"] == "item-42"
    assert result["retrieval"]["kept_item_ids"] == ["item-1", "item-4"]


def test_no_flat_alternative_leaves_the_outfit_untouched(make_client, rag_engine):
    result = _edit(
        make_client(engine=rag_engine), "slot-empty", "Замени туфли на обувь без каблука",
        ["item-1", "item-4", "item-7", "item-35", "item-42"], ["item-1", "item-4", "item-42"],
        "Подбери образ на деловую встречу",
    )
    assert "suggestedOutfit" not in result and "edit" not in result and result["source"] == "none"
    assert "Прежний образ оставляю без изменений" in result["text"]
    assert result["retrieval"]["candidates"] == []


def test_llm_picks_among_real_slot_candidates(make_client, rag_engine):
    llm = ScriptedLLM([json.dumps({"outfit": {"item_ids": ["item-35"]}})])
    result = _edit(
        make_client(engine=rag_engine, llm=llm), "slot-pick", "Замени туфли",
        ["item-1", "item-4", "item-7", "item-35", "item-36", "item-42"], ["item-1", "item-4", "item-42"],
        "Подбери образ в офис",
    )
    assert result["source"] == "llm" and result["edit"]["addedItemIds"] == ["item-35"]
    offered = llm.calls[0][1]["content"].split("Допустимые ID:")[1]
    assert '"item-42"' not in offered and '"item-35"' in offered


def test_editing_one_item_does_not_re_encode_the_whole_wardrobe(settings, tmp_path, monkeypatch):
    """Бэкенд включает кеш эмбеддингов: правка одной вещи кодирует одну вещь, а не весь каталог."""
    import wardrobe_rag.embedding as embedding

    from app.main import create_app
    from fastapi.testclient import TestClient
    from tests.conftest import REPO_ROOT, DeterministicTestEmbedder

    monkeypatch.setattr(embedding, "SentenceTransformerEmbedder", lambda **kwargs: DeterministicTestEmbedder())
    base = {
        "rag_engine": "wardrobe_rag", "rag_cache_dir": str(tmp_path / "models"),
        "rag_public_root": str(REPO_ROOT / "public"), "rag_offline": True,
    }
    capsule = list(_capsule50().values())
    edited = [dict(capsule[0], color="Красный"), *capsule[1:]]

    def sync_counts(client, user_id, items):
        report = client.post("/api/wardrobe/sync", json={"user_id": user_id, "items": items}).json()
        return report["encoded_text_count"], report["encoded_image_count"]

    cached = TestClient(create_app(settings.model_copy(update={**base, "rag_data_dir": str(tmp_path / "with")})))
    assert cached.get("/health").json()["retrieval"]["embedding_cache"] is True
    # 10 из 50 вещей уже закодированы при создании демо-пользователя на старте сервера.
    assert sync_counts(cached, "alice", capsule) == (40, 40)
    assert sync_counts(cached, "alice", edited) == (1, 0), "изменился текст одной вещи"
    assert sync_counts(cached, "bob", capsule) == (0, 0), "та же капсула у другого пользователя"
    assert (tmp_path / "with" / "embedding_cache.sqlite3").exists()

    plain = TestClient(create_app(settings.model_copy(update={
        **base, "rag_data_dir": str(tmp_path / "without"), "rag_embedding_cache": False,
    })))
    assert sync_counts(plain, "alice", capsule) == (50, 50)
    assert sync_counts(plain, "alice", edited) == (50, 50), "без кеша правка перекодирует всё"


def test_detailed_query_routes_to_wardrobe_and_rejects_wrong_component(make_client, rag_engine):
    items = [
        {"id": "top", "category": "tops", "title": "Рубашка"},
        {"id": "pants", "category": "bottoms", "title": "Брюки"},
        {"id": "shoe", "category": "shoes", "title": "Кроссовки"},
        {"id": "wrong", "category": "outerwear", "title": "Пальто", "color": "Бежевый",
         "material": "100% вискоза", "materialDetails": {"lining": "100% шерсть"}},
        {"id": "right", "category": "outerwear", "title": "Пальто", "color": "Бежевый",
         "material": "100% шерсть", "materialDetails": {"lining": "100% вискоза"}},
    ]
    llm = ScriptedLLM([_answer(["top", "pants", "shoe", "wrong"]), _answer(["top", "pants", "shoe", "right"])])
    result = _recommend(make_client(engine=rag_engine, llm=llm), query="Хочу бежевое пальто с подкладкой из вискозы",
                        wardrobe=items, user_id="precision-case", debug=True)
    assert set(result["referencedItemIds"]) == {"right", "top", "pants", "shoe"}
    assert result["retrieval"]["missing_slots"] == []


def test_insulation_is_only_a_preference_not_a_frost_rating(make_client, rag_engine):
    items = [
        {"id": "top", "category": "tops", "title": "Рубашка"},
        {"id": "pants", "category": "bottoms", "title": "Брюки"},
        {"id": "coat", "category": "outerwear", "title": "Куртка", "weather": {"temperature_min": -30}},
        {"id": "shoes", "category": "shoes", "title": "Кроссовки", "season": "unknown",
         "materialDetails": {"insulation": "100% полиэстер"}},
    ]
    client = make_client(engine=rag_engine)
    result = _recommend(client, query="Подбери образ для прогулки при −25°C", wardrobe=items,
                        user_id="unrated-insulation", debug=True)
    assert result["missingSlots"] == ["shoes"]
    assert result["source"] == "none" and "suggestedOutfit" not in result
