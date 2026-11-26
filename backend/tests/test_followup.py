"""Разбор реплики после карточки: правка, вопрос об образе или обычный разговор."""
import pytest

from app.services.analysis import starts_new_topic
from app.services.followup import classify_followup, refers_to_dialogue


@pytest.mark.parametrize("query, kind, slot", [
    ("А можешь добавить какую-нибудь куртку, если похолодает?", "add", "outerwear"),
    ("Добавь верхнюю одежду", "add", "outerwear"),
    ("накинь что-нибудь, например жилет", "add", "outerwear"),
    ("добавь шарф", "add", "accessories"),
    ("Замени туфли на что-нибудь без каблука, остальное оставь", "replace", "shoes"),
    ("замени верх на что-то теплее", "replace", "tops"),
    ("поменяй брюки на юбку", "replace", "bottoms"),
    ("другую обувь, пожалуйста", "replace", "shoes"),
    ("замени сумку на шарф", "replace", "accessories"),
    ("Без сумки, пожалуйста", "remove", "accessories"),
    ("а без куртки?", "remove", "outerwear"),
    ("не надо шарф", "remove", "accessories"),
    ("убери обувь", "remove", "shoes"),
    ("сними блейзер", "remove", "outerwear"),
    ("Замени вот это", "ask_item", None),
    ("убери это", "ask_item", None),
    ("добавь что-нибудь яркое", "ask_item", None),
    ("Мне в этом будет комфортно?", "card_question", None),
    ("не замёрзну в этом?", "card_question", None),
    ("а это подойдёт для офиса?", "card_question", None),
    ("Не жарко будет?", "card_question", None),
])
def test_follow_ups_are_recognised(query, kind, slot):
    follow_up = classify_followup(query)
    assert follow_up is not None and (follow_up.kind, follow_up.slot) == (kind, slot)


@pytest.mark.parametrize("query", [
    "А можно потеплее?",                      # новый вариант целиком — отдельная ветка
    "другой образ",
    "есть другие варианты?",
    "а другие цвета подойдут к серому",
    "Не надо, спасибо",
    "Удобно, спасибо!",
    "Нормально",
    "Спасибо!",
    "а без каблука есть что-нибудь?",          # свойство обуви, а не просьба что-то убрать
    "плюс 10 завтра, это много?",
    "надо что-то удобное для прогулки в парке",
    "С чем носить чёрные ботинки на день рождения?",
    "Туфли на низком каблуке — это уместно на собеседовании в банке или лучше лоферы",
])
def test_ordinary_remarks_are_not_edits(query):
    assert classify_followup(query) is None


@pytest.mark.parametrize("query, expected", [
    ("Подбери образ в офис и добавь шарф", True),
    ("С чем носить чёрные ботинки на день рождения?", True),
    ("Что надеть вместо пальто?", True),
    ("Замени туфли на кеды из моего гардероба", False),
    ("Добавь куртку", False),
])
def test_explicit_new_request_wins_over_an_edit(query, expected):
    assert starts_new_topic(query) is expected


@pytest.mark.parametrize("query, expected", [
    ("С чем носить чёрные ботинки на день рождения?", False),
    ("Какие цвета сочетаются с бордовым в деловом гардеробе?", False),
    ("А с кроссовками?", True),
    ("Спасибо!", True),
    ("а это подойдёт для собеседования в банке или лучше что-то строже", True),
    ("Ты говорил про приталенный верх, поясни", True),
])
def test_only_self_contained_questions_drop_the_history(query, expected):
    assert refers_to_dialogue(query) is expected
