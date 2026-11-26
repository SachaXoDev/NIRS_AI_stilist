"""Порт поискового движка: всё, что оркестратору нужно от RAG.

Реализаций две:
* `WardrobeRagEngine` — адаптер к пакету `wardrobe_rag` из каталога `rag/` (Chroma, BM25,
  текстовые и визуальные эмбеддинги, RRF). Это основной режим.
* `BuiltinEngine` — лексический BM25 без нейросетевых моделей. Запасной режим, который
  всегда явно помечается в ответе (`meta.retriever`, `/health`).

Обе реализации следуют одним правилам состава образа (см. `rag/README.md`): по одной вещи
в слотах tops/bottoms/shoes/outerwear и не больше двух аксессуаров.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.schemas import WardrobeItem

SLOTS: tuple[str, ...] = ("tops", "bottoms", "shoes", "outerwear", "accessories")
CORE_SLOTS: tuple[str, ...] = ("tops", "bottoms", "shoes")
SLOT_LIMITS: dict[str, int] = {
    "tops": 1,
    "bottoms": 1,
    "shoes": 1,
    "outerwear": 1,
    "accessories": 2,
}


class RagEngineError(RuntimeError):
    """Поиск не смог обработать запрос (движок недоступен, запрос некорректен)."""


class AnchorRejected(RagEngineError):
    """Якорная вещь отсутствует в гардеробе или противоречит ограничениям запроса."""


@dataclass
class RetrievalQuery:
    user_id: str
    query: str
    mode: str = "hybrid"
    alpha: float = 0.65
    visual_weight: float = 0.35
    occasion: str | None = None
    weather: str | None = None
    vibe: str | None = None
    anchor_item_id: str | None = None
    exclude_item_ids: list[str] = field(default_factory=list)
    query_image: str | None = None
    require_outerwear: bool = False


@dataclass
class SlotCandidate:
    item: WardrobeItem
    score: float = 0.0
    anchored: bool = False
    fallback: bool = False  # слот заполнен без поисковых свидетельств


@dataclass
class RetrievalOutcome:
    user_id: str
    query: str
    engine: str
    mode: str
    candidates_by_slot: dict[str, list[SlotCandidate]]
    required_slots: list[str]
    missing_slots: list[str]
    context: dict[str, Any]  # occasion, weather, vibe, temperature_c, rain, wind
    anchor_item_id: str | None
    warnings: list[str]
    timings_ms: dict[str, float]
    revision: str
    diagnostics: dict[str, Any]  # JSON-представление в формате RetrievalResult
    raw: Any = None  # «родной» объект движка — нужен ему же для validate_selection

    @property
    def allowed_items(self) -> dict[str, WardrobeItem]:
        return {c.item.id: c.item for group in self.candidates_by_slot.values() for c in group}


@dataclass
class SlotQuery:
    """Поиск одной вещи к уже собранному образу (точечная правка)."""

    user_id: str
    query: str
    slot: str
    operation: str  # "add" | "replace"
    outfit_item_ids: list[str]
    replace_item_id: str | None = None
    mode: str = "hybrid"
    alpha: float = 0.65
    visual_weight: float = 0.35
    occasion: str | None = None
    weather: str | None = None
    vibe: str | None = None
    temperature_c: float | None = None
    rain: bool | None = None
    wind: bool | None = None
    exclude_item_ids: list[str] = field(default_factory=list)


@dataclass
class SlotOutcome:
    slot: str
    candidates: list[SlotCandidate]  # пустой список — подходящей вещи нет, слот не заполняется
    kept_item_ids: list[str]
    replaced_item_id: str | None
    context: dict[str, Any]
    warnings: list[str]
    timings_ms: dict[str, float]
    revision: str
    diagnostics: dict[str, Any]  # JSON в формате SlotSearchResult + поле engine


def composition_errors(items: list[WardrobeItem]) -> list[str]:
    """Правила состава готового образа — общие для подбора и точечной правки."""
    errors: list[str] = []
    counts: dict[str, int] = {}
    for item in items:
        counts[item.category] = counts.get(item.category, 0) + 1
    if len({item.id for item in items}) != len(items):
        errors.append("вещи в образе повторяются")
    for slot, limit in SLOT_LIMITS.items():
        if counts.get(slot, 0) > limit:
            errors.append(f"в слоте {slot} больше {limit} вещей")
    missing = [slot for slot in CORE_SLOTS if not counts.get(slot)]
    if missing:
        errors.append("не заполнены обязательные слоты: " + ", ".join(missing))
    return errors


@dataclass
class SelectionCheck:
    valid: bool
    complete: bool
    items: list[WardrobeItem] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stale: bool = False  # гардероб изменился после поиска: нужен новый retrieve, а не повтор LLM


class RagEngine(Protocol):
    name: str

    def info(self) -> dict[str, Any]:
        """Сведения для /health."""
        ...

    def sync(self, user_id: str, items: list[WardrobeItem]) -> dict[str, Any]:
        """Заменить снимок гардероба пользователя. Возвращает SyncResult в виде JSON."""
        ...

    def get_items(self, user_id: str) -> list[WardrobeItem]:
        ...

    def retrieve(self, query: RetrievalQuery) -> RetrievalOutcome:
        ...

    def validate_selection(self, item_ids: list[str], outcome: RetrievalOutcome) -> SelectionCheck:
        """Проверить id, выбранные LLM, относительно этой выдачи."""
        ...

    def assemble(self, outcome: RetrievalOutcome) -> SelectionCheck:
        """Детерминированная сборка образа без LLM (mock-режим и фолбэк)."""
        ...

    def retrieve_slot(self, query: SlotQuery) -> SlotOutcome:
        """Кандидаты одной категории к существующему образу. Вещи образа в выдачу не попадают."""
        ...

    def get_revision(self, user_id: str) -> str:
        """Текущая ревизия гардероба — чтобы не показать карточку по устаревшему поиску."""
        ...
