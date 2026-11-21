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
