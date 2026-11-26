"""Точечная правка последнего образа, вопрос о нём и новый вопрос после старого диалога.

Сценарии проверяют HTTP-контракт без сети и весов; ключевые диалоги проходят
и на встроенном движке, и с настоящим индексом wardrobe_rag.
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


# --- правки в диалоге и доказуемое утепление -------------------------------------------------------

WALK = ["item-11", "item-23", "item-32", "item-41"]  # поплин, чиносы, парка, ботинки
WALK_REQUEST = "Подбери образ на прогулку с вещью «Хвойная утепленная парка с капюшоном»."


@pytest.fixture(params=["builtin", "rag_engine"])
def dialogue_client(request, make_client):
    engine = request.getfixturevalue("rag_engine") if request.param == "rag_engine" else None
    return make_client(engine=engine)


def _assert_card_change(result, base, *, removed, added):
    kept = set(base) - removed
    expected = kept | added
    ids = _ids(result)
    assert set(ids) == expected and len(ids) == len(expected)
    assert result["referencedItemIds"] == ids
    edit = result["edit"]
    assert set(edit["baseItemIds"]) == set(base)
    assert set(edit["keptItemIds"]) == kept
    assert set(edit["removedItemIds"]) == removed
    assert set(edit["addedItemIds"]) == added


def _assert_text_only(result):
    assert result["text"].strip()
    assert "suggestedOutfit" not in result and "edit" not in result


def test_rejecting_tee_replaces_only_tee_and_excludes_other_tees(dialogue_client, capsule50):
    base = ["item-13", *WALK[1:]]
    tee = capsule50["item-13"]
    other_tee = dict(tee, id="other-tee", title="Синяя футболка в полоску")
    wardrobe = [*(capsule50[i] for i in [*base, "item-11"]), other_tee]

    result = _ask(dialogue_client, "не хочу футболку", wardrobe, _history(base, WALK_REQUEST))

    _assert_card_change(result, base, removed={"item-13"}, added={"item-11"})

    tees_only = [capsule50[i] for i in base] + [other_tee]
    _assert_text_only(_ask(dialogue_client, "не хочу футболку", tees_only, _history(base, WALK_REQUEST)))

def test_followup_replacement_does_not_bring_back_a_rejected_tee(dialogue_client, capsule50):
    base = ["item-13", *WALK[1:]]
    wardrobe = [capsule50[i] for i in [*base, "item-11", "item-12", "item-22"]]
    history = _history(base, WALK_REQUEST, *_history(WALK, "не хочу футболку"))

    result = _ask(dialogue_client, "замени верх и низ", wardrobe, history)

    _assert_card_change(result, WALK, removed={"item-11", "item-23"}, added={"item-12", "item-22"})



def test_compatibility_question_discusses_actual_shirt_and_chinos_without_a_card(dialogue_client, capsule50):
    wardrobe = [capsule50[i] for i in [*WALK, "item-1", "item-22"]]
    result = _ask(dialogue_client, "думаешь рубашка со штанами сочетается??", wardrobe,
                  _history(WALK, WALK_REQUEST))

    _assert_text_only(result)
    for item_id in WALK[:2]:
        assert capsule50[item_id]["title"].casefold() in result["text"].casefold()
    for item_id in ("item-1", "item-22"):
        assert capsule50[item_id]["title"].casefold() not in result["text"].casefold()


def _clarify_replacement(client, wardrobe, history):
    query = "я не думаю, поменяй"
    result = _ask(client, query, wardrobe, history)
    _assert_text_only(result)
    assert "какую вещь заменить" in result["text"].casefold() and result["text"].count("?") == 1
    return [*history, {"sender": "user", "text": query}, {"sender": "assistant", "text": result["text"]}]


@pytest.mark.parametrize("clarified", [False, True], ids=["explicit", "clarified"])
@pytest.mark.parametrize("missing", [False, True], ids=["complete", "no-bottom"])
def test_replace_top_and_bottom_is_atomic(dialogue_client, capsule50, clarified, missing):
    candidates = ["item-12"] if missing else ["item-12", "item-22"]
    wardrobe = [capsule50[i] for i in [*WALK, *candidates]]
    history = _history(WALK, WALK_REQUEST)
    query = "замени верх и низ"
    if clarified:
        history = _clarify_replacement(dialogue_client, wardrobe, history)
        query = "верх и низ"

    result = _ask(dialogue_client, query, wardrobe, history)

    if missing:
        _assert_text_only(result)
        assert result["referencedItemIds"] == []
    else:
        _assert_card_change(result, WALK, removed={"item-11", "item-23"}, added={"item-12", "item-22"})


def test_bare_slots_do_not_edit_without_immediate_clarification(dialogue_client, capsule50):
    wardrobe = [capsule50[i] for i in [*WALK, "item-12", "item-22"]]
    history = _history(WALK, WALK_REQUEST)
    _assert_text_only(_ask(dialogue_client, "верх и низ", wardrobe, history))

    clarified = _clarify_replacement(dialogue_client, wardrobe, history)
    # After another exchange, the old question no longer authorizes an edit.
    unrelated = "думаешь рубашка со штанами сочетается??"
    answer = _ask(dialogue_client, unrelated, wardrobe, clarified)
    _assert_text_only(answer)
    stale = [*clarified, {"sender": "user", "text": unrelated}, {"sender": "assistant", "text": answer["text"]}]
    _assert_text_only(_ask(dialogue_client, "верх и низ", wardrobe, stale))


def test_warmer_replaces_only_the_documented_stronger_layer(dialogue_client, capsule50):
    wardrobe = [capsule50[i] for i in [*WALK, "item-19", "item-21", "item-31"]]
    result = _ask(dialogue_client, "А можно потеплее?", wardrobe,
                  _history(WALK, f"{WALK_REQUEST} На улице +4°C."), anchor_item_id="item-32")

    _assert_card_change(result, WALK, removed={"item-11"}, added={"item-19"})
    assert capsule50["item-19"]["title"] in result["text"]


def test_warmer_with_no_retrievable_improvement_leaves_card_alone(dialogue_client, capsule50):
    # Меринос есть в гардеробе, но его диапазон не подходит для +4°C. Шерстяная юбка
    # не согреет лучше длинных брюк только потому, что у неё теплее материал.
    unavailable = dict(capsule50["item-19"], weather={"temperature_max": 0})
    wardrobe = [*(capsule50[i] for i in [*WALK, "item-21"]), unavailable]
    result = _ask(dialogue_client, "А можно потеплее?", wardrobe,
                  _history(WALK, f"{WALK_REQUEST} На улице +4°C."), anchor_item_id="item-32")

    _assert_text_only(result)
    assert "температур" not in result["text"].casefold() or "?" not in result["text"]


def test_warmer_asks_for_temperature_then_applies_the_same_edit(dialogue_client, capsule50):
    wardrobe = [capsule50[i] for i in [*WALK, "item-19", "item-21"]]
    history = _history(WALK, WALK_REQUEST)
    query = "А можно потеплее?"
    result = _ask(dialogue_client, query, wardrobe, history, anchor_item_id="item-32")
    _assert_text_only(result)
    assert "температур" in result["text"].casefold() and result["text"].count("?") == 1

    history += [{"sender": "user", "text": query}, {"sender": "assistant", "text": result["text"]}]
    warmed = _ask(dialogue_client, "+4°C", wardrobe, history, anchor_item_id="item-32")
    _assert_card_change(warmed, WALK, removed={"item-11"}, added={"item-19"})


def test_warmer_after_compatibility_question_keeps_the_latest_outfit(dialogue_client, capsule50):
    root = 'Подбери образ из моего гардероба с вещью «Куртка утепленная».'
    jacket = dict(capsule50["item-32"], title="Куртка утепленная")
    initial = ["item-13", "item-23", "item-32", "item-41"]
    wardrobe = [jacket, *(capsule50[i] for i in ["item-13", "item-19", "item-23", "item-41", "item-21", "item-28"])]
    history = _history(initial, root)

    rejection = "не хочу футболку"
    changed = _ask(dialogue_client, rejection, wardrobe, history)
    _assert_card_change(changed, initial, removed={"item-13"}, added={"item-19"})
    history += [
        {"sender": "user", "text": rejection},
        {"sender": "assistant", "text": changed["text"], "hasOutfit": True, "itemIds": _ids(changed)},
    ]
    compatibility = "водолазка со штанами сочетается?"
    answer = _ask(dialogue_client, compatibility, wardrobe, history)
    _assert_text_only(answer)
    assert capsule50["item-19"]["title"] in answer["text"]
    assert capsule50["item-23"]["title"] in answer["text"]
    history += [{"sender": "user", "text": compatibility}, {"sender": "assistant", "text": answer["text"]}]

    query = "может потеплее образ?"
    clarification = _ask(dialogue_client, query, wardrobe, history)
    _assert_text_only(clarification)
    assert "температуру" in clarification["text"] and clarification["text"].count("?") == 1

    history += [{"sender": "user", "text": query}, {"sender": "assistant", "text": clarification["text"]}]
    warmed = _ask(dialogue_client, "+4°C", wardrobe, history)
    _assert_text_only(warmed)
    assert "состав не меняю" in warmed["text"].casefold()


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
