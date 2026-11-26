"""Точечная правка последнего образа, вопрос о нём и новый вопрос после старого диалога.

Сценарии — из таблицы «Что должен уметь стилист» и критериев приёмки задачи. Встроенный
движок и сценарная LLM: сеть и веса не нужны. То же самое на настоящем поиске — в
`test_wardrobe_rag_integration.py`.
"""
import json

import pytest

from app.services.llm.base import LLMError
from app.storage.app_store import load_base_capsule

from tests.conftest import ScriptedLLM

OFFICE = ["item-1", "item-4", "item-42"]  # рубашка, брюки палаццо, лодочки на каблуке
OFFICE_REQUEST = "Подбери образ в офис."
#            верх       низ       каблук     плоская    каблук     кеды      дождевик   жакет      джинсовка  сумка     платок
WARDROBE = ["item-1", "item-4", "item-42", "item-36", "item-35", "item-7", "item-33", "item-28", "item-29", "item-9", "item-10"]


@pytest.fixture(scope="module")
def capsule50():
    return {item.id: item.model_dump(by_alias=True, mode="json") for item in load_base_capsule()}


@pytest.fixture
def wardrobe(capsule50):
    return [capsule50[item_id] for item_id in WARDROBE]


def _history(item_ids, request=OFFICE_REQUEST, *extra):
    return [
        {"sender": "user", "text": request},
        {"sender": "assistant", "text": "В образ вошли: …", "hasOutfit": True, "itemIds": item_ids},
        *extra,
    ]


def _pick(item_id) -> str:
    return json.dumps({"outfit": {"item_ids": [item_id]}})


def _ask(client, query, wardrobe, history, **payload):
    response = client.post("/api/recommend-outfit", json={
        "query": query, "wardrobe": wardrobe, "user_id": "u-edit", "history": history, **payload,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _ids(result) -> list[str]:
    return [item["id"] for item in result["suggestedOutfit"]["items"]]


# --- добавить ---------------------------------------------------------------------------------


def test_add_jacket_keeps_the_three_original_ids(make_client, wardrobe):
    llm = ScriptedLLM([_pick("item-29")])
    result = _ask(make_client(llm=llm), "А можешь добавить какую-нибудь куртку, если похолодает?",
                  wardrobe, _history(OFFICE))
    ids = _ids(result)
    assert set(OFFICE) < set(ids) and len(ids) == 4, "три исходные вещи на месте, добавлена одна"
    assert result["edit"] == {
        "operation": "add", "slot": "outerwear", "baseItemIds": OFFICE,
        "keptItemIds": OFFICE, "addedItemIds": ["item-29"], "removedItemIds": [],
    }
    assert result["referencedItemIds"] == ids and result["source"] == "llm"


def test_slot_prompt_offers_only_candidates_and_no_chat_history(make_client, wardrobe):
    llm = ScriptedLLM([_pick("item-29")])
    _ask(make_client(llm=llm), "Добавь куртку", wardrobe,
         [{"sender": "user", "text": "секретная старая реплика"}, {"sender": "assistant", "text": "ответ"},
          *_history(OFFICE)])
    messages = llm.calls[0]
    assert [m["role"] for m in messages] == ["system", "user"]
    prompt = messages[1]["content"]
    assert "ПРАВКА ГОТОВОГО ОБРАЗА" in messages[0]["content"] and "секретная" not in prompt
    assert "Остаются в образе" in prompt and "Белая хлопковая рубашка оверсайз" in prompt
    for item_id in OFFICE:
        assert f'"{item_id}"' not in prompt.split("Кандидаты")[1], "вещи образа не предлагаются как кандидаты"


def test_invalid_llm_pick_is_repaired_then_falls_back(make_client, wardrobe):
    llm = ScriptedLLM([_pick("item-999"), _pick("item-29")])
    result = _ask(make_client(llm=llm), "Добавь куртку", wardrobe, _history(OFFICE))
    assert result["edit"]["addedItemIds"] == ["item-29"] and result["meta"]["llmAttempts"] == 2
    assert "item-999" in llm.calls[1][-1]["content"] or "допустимых" in llm.calls[1][-1]["content"]
    assert "item-999" not in json.dumps(result, ensure_ascii=False)

    for answers in (["мусор", "{}"], [LLMError("ollama is down")]):
        result = _ask(make_client(llm=ScriptedLLM(answers)), "Добавь куртку", wardrobe, _history(OFFICE))
        assert result["source"] == "fallback" and set(OFFICE) < set(_ids(result))
        assert result["edit"]["keptItemIds"] == OFFICE and len(result["edit"]["addedItemIds"]) == 1


def test_add_to_a_filled_slot_becomes_an_explained_replacement(make_client, wardrobe):
    base = [*OFFICE, "item-28"]  # жакет уже есть
    llm = ScriptedLLM([_pick("item-29")])
    result = _ask(make_client(llm=llm), "Добавь куртку", wardrobe, _history(base))
    assert result["edit"]["operation"] == "replace" and result["edit"]["removedItemIds"] == ["item-28"]
    assert result["edit"]["addedItemIds"] == ["item-29"]
    assert result["edit"]["keptItemIds"] == OFFICE


# --- заменить ---------------------------------------------------------------------------------


def test_replace_shoes_changes_exactly_one_id(make_client, wardrobe):
    llm = ScriptedLLM([])  # единственная пара «без каблука» — выбирать нечего, модель не нужна
    result = _ask(make_client(llm=llm), "Замени туфли на что-нибудь без каблука, остальное оставь",
                  wardrobe, _history(OFFICE))
    ids = _ids(result)
    assert set(ids) ^ set(OFFICE) == {"item-42", "item-36"}, "изменился ровно один ID"
    assert result["edit"]["keptItemIds"] == ["item-1", "item-4"]
    assert (result["edit"]["removedItemIds"], result["edit"]["addedItemIds"]) == (["item-42"], ["item-36"])
    assert result["source"] == "rules" and llm.calls == []
    assert all(item["title"] in result["text"] for item in wardrobe if item["id"] in {"item-42", "item-36"})
    assert "Остальные вещи оставила" in result["text"]


def test_office_edit_does_not_offer_beach_sandals_as_flat_shoes(make_client, capsule50):
    llm = ScriptedLLM([])
    result = _ask(make_client(llm=llm), "Замени туфли на что-нибудь без каблука, остальное оставь",
                  list(capsule50.values()), _history(OFFICE))
    # В полной капсуле «плоская подошва» есть у кед и у пляжных сандалий; в офис годятся только кеды.
    assert result["edit"]["addedItemIds"] == ["item-36"] and result["source"] == "rules"


def test_frost_edit_does_not_keep_unsuitable_shoes_in_a_new_card(make_client, wardrobe):
    result = _ask(make_client(llm=ScriptedLLM([])), "Без сумки, пожалуйста", wardrobe,
                  _history([*OFFICE, "item-9"], "Подбери образ на -30"))
    assert "suggestedOutfit" not in result and "shoes" in result["missingSlots"]


def test_replacement_never_offers_the_same_pair(make_client, wardrobe):
    llm = ScriptedLLM([_pick("item-42"), _pick("item-42")])  # модель упорно возвращает прежние туфли
    result = _ask(make_client(llm=llm), "Замени туфли", wardrobe, _history(OFFICE))
    assert "item-42" not in _ids(result) and result["source"] == "fallback"
    assert '"item-42"' not in llm.calls[0][1]["content"].split("Кандидаты")[1]


def test_no_suitable_replacement_means_no_new_card(make_client, capsule50):
    wardrobe = [capsule50[i] for i in WARDROBE if i != "item-36"]  # обуви с плоской подошвой нет
    llm = ScriptedLLM([])
    result = _ask(make_client(llm=llm), "Замени туфли на что-нибудь без каблука, остальное оставь",
                  wardrobe, _history(OFFICE))
    assert "suggestedOutfit" not in result and "edit" not in result and result["referencedItemIds"] == []
    assert result["source"] == "none" and llm.calls == []
    assert "без каблука" in result["text"] and "Прежний образ оставляю без изменений" in result["text"]


def test_replace_in_empty_slot_adds_with_explanation(make_client, wardrobe):
    result = _ask(make_client(llm=ScriptedLLM([_pick("item-29")])), "Замени куртку", wardrobe, _history(OFFICE))
    assert result["edit"]["operation"] == "add" and result["edit"]["keptItemIds"] == OFFICE


def test_ambiguous_request_gets_one_short_question(make_client, wardrobe):
    llm = ScriptedLLM([])
    result = _ask(make_client(llm=llm), "Замени вот это", wardrobe, _history(OFFICE))
    assert "suggestedOutfit" not in result and llm.calls == [], "сервер не угадывает и не зовёт модель"
    assert result["text"].count("?") == 1 and result["text"].startswith("Уточните, какую вещь заменить")
    assert "Черные лодочки на устойчивом каблуке" in result["text"]


def test_two_accessories_need_a_name_or_a_question(make_client, wardrobe):
    base = [*OFFICE, "item-9", "item-10"]
    result = _ask(make_client(llm=ScriptedLLM([])), "Замени аксессуар", wardrobe, _history(base))
    assert "suggestedOutfit" not in result and "Какую заменить?" in result["text"]


# --- убрать -----------------------------------------------------------------------------------


def test_without_bag_removes_only_the_bag(make_client, wardrobe):
    base = [*OFFICE, "item-9", "item-10"]
    llm = ScriptedLLM([])
    result = _ask(make_client(llm=llm), "Без сумки, пожалуйста", wardrobe, _history(base))
    assert set(_ids(result)) == {*OFFICE, "item-10"}, "платок остался, убрана только сумка"
    assert result["edit"]["operation"] == "remove" and result["edit"]["removedItemIds"] == ["item-9"]
    assert result["source"] == "rules" and llm.calls == []


def test_removing_the_only_shoes_asks_instead_of_showing_incomplete_outfit(make_client, wardrobe):
    result = _ask(make_client(llm=ScriptedLLM([])), "Убери обувь", wardrobe, _history(OFFICE))
    assert "suggestedOutfit" not in result and result["missingSlots"] == ["shoes"]
    assert result["text"].endswith("Подобрать замену из вашего гардероба?")


def test_removing_absent_category_changes_nothing(make_client, wardrobe):
    result = _ask(make_client(llm=ScriptedLLM([])), "Без сумки, пожалуйста", wardrobe, _history(OFFICE))
    assert "suggestedOutfit" not in result and "убирать нечего" in result["text"]


# --- вопрос об образе ---------------------------------------------------------------------------


def test_comfort_question_uses_the_shoes_from_the_last_card_without_editing(make_client, wardrobe):
    llm = ScriptedLLM([])
    result = _ask(make_client(llm=llm), "Будет ли мне удобно в этом образе?", wardrobe, _history(OFFICE))
    assert "suggestedOutfit" not in result and "edit" not in result
    text = result["text"]
    assert "Черные лодочки на устойчивом каблуке" in text and "натирала" in text
    assert "Кеды" not in text and "Неизвестно" not in text and "Чего я не знаю" not in text
    assert llm.calls == []


def test_comfort_question_uses_documented_weather_limits(make_client, capsule50):
    wardrobe = [capsule50[i] for i in ("item-18", "item-27", "item-41")]  # ботинки: до +8°C
    history = _history(["item-18", "item-27", "item-41"], "Подбери образ на прогулку, +25°C")
    result = _ask(make_client(), "Не жарко будет в этом?", wardrobe, history)  # mock-провайдер
    assert "suggestedOutfit" not in result
    assert "Шоколадные утепленные ботинки на шнуровке" in result["text"]
    assert "+25 °C" in result["text"] and "+8 °C" in result["text"]
    assert "?" not in result["text"], "температура известна из запроса образа"


def test_heat_question_without_forecast_asks_for_temperature(make_client, capsule50):
    ids = ["item-18", "item-27", "item-41"]
    result = _ask(make_client(), "Не жарко будет в этом?",
                  [capsule50[i] for i in ids], _history(ids, "Подбери образ на прогулку"))
    text = result["text"]
    assert text.count("?") == 1 and "температура" in text
    assert "не выбирала" not in text and "зимнего сезона" not in text


# --- удалённая вещь, образ без карточки ---------------------------------------------------------


def test_deleted_item_is_explained_instead_of_silent_change(make_client, capsule50):
    wardrobe = [capsule50[i] for i in WARDROBE if i != "item-4"]  # брюки удалили из гардероба
    llm = ScriptedLLM([])
    result = _ask(make_client(llm=llm), "Добавь куртку", wardrobe, _history(OFFICE))
    assert "suggestedOutfit" not in result and llm.calls == []
    assert "уже нет в вашем гардеробе" in result["text"] and "собрать образ заново" in result["text"]
    assert any("item-4" in warning for warning in result["warnings"])


def test_edit_without_any_card_explains_what_to_do(make_client, wardrobe):
    llm = ScriptedLLM([])
    result = _ask(make_client(llm=llm), "Замени туфли на кеды", wardrobe, [])
    assert "suggestedOutfit" not in result and "сначала попросите собрать образ" in result["text"]
    assert llm.calls == []


def test_old_client_without_item_ids_keeps_previous_behaviour(make_client, wardrobe):
    history = [{"sender": "user", "text": OFFICE_REQUEST},
               {"sender": "assistant", "text": "Рубашка, брюки и лодочки.", "hasOutfit": True}]
    llm = ScriptedLLM([json.dumps({"outfit": {"item_ids": ["item-1", "item-4", "item-36", "item-33"]}})])
    result = _ask(make_client(llm=llm), "Замени туфли", wardrobe, history)
    assert result["suggestedOutfit"] and "edit" not in result  # новый подбор, как до появления правки по ID


# --- новый вопрос после старого диалога -----------------------------------------------------------

BEACH = ["item-18", "item-27", "item-39"]
BEACH_REQUEST = "Подбери образ на пляж: +30°C, сухая погода."


def test_birthday_question_after_beach_dialogue_does_not_inherit_the_beach(make_client, capsule50):
    llm = ScriptedLLM(['{"text": "Чёрные ботинки хороши с тёмными брюками.", "outfit": null}'])
    result = _ask(make_client(llm=llm), "С чем носить чёрные ботинки на день рождения?",
                  list(capsule50.values()), _history(BEACH, BEACH_REQUEST))
    assert "suggestedOutfit" not in result and result["source"] == "llm"
    sent = json.dumps(llm.calls[0], ensure_ascii=False).lower()
    assert "пляж" not in sent and "сандал" not in sent and "+30" not in sent
    assert [m["role"] for m in llm.calls[0]] == ["system", "user"], "самостоятельный вопрос уходит без истории"
    assert "retriever" not in result["meta"]


def test_birthday_outfit_from_wardrobe_after_beach_is_a_new_request(make_client, capsule50):
    result = _ask(make_client(), "С чем носить чёрные ботинки на день рождения из моего гардероба?",
                  list(capsule50.values()), _history(BEACH, BEACH_REQUEST), debug=True)
    assert result["suggestedOutfit"] and "edit" not in result
    assert result["meta"]["occasion"] == "Вечерний выход"
    assert result["retrieval"]["context"]["occasion"] != "beach"
    assert result["retrieval"]["context"]["temperature_c"] is None, "+30°C из пляжного запроса не унаследованы"
    assert not set(_ids(result)) & {"item-39", "item-47", "item-48"}, "пляжные сандалии, шляпа и сумка не при чём"


def test_follow_up_that_names_a_new_occasion_drops_the_old_one(make_client, capsule50):
    result = _ask(make_client(), "А на день рождения?", list(capsule50.values()),
                  _history(BEACH, BEACH_REQUEST), debug=True)
    assert result["meta"]["occasion"] == "Вечерний выход"
    assert result["retrieval"]["context"]["occasion"] != "beach"


def test_follow_up_question_keeps_dialogue_history(make_client, wardrobe):
    llm = ScriptedLLM(['{"text": "Да, подойдёт.", "outfit": null}'])
    history = [{"sender": "user", "text": "С чем носить широкие брюки?"},
               {"sender": "assistant", "text": "С приталенным верхом."}]
    _ask(make_client(llm=llm), "А с кроссовками?", wardrobe, history)
    assert [m["role"] for m in llm.calls[0]] == ["system", "user", "assistant", "user"]


# --- «потеплее»: новый вариант и метаданные изменений -----------------------------------------------


def test_warmer_preserves_the_edit_metadata_and_occasion(make_client, wardrobe):
    llm = ScriptedLLM([json.dumps({"outfit": {"item_ids": ["item-1", "item-4", "item-35", "item-28"]}})])
    result = _ask(make_client(llm=llm), "А можно потеплее?", wardrobe, _history(OFFICE))
    assert set(_ids(result)) == {"item-1", "item-4", "item-35", "item-28"}
    assert result["edit"]["addedItemIds"] == ["item-28", "item-35"]
    assert result["edit"]["removedItemIds"] == ["item-42"]
    assert result["edit"]["operation"] == "restyle" and result["edit"]["keptItemIds"] == ["item-1", "item-4"]
    assert result["meta"]["occasion"] == "Деловой выход", "повод прошлого образа сохранён"


# --- поправка о холоде и возврат карточки -------------------------------------------------------


def test_cold_bottom_edit_filters_shorts_and_preserves_the_other_items(make_client, capsule50):
    jacket = dict(capsule50["item-2"], title="Куртка утепленная")
    original = ["item-1", "item-23", "item-41", "item-2"]
    wardrobe = [jacket, *(capsule50[i] for i in ("item-1", "item-23", "item-41", "item-25", "item-22"))]
    root = "Подбери образ из моего гардероба с вещью «Куртка утепленная»."
    llm = ScriptedLLM([])
    client = make_client(llm=llm)

    replacement = _ask(client, "хочу другой низ", wardrobe, _history(original, root))
    assert set(_ids(replacement)) == set(original) - {"item-23"} | {"item-22"}
    assert capsule50["item-22"]["title"] in replacement["text"]

    # Уже показанная неудачная карточка остаётся в старых диалогах.
    with_shorts = ["item-1", "item-25", "item-41", "item-2"]
    history = _history(original, root, *_history(with_shorts, "хочу другой низ"))
    corrected = _ask(client, "ты дурак, зачем шорты - холодно", wardrobe, history)
    assert corrected["edit"]["removedItemIds"] == ["item-25"]
    assert set(corrected["edit"]["keptItemIds"]) == {"item-1", "item-41", "item-2"}
    assert "item-25" not in _ids(corrected) and capsule50["item-25"]["title"] in corrected["text"]

    history += _history(_ids(corrected), "ты дурак, зачем шорты - холодно")
    restored = _ask(client, "верни предыдущий образ", wardrobe, history, debug=True)
    assert _ids(restored) == with_shorts and restored["source"] == "rules"
    assert "retrieval" not in restored and restored["meta"]["llmAttempts"] == 0
    assert "погоде" in restored["text"]


def test_cold_feedback_without_long_bottom_does_not_publish_another_card(make_client, capsule50):
    base = ["item-1", "item-25", "item-41"]
    wardrobe = [capsule50[i] for i in [*base, "item-27", "item-21"]]
    result = _ask(make_client(llm=ScriptedLLM([])), "В шортах холодно", wardrobe, _history(base))
    assert "suggestedOutfit" not in result and "не нашла" in result["text"]


def test_restore_does_not_invent_a_card_when_previous_is_missing(make_client, wardrobe):
    llm = ScriptedLLM([])
    client = make_client(llm=llm)
    only_one = _ask(client, "Верни предыдущий образ", wardrobe, _history(OFFICE))
    assert "suggestedOutfit" not in only_one and "ещё нет" in only_one["text"]
    deleted = _ask(client, "Верни предыдущий образ", wardrobe,
                   _history(["item-1", "deleted", "item-42"], OFFICE_REQUEST, *_history(OFFICE, "Замени низ")))
    assert "suggestedOutfit" not in deleted and "нет части" in deleted["text"]
    assert llm.calls == []


# --- поток и гонка -------------------------------------------------------------------------------


def test_edit_over_sse_returns_text_and_card(make_client, wardrobe):
    client = make_client(llm=ScriptedLLM([_pick("item-29")]))
    response = client.post("/api/recommend-outfit/stream", json={
        "query": "Добавь куртку", "wardrobe": wardrobe, "user_id": "u-edit", "history": _history(OFFICE),
    })
    events = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    assert [name for name, _ in events][-2:] == ["delta", "result"]
    result = events[-1][1]
    assert events[-2][1]["text"] == result["text"] and result["edit"]["addedItemIds"] == ["item-29"]


def test_wardrobe_changed_during_edit_is_rejected(make_client, wardrobe, capsule50):
    holder = {}

    class ChangingLLM(ScriptedLLM):
        def _next(self, messages):
            from app.schemas import WardrobeItem
            smaller = [WardrobeItem.model_validate(item) for item in wardrobe if item["id"] != "item-10"]
            holder["client"].app.state.service._engine.sync("u-edit", smaller)
            return super()._next(messages)

    client = holder["client"] = make_client(llm=ChangingLLM([_pick("item-29")]))
    response = client.post("/api/recommend-outfit", json={
        "query": "Добавь куртку", "wardrobe": wardrobe, "user_id": "u-edit", "history": _history(OFFICE),
    })
    assert response.status_code == 503 and "изменился" in response.json()["detail"]
