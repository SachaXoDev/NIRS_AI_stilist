"""Оркестрация пайплайна стилиста (схема из `rag/INTEGRATION.md`).

    синхронизация → фильтр повода и погоды → поиск кандидатов → LLM выбирает ID
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
    RecommendContext,
    RecommendRequest,
    RecommendResponse,
    ResponseMeta,
    RuntimeSettings,
    WardrobeItem,
)
from app.services.analysis import (
    analyze_query, is_outfit_query, is_outfit_revision, outfit_revision, small_talk_reply, starts_new_topic,
)
from app.services.editing import (
    NOTHING_TO_EDIT_TEXT, LastCard, OutfitEditor, edit_comment, find_last_card, merge_context, restyle_edit,
)
from app.services.followup import FollowUp, classify_followup, refers_to_dialogue
from app.services.llm.base import LLMClient, LLMError
from app.services.prompts import PromptContext, build_conversation_messages, build_messages, build_repair_messages
from app.services.scoring import MATCH_SCORE_METHOD, match_score
from app.services.streaming import JsonStringFieldExtractor
from app.services.styling import styling_comment
from app.services.suitability import FROST_CRITICAL_SLOTS, frost_gap_text, is_severe_frost, unsuitable_reason
from app.services.validation import (
    MAX_TEXT_CHARS,
    DraftParseError,
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
    # Вещи прошлой карточки, если новый образ — её переработка («потеплее», «наряднее»)
    previous: list[WardrobeItem] | None = None


@dataclass
class _Conversation:
    query: str
    messages: list[dict[str, str]]
    runtime: RuntimeSettings
    started: float
    timings: dict[str, float] = field(default_factory=dict)


@dataclass
class _Generation:
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

    def _detailed_selection(self, query: str) -> bool:
        if self._engine.name != "wardrobe_rag":
            return False
        from wardrobe_rag.query_attributes import is_detailed_selection

        return is_detailed_selection(query)

    def _uses_wardrobe(self, request: RecommendRequest, prior_request: str | None) -> bool:
        context = request.context
        return bool(
            prior_request or request.anchor_item_id or request.query_image or request.mode
            or (context and (context.occasion or context.weather or context.vibe))
            or is_outfit_query(request.query)
            or self._detailed_selection(request.query)
        )

    async def recommend(self, request: RecommendRequest) -> RecommendResponse:
        prior_request = _last_outfit_request(request)
        prepared = await self._prepare(request, prior_request)
        if isinstance(prepared, RecommendResponse):
            return prepared
        if isinstance(prepared, _Conversation):
            return await self._answer_conversation(prepared)
        generation = await self._generate(prepared)
        return self._build_response(prepared, generation)

    async def recommend_stream(self, request: RecommendRequest) -> AsyncIterator[StreamEvent]:
        """Диалог: status → delta* → result. Для подбора добавляется диагностика поиска."""
        prior_request = _last_outfit_request(request)
        if self._uses_wardrobe(request, prior_request):
            yield "status", {"stage": "retrieval"}
        prepared = await self._prepare(request, prior_request)
        if isinstance(prepared, RecommendResponse):
            yield "delta", {"text": prepared.text}
            yield "result", _dump(prepared)
            return

        outfit = isinstance(prepared, _Prepared)
        if outfit:
            yield "retrieval", _retrieval_payload(prepared.ctx.outcome, full=prepared.debug)
        yield "status", {"stage": "generation"}

        raw_parts: list[str] = []
        extractor = JsonStringFieldExtractor("text")
        stream_error: str | None = None
        llm_started = time.perf_counter()
        try:
            async for chunk in self._llm.stream(
                prepared.messages, context=prepared.ctx if outfit else None,
                temperature=prepared.runtime.temperature,
            ):
                raw_parts.append(chunk)
                if not outfit and (delta := extractor.feed(chunk)):
                    prepared.timings.setdefault("llmFirstTextMs", _ms_since(llm_started))
                    yield "delta", {"text": delta}
        except LLMError as exc:
            stream_error = str(exc)
            logger.warning("LLM stream failed: %s", exc)
        prepared.timings["llmMs"] = _ms_since(llm_started)

        if isinstance(prepared, _Conversation):
            response = await self._answer_conversation(
                prepared, raw="".join(raw_parts), failed=stream_error is not None,
            )
            yield "result", _dump(response)
            return

        yield "status", {"stage": "validation"}
        generation = await self._generate(
            prepared, first_raw="".join(raw_parts), first_error=stream_error
        )
        response = self._build_response(prepared, generation)
        yield "delta", {"text": response.text}
        yield "result", _dump(response)

    # --- шаги пайплайна -----------------------------------------------------------

    def _meta(
        self, *, attempts: int = 0, revision: str = "", occasion: str = "", searched: bool = True,
    ) -> ResponseMeta:
        provider, model = self.llm_info
        return ResponseMeta(
            llm_provider=provider,
            llm_model=model,
            llm_attempts=attempts,
            retriever=self._engine.name if searched else None,
            wardrobe_revision=revision,
            occasion=occasion,
            match_score_method=MATCH_SCORE_METHOD if searched else "",
        )

    async def _prepare(
        self, request: RecommendRequest, prior_request: str | None,
    ) -> _Prepared | _Conversation | RecommendResponse:
        started = time.perf_counter()
        runtime = self.get_runtime_settings()
        context = request.context

        # Правка последней карточки или вопрос о ней — отдельная ветка: остальной образ не трогаем.
        card = find_last_card(request.history)
        follow_up = self._follow_up(request, card)
        if isinstance(follow_up, RecommendResponse):
            return follow_up
        if follow_up is not None and follow_up.kind == "restore":
            return await OutfitEditor(self).restore(request, card, started)
        if follow_up is not None and card is not None:
            return await OutfitEditor(self).run(request, follow_up, card, runtime, started)

        if not self._uses_wardrobe(request, prior_request):
            # Самостоятельный вопрос уходит модели без истории: прошлый повод не просочится в ответ.
            history = request.history if refers_to_dialogue(request.query) else []
            return _Conversation(
                query=request.query,
                messages=build_conversation_messages(request.query, history, runtime.persona_prompt),
                runtime=runtime,
                started=started,
            )

        occasion, warmer = outfit_revision(request.query, prior_request)
        if occasion and not (context and context.occasion):
            context = (context or RecommendContext()).model_copy(update={"occasion": occasion})

        timings: dict[str, float] = {}
        warnings: list[str] = []
        user_id, items, exclude = await self.load_wardrobe(request, timings, warnings)

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

        analysis = analyze_query(request.query, context, items)
        if prior_request and card is not None and not starts_new_topic(request.query) and not request.query_image:
            analysis = merge_context(request.model_copy(update={"context": context}), card, items)
        elif prior_request and analysis.temperature_c is None:
            analysis.temperature_c = analyze_query(prior_request).temperature_c
        known_ids = {item.id for item in items}
        anchor = request.anchor_item_id or next(iter(analysis.anchor_item_ids), None)
        if anchor is not None and anchor not in known_ids:
            warnings.append(f"Якорной вещи {anchor} нет в гардеробе — подбор без неё")
            anchor = None
        unsuitable = {item.id: reason for item in items if (reason := unsuitable_reason(item, analysis))}
        if anchor in unsuitable:
            warnings.append(f"Якорная вещь {anchor} не подходит: {unsuitable[anchor]}. Подбор без неё.")
            anchor = None
        if unsuitable:
            warnings.append(f"Исключено вещей по поводу или погоде: {len(unsuitable)}")
            exclude.extend(unsuitable)

        query = RetrievalQuery(
            user_id=user_id,
            query=request.query,
            mode=request.mode or runtime.mode,
            alpha=request.alpha if request.alpha is not None else runtime.alpha,
            visual_weight=(
                request.visual_weight if request.visual_weight is not None else runtime.visual_weight
            ),
            occasion="beach" if analysis.occasion == "beach" else (context.occasion if context else None),
            weather=context.weather if context else None,
            vibe=context.vibe if context else None,
            anchor_item_id=anchor,
            exclude_item_ids=exclude,
            query_image=request.query_image,
            require_outerwear=warmer,
            temperature_c=analysis.temperature_c,
        )
        phase = time.perf_counter()
        try:
            outcome = await asyncio.to_thread(self._engine.retrieve, query)
        except AnchorRejected as exc:
            warnings.append(
                f"Якорная вещь {anchor} не подходит под ограничения запроса (например, по погоде), "
                f"подбор выполнен без неё: {exc}"
            )
            if anchor is not None:
                query.exclude_item_ids.append(anchor)
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
                text=_incomplete_text(missing, outcome, unsuitable_slots={
                    item.category for item in items if item.id in unsuitable
                }),
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
        previous = None
        if prior_request and card is not None:
            current = {item.id: item for item in items}
            # Сравниваем только если прошлый образ целиком есть в текущем гардеробе.
            if all(item_id in current for item_id in card.item_ids):
                previous = [current[item_id] for item_id in card.item_ids]
        return _Prepared(
            ctx=ctx,
            messages=build_messages(ctx, runtime.persona_prompt),
            runtime=runtime,
            debug=request.debug,
            started=started,
            warnings=warnings,
            timings=timings,
            previous=previous,
        )

    def _follow_up(
        self, request: RecommendRequest, card: LastCard | None
    ) -> FollowUp | RecommendResponse | None:
        """Правка/вопрос о последней карточке, готовый ответ «нечего менять» или None — обычный путь."""
        follow_up = classify_followup(request.query)
        if follow_up is not None and follow_up.kind == "restore":
            return follow_up
        if starts_new_topic(request.query) or self._detailed_selection(request.query):
            return None  # «подбери образ…», «с чем носить…» — прошлая карточка ни при чём
        if follow_up is None or card is not None:
            return follow_up
        if any(message.has_outfit for message in request.history):
            return None  # карточка была, но клиент не прислал ID: прежнее поведение без правки по ID
        if follow_up.slot is None:
            return None  # «мне будет комфортно?» без образа — обычный разговор
        return RecommendResponse(
            text=NOTHING_TO_EDIT_TEXT, source="none",
            timings={"totalMs": 0.0}, meta=self._meta(searched=False),
        )

    async def load_wardrobe(
        self, request: RecommendRequest, timings: dict[str, float], warnings: list[str]
    ) -> tuple[str, list[WardrobeItem], list[str]]:
        """Синхронизировать присланный снимок и вернуть (user_id, вещи запроса, исключённые id)."""
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
        return user_id, items, exclude

    async def _answer_conversation(
        self, prepared: _Conversation, *, raw: str | None = None, failed: bool = False,
    ) -> RecommendResponse:
        if raw is None:
            llm_started = time.perf_counter()
            try:
                raw = await self._llm.complete(
                    prepared.messages, context=None, temperature=prepared.runtime.temperature,
                )
            except LLMError as exc:
                logger.warning("Conversation LLM failed: %s", exc)
                failed = True
            prepared.timings["llmMs"] = _ms_since(llm_started)

        text = ""
        if raw and not failed:
            try:
                text = parse_draft(raw).text[:MAX_TEXT_CHARS]
            except DraftParseError:
                logger.warning("Conversation LLM returned an invalid reply")
        source = "mock" if self._llm.provider == "mock" else "llm"
        warnings = []
        if not text:
            source = "fallback"
            warnings.append("Языковая модель не вернула ответ на разговорный запрос")
            text = small_talk_reply(prepared.query) or (
                "Не удалось получить ответ стилиста. Попробуйте отправить вопрос ещё раз."
            )
        return RecommendResponse(
            text=text, source=source, warnings=warnings,
            timings={**prepared.timings, "totalMs": _ms_since(prepared.started)},
            meta=self._meta(attempts=1, searched=False),
        )

    async def _review(
        self, raw: str, ctx: PromptContext
    ) -> tuple[list[WardrobeItem], list[str]]:
        """Разобрать ответ LLM и проверить выбранные id движком поиска."""
        try:
            draft = parse_draft(raw)
        except DraftParseError as exc:
            return [], [str(exc)]
        if draft.outfit is None or not draft.outfit.item_ids:
            return [], ["выбери вещи в outfit.item_ids"]
        check = await asyncio.to_thread(
            self._engine.validate_selection, draft.outfit.item_ids, ctx.outcome
        )
        if check.stale:
            raise RagEngineError(
                "Гардероб изменился, пока стилист подбирал образ. Повторите запрос."
            )
        errors = list(check.violations)
        if check.missing_slots:
            errors.append(
                "в образе не заполнены обязательные слоты: " + ", ".join(check.missing_slots)
            )
        return check.items, errors

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
                items, errors = await self._review(raw, ctx)
                if not errors:
                    source = "mock" if provider == "mock" else "llm"
                    return _Generation(_sort_items(items), attempts, source)
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
        check = await asyncio.to_thread(
            self._engine.validate_selection, [item.id for item in ctx.assembly.items], ctx.outcome,
        )
        if not check.complete:
            raise RagEngineError("Гардероб изменился, пока стилист подбирал образ. Повторите запрос.")
        return _Generation(_sort_items(check.items), attempts, "fallback")

    def _build_response(self, prepared: _Prepared, generation: _Generation) -> RecommendResponse:
        ctx = prepared.ctx
        outcome = ctx.outcome
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

        items = [with_image(item) for item in generation.items]
        edit = restyle_edit(prepared.previous, items) if prepared.previous is not None else None
        text = (edit_comment(prepared.previous, items, edit) if prepared.previous is not None and edit is not None
                else styling_comment(items, ctx.analysis))
        outfit = OutfitLook(
            id=f"outfit-{uuid.uuid4().hex[:12]}",
            title=f"Образ · {ctx.analysis.occasion_label}",
            description=text,
            occasion=ctx.analysis.occasion_label,
            items=items,
            stylist_reasoning="",
            match_score=match_score(generation.items, outcome),
            confidence_tips=[],
        )
        return RecommendResponse(
            text=text,
            suggested_outfit=outfit,
            referenced_item_ids=[item.id for item in items],
            edit=edit,
            **common,
        )


def _last_outfit_request(request: RecommendRequest) -> str | None:
    """Короткую правку связываем только с запросами, для которых была карточка."""
    if not request.history or not is_outfit_revision(request.query):
        return None
    previous = None
    for user, reply in zip(request.history, request.history[1:]):
        if user.sender == "user" and reply.sender == "assistant" and reply.has_outfit:
            if previous is None or is_outfit_query(user.text):
                previous = user.text
    return previous


def _incomplete_text(missing: list[str], outcome: RetrievalOutcome, *, unsuitable_slots: set[str]) -> str:
    if not missing:
        return (
            "Не получилось собрать из гардероба образ, который проходит проверку слотов и "
            "погодных ограничений. Попробуйте уточнить запрос или добавить вещи."
        )
    labels = ", ".join(CATEGORY_LABELS_RU[slot] for slot in missing)
    if set(missing) & set(outcome.diagnostics.get("attribute_blocked_slots", [])):
        return (f"Не могу подтвердить, что вещи в этих категориях подходят под условия запроса: {labels}. "
                "Проверьте характеристики в гардеробе или уточните, какое условие можно смягчить.")
    if set(missing) & unsuitable_slots or outcome.context.get("occasion") == "beach":
        text = f"Не могу собрать подходящий образ для этого повода и погоды. Не хватает подходящих вещей: {labels}."
    else:
        text = f"Пока не могу собрать законченный образ: в гардеробе не хватает — {labels}."
    temperature = outcome.context.get("temperature_c")
    frost_slots = set(missing) & FROST_CRITICAL_SLOTS
    if frost_slots and temperature is not None and is_severe_frost(temperature):
        return f"{frost_gap_text(temperature, frost_slots)} Для улицы я бы не заменял их демисезонными вещами."
    if "outerwear" in missing and temperature is not None:
        text += f" При {temperature:+g}°C без верхней одежды не обойтись."
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


def with_image(item: WardrobeItem) -> WardrobeItem:
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
