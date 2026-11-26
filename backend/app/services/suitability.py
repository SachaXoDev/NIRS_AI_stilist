"""Консервативные продуктовые правила; исследовательский поиск не меняется."""
from __future__ import annotations

import re

from app.schemas import WardrobeItem
from app.services.analysis import QueryAnalysis
from app.services.textutils import normalize

SEVERE_FROST_MAX_C = -15
FROST_CRITICAL_SLOTS = frozenset({"shoes", "outerwear"})
_SHORTS_RE = re.compile(r"\bшорт\w*\b")
_INSULATED_RE = re.compile(r"\b(?:утепл\w*|пуховик\w*|зимн\w*)\b")


def is_shorts(item: WardrobeItem) -> bool:
    return item.category == "bottoms" and any(
        _SHORTS_RE.search(normalize(label)) for label in (item.title, *item.tags)
    )


def is_insulated_outerwear_or_shoes(item: WardrobeItem) -> bool:
    return item.category in FROST_CRITICAL_SLOTS and any(
        _INSULATED_RE.search(normalize(label)) for label in (item.title, *item.tags)
    )


def is_severe_frost(temperature: int | float | None) -> bool:
    return temperature is not None and temperature <= SEVERE_FROST_MAX_C


def frost_gap_text(temperature: int | float, slots: set[str]) -> str:
    missing = []
    if "shoes" in slots:
        missing.append("зимних ботинок или сапог")
    if "outerwear" in slots:
        missing.append("тёплой верхней одежды")
    return f"Для {temperature:g} °C в гардеробе не хватает {' и '.join(missing)}, рассчитанных на такой мороз."


def unsuitable_reason(item: WardrobeItem, analysis: QueryAnalysis) -> str | None:
    facts = item.weather
    temperature = analysis.temperature_c
    if analysis.is_cold and is_shorts(item):
        return "шорты не подходят для холода на улице"
    if facts and temperature is not None:
        if facts.temperature_min is not None and temperature < facts.temperature_min:
            return "ниже указанного для вещи диапазона температур"
        if facts.temperature_max is not None and temperature > facts.temperature_max:
            return "выше указанного для вещи диапазона температур"
    if is_severe_frost(temperature) and item.category in FROST_CRITICAL_SLOTS:
        if facts is None or facts.temperature_min is None:
            return "нет подтверждения, что вещь рассчитана на такой мороз"
    if facts and item.category in {"shoes", "outerwear"}:
        if "rain" in analysis.weather and facts.waterproof is False:
            return "не подходит для дождя по данным вещи"
        if item.category == "shoes" and facts.open_shoes and (
            analysis.is_cold or "rain" in analysis.weather
        ):
            return "открытая обувь не подходит для холода или дождя"
    if item.category == "shoes" and analysis.is_cold and any(
        "лодочк" in normalize(label) for label in [item.title, *item.tags]
    ):
        return "лодочки не подходят для холода на улице"
    if analysis.is_hot and item.season == "autumn/winter" and item.category != "accessories":
        return "вещь зимнего сезона для жаркой погоды"

    if analysis.occasion == "beach":
        # Уместность для пляжа нельзя вывести из наличия обязательных слотов.
        # Используем явную разметку или название, но не embeddingSnippet: там могут
        # упоминаться другие вещи. Для пляжной обуви нужна открытая пара.
        labels = [normalize(value).strip() for value in [item.title, *item.tags, *item.style]]
        beach = any("пляж" in label or label == "beach" for label in labels)
        if item.category == "shoes":
            if facts and facts.open_shoes is False:
                return "закрытая обувь для пляжа"
            if not any(
                word.startswith(("сандал", "босонож", "сланц", "вьетнам", "шлепан"))
                for label in labels for word in label.split()
            ) and not (facts and facts.open_shoes and beach):
                return "нет признаков пляжной обуви"
        elif not beach:
            return "нет признаков пляжной вещи"
        if item.season == "autumn/winter":
            return "зимняя вещь для пляжа"
    return None
