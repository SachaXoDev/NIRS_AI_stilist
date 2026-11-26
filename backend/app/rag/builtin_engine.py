"""Встроенный запасной движок поиска: лексический BM25 + простые правила, без нейросетей.

Нужен, чтобы бэкенд поднимался там, где пакет `wardrobe_rag` или его модели недоступны
(машина без скачанного кеша, CI, разработка фронтенда). По качеству поиска он не заменяет
`wardrobe_rag` и всегда явно обозначается в ответе: `meta.retriever = "builtin-bm25"`.
Правила слотов и проверки выбора намеренно повторяют `wardrobe_rag.constraints`.
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import Any

from app.rag.base import (
    CORE_SLOTS,
    SLOT_LIMITS,
    SLOTS,
    AnchorRejected,
    RagEngineError,
    RetrievalOutcome,
    RetrievalQuery,
    SelectionCheck,
    SlotCandidate,
    SlotOutcome,
    SlotQuery,
)
from app.schemas import CATEGORY_LABELS_RU, RecommendContext, WardrobeItem
from app.services.analysis import QueryAnalysis, analyze_query
from app.services.scoring import palette_score
from app.services.textutils import normalize, tokenize
from app.storage.app_store import AppStore

SLOT_BUDGET: dict[str, int] = {"tops": 3, "bottoms": 3, "shoes": 3, "outerwear": 2, "accessories": 2}
FINGERPRINT = "builtin-bm25-v1"

_EXPANSION_WEIGHT = 0.5
_K1 = 1.5
_B = 0.75
_LEX_WEIGHT = 0.6
_FIT_WEIGHT = 0.4

_WARM_MATERIALS = ("шерст", "кашемир", "твид", "пух", "флис", "мех", "вельвет", "драп")
_LIGHT_MATERIALS = ("лен", "льн", "шелк", "вискоз", "хлоп", "шифон")
_RAIN_FRIENDLY = ("водооттал", "дожд", "плащ", "тренч", "непромока", "резин")
_RAIN_HOSTILE_SHOES = ("замш", "текстил", "сандал", "босонож", "открыт", "эспадрил", "шлепан")


def item_document(item: WardrobeItem) -> str:
    """Лексическое представление вещи; название и теги учитываются дважды."""
    parts = [
        item.title,
        item.title,
        CATEGORY_LABELS_RU.get(item.category, item.category),
        item.color,
        item.material or "",
        item.brand or "",
        " ".join(item.tags),
        " ".join(item.tags),
        " ".join(item.style),
    ]
    return " ".join(p for p in parts if p)


def lexical_scores(
    query: str, analysis: QueryAnalysis, wardrobe: list[WardrobeItem]
) -> dict[str, float]:
    """BM25 по гардеробу. Возвращает сырые баллы; вещи без совпадений получают 0."""
    if not wardrobe:
        return {}
    # Термы запроса весят 1.0, термы расширения (повод/погода) — меньше.
    weights: dict[str, float] = {}
    for term in tokenize(" ".join(analysis.expansion_terms)):
        weights[term] = _EXPANSION_WEIGHT
    for term in tokenize(" ".join(filter(None, [query, analysis.vibe]))):
        weights[term] = 1.0

    docs = [tokenize(item_document(item), drop_stopwords=False) for item in wardrobe]
    n_docs = len(docs)
    avg_len = sum(len(d) for d in docs) / n_docs or 1.0
    doc_freq: Counter[str] = Counter()
    for doc in docs:
        doc_freq.update(set(doc))

    scores: dict[str, float] = {}
    for item, doc in zip(wardrobe, docs):
        term_freq = Counter(doc)
        total = 0.0
        for term, weight in weights.items():
            freq = term_freq.get(term, 0)
            if not freq:
                continue
            idf = math.log(1.0 + (n_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            norm = freq * (_K1 + 1) / (freq + _K1 * (1 - _B + _B * len(doc) / avg_len))
            total += weight * idf * norm
        scores[item.id] = total
    return scores


def fit_score(item: WardrobeItem, analysis: QueryAnalysis) -> float:
    """Соответствие вещи поводу и погоде, 0..1 — по сезону, материалу и тегам."""
    score = 0.5
    text = normalize(" ".join([item.title, item.material or "", " ".join(item.tags)]))
    if {normalize(s) for s in item.style} & analysis.occasion_styles:
        score += 0.25
    warm = any(m in text for m in _WARM_MATERIALS)
    light = any(m in text for m in _LIGHT_MATERIALS)
    if analysis.is_hot:
        if item.season == "autumn/winter":
            score -= 0.3
        if warm:
            score -= 0.2
        if light:
            score += 0.15
    elif analysis.is_cold:
        if item.season == "autumn/winter":
            score += 0.15
        if warm:
            score += 0.1
        if item.season == "spring/summer" and item.category != "outerwear" and not warm:
            score -= 0.1
    if "rain" in analysis.weather or "snow" in analysis.weather:
        if any(m in text for m in _RAIN_FRIENDLY):
            score += 0.25
        if item.category == "shoes":
            if any(m in text for m in _RAIN_HOSTILE_SHOES):
                score -= 0.3
            elif "кож" in text:
                score += 0.1
    return max(0.0, min(1.0, score))


class BuiltinEngine:
    name = "builtin-bm25"

    def __init__(self, store: AppStore) -> None:
        self._store = store

    def info(self) -> dict[str, Any]:
        return {
            "engine": self.name,
            "model_fingerprint": FINGERPRINT,
            "note": "запасной лексический поиск без эмбеддингов",
        }

    def sync(self, user_id: str, items: list[WardrobeItem]) -> dict[str, Any]:
        started = time.perf_counter()
        unique: dict[str, WardrobeItem] = {}
        for item in items:
            unique.setdefault(item.id, item)
        _, old_items = self._store.get_snapshot(user_id)
        old = {item.id: item for item in old_items}
        revision = self._store.replace_snapshot(user_id, list(unique.values()))
        updated = sum(1 for key in old.keys() & unique.keys() if old[key] != unique[key])
        return {
            "user_id": user_id,
            "revision": revision,
            "indexed_count": len(unique),
            "image_count": 0,
            "added_count": len(unique.keys() - old.keys()),
            "updated_count": updated,
            "deleted_count": len(old.keys() - unique.keys()),
            "unchanged_count": len(old.keys() & unique.keys()) - updated,
            "warnings": ["Встроенный движок не индексирует изображения: поиск только лексический"],
            "timings_ms": {"total_ms": (time.perf_counter() - started) * 1000},
        }

    def get_items(self, user_id: str) -> list[WardrobeItem]:
        return self._store.get_snapshot(user_id)[1]

    def retrieve(self, query: RetrievalQuery) -> RetrievalOutcome:
        started = time.perf_counter()
        revision, items = self._store.get_snapshot(query.user_id)
        by_id = {item.id: item for item in items}
        if query.anchor_item_id is not None and query.anchor_item_id not in by_id:
            raise AnchorRejected("anchor_item_id is not present in this user's wardrobe")

        context = RecommendContext(occasion=query.occasion, weather=query.weather, vibe=query.vibe)
        analysis = analyze_query(query.query, context, [])
        warnings: list[str] = [
            "Работает запасной встроенный поиск builtin-bm25 (только лексика, без эмбеддингов "
            "и изображений), а не wardrobe_rag"
        ]
        if query.query_image:
            warnings.append("Встроенный движок не поддерживает поиск по изображению")
        if not items:
            warnings.append("The user's wardrobe is empty; no demo-catalog items were substituted")

        excluded = set(query.exclude_item_ids) - {query.anchor_item_id}
        allowed = [item for item in items if item.id not in excluded]
        raw_scores = lexical_scores(query.query, analysis, allowed)
        top_raw = max(raw_scores.values(), default=0.0)
        ranked = sorted((s for s in raw_scores.values() if s > 0), reverse=True)

        candidates_by_slot: dict[str, list[SlotCandidate]] = {}
        diagnostics_by_slot: dict[str, list[dict[str, Any]]] = {}
        for slot in SLOTS:
            rows = []
            for item in (i for i in allowed if i.category == slot):
                raw = raw_scores.get(item.id, 0.0)
                lexical = raw / top_raw if top_raw > 0 else 0.0
                anchored = item.id == query.anchor_item_id
                score = _LEX_WEIGHT * lexical + _FIT_WEIGHT * fit_score(item, analysis)
                rows.append((item, raw, score, anchored))
            rows.sort(key=lambda row: (not row[3], -row[2], row[0].id))
            rows = rows[: SLOT_BUDGET[slot]]
            candidates_by_slot[slot] = [
                SlotCandidate(item=item, score=score, anchored=anchored, fallback=raw <= 0 and not anchored)
                for item, raw, score, anchored in rows
            ]
            diagnostics_by_slot[slot] = [
                {
                    "item": item.model_dump(by_alias=True, mode="json"),
                    "score": score,
                    "bm25_score": raw if raw > 0 else None,
                    "bm25_rank": ranked.index(raw) + 1 if raw > 0 else None,
                    "dense_distance": None,
                    "dense_rank": None,
                    "visual_distance": None,
                    "visual_rank": None,
                    "bm25_contribution": score,
                    "dense_contribution": 0,
                    "visual_contribution": 0,
                    "anchored": anchored,
                    "fallback": raw <= 0 and not anchored,
                }
                for item, raw, score, anchored in rows
            ]

        required = list(CORE_SLOTS)
        rain = "rain" in analysis.weather
        if query.require_outerwear or rain or (analysis.temperature_c is not None and analysis.temperature_c <= 12):
            required.append("outerwear")
        missing = [slot for slot in required if not candidates_by_slot.get(slot)]
        if missing:
            warnings.append("No eligible retrieved candidates for required slots: " + ", ".join(missing))

        resolved_context = {
            "occasion": query.occasion,
            "weather": query.weather,
            "vibe": query.vibe,
            "temperature_c": analysis.temperature_c,
            "rain": True if rain else None,
            "wind": True if "wind" in analysis.weather else None,
        }
        timings = {"total": (time.perf_counter() - started) * 1000}
        return RetrievalOutcome(
            user_id=query.user_id,
            query=query.query,
            engine=self.name,
            mode="bm25",
            candidates_by_slot=candidates_by_slot,
            required_slots=required,
            missing_slots=missing,
            context=resolved_context,
            anchor_item_id=query.anchor_item_id,
            warnings=warnings,
            timings_ms=timings,
            revision=revision,
            diagnostics={
                "engine": self.name,
                "user_id": query.user_id,
                "query": query.query,
                "mode": "bm25",
                "alpha": 0.0,
                "visual_weight": 0.0,
                "rrf_c": 0,
                "candidates_by_slot": diagnostics_by_slot,
                "required_slots": required,
                "missing_slots": missing,
                "context": resolved_context,
                "anchor_item_id": query.anchor_item_id,
                "warnings": warnings,
                "timings_ms": timings,
                "wardrobe_revision": revision,
                "model_fingerprint": FINGERPRINT,
                "score_method": "bm25_plus_rules",
            },
            raw=analysis,
        )

    def validate_selection(self, item_ids: list[str], outcome: RetrievalOutcome) -> SelectionCheck:
        allowed = outcome.allowed_items
        violations: list[str] = []
        if len(set(item_ids)) != len(item_ids):
            violations.append("Duplicate item IDs are not allowed")
        unknown = sorted(set(item_ids) - allowed.keys())
        if unknown:
            violations.append(
                "IDs are outside this user's retrieved candidate set: " + ", ".join(unknown)
            )
        selected = [allowed[i] for i in dict.fromkeys(item_ids) if i in allowed]
        counts = Counter(item.category for item in selected)
        for slot, limit in SLOT_LIMITS.items():
            if counts[slot] > limit:
                violations.append(
                    "At most two accessories are allowed"
                    if slot == "accessories"
                    else f"At most one item is allowed in slot {slot}"
                )
        mandatory = list(dict.fromkeys([*CORE_SLOTS, *outcome.required_slots]))
        missing = [slot for slot in mandatory if counts[slot] == 0]
        if outcome.anchor_item_id is not None and outcome.anchor_item_id not in item_ids:
            violations.append("Required anchor item is missing")
        stale = self._store.get_snapshot(outcome.user_id)[0] != outcome.revision
        if stale:
            violations.append(
                "Wardrobe changed since retrieval; retrieve fresh candidates before accepting the outfit"
            )
        return SelectionCheck(
            valid=not violations,
            complete=not violations and not missing,
            items=selected,
            missing_slots=missing,
            violations=violations,
            warnings=[],
            stale=stale,
        )

    def assemble(self, outcome: RetrievalOutcome) -> SelectionCheck:
        analysis: QueryAnalysis | None = outcome.raw if isinstance(outcome.raw, QueryAnalysis) else None
        slots = list(dict.fromkeys([*CORE_SLOTS, *outcome.required_slots]))
        dressy = analysis is not None and analysis.occasion in ("business", "evening")
        hot = analysis is not None and analysis.is_hot
        if "outerwear" not in slots and dressy and not hot:
            slots.append("outerwear")
        if "accessories" not in slots:
            slots.append("accessories")
        chosen: list[WardrobeItem] = []
        for slot in slots:
            group = outcome.candidates_by_slot.get(slot, [])
            if group:
                chosen.append(group[0].item)  # якорная вещь всегда первая в своём слоте
        anchor = outcome.anchor_item_id
        if anchor and anchor not in {item.id for item in chosen} and anchor in outcome.allowed_items:
            chosen.append(outcome.allowed_items[anchor])
        # Лишний цветовой акцент убираем за счёт необязательного аксессуара.
        if palette_score(chosen) < 1.0:
            trimmed = [i for i in chosen if i.category != "accessories" or i.id == anchor]
            if palette_score(trimmed) > palette_score(chosen):
                chosen = trimmed
        return self.validate_selection([item.id for item in chosen], outcome)

    def get_revision(self, user_id: str) -> str:
        return self._store.get_snapshot(user_id)[0]

    def retrieve_slot(self, query: SlotQuery) -> SlotOutcome:
        """Упрощённый аналог `wardrobe_rag.retrieve_slot` с теми же правилами отбора."""
        started = time.perf_counter()
        revision, items = self._store.get_snapshot(query.user_id)
        by_id = {item.id: item for item in items}
        if set(query.outfit_item_ids) - by_id.keys():
            raise RagEngineError("The existing outfit contains IDs outside this user's current wardrobe")
        in_slot = [i for i in query.outfit_item_ids if by_id[i].category == query.slot]
        replaced = query.replace_item_id
        if query.operation == "replace":
            if replaced is None and len(in_slot) == 1:
                replaced = in_slot[0]
            if replaced is None or replaced not in in_slot:
                raise RagEngineError("Choose one existing item from the requested slot to replace")
        elif len(in_slot) >= SLOT_LIMITS[query.slot]:
            raise RagEngineError("The requested slot is full; use operation=replace")

        warnings = [
            "Работает запасной встроенный поиск builtin-bm25 (только лексика, без эмбеддингов "
            "и изображений), а не wardrobe_rag"
        ]
        blocked = set(query.outfit_item_ids) | set(query.exclude_item_ids)
        pool = [item for item in items if item.category == query.slot and item.id not in blocked]
        text = normalize(query.query)
        if query.slot == "shoes" and _FLAT_REQUEST_RE.search(text):
            pool = [item for item in pool if _is_documented_flat(item)]
            warnings.append("Flat footwear required; candidates without an explicit flat-sole annotation were excluded")

        context = RecommendContext(occasion=query.occasion, weather=query.weather, vibe=query.vibe)
        analysis = analyze_query(query.query, context, [])
        kept = [by_id[i] for i in query.outfit_item_ids if i != replaced]
        search = " ".join(filter(None, [query.query, query.occasion, *(item.title for item in kept)]))
        raw_scores = lexical_scores(search, analysis, pool)
        top_raw = max(raw_scores.values(), default=0.0)
        rows = sorted(
            (
                (
                    _LEX_WEIGHT * (raw_scores.get(item.id, 0.0) / top_raw if top_raw > 0 else 0.0)
                    + _FIT_WEIGHT * fit_score(item, analysis),
                    item,
                )
                for item in pool
            ),
            key=lambda row: (-row[0], row[1].id),
        )[: SLOT_BUDGET[query.slot]]
        candidates = [SlotCandidate(item=item, score=score) for score, item in rows]
        resolved = {
            "occasion": query.occasion, "weather": query.weather, "vibe": query.vibe,
            "temperature_c": query.temperature_c if query.temperature_c is not None else analysis.temperature_c,
            "rain": query.rain if query.rain is not None else ("rain" in analysis.weather or None),
            "wind": query.wind if query.wind is not None else ("wind" in analysis.weather or None),
        }
        timings = {"total": (time.perf_counter() - started) * 1000}
        return SlotOutcome(
            slot=query.slot,
            candidates=candidates,
            kept_item_ids=[item.id for item in kept],
            replaced_item_id=replaced,
            context=resolved,
            warnings=warnings,
            timings_ms=timings,
            revision=revision,
            diagnostics={
                "engine": self.name, "user_id": query.user_id, "slot": query.slot,
                "candidates": [
                    {"item": c.item.model_dump(by_alias=True, mode="json"), "score": c.score,
                     "anchored": False, "fallback": False}
                    for c in candidates
                ],
                "kept_item_ids": [item.id for item in kept], "replaced_item_id": replaced,
                "context": resolved, "warnings": warnings, "timings_ms": timings,
                "wardrobe_revision": revision, "model_fingerprint": FINGERPRINT,
            },
        )


_FLAT_REQUEST_RE = re.compile(r"без\s+каблук|плоск\w*\s+подошв|на\s+плоском\s+ходу")
_HEEL_NOTE_RE = re.compile(r"(?:на|с)\s+(?:\w+\s+){0,2}каблук(?:е|ом)")


def _is_documented_flat(item: WardrobeItem) -> bool:
    parts = [normalize(part) for part in (item.title, *item.tags)]
    return any(_FLAT_REQUEST_RE.search(part) for part in parts) and not any(
        _HEEL_NOTE_RE.search(part) for part in parts
    )
