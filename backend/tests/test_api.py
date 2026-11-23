"""Контракт HTTP API на встроенном движке и mock/сценарной LLM (без сети и моделей)."""
import json

import pytest

from app.services.llm.base import LLMError

from tests.conftest import ScriptedLLM

BASE_IDS = [f"item-{i}" for i in range(1, 11)]
OUTFIT_KEYS = {
    "id", "title", "description", "occasion", "items", "stylistReasoning", "matchScore",
    "confidenceTips",
}


def _answer(item_ids, text="Собрал лаконичный образ.", **outfit) -> str:
    body = {
        "title": "Деловой минимализм",
        "description": "Строгий силуэт.",
        "occasion": "Офис",
        "item_ids": item_ids,
        "stylistReasoning": "Контраст чёрного и серого.",
        "confidenceTips": ["Подверните рукава.", "Сумку держите в руке."],
    }
    body.update(outfit)
    return json.dumps({"text": text, "outfit": body}, ensure_ascii=False)


def _recommend(client, **payload):
    response = client.post("/api/recommend-outfit", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _events(client, **payload):
    response = client.post("/api/recommend-outfit/stream", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


# --- базовый контракт -----------------------------------------------------------------


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm"] == {"provider": "mock", "model": "rule-based-stylist"}
    assert body["retrieval"]["engine"] == "builtin-bm25"


def test_cors_allows_vite_dev_origin(client):
    response = client.options(
        "/api/recommend-outfit",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_kt1_request_shape_returns_frontend_contract(client):
    """Запрос ровно в том виде, как его шлёт stylistApi.ts из КТ-1 (только id)."""
    data = _recommend(
        client,
        query="Подбери образ для деловой встречи",
        wardrobe_ids=BASE_IDS,
        context={"occasion": "business", "weather": "rainy", "vibe": "minimalism"},
    )
    assert {"text", "suggestedOutfit", "referencedItemIds"} <= data.keys()
    outfit = data["suggestedOutfit"]
    assert set(outfit) == OUTFIT_KEYS
    assert 0 <= outfit["matchScore"] <= 100 and isinstance(outfit["matchScore"], int)
    assert data["referencedItemIds"] == [item["id"] for item in outfit["items"]]
    assert set(data["referencedItemIds"]) <= set(BASE_IDS)
    for item in outfit["items"]:  # полные WardrobeItem в camelCase
        assert {"id", "title", "category", "color", "season", "style", "tags", "imageUrl"} <= item.keys()
        assert item["imageUrl"]
    categories = [item["category"] for item in outfit["items"]]
    assert {"tops", "bottoms", "shoes"} <= set(categories)
    assert all(categories.count(slot) == 1 for slot in ("tops", "bottoms", "shoes", "outerwear") if slot in categories)
    assert data["source"] == "mock" and data["missingSlots"] == []
    assert data["meta"]["retriever"] == "builtin-bm25"
    assert "retrieval" not in data, "полная диагностика — только по debug=true"


def test_query_only_uses_seeded_demo_wardrobe(client):
    data = _recommend(client, query="Дождь и +12°C")
    categories = {item["category"] for item in data["suggestedOutfit"]["items"]}
    assert "outerwear" in categories
    assert "item-6" in data["referencedItemIds"], "в дождь ожидаем тренч"


def test_inline_wardrobe_is_synced_and_used(client, capsule_json):
    custom = {
        "id": "custom-1", "title": "Красные замшевые балетки", "category": "shoes",
        "color": "Красный", "season": "all", "style": ["минимализм"], "tags": ["shoes"],
        "imageUrl": "", "uploadedAt": "2026-11-20T10:00:00Z",
    }
    wardrobe = [item for item in capsule_json if item["category"] != "shoes"] + [custom]
    data = _recommend(client, query="образ на прогулку", wardrobe=wardrobe, user_id="user-elena")
    shoes = [item for item in data["suggestedOutfit"]["items"] if item["category"] == "shoes"]
    assert [item["id"] for item in shoes] == ["custom-1"]
    assert shoes[0]["imageUrl"] == "/clothes/loafers.svg", "пустая картинка заменяется силуэтом"

    stored = client.get("/api/wardrobe", params={"user_id": "user-elena"}).json()
    assert len(stored["items"]) == 9
    # следующий запрос того же пользователя может прийти уже только с id
    again = _recommend(client, query="образ на прогулку", wardrobe_ids=["custom-1", "item-1", "item-3"], user_id="user-elena")
    assert set(again["referencedItemIds"]) == {"custom-1", "item-1", "item-3"}


def test_wardrobe_ids_restrict_the_search(client):
    data = _recommend(client, query="образ в офис", wardrobe_ids=["item-1", "item-3", "item-7"])
    assert set(data["referencedItemIds"]) == {"item-1", "item-3", "item-7"}


def test_unknown_ids_are_reported(client):
    data = _recommend(client, query="образ в офис", wardrobe_ids=["item-1", "item-3", "item-7", "ghost-1"])
    assert any("ghost-1" in warning for warning in data["warnings"])


def test_empty_wardrobe_returns_text_only(client):
    data = _recommend(client, query="образ в офис", wardrobe=[], user_id="guest-1")
    assert "suggestedOutfit" not in data and data["referencedItemIds"] == []
    assert data["source"] == "none" and data["missingSlots"] == ["tops", "bottoms", "shoes"]
    assert "гардероб" in data["text"].lower()


def test_incomplete_wardrobe_is_not_presented_as_outfit(client, capsule_json):
    no_shoes = [item for item in capsule_json if item["category"] != "shoes"]
    data = _recommend(client, query="образ в офис", wardrobe=no_shoes, user_id="u-no-shoes")
    assert "suggestedOutfit" not in data
    assert data["missingSlots"] == ["shoes"] and data["source"] == "none"
    assert "обувь" in data["text"]


def test_cold_weather_without_outerwear_is_incomplete(client, capsule_json):
    wardrobe = [item for item in capsule_json if item["category"] != "outerwear"]
    data = _recommend(client, query="на улице -5", wardrobe=wardrobe, user_id="u-no-coat")
    assert data["missingSlots"] == ["outerwear"] and "-5°C" in data["text"]


def test_anchor_from_item_title_is_included(client):
    query = (
        "Подбери законченный образ для ужина с вещью «Шелковый шейный платок с геометрическим "
        "принтом». С чем из моей капсулы она комбинируется гармоничнее всего?"
    )
    assert "item-10" in _recommend(client, query=query)["referencedItemIds"]


def test_explicit_anchor_and_unknown_anchor(client):
    data = _recommend(client, query="образ в офис", anchor_item_id="item-7")
    assert "item-7" in data["referencedItemIds"]
    data = _recommend(client, query="образ в офис", anchor_item_id="ghost")
    assert data["suggestedOutfit"] and any("ghost" in w for w in data["warnings"])


def test_debug_returns_full_retrieval_diagnostics(client):
    data = _recommend(client, query="образ в офис", debug=True)
    retrieval = data["retrieval"]
    assert retrieval["engine"] == "builtin-bm25"
    assert {"candidates_by_slot", "required_slots", "missing_slots", "timings_ms", "wardrobe_revision"} <= retrieval.keys()
    candidate = retrieval["candidates_by_slot"]["shoes"][0]
    assert {"item", "score", "bm25_rank", "anchored", "fallback"} <= candidate.keys()
    assert data["meta"]["wardrobeRevision"] == retrieval["wardrobe_revision"]
    assert "не вероятность" in data["meta"]["matchScoreMethod"]


def test_request_validation(client):
    assert client.post("/api/recommend-outfit", json={"query": "   "}).status_code == 422
    assert client.post("/api/recommend-outfit", json={}).status_code == 422
    bad_item = {"id": "x", "title": "Шляпа", "category": "hats"}
    response = client.post("/api/recommend-outfit", json={"query": "образ", "wardrobe": [bad_item]})
    assert response.status_code == 422


# --- LLM: исправление и фолбэк ----------------------------------------------------------


def test_valid_llm_selection_is_used_but_prose_is_grounded_in_card(make_client):
    llm = ScriptedLLM([_answer(["item-8", "item-4", "item-1", "item-2"], text="Красные сапоги.",
                               title="Красные сапоги", description="Красные сапоги.")])
    data = _recommend(make_client(llm=llm), query="образ в офис")
    assert all(item["title"] in data["text"] for item in data["suggestedOutfit"]["items"])
    assert "сапоги" not in json.dumps(data, ensure_ascii=False).lower()
    assert data["source"] == "llm" and data["meta"]["llmAttempts"] == 1
    assert data["referencedItemIds"] == ["item-2", "item-1", "item-4", "item-8"], "порядок: сверху вниз"
    assert data["suggestedOutfit"]["description"] == data["text"]
    assert data["meta"]["llmProvider"] == "scripted"


def test_prompt_contains_candidates_rules_and_no_images(make_client, capsule_json):
    capsule_json[0]["imageUrl"] = "data:image/png;base64," + "A" * 5000
    llm = ScriptedLLM([_answer(["item-1", "item-4", "item-8"])])
    _recommend(
        make_client(llm=llm), query="образ в офис", wardrobe=capsule_json, user_id="u1",
        history=[{"sender": "user", "text": "привет"}, {"sender": "assistant", "text": "Здравствуйте!"}],
    )
    messages = llm.calls[0]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    system, user = messages[0]["content"], messages[-1]["content"]
    assert "12 STOREEZ" in system and "ФОРМАТ ОТВЕТА" in system
    assert "образ в офис" in user and '"id": "item-8"' in user and "Обязательные слоты" in user
    assert "base64" not in user and "AAAA" not in user, "фото в промпт не попадают"


def test_invalid_json_is_repaired_on_second_attempt(make_client):
    llm = ScriptedLLM(["Конечно! Вот образ: рубашка и брюки.", _answer(["item-1", "item-4", "item-8"])])
    data = _recommend(make_client(llm=llm), query="образ в офис")
    assert data["source"] == "llm" and data["meta"]["llmAttempts"] == 2
    repair = llm.calls[1]
    assert repair[-2]["role"] == "assistant" and "не прошёл проверку" in repair[-1]["content"]


def test_hallucinated_and_duplicate_slots_trigger_repair_with_reasons(make_client):
    llm = ScriptedLLM([
        _answer(["item-1", "item-4", "item-8", "item-7", "prada-bag"]),
        _answer(["item-1", "item-4", "item-8"]),
    ])
    data = _recommend(make_client(llm=llm), query="образ в офис")
    assert data["referencedItemIds"] == ["item-1", "item-4", "item-8"]
    feedback = llm.calls[1][-1]["content"]
    assert "prada-bag" in feedback and "shoes" in feedback


def test_missing_required_slot_triggers_repair(make_client):
    llm = ScriptedLLM([_answer(["item-1", "item-4"]), _answer(["item-1", "item-4", "item-8"])])
    data = _recommend(make_client(llm=llm), query="образ в офис")
    assert data["meta"]["llmAttempts"] == 2
    assert "обязательные слоты: shoes" in llm.calls[1][-1]["content"]


def test_persistently_bad_llm_falls_back_to_deterministic_outfit(make_client):
    llm = ScriptedLLM(["мусор", "{}", "ещё мусор"])
    data = _recommend(make_client(llm=llm), query="образ в офис")
    assert data["source"] == "fallback" and data["meta"]["llmAttempts"] == 2
    assert data["suggestedOutfit"]["items"] and len(llm.calls) == 2, "LLM_MAX_REPAIRS=1 → две попытки"
    assert any("не прошёл проверку" in warning for warning in data["warnings"])


def test_llm_outage_falls_back_without_500(make_client):
    llm = ScriptedLLM([LLMError("connection refused")])
    data = _recommend(make_client(llm=llm), query="Дождь и +12°C")
    assert data["source"] == "fallback" and "item-6" in data["referencedItemIds"]
    assert any("LLM недоступна" in warning for warning in data["warnings"])


@pytest.mark.parametrize("query", ["Привет!", "С чем носить широкие брюки?", "Что такое капсульный гардероб?"])
def test_conversation_works_with_empty_wardrobe(make_client, query):
    llm = ScriptedLLM([_answer(["item-1", "item-4", "item-8"], text="Совет по стилю.")])
    result = _recommend(make_client(llm=llm), query=query, wardrobe=[], debug=True)
    assert "suggestedOutfit" not in result and result["missingSlots"] == []
    assert result["source"] == "llm" and "retriever" not in result["meta"]
    assert "retrieval" not in result


def test_repairs_can_be_disabled(make_client):
    llm = ScriptedLLM(["мусор", _answer(["item-1", "item-4", "item-8"])])
    data = _recommend(make_client(llm=llm, llm_max_repairs=0), query="образ в офис")
    assert data["source"] == "fallback" and len(llm.calls) == 1


# --- SSE ---------------------------------------------------------------------------------


def test_stream_event_order_and_text_deltas(client):
    events = _events(client, query="Дождь и +12°C")
    names = [name for name, _ in events]
    assert names[:3] == ["status", "retrieval", "status"]
    assert names[-3:] == ["status", "delta", "result"]
    result = events[-1][1]
    streamed = "".join(data["text"] for name, data in events if name == "delta")
    assert streamed == result["text"], "дельты складываются ровно в итоговый текст"
    assert result["suggestedOutfit"]["items"] and result["source"] == "mock"
    retrieval = events[1][1]
    assert retrieval["engine"] == "builtin-bm25" and "item-6" in retrieval["candidate_ids_by_slot"]["outerwear"]
    assert "candidates_by_slot" not in retrieval


def test_stream_with_broken_llm_still_ends_with_valid_result(make_client):
    llm = ScriptedLLM([LLMError("boom")])
    events = _events(make_client(llm=llm), query="образ в офис")
    assert events[-1][0] == "result"
    assert events[-1][1]["source"] == "fallback" and events[-1][1]["suggestedOutfit"]


def test_stream_repairs_invalid_streamed_answer(make_client):
    llm = ScriptedLLM([_answer(["item-1", "item-4"], text="Черновик."), _answer(["item-1", "item-4", "item-8"], text="Исправлено.")])
    events = _events(make_client(llm=llm), query="образ в офис")
    result = events[-1][1]
    assert result["meta"]["llmAttempts"] == 2
    assert [data["text"] for event, data in events if event == "delta"] == [result["text"]]


def test_stream_for_incomplete_wardrobe(client):
    events = _events(client, query="Привет! Подбери образ в офис", wardrobe=[], user_id="guest-2")
    assert [name for name, _ in events] == ["status", "delta", "result"]
    assert events[-1][1]["source"] == "none"
    assert events[-1][1]["missingSlots"] == ["tops", "bottoms", "shoes"]


def test_stream_greeting_with_incomplete_wardrobe(make_client, capsule_json):
    llm = ScriptedLLM(['{"text": "Здравствуйте! Обсудим стиль?", "outfit": null}'])
    events = _events(make_client(llm=llm), query="привет", wardrobe=[capsule_json[0]])
    name, result = events[-1]
    assert name == "result" and "suggestedOutfit" not in result
    assert result["missingSlots"] == [] and result["source"] == "llm"
    assert all(event != "retrieval" for event, _ in events)
    assert "".join(payload["text"] for event, payload in events if event == "delta") == result["text"]

_OFFICE_HISTORY = [
    {"sender": "user", "text": "Подбери образ в офис"},
    {"sender": "assistant", "text": "Рубашка, брюки и лоферы.", "hasOutfit": True},
]


def test_warmer_followup_requires_outerwear_and_keeps_occasion(make_client):
    llm = ScriptedLLM([_answer(["item-1", "item-4", "item-8"]), _answer(["item-5", "item-4", "item-8", "item-6"])])
    result = _events(make_client(llm=llm), query="А можно потеплее?", history=_OFFICE_HISTORY, debug=True)[-1][1]
    assert result["source"] == "llm" and result["retrieval"]["context"]["occasion"] == "business"
    assert {item["category"] for item in result["suggestedOutfit"]["items"]} == {"tops", "bottoms", "shoes", "outerwear"}


def test_warmer_followup_rechecks_current_wardrobe(client, capsule_json):
    result = _recommend(client, query="А можно потеплее?", history=_OFFICE_HISTORY,
                        wardrobe=[item for item in capsule_json if item["category"] != "outerwear"])
    assert result["missingSlots"] == ["outerwear"] and "suggestedOutfit" not in result


def test_conversation_outage_does_not_trigger_outfit_fallback(make_client):
    result = _events(make_client(llm=ScriptedLLM([LLMError("offline")])), query="Что такое оверсайз?")[-1][1]
    assert result["source"] == "fallback" and "suggestedOutfit" not in result and not result["missingSlots"]


# --- гардероб ---------------------------------------------------------------------------


def test_wardrobe_sync_is_full_snapshot(client, capsule_json):
    first = client.post("/api/wardrobe/sync", json={"user_id": "u1", "items": capsule_json}).json()
    assert first["indexed_count"] == 10 and first["added_count"] == 10 and first["revision"]

    again = client.post("/api/wardrobe/sync", json={"user_id": "u1", "items": capsule_json}).json()
    assert again["revision"] == first["revision"] and again["unchanged_count"] == 10

    smaller = client.post("/api/wardrobe/sync", json={"user_id": "u1", "items": capsule_json[:3]}).json()
    assert smaller["deleted_count"] == 7
    ids = [item["id"] for item in client.get("/api/wardrobe", params={"user_id": "u1"}).json()["items"]]
    assert sorted(ids) == ["item-1", "item-2", "item-3"]

    cleared = client.post("/api/wardrobe/sync", json={"user_id": "u1", "items": []}).json()
    assert cleared["indexed_count"] == 0
    assert len(client.get("/api/wardrobe", params={"user_id": "demo"}).json()["items"]) == 10


def test_base_capsule_endpoint(client):
    items = client.get("/api/wardrobe/base-capsule").json()
    assert [item["id"] for item in items] == [f"item-{i}" for i in range(1, 51)]


# --- админка ----------------------------------------------------------------------------


def test_admin_settings_are_read_only_without_token(client):
    body = client.get("/api/admin/settings").json()
    assert body["editable"] is False
    assert body["settings"]["mode"] == "hybrid" and body["settings"]["alpha"] == 0.65
    assert client.put("/api/admin/settings", json={"alpha": 0.5}).status_code == 403


def test_admin_settings_update_changes_generation(make_client):
    llm = ScriptedLLM([_answer(["item-1", "item-4", "item-8"])])
    client = make_client(llm=llm, admin_token="s3cret")
    assert client.put("/api/admin/settings", json={"alpha": 0.5}).status_code == 401
    assert client.put("/api/admin/settings", json={"alpha": 0.5}, headers={"X-Admin-Token": "nope"}).status_code == 401

    response = client.put(
        "/api/admin/settings",
        json={"personaPrompt": "Ты — стилист-минималист, отвечай предельно кратко.", "temperature": 0.2, "mode": "multimodal"},
        headers={"X-Admin-Token": "s3cret"},
    )
    assert response.status_code == 200
    saved = response.json()["settings"]
    assert saved["temperature"] == 0.2 and saved["mode"] == "multimodal" and saved["alpha"] == 0.65

    _recommend(client, query="образ в офис")
    system = llm.calls[0][0]["content"]
    assert system.startswith("Ты — стилист-минималист") and "ФОРМАТ ОТВЕТА" in system

    bad = client.put("/api/admin/settings", json={"alpha": 7}, headers={"X-Admin-Token": "s3cret"})
    assert bad.status_code == 422


# --- гонка: гардероб изменился, пока LLM думала ---------------------------------------------


class _WardrobeChangingLLM(ScriptedLLM):
    """Во время «генерации» пользователь успевает удалить вещь из гардероба."""

    def __init__(self, answers, on_call):
        super().__init__(answers)
        self._on_call = on_call

    def _next(self, messages):
        self._on_call()
        return super()._next(messages)


def test_stale_wardrobe_is_rejected_instead_of_returning_outdated_outfit(make_client, capsule):
    holder = {}
    llm = _WardrobeChangingLLM(
        [_answer(["item-1", "item-4", "item-8"])] * 2,
        on_call=lambda: holder["client"].app.state.service._engine.sync("demo", capsule[:9]),
    )
    client = holder["client"] = make_client(llm=llm)
    response = client.post("/api/recommend-outfit", json={"query": "образ в офис"})
    assert response.status_code == 503 and "изменился" in response.json()["detail"]

    events = _events(client, query="образ в офис")
    # снимок уже новый, поэтому второй запрос проходит: ревизия совпадает с актуальной
    assert events[-1][0] == "result"


def test_stream_reports_stale_wardrobe_as_error_event(make_client, capsule):
    holder = {"n": 0}

    def shrink():
        holder["n"] += 1
        holder["client"].app.state.service._engine.sync("demo", capsule[: 10 - holder["n"]])

    llm = _WardrobeChangingLLM([_answer(["item-1", "item-4", "item-8"])], on_call=shrink)
    client = holder["client"] = make_client(llm=llm)
    events = _events(client, query="образ в офис")
    assert events[-1][0] == "error" and "изменился" in events[-1][1]["message"]
