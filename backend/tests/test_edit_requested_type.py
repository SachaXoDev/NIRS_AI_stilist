"""Правка образа на встроенном поиске: названный тип вещи, повод после нескольких правок,
оценка возвращённого образа."""
from __future__ import annotations

import pytest

from app.schemas import WardrobeItem
from app.services.analysis import analyze_query
from app.services.followup import classify_followup
from app.services.garment_type import is_type, requested_types
from app.storage.app_store import load_base_capsule

OFFICE = ["item-2", "item-12", "item-20", "item-35"]  # блейзер, блуза, костюмные брюки, дерби
OFFICE_REQUEST = "Подбери образ в офис."


@pytest.fixture(scope="module")
def capsule():
    return load_base_capsule()


@pytest.fixture(scope="module")
def wardrobe(capsule):
    return [item.model_dump(by_alias=True, mode="json") for item in capsule]


@pytest.fixture
def titles(capsule):
    return {item.id: item.title for item in capsule}


def _card(item_ids):
    return {"sender": "assistant", "text": "В образ вошли: …", "hasOutfit": True, "itemIds": item_ids}


def _ask(client, query, wardrobe, history):
    response = client.post("/api/recommend-outfit", json={
        "query": query, "wardrobe": wardrobe, "user_id": "u-type", "history": history,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _ids(result) -> list[str]:
    return [item["id"] for item in result["suggestedOutfit"]["items"]]


def _office():
    return [{"sender": "user", "text": OFFICE_REQUEST}, _card(OFFICE)]


# --- какое слово называет нужную вещь -------------------------------------------------------


@pytest.mark.parametrize("query, slot, expected", [
    ("Добавь сумку", "accessories", ["сумку"]),
    ("Добавь сумку на длинном ремне", "accessories", ["сумку"]),
    ("Замени брюки на юбку", "bottoms", ["юбку"]),
    ("Замени брюки на юбку или джинсы", "bottoms", ["юбку", "джинсы"]),
    ("Поменяй обувь на красные сапоги", "shoes", ["сапоги"]),
    ("Замени блейзер на пиджак", "outerwear", ["пиджак"]),
    ("Замени обувь", "shoes", []),                              # тип не назван
    ("Добавь аксессуар", "accessories", []),                    # категория, а не вещь
    ("Добавь верхнюю одежду", "outerwear", []),
    ("Замени туфли на что-нибудь без каблука", "shoes", []),    # признак, а не тип
    ("Замени обувь на более удобную", "shoes", []),
    ("Не хочу кеды", "shoes", []),                              # отказ от вещи нужного типа не задаёт
    ("Замени туфли и сумку", "shoes", []),                      # правка двух слотов сразу
    ("Убери платок", "accessories", []),
    ("Подбери образ в офис", "shoes", []),                      # не правка
])
def test_requested_types_reads_the_garment_the_user_named(query, slot, expected):
    assert requested_types(query, slot) == expected


def _item(title: str, *tags: str, category: str = "bottoms") -> WardrobeItem:
    return WardrobeItem(id="x", title=title, category=category, tags=list(tags))


@pytest.mark.parametrize("title, tags, word, expected", [
    ("Графитовая юбка-карандаш", ["юбки"], "юбку", True),
    ("Прямые темно-синие джинсы", ["деним"], "юбку", False),
    ("Прямые темно-синие джинсы", ["деним"], "брюки", True),        # общее название включает частное
    ("Темно-синие костюмные брюки", ["офис"], "джинсы", False),     # но не наоборот
    ("Черный структурированный блейзер", [], "пиджак", True),       # синонимы
    ("Кашемировый джемпер", [], "свитером", True),
    ("Шелковый шейный платок", [], "платком", True),                # беглая гласная
    ("Летнее платье", [], "платок", False),                         # короткие основы не путаем
    ("Структурированная кожаная сумка-тоут", [], "сумку", True),
    ("Темно-синяя спортивная бейсболка", ["головные уборы"], "сумку", False),
    ("Черные лодочки на устойчивом каблуке", ["туфли и лоферы"], "туфли", True),
])
def test_is_type_matches_title_and_tags(title, tags, word, expected):
    assert is_type(_item(title, *tags), word) is expected


# --- правка образа --------------------------------------------------------------------------


def test_add_bag_adds_a_bag_not_another_accessory(client, wardrobe, titles):
    result = _ask(client, "Добавь сумку", wardrobe, _office())
    added = result["edit"]["addedItemIds"]
    assert len(added) == 1 and "сумка" in titles[added[0]].lower()
    assert result["edit"]["keptItemIds"] == OFFICE


def test_replace_trousers_with_skirt_picks_a_skirt(client, wardrobe, titles):
    result = _ask(client, "Замени брюки на юбку", wardrobe, _office())
    assert result["edit"]["removedItemIds"] == ["item-20"]
    assert "юбка" in titles[result["edit"]["addedItemIds"][0]].lower()


def test_named_garment_missing_from_wardrobe_leaves_the_outfit_alone(client, wardrobe):
    result = _ask(client, "Добавь рюкзак", wardrobe, _office())
    assert result.get("suggestedOutfit") is None and result.get("edit") is None
    assert "без изменений" in result["text"]


def test_named_garment_is_not_replaced_by_a_lookalike_when_all_are_excluded(client, wardrobe):
    without_skirts = [item for item in wardrobe if "юбка" not in item["title"].lower()]
    result = _ask(client, "Замени брюки на юбку", without_skirts, _office())
    assert result.get("suggestedOutfit") is None, "джинсы вместо юбки не подставляем"


def test_occasion_survives_several_edits(client, wardrobe, capsule):
    history = _office()
    first = _ask(client, "Замени обувь", wardrobe, history)
    history += [{"sender": "user", "text": "Замени обувь"}, _card(_ids(first))]
    second = _ask(client, "Добавь аксессуар", wardrobe, history)
    assert second["suggestedOutfit"]["occasion"] == "Деловой выход"
    sport_only = {item.id for item in capsule if item.style == ["sport"]}
    assert not sport_only & set(second["edit"]["addedItemIds"]), "вещь только для спорта в офисный образ не добавляется"


def test_office_shoe_swap_never_offers_running_shoes(client, wardrobe, titles):
    result = _ask(client, "Замени обувь на кеды", wardrobe, _office())
    chosen = titles[result["edit"]["addedItemIds"][0]].lower()
    assert "кеды" in chosen and "бегов" not in chosen


def test_restored_outfit_has_a_real_match_score(client, wardrobe):
    history = _office()
    edited = _ask(client, "Замени обувь", wardrobe, history)
    history += [{"sender": "user", "text": "Замени обувь"}, _card(_ids(edited))]
    restored = _ask(client, "Верни предыдущий образ", wardrobe, history)
    assert _ids(restored) == OFFICE
    assert restored["suggestedOutfit"]["matchScore"] > 0, "в сохранённых образах не должно быть «0%»"


@pytest.mark.parametrize("query", [
    "Что надеть на свадьбу подруги?", "Образ на выпускной", "Собери образ на корпоратив", "Иду на банкет",
])
def test_festive_occasions_are_not_treated_as_casual(query):
    assert analyze_query(query).occasion == "evening"


def test_builtin_search_treats_no_heel_as_a_requirement(client, wardrobe, titles):
    result = client.post("/api/recommend-outfit", json={
        "query": "Хочу что-нибудь без каблуков на свадьбу летом", "wardrobe": wardrobe, "user_id": "u-flat",
    }).json()
    shoes = [item for item in result["suggestedOutfit"]["items"] if item["category"] == "shoes"]
    assert shoes and all("каблук" not in titles[item["id"]].lower() for item in shoes)


@pytest.mark.parametrize("query, slot", [
    ("А обувь другую можно?", "shoes"), ("Сумку другую подбери", "accessories"), ("Давай брюки другие", "bottoms"),
])
def test_other_after_the_garment_is_a_replacement(query, slot):
    follow_up = classify_followup(query)
    assert follow_up is not None and (follow_up.kind, follow_up.slot) == ("replace", slot)


@pytest.mark.parametrize("query", ["Обувь другого цвета у меня есть?", "Другие варианты?", "Обувь удобная, спасибо"])
def test_other_without_a_replacement_request_is_not_an_edit(query):
    follow_up = classify_followup(query)
    assert follow_up is None or follow_up.kind != "replace"
