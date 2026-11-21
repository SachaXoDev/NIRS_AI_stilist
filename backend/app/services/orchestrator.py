"""Оркестрация пайплайна стилиста (схема из `rag/INTEGRATION.md`).

    синхронизация гардероба → поиск кандидатов по слотам → LLM выбирает id и пишет тексты
    → проверка выбора движком → (исправление LLM) → детерминированная сборка как фолбэк

Гарантии для фронтенда:
* в образ попадают только реальные вещи из гардероба пользователя, прошедшие проверку слотов;
* если обязательной категории нет, образ не выдаётся за законченный: приходит текст с
  объяснением и `missingSlots`;
* поле `source` честно говорит, кто собрал ответ: `llm`, `mock`, `fallback` или `none`.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.config import Settings
from app.rag.base import (
    CORE_SLOTS,
    SLOTS,
    AnchorRejected,
    RagEngine,
    RagEngineError,
    RetrievalOutcome,
    RetrievalQuery,
    SelectionCheck,
)
from app.schemas import (
    CATEGORY_LABELS_RU,
    CATEGORY_ORDER,
    OutfitLook,
    RecommendRequest,
    RecommendResponse,
    ResponseMeta,
    RuntimeSettings,
    WardrobeItem,
)
from app.services.analysis import analyze_query
from app.services.llm.base import LLMClient, LLMError
from app.services.llm.mock import build_mock_draft
from app.services.prompts import PromptContext, build_messages, build_repair_messages
from app.services.scoring import MATCH_SCORE_METHOD, match_score
from app.services.streaming import JsonStringFieldExtractor
from app.services.validation import (
    MAX_TIPS,
    DraftParseError,
    StylistDraft,
    field_errors,
    parse_draft,
)
from app.storage.app_store import DEMO_USER_ID, AppStore

logger = logging.getLogger(__name__)

RUNTIME_SETTINGS_KEY = "runtime_settings"
EMPTY_WARDROBE_TEXT = (
    "В вашем гардеробе пока нет вещей. Добавьте хотя бы верх, низ и обувь — "
    "или загрузите базовую капсулу, и я соберу образ."
)
_FALLBACK_SVG = {
    "tops": "/clothes/shirt.svg",
    "bottoms": "/clothes/palazzo.svg",
    "outerwear": "/clothes/blazer.svg",
    "shoes": "/clothes/loafers.svg",
    "accessories": "/clothes/tote.svg",
}

# Событие стрима: (имя события, полезная нагрузка)
StreamEvent = tuple[str, dict[str, Any]]


@dataclass
class _Prepared:
    ctx: PromptContext
    messages: list[dict[str, str]]
    runtime: RuntimeSettings
    debug: bool
    started: float
    warnings: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)


@dataclass
class _Generation:
    draft: StylistDraft
    items: list[WardrobeItem]
    attempts: int
    source: str


class StylistService:
    def __init__(
        self, settings: Settings, store: AppStore, engine: RagEngine, llm: LLMClient
    ) -> None:
        self._settings = settings
        self._store = store
        self._engine = engine
        self._llm = llm

    # --- настройки куратора -------------------------------------------------------

    def get_runtime_settings(self) -> RuntimeSettings:
        defaults = {
            "mode": self._settings.rag_mode,
            "alpha": self._settings.rag_alpha,
            "visual_weight": self._settings.rag_visual_weight,
            "temperature": self._settings.llm_temperature,
            "persona_prompt": self._settings.persona_prompt,
        }
        stored = self._store.get_json(RUNTIME_SETTINGS_KEY) or {}
        try:
            return RuntimeSettings.model_validate({**defaults, **stored})
        except ValueError:
            logger.warning("Stored runtime settings are invalid; using defaults")
            return RuntimeSettings.model_validate(defaults)

    def update_runtime_settings(self, patch: dict[str, Any]) -> RuntimeSettings:
        current = self.get_runtime_settings().model_dump()
        current.update({key: value for key, value in patch.items() if value is not None})
        updated = RuntimeSettings.model_validate(current)
        self._store.set_json(RUNTIME_SETTINGS_KEY, updated.model_dump())
        return updated

    @property
    def llm_info(self) -> tuple[str, str]:
        return self._llm.provider, self._llm.model

    @property
    def engine_name(self) -> str:
        return self._engine.name

    def engine_info(self) -> dict[str, Any]:
        return self._engine.info()

    # --- гардероб -----------------------------------------------------------------

    async def sync_wardrobe(self, user_id: str, items: list[WardrobeItem]) -> dict[str, Any]:
        # Кодирование и индексация — блокирующие операции: уводим их из event loop.
        return await asyncio.to_thread(self._engine.sync, user_id, items)

    async def get_wardrobe(self, user_id: str) -> list[WardrobeItem]:
        return await asyncio.to_thread(self._engine.get_items, user_id)

    # --- рекомендация -------------------------------------------------------------

    async def recommend(self, request: RecommendRequest) -> RecommendResponse:
        prepared = await self._prepare(request)
        if isinstance(prepared, RecommendResponse):
            return prepared
        generation = await self._generate(prepared)
        return self._build_response(prepared, generation)

    async def recommend_stream(self, request: RecommendRequest) -> AsyncIterator[StreamEvent]:
        """События: status → retrieval → delta* → result.

        Сначала уходит диагностика поиска, затем настоящие текстовые чанки LLM, последним —
        проверенный ответ (тот же объект, что у обычного эндпоинта; его `text` авторитетен).
        """
        yield "status", {"stage": "retrieval"}
        prepared = await self._prepare(request)
        if isinstance(prepared, RecommendResponse):
            yield "delta", {"text": prepared.text}
            yield "result", _dump(prepared)
            return

        yield "retrieval", _retrieval_payload(prepared.ctx.outcome, full=prepared.debug)
        yield "status", {"stage": "generation"}

        raw_parts: list[str] = []
        extractor = JsonStringFieldExtractor("text")
        stream_error: str | None = None
        llm_started = time.perf_counter()
        try:
            async for chunk in self._llm.stream(
                prepared.messages, context=prepared.ctx, temperature=prepared.runtime.temperature
            ):
                raw_parts.append(chunk)
                delta = extractor.feed(chunk)
                if delta:
                    # Время до первого текста и до готового JSON измеряются раздельно.
                    prepared.timings.setdefault("llmFirstTextMs", _ms_since(llm_started))
                    yield "delta", {"text": delta}
        except LLMError as exc:
            stream_error = str(exc)
            logger.warning("LLM stream failed: %s", exc)
        prepared.timings["llmMs"] = _ms_since(llm_started)

        yield "status", {"stage": "validation"}
        generation = await self._generate(
            prepared, first_raw="".join(raw_parts), first_error=stream_error
        )
        yield "result", _dump(self._build_response(prepared, generation))

    # --- шаги пайплайна -----------------------------------------------------------

    def _meta(self, *, attempts: int = 0, revision: str = "", occasion: str = "") -> ResponseMeta:
        provider, model = self.llm_info
        return ResponseMeta(
            llm_provider=provider,
            llm_model=model,
            llm_attempts=attempts,
            retriever=self._engine.name,
            wardrobe_revision=revision,
            occasion=occasion,
            match_score_method=MATCH_SCORE_METHOD,
        )

    async def _prepare(self, request: RecommendRequest) -> _Prepared | RecommendResponse:
        started = time.perf_counter()
        timings: dict[str, float] = {}
        warnings: list[str] = []
        runtime = self.get_runtime_settings()
        user_id = request.user_id or DEMO_USER_ID

        if request.wardrobe is not None:
            phase = time.perf_counter()
            report = await self.sync_wardrobe(user_id, request.wardrobe)
            timings["syncMs"] = _ms_since(phase)
            warnings.extend(report.get("warnings", []))

        items = await self.get_wardrobe(user_id)
        exclude: list[str] = []
        if request.wardrobe is None and request.wardrobe_ids:
            wanted = set(request.wardrobe_ids)
            unknown = sorted(wanted - {item.id for item in items})
            if unknown:
                warnings.append(
                    f"{len(unknown)} из {len(wanted)} id нет в синхронизированном гардеробе "
                    f"пользователя ({', '.join(unknown[:5])}): передайте вещи целиком в поле "
                    "wardrobe или вызовите POST /api/wardrobe/sync"
                )
            exclude = [item.id for item in items if item.id not in wanted]
            items = [item for item in items if item.id in wanted]

        if not items:
            timings["totalMs"] = _ms_since(started)
            return RecommendResponse(
                text=EMPTY_WARDROBE_TEXT,
                source="none",
                missing_slots=list(CORE_SLOTS),
                warnings=_unique(warnings),
                timings=timings,
                meta=self._meta(),
            )

        analysis = analyze_query(request.query, request.context, items)
        known_ids = {item.id for item in items}
        anchor = request.anchor_item_id or next(iter(analysis.anchor_item_ids), None)
        if anchor is not None and anchor not in known_ids:
            warnings.append(f"Якорной вещи {anchor} нет в гардеробе — подбор без неё")
            anchor = None

        context = request.context
        query = RetrievalQuery(
            user_id=user_id,
            query=request.query,
            mode=request.mode or runtime.mode,
            alpha=request.alpha if request.alpha is not None else runtime.alpha,
            visual_weight=(
                request.visual_weight if request.visual_weight is not None else runtime.visual_weight
            ),
            occasion=context.occasion if context else None,
            weather=context.weather if context else None,
            vibe=context.vibe if context else None,
            anchor_item_id=anchor,
            exclude_item_ids=exclude,
            query_image=request.query_image,
        )
        phase = time.perf_counter()
        try:
            outcome = await asyncio.to_thread(self._engine.retrieve, query)
        except AnchorRejected as exc:
            warnings.append(
                f"Вещь {anchor} не подходит под ограничения запроса (например, по погоде), "
                f"подбор выполнен без неё: {exc}"
            )
            query.anchor_item_id = None
            outcome = await asyncio.to_thread(self._engine.retrieve, query)
        timings["retrievalMs"] = _ms_since(phase)
        warnings.extend(outcome.warnings)

        assembly: SelectionCheck | None = None
        if not outcome.missing_slots:
            assembly = await asyncio.to_thread(self._engine.assemble, outcome)
            warnings.extend(assembly.warnings)
        if assembly is None or not assembly.complete:
            # Не выдаём неполный комплект за законченный образ.
            missing = outcome.missing_slots or (assembly.missing_slots if assembly else [])
            if assembly is not None:
                warnings.extend(assembly.violations)
            timings["totalMs"] = _ms_since(started)
            return RecommendResponse(
                text=_incomplete_text(missing, outcome),
                source="none",
                missing_slots=missing,
                warnings=_unique(warnings),
                timings=timings,
                meta=self._meta(revision=outcome.revision, occasion=analysis.occasion_label),
                retrieval=_retrieval_payload(outcome, full=True) if request.debug else None,
            )

        ctx = PromptContext(
            query=request.query,
            analysis=analysis,
            outcome=outcome,
            assembly=assembly,
            history=request.history,
        )
        return _Prepared(
            ctx=ctx,
            messages=build_messages(ctx, runtime.persona_prompt),
            runtime=runtime,
            debug=request.debug,
            started=started,
            warnings=warnings,
            timings=timings,
        )

    async def _review(
        self, raw: str, ctx: PromptContext
    ) -> tuple[StylistDraft | None, list[WardrobeItem], list[str]]:
        """Разобрать ответ LLM и проверить выбранные id движком поиска."""
        try:
            draft = parse_draft(raw)
        except DraftParseError as exc:
            return None, [], [str(exc)]
        errors = field_errors(draft)
        if draft.outfit is None or not draft.outfit.item_ids:
            return draft, [], errors
        check = await asyncio.to_thread(
            self._engine.validate_selection, draft.outfit.item_ids, ctx.outcome
        )
        if check.stale:
            raise RagEngineError(
                "Гардероб изменился, пока стилист подбирал образ. Повторите запрос."
            )
        errors.extend(check.violations)
        if check.missing_slots:
            errors.append(
                "в образе не заполнены обязательные слоты: " + ", ".join(check.missing_slots)
            )
        return draft, check.items, errors

    async def _generate(
        self,
        prepared: _Prepared,
        *,
        first_raw: str | None = None,
        first_error: str | None = None,
    ) -> _Generation:
        """Генерация с проверкой: попытка → (исправление)* → детерминированный фолбэк."""
        ctx = prepared.ctx
        provider = self._llm.provider
        messages = prepared.messages
        max_attempts = 1 + self._settings.llm_max_repairs
        attempts = 0
        raw = first_raw
        llm_down = first_error is not None
        llm_started = time.perf_counter()
        spent_before = prepared.timings.get("llmMs", 0.0)

        try:
            while attempts < max_attempts and not llm_down:
                attempts += 1
                if raw is None:
                    try:
                        raw = await self._llm.complete(
                            messages, context=ctx, temperature=prepared.runtime.temperature
                        )
                    except LLMError as exc:
                        logger.warning("LLM call failed: %s", exc)
                        llm_down = True
                        break
                draft, items, errors = await self._review(raw, ctx)
                if draft is not None and not errors:
                    source = "mock" if provider == "mock" else "llm"
                    return _Generation(draft, _sort_items(items), attempts, source)
                logger.info("LLM draft rejected (attempt %d): %s", attempts, errors)
                messages = build_repair_messages(prepared.messages, raw, errors)
                raw = None
        finally:
            # Время, проведённое в LLM и проверках сверх стрима
            prepared.timings["llmMs"] = spent_before + _ms_since(llm_started)

        prepared.warnings.append(
            "LLM недоступна — образ собран детерминированно, без модели"
            if llm_down
            else "Ответ LLM не прошёл проверку — образ собран детерминированно, без модели"
        )
        draft = StylistDraft.model_validate(build_mock_draft(ctx))
        return _Generation(draft, _sort_items(ctx.assembly.items), attempts, "fallback")

    def _build_response(self, prepared: _Prepared, generation: _Generation) -> RecommendResponse:
        ctx = prepared.ctx
        outcome = ctx.outcome
        draft = generation.draft
        prepared.timings["totalMs"] = _ms_since(prepared.started)
        common: dict[str, Any] = {
            "source": generation.source,
            "warnings": _unique(prepared.warnings),
            "timings": {key: round(value, 1) for key, value in prepared.timings.items()},
            "meta": self._meta(
                attempts=generation.attempts,
                revision=outcome.revision,
                occasion=ctx.analysis.occasion_label,
            ),
            "retrieval": _retrieval_payload(outcome, full=True) if prepared.debug else None,
        }

        outfit_draft = draft.outfit
        if outfit_draft is None or not generation.items:
            # Разговорная реплика: образа нет, это не ошибка.
            return RecommendResponse(text=draft.text, **common)

        items = [_with_image(item) for item in generation.items]
        outfit = OutfitLook(
            id=f"outfit-{uuid.uuid4().hex[:12]}",
            title=outfit_draft.title[:120],
            description=outfit_draft.description or draft.text,
            occasion=outfit_draft.occasion or ctx.analysis.occasion_label,
            items=items,
            stylist_reasoning=outfit_draft.stylist_reasoning,
            match_score=match_score(generation.items, outcome),
            confidence_tips=outfit_draft.confidence_tips[:MAX_TIPS],
        )
        return RecommendResponse(
            text=draft.text,
            suggested_outfit=outfit,
            referenced_item_ids=[item.id for item in items],
            **common,
        )


def _incomplete_text(missing: list[str], outcome: RetrievalOutcome) -> str:
    if not missing:
        return (
            "Не получилось собрать из гардероба образ, который проходит проверку слотов и "
            "погодных ограничений. Попробуйте уточнить запрос или добавить вещи."
        )
    labels = ", ".join(CATEGORY_LABELS_RU[slot] for slot in missing)
    text = f"Пока не могу собрать законченный образ: в гардеробе не хватает — {labels}."
    if "outerwear" in missing and outcome.context.get("temperature_c") is not None:
        text += f" При {outcome.context['temperature_c']:+g}°C без верхней одежды не обойтись."
    elif "outerwear" in missing:
        text += " По погоде нужен верхний слой."
    return text + " Добавьте недостающее — и я подберу комплект."


def _retrieval_payload(outcome: RetrievalOutcome, *, full: bool) -> dict[str, Any]:
    """Диагностика поиска: целиком (панель защиты) или краткая сводка без самих вещей."""
    if full:
        return outcome.diagnostics
    keys = (
        "engine", "mode", "alpha", "visual_weight", "rrf_c", "required_slots", "missing_slots",
        "context", "anchor_item_id", "timings_ms", "wardrobe_revision", "model_fingerprint",
        "score_method",
    )
    summary = {key: outcome.diagnostics[key] for key in keys if key in outcome.diagnostics}
    summary["candidate_ids_by_slot"] = {
        slot: [candidate.item.id for candidate in outcome.candidates_by_slot.get(slot, [])]
        for slot in SLOTS
    }
    return summary


def _sort_items(items: list[WardrobeItem]) -> list[WardrobeItem]:
    order = {category: index for index, category in enumerate(CATEGORY_ORDER)}
    return sorted(items, key=lambda item: order.get(item.category, len(order)))


def _with_image(item: WardrobeItem) -> WardrobeItem:
    """Как и мок на фронте, гарантируем картинку: пустой imageUrl → векторный силуэт категории."""
    if item.image_url and item.image_url.strip():
        return item
    return item.model_copy(update={"image_url": _FALLBACK_SVG[item.category]})


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _ms_since(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _dump(response: RecommendResponse) -> dict[str, Any]:
    return response.model_dump(by_alias=True, exclude_none=True)
