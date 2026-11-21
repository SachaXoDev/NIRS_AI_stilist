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
