"""`matchScore` для карточки образа.

Фронтенд требует число 0..100. Это НЕ вероятность и не оценка модели: RRF-score поиска не
переводится в проценты, а LLM себя не оценивает. Значение считается прозрачной эвристикой
из трёх наблюдаемых величин — её состав возвращается в `meta.matchScoreMethod`.
"""
from __future__ import annotations

from app.rag.base import RetrievalOutcome
from app.schemas import WardrobeItem
from app.services.textutils import normalize

MATCH_SCORE_METHOD = (
    "эвристика: 40% полнота обязательных слотов + 25% позиция выбранных вещей в поисковой "
    "выдаче + 20% доля вещей с поисковыми свидетельствами + 15% сдержанность палитры; "
    "не вероятность"
)

_NEUTRAL_COLORS = (
    "бел", "черн", "сер", "беж", "молоч", "крем", "экрю", "песоч", "корич", "шокол", "син",
    "графит", "айвори", "слонов", "карамел", "хаки", "деним", "navy", "black", "white", "grey",
    "gray", "beige",
)


def is_neutral_color(color: str) -> bool:
    text = normalize(color)
    return any(stem in text for stem in _NEUTRAL_COLORS)


def palette_score(items: list[WardrobeItem]) -> float:
    accents = sum(1 for item in items if item.color and not is_neutral_color(item.color))
    return 1.0 if accents <= 1 else 0.8 if accents == 2 else 0.6


def match_score(items: list[WardrobeItem], outcome: RetrievalOutcome) -> int:
    if not items:
        return 0
    present = {item.category for item in items}
    required = outcome.required_slots or ["tops", "bottoms", "shoes"]
    completeness = sum(1 for slot in required if slot in present) / len(required)

    ranks: list[float] = []
    evidenced = 0
    for item in items:
        group = outcome.candidates_by_slot.get(item.category, [])
        candidate = next((c for c in group if c.item.id == item.id), None)
        if candidate is None:
            ranks.append(0.0)
            continue
        if candidate.anchored:
            ranks.append(1.0)  # вещь выбрал сам пользователь
            evidenced += 1
            continue
        top = max((c.score for c in group), default=0.0)
        ranks.append(candidate.score / top if top > 0 else 0.5)
        if not candidate.fallback:
            evidenced += 1
    rank_quality = sum(ranks) / len(ranks)
    evidence = evidenced / len(items)

    value = 0.40 * completeness + 0.25 * rank_quality + 0.20 * evidence + 0.15 * palette_score(items)
    return max(0, min(100, round(value * 100)))
