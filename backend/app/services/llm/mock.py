"""Mock-провайдер: оформляет шаблонами образ, собранный поисковым движком без LLM.

Нужен, чтобы бэкенд запускался и демонстрировался без ключей и сети, а тесты были
детерминированными. Формат ответа — тот же JSON, что требуется от настоящей модели,
поэтому весь остальной пайплайн (парсинг, валидация, стриминг) работает одинаково.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from app.rag.base import CORE_SLOTS
from app.schemas import CATEGORY_LABELS_RU, WardrobeItem
from app.services.llm.base import Messages
from app.services.prompts import PromptContext

_TITLES = {
    "business": "Smart-casual для офиса и деловых встреч",
    "evening": "Элегантный вечерний образ с акцентом",
    "travel": "Удобный образ в дорогу",
    "sport": "Собранный образ для активного дня",
    "casual": "Комфортный городской минимализм",
}
_COLD_TITLE = "Многослойный образ для прохладной погоды"
_HOT_TITLE = "Лёгкий образ для тёплого дня"

_DESCRIPTIONS = {
    "business": "Собранный силуэт с чёткой линией плеч и спокойной палитрой.",
    "evening": "Сдержанный вечерний силуэт с одним выразительным акцентом.",
    "travel": "Мягкий силуэт, в котором удобно провести весь день в пути.",
    "sport": "Свободный силуэт, который не сковывает движения.",
    "casual": "Расслабленный городской силуэт на базовых вещах.",
}

_TIPS = {
    "business": [
        "Расстегните верхнюю пуговицу и слегка подверните рукава — образ станет менее формальным.",
        "Сумку держите в руке, чтобы линия плеч оставалась чистой.",
    ],
    "evening": [
        "Накиньте верхний слой на плечи для более расслабленной подачи.",
        "Оставьте один акцент — аксессуар или фактуру, остальное пусть будет спокойным.",
    ],
    "travel": [
        "Выбирайте слои, которые легко снять в помещении или в транспорте.",
        "Сумку возьмите вместительную — она заменит дополнительный аксессуар.",
    ],
    "sport": [
        "Оставьте силуэт свободным: одна вещь объёмная, вторая — по фигуре.",
        "Белая обувь освежит даже самый простой комплект.",
    ],
    "casual": [
        "Заправьте верх спереди — талия обозначится, а посадка останется свободной.",
        "Подверните низ на один оборот, чтобы открыть щиколотку и обувь.",
    ],
}
_COLD_TIP = "Верхний слой оставьте расстёгнутым в помещении — так видно фактуру вещей под ним."
_RAIN_TIP = "В дождь выбирайте гладкую кожу в обуви и держите длину низа выше щиколотки."
_HOT_TIP = "Оставьте свободу в силуэте: лёгким тканям нужен воздух."


def _short(item: WardrobeItem) -> str:
    title = item.title.strip()
    return title[:1].lower() + title[1:]


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " и " + parts[-1]


def _title(ctx: PromptContext) -> str:
    if ctx.analysis.occasion == "casual":
        if ctx.is_cold or ctx.is_rainy:
            return _COLD_TITLE
        if ctx.is_hot:
            return _HOT_TITLE
    return _TITLES[ctx.analysis.occasion]


def build_mock_draft(ctx: PromptContext) -> dict:
    """Шаблонный ответ вокруг детерминированной сборки (`ctx.assembly`)."""
    analysis = ctx.analysis
    items = ctx.assembly.items
    by_category: dict[str, list[WardrobeItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    core = [_short(i) for slot in CORE_SLOTS for i in by_category.get(slot, [])]
    text = f"Собрал для вас образ: {_join(core)}." if core else "Собрал образ из того, что есть в гардеробе."
    if by_category.get("outerwear"):
        outer = _short(by_category["outerwear"][0])
        if "outerwear" in ctx.outcome.required_slots:
            text += f" Сверху — {outer}: по погоде ({ctx.weather_summary()}) без верхнего слоя не обойтись."
        else:
            text += f" Сверху — {outer}, он собирает силуэт."
    missing = [CATEGORY_LABELS_RU[slot] for slot in CORE_SLOTS if slot not in by_category]
    if missing:
        text += f" В гардеробе пока нет категории «{_join(missing)}» — добавьте её, и образ станет законченным."

    colors = list(dict.fromkeys(i.color.split("/")[0].strip().lower() for i in items if i.color))
    materials = list(
        dict.fromkeys(i.material.strip().lower() for i in items if i.material and i.material.strip())
    )
    reasoning = "Спокойная палитра"
    if colors:
        reasoning += f" ({_join(colors[:3])})"
    reasoning += " держит образ цельным"
    if len(materials) >= 2:
        reasoning += f", а контраст фактур — {materials[0]} и {materials[1]} — добавляет глубины"
    reasoning += "."

    tips = list(_TIPS[analysis.occasion])
    if ctx.is_hot:
        tips[1] = _HOT_TIP
    elif ctx.is_rainy:
        tips[1] = _RAIN_TIP
    elif ctx.is_cold and by_category.get("outerwear"):
        tips[1] = _COLD_TIP

    return {
        "text": text,
        "outfit": {
            "title": _title(ctx),
            "description": _DESCRIPTIONS[analysis.occasion],
            "occasion": analysis.occasion_label,
            "item_ids": [item.id for item in items],
            "stylistReasoning": reasoning,
            "confidenceTips": tips,
        },
    }


class MockLLM:
    provider = "mock"
    model = "rule-based-stylist"

    def __init__(self, stream_delay_s: float = 0.0) -> None:
        self._delay = stream_delay_s

    async def complete(
        self, messages: Messages, *, context: PromptContext, temperature: float
    ) -> str:
        return json.dumps(build_mock_draft(context), ensure_ascii=False)

    async def stream(
        self, messages: Messages, *, context: PromptContext, temperature: float
    ) -> AsyncIterator[str]:
        raw = json.dumps(build_mock_draft(context), ensure_ascii=False)
        step = 12
        for start in range(0, len(raw), step):
            if self._delay:
                await asyncio.sleep(self._delay)
            yield raw[start : start + step]
