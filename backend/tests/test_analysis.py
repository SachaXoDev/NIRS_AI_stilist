import pytest

from app.schemas import RecommendContext
from app.services.analysis import analyze_query


@pytest.mark.parametrize(
    "query, occasion",
    [
        ("Подбери образ для деловой встречи", "business"),
        ("Что надеть в офис на презентацию?", "business"),
        ("Ужин в ресторане", "evening"),
        ("Собери образ для пробежки в тёплый день", "running"),
        ("Что надеть, чтобы побегать в парке?", "running"),
        ("Что надеть на тренировку по йоге?", "sport"),
        ("Подбери образ в офис, не для пробежки", "business"),
        ("Иду на свидание вечером", "evening"),
        ("Собираюсь в командировку, перелет 4 часа", "travel"),
        ("Прогулка по городу с друзьями", "casual"),
        ("Просто собери что-нибудь", "casual"),
    ],
)
def test_occasion_detection(query, occasion):
    assert analyze_query(query).occasion == occasion


@pytest.mark.parametrize(
    "query, temperature",
    [
        ("Москва сегодня: +6°C, пасмурно", 6),
        ("Дождь и +12°C", 12),
        ("на улице -5, что надеть", -5),
        ("сегодня −3 и снег", -3),
        ("обещают 25 градусов", 25),
        ("за окном 18°", 18),
        ("хочу образ из 5-6 вещей", None),
        ("лук в стиле 12 STOREEZ", None),
        ("поездка на 2-3 дня", None),
    ],
)
def test_temperature_detection(query, temperature):
    assert analyze_query(query).temperature_c == temperature


def test_cold_rain_flags():
    analysis = analyze_query("Дождь и +12°C")
    assert "rain" in analysis.weather and "cold" in analysis.weather
    assert analysis.is_cold and not analysis.is_hot


def test_heat_wins_over_cold_keywords():
    analysis = analyze_query("осень, но аномальные +26")
    assert analysis.is_hot and "cold" not in analysis.weather


def test_stems_match_only_word_starts():
    # «перелетом» содержит «лето», но это не про жару
    assert "heat" not in analyze_query("образ перед перелетом").weather


def test_explicit_context_beats_query_heuristics():
    context = RecommendContext(occasion="Деловая встреча", weather="дождь, +9°C", vibe="минимализм")
    analysis = analyze_query("хочу что-нибудь на вечер", context)
    assert analysis.occasion == "business"
    assert analysis.occasion_label == "Деловая встреча"
    assert analysis.temperature_c == 9 and "rain" in analysis.weather
    assert analysis.vibe == "минимализм"


def test_anchor_item_detected_by_title(capsule):
    query = (
        "Подбери законченный образ для ужина с вещью «Шелковый шейный платок с "
        "геометрическим принтом». С чем из моей капсулы она комбинируется?"
    )
    assert analyze_query(query, None, capsule).anchor_item_ids == ["item-10"]
