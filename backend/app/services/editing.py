"""Точечная правка последнего образа и ответы на вопросы о нём.

Правка работает по ID вещей из карточки, которые фронтенд присылает в истории: состав не
восстанавливается по названиям в тексте. Незатронутые вещи сохраняются как есть, меняется
ровно одна. Перед показом комплект сверяется с текущим гардеробом. Если подходящей вещи нет
или вещь из прошлого образа уже удалена, пользователь получает объяснение, а не молча
изменённую карточку.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from app.rag.base import (
    CORE_SLOTS,
    SLOT_LIMITS,
    RagEngineError,
    RetrievalOutcome,
    SelectionCheck,
    SlotCandidate,
    SlotOutcome,
    SlotQuery,
    composition_errors,
)
from app.schemas import (
    CATEGORY_LABELS_RU,
    CATEGORY_ORDER,
    HistoryMessage,
    OutfitEdit,
    OutfitLook,
    RecommendRequest,
    RecommendResponse,
    RuntimeSettings,
    WardrobeItem,
)
from app.services.analysis import (
    COLD_MAX_C,
    DEFAULT_OCCASION,
    HOT_MIN_C,
    QueryAnalysis,
    analyze_query,
    is_outfit_revision,
    names_occasion,
)
from app.services.followup import FollowUp, classify_followup
from app.services.llm.base import LLMError
from app.services.prompts import (
    PromptContext,
    build_card_question_messages,
    build_repair_messages,
    build_slot_messages,
)
from app.services.scoring import match_score
from app.services.suitability import (
    FROST_CRITICAL_SLOTS, frost_gap_text, is_insulated_outerwear_or_shoes, is_severe_frost,
    is_shorts, unsuitable_reason,
)
from app.services.textutils import normalize
from app.services.validation import MAX_TEXT_CHARS, DraftParseError, parse_draft

if TYPE_CHECKING:  # только для подсказок типов: циклического импорта во время работы нет
    from app.services.orchestrator import StylistService

logger = logging.getLogger(__name__)

_SLOT_ACC = {"tops": "верх", "bottoms": "низ", "shoes": "обувь", "outerwear": "верхнюю одежду",
             "accessories": "аксессуар"}
_SLOT_GEN = {"tops": "верха", "bottoms": "низа", "shoes": "обуви", "outerwear": "верхней одежды",
             "accessories": "аксессуара"}
# Название категории («аксессуар», «обувь») не указывает на конкретную вещь из двух.
_GENERIC_MENTIONS = frozenset({"аксе", "обув", "верх", "низ", "низа", "низу", "слой", "слоя"})
_FLAT_WORDS = ("без каблук", "плоск", "на плоском ходу")
_LONG_BOTTOM_RE = re.compile(r"\b(?:брюк\w*|джинс\w*|штан\w*|чинос\w*|леггинс\w*|легинс\w*)\b")
_THERMAL_QUESTION = re.compile(r"\b(?:жарко|холодно|прохладно|тепло|замерз\w*|вспотею)\b")
_FIT_QUESTION = re.compile(r"\b(?:комфорт\w*|удобн\w*)\b")
NOTHING_TO_EDIT_TEXT = (
    "Пока нечего менять: сначала попросите собрать образ — например, «Подбери образ в офис», — "
    "а потом скажите, что в нём заменить, добавить или убрать."
)


@dataclass(frozen=True)
class LastCard:
    item_ids: list[str]
    root_request: str | None  # запрос, с которого начался этот образ: его повод и погода
    index: int
    followups: tuple[str, ...] = ()


def find_last_card(history: list[HistoryMessage], *, before: int | None = None) -> LastCard | None:
    """Последняя карточка до указанной позиции и запросы, которые её уточняли."""
    stop = len(history) if before is None else before
    index = next((i for i in range(stop - 1, -1, -1)
                  if history[i].sender == "assistant" and history[i].item_ids), None)
    if index is None:
        return None
    root = None
    followups: list[str] = []
    for message in reversed(history[index + 1:stop]):
        follow_up = classify_followup(message.text) if message.sender == "user" else None
        if follow_up is not None and follow_up.kind == "cold_feedback":
            followups.append(message.text)
    for message in reversed(history[:index]):
        if message.sender != "user":
            continue
        follow_up = classify_followup(message.text)
        if follow_up is None and not is_outfit_revision(message.text):
            root = message.text
            break
        if follow_up is None or follow_up.kind not in {"card_question", "restore"}:
            followups.append(message.text)
    return LastCard(list(dict.fromkeys(history[index].item_ids)), root, index, tuple(reversed(followups)))


def merge_context(
    request: RecommendRequest, card: LastCard, items: list[WardrobeItem]
) -> QueryAnalysis:
    """Повод и погода прошлого образа, если в новой реплике они не названы заново."""
    current = analyze_query(request.query, request.context, items)
    prior = analyze_query(card.root_request or "")
    for query in card.followups:
        prior = _merge_weather(prior, analyze_query(query))
    explicit_occasion = names_occasion(request.query) or bool(request.context and request.context.occasion)
    current = _merge_weather(prior, current)
    return replace(
        current,
        occasion=current.occasion if explicit_occasion else prior.occasion,
        occasion_label=current.occasion_label if explicit_occasion else prior.occasion_label,
    )


def _merge_weather(prior: QueryAnalysis, current: QueryAnalysis) -> QueryAnalysis:
    if current.temperature_c is not None:
        return current
    temperature = prior.temperature_c
    weather = list(dict.fromkeys([*prior.weather, *current.weather]))
    if current.is_cold:
        weather = [flag for flag in weather if flag != "heat"]
        if temperature is not None and temperature > COLD_MAX_C:
            temperature = None  # актуальное «холодно» важнее старого тёплого прогноза
    elif current.is_hot:
        weather = [flag for flag in weather if flag not in {"cold", "snow"}]
        if temperature is not None and temperature < HOT_MIN_C:
            temperature = None
    return replace(current, temperature_c=temperature, weather=weather)


_DRESSY_OCCASIONS = frozenset({"business", "evening"})


def _is_beach_item(item: WardrobeItem) -> bool:
    labels = [normalize(value).strip() for value in (item.title, *item.tags, *item.style)]
    return any("пляж" in label or label == "beach" for label in labels)


def quote(item: WardrobeItem) -> str:
    return f"«{item.title}»"


def sort_items(items: list[WardrobeItem]) -> list[WardrobeItem]:
    order = {category: index for index, category in enumerate(CATEGORY_ORDER)}
    return sorted(items, key=lambda item: order.get(item.category, len(order)))


def _listing(items: list[WardrobeItem]) -> str:
    return "; ".join(quote(item) for item in sort_items(items))


def restyle_edit(before: list[WardrobeItem], after: list[WardrobeItem]) -> OutfitEdit:
    """Сохраняет машинное описание правки, не дублируя карточку в чате."""
    old, new = {item.id: item for item in before}, {item.id: item for item in after}
    kept = [item for item in after if item.id in old]
    return OutfitEdit(
        operation="restyle",
        base_item_ids=[item.id for item in before],
        kept_item_ids=[item.id for item in kept],
        added_item_ids=[item.id for item in after if item.id not in old],
        removed_item_ids=[item.id for item in before if item.id not in new],
    )


def _named(items: list[WardrobeItem], mention: str | None) -> WardrobeItem | None:
    """Одна вещь из нескольких в слоте — та, которую пользователь назвал словом («сумку»)."""
    if len(items) == 1:
        return items[0]
    if mention and mention not in _GENERIC_MENTIONS:
        matched = [
            item for item in items
            if mention in normalize(" ".join([item.title, *item.tags]))
        ]
        if len(matched) == 1:
            return matched[0]
    return None


class OutfitEditor:
    def __init__(self, service: "StylistService") -> None:
        self._service = service
        self._engine = service._engine
        self._llm = service._llm
        self._settings = service._settings

    # --- вход ---------------------------------------------------------------------

    async def run(
        self,
        request: RecommendRequest,
        follow_up: FollowUp,
        card: LastCard,
        runtime: RuntimeSettings,
        started: float,
    ) -> RecommendResponse:
        timings: dict[str, float] = {}
        warnings: list[str] = []
        user_id, items, _ = await self._service.load_wardrobe(request, timings, warnings)
        by_id = {item.id: item for item in items}
        base = [by_id[item_id] for item_id in card.item_ids if item_id in by_id]
        analysis = merge_context(request, card, items)
        reply = _Reply(self._service, analysis, timings, warnings, started)

        gone = [item_id for item_id in card.item_ids if item_id not in by_id]
        if gone:
            warnings.append("ID вещей прошлого образа, которых нет в гардеробе: " + ", ".join(gone))
            left = f" Остались: {_listing(base)}." if base else ""
            return reply.text(
                f"Не могу изменить прошлый образ: {_count(len(gone))} из него уже нет в вашем гардеробе."
                f"{left} Попросите собрать образ заново — подберу из актуальных вещей."
            )
        if follow_up.kind == "card_question":
            return await self._answer_question(request, base, analysis, runtime, reply)
        if follow_up.kind == "cold_feedback":
            if not any(is_shorts(item) for item in base):
                return reply.text("Какая часть образа кажется слишком лёгкой? Могу заменить её, не меняя остальное.")
            follow_up = FollowUp(kind="replace", slot="bottoms", mention="шорт", operation="replace")
        if follow_up.kind == "ask_item" or follow_up.slot is None:
            return reply.text(_ask_which_item(follow_up.operation, base))

        slot = follow_up.slot
        in_slot = [item for item in base if item.category == slot]
        if follow_up.kind == "remove":
            return self._remove(base, slot, in_slot, follow_up, reply)
        return await self._add_or_replace(
            request, user_id, items, base, slot, in_slot, follow_up, analysis, runtime, reply
        )

    async def restore(self, request: RecommendRequest, card: LastCard | None, started: float) -> RecommendResponse:
        previous = find_last_card(request.history, before=card.index) if card else None
        timings: dict[str, float] = {}
        warnings: list[str] = []
        if previous is None or card is None:
            reply = _Reply(self._service, analyze_query(request.query), timings, warnings, started)
            return reply.text("В этом диалоге ещё нет предыдущего образа, который можно вернуть.")

        _, wardrobe, _ = await self._service.load_wardrobe(request, timings, warnings)
        by_id = {item.id: item for item in wardrobe}
        reply = _Reply(self._service, merge_context(request, previous, wardrobe), timings, warnings, started)
        if any(item_id not in by_id for item_id in previous.item_ids):
            return reply.text("Не могу вернуть предыдущий образ целиком: в гардеробе уже нет части его вещей.")

        from app.services.orchestrator import with_image

        items = [with_image(by_id[item_id]) for item_id in previous.item_ids]
        text = "Вернула предыдущий образ из этого диалога. Состав тот же."
        weather = replace(merge_context(request, card, wardrobe), occasion=DEFAULT_OCCASION)
        if any(unsuitable_reason(item, weather) for item in items):
            text += " По текущей погоде не все вещи в нём подходят."
        label = reply.analysis.occasion_label
        return RecommendResponse(
            text=text, referenced_item_ids=previous.item_ids,
            suggested_outfit=OutfitLook(
                id=f"outfit-{uuid.uuid4().hex[:12]}", title=f"Образ · {label}", description=text,
                occasion=label, items=items, stylist_reasoning="", match_score=0, confidence_tips=[],
            ),  # История передаёт состав, но не оценку поисковой выдачи.
            **reply._common("rules", 0, ""),
        )

    # --- убрать -------------------------------------------------------------------

    def _remove(
        self, base: list[WardrobeItem], slot: str, in_slot: list[WardrobeItem],
        follow_up: FollowUp, reply: "_Reply",
    ) -> RecommendResponse:
        if not in_slot:
            return reply.text(
                f"В этом образе нет {_SLOT_GEN[slot]} — убирать нечего. Образ остаётся прежним: {_listing(base)}."
            )
        target = _named(in_slot, follow_up.mention)
        if target is None:
            return reply.text(f"В образе несколько вещей этой категории: {_listing(in_slot)}. Какую убрать?")
        if slot in CORE_SLOTS:
            # Неполный комплект не выдаём за готовый образ.
            return reply.text(
                f"Если убрать {quote(target)}, образ останется без {_SLOT_GEN[slot]}, а это обязательная "
                "часть комплекта. Подобрать замену из вашего гардероба?",
                missing_slots=[slot],
            )
        kept = [item for item in base if item.id != target.id]
        return reply.card(
            kept, source="rules", attempts=0, revision="",
            edit=OutfitEdit(
                operation="remove", slot=slot, base_item_ids=[item.id for item in base],
                kept_item_ids=[item.id for item in kept], removed_item_ids=[target.id],
            ),
            ranked=None, before=base,
        )

    # --- добавить или заменить ----------------------------------------------------

    async def _add_or_replace(
        self,
        request: RecommendRequest,
        user_id: str,
        items: list[WardrobeItem],
        base: list[WardrobeItem],
        slot: str,
        in_slot: list[WardrobeItem],
        follow_up: FollowUp,
        analysis: QueryAnalysis,
        runtime: RuntimeSettings,
        reply: "_Reply",
    ) -> RecommendResponse:
        operation = follow_up.kind
        target: WardrobeItem | None = None
        if operation == "add" and len(in_slot) >= SLOT_LIMITS[slot]:
            if slot == "accessories":
                return reply.text(
                    f"В образе уже два аксессуара: {_listing(in_slot)}. Какой из них заменить?"
                )
            operation, target = "replace", in_slot[0]
        elif operation == "replace":
            if not in_slot:
                operation = "add"
            else:
                target = _named(in_slot, follow_up.mention)
                if target is None:
                    return reply.text(
                        f"В образе несколько вещей этой категории: {_listing(in_slot)}. Какую заменить?"
                    )

        # Погодные ограничения вещей действуют и при правке. Белый список «только пляжное»
        # здесь не применяем: пользователь сам попросил конкретную вещь.
        weather_only = replace(analysis, occasion=DEFAULT_OCCASION)
        unsuitable = [item.id for item in items if unsuitable_reason(item, weather_only)]
        if slot == "bottoms" and not analysis.is_hot:
            if analysis.is_cold and target is not None and is_shorts(target):
                unsuitable.extend(item.id for item in items if item.category == slot and not any(
                    _LONG_BOTTOM_RE.search(normalize(label)) for label in (item.title, *item.tags)
                ))
            elif any(is_insulated_outerwear_or_shoes(item) for item in base):
                unsuitable.extend(item.id for item in items if is_shorts(item))
        if analysis.occasion in _DRESSY_OCCASIONS:
            # Пляжные сандалии формально «без каблука», но в офисный или вечерний образ не годятся.
            unsuitable += [item.id for item in items if _is_beach_item(item) and item.id not in unsuitable]
        base_ids = [item.id for item in base]
        query = SlotQuery(
            user_id=user_id,
            query=request.query,
            slot=slot,
            operation=operation,
            outfit_item_ids=base_ids,
            replace_item_id=target.id if target else None,
            mode=request.mode or runtime.mode,
            alpha=request.alpha if request.alpha is not None else runtime.alpha,
            visual_weight=(
                request.visual_weight if request.visual_weight is not None else runtime.visual_weight
            ),
            occasion=analysis.occasion_label,
            vibe=analysis.vibe,
            temperature_c=analysis.temperature_c,
            rain=True if "rain" in analysis.weather else None,
            wind=True if "wind" in analysis.weather else None,
            exclude_item_ids=list(dict.fromkeys(item_id for item_id in unsuitable if item_id not in base_ids)),
        )
        phase = time.perf_counter()
        outcome = await asyncio.to_thread(self._engine.retrieve_slot, query)
        reply.timings["retrievalMs"] = _ms_since(phase)
        reply.warnings.extend(outcome.warnings)
        reply.retrieval = outcome.diagnostics if request.debug else None

        if not outcome.candidates:
            # Альтернативы нет — прежний комплект остаётся, новой карточки не будет.
            temperature = analysis.temperature_c
            if slot in FROST_CRITICAL_SLOTS and temperature is not None and is_severe_frost(temperature):
                return reply.text(frost_gap_text(temperature, {slot}), revision=outcome.revision)
            if slot == "bottoms" and target is not None and is_shorts(target) and analysis.is_cold:
                return reply.text(
                    "Шорты для холода не подойдут, а подходящей замены из гардероба я не нашла. "
                    "Остальные вещи можно оставить. Есть брюки или джинсы, которых пока нет в гардеробе?",
                    revision=outcome.revision,
                )
            return reply.text(_no_alternative_text(request.query, operation, slot, target), revision=outcome.revision)

        chosen, source, attempts = await self._pick(
            request.query, analysis, outcome, base, target, operation, runtime, reply
        )
        kept = [item for item in base if target is None or item.id != target.id]
        final = [*kept, chosen.item]
        problems = composition_errors(final)
        if problems:
            reply.warnings.extend(problems)
            return reply.text(
                "Не получилось собрать корректный комплект после правки, поэтому прежний образ "
                f"оставляю без изменений: {_listing(base)}.",
                revision=outcome.revision,
            )
        if await asyncio.to_thread(self._engine.get_revision, user_id) != outcome.revision:
            raise RagEngineError("Гардероб изменился, пока стилист подбирал вещь. Повторите запрос.")

        return reply.card(
            final, source=source, attempts=attempts, revision=outcome.revision,
            edit=OutfitEdit(
                operation=operation, slot=slot, base_item_ids=base_ids,  # type: ignore[arg-type]
                kept_item_ids=[item.id for item in kept], added_item_ids=[chosen.item.id],
                removed_item_ids=[target.id] if target else [],
            ),
            ranked=outcome, before=base,
        )

    async def _pick(
        self,
        query: str,
        analysis: QueryAnalysis,
        outcome: SlotOutcome,
        base: list[WardrobeItem],
        target: WardrobeItem | None,
        operation: str,
        runtime: RuntimeSettings,
        reply: "_Reply",
    ) -> tuple[SlotCandidate, str, int]:
        """Выбрать одну вещь из кандидатов поиска: LLM, при сбое — первый по релевантности."""
        candidates = outcome.candidates
        if len(candidates) == 1:
            return candidates[0], "rules", 0  # выбирать не из чего: модель не нужна

        by_id = {candidate.item.id: candidate for candidate in candidates}
        ctx = PromptContext(
            query=query,
            analysis=analysis,
            outcome=_slot_as_outcome(outcome, self._engine.name),
            assembly=SelectionCheck(valid=True, complete=True, items=[candidates[0].item]),
        )
        kept = [item for item in base if target is None or item.id != target.id]
        task = (
            f"добавить {_SLOT_ACC[outcome.slot]}"
            if operation == "add"
            else f"заменить {quote(target)} ({CATEGORY_LABELS_RU[outcome.slot]}) другой вещью"  # type: ignore[arg-type]
        )
        first = messages = build_slot_messages(ctx, kept, task, runtime.persona_prompt)
        attempts = 0
        llm_started = time.perf_counter()
        try:
            while attempts < 1 + self._settings.llm_max_repairs:
                attempts += 1
                try:
                    raw = await self._llm.complete(messages, context=ctx, temperature=runtime.temperature)
                except LLMError as exc:
                    logger.warning("LLM call failed during outfit edit: %s", exc)
                    reply.warnings.append("LLM недоступна — вещь выбрана по релевантности поиска, без модели")
                    return candidates[0], "fallback", attempts
                try:
                    ids = (parse_draft(raw).outfit or _NO_OUTFIT).item_ids
                    error = None if len(ids) == 1 and ids[0] in by_id else (
                        "нужен ровно один id из списка допустимых: " + ", ".join(by_id)
                    )
                except DraftParseError as exc:
                    ids, error = [], str(exc)
                if error is None:
                    return by_id[ids[0]], "mock" if self._llm.provider == "mock" else "llm", attempts
                logger.info("LLM slot pick rejected (attempt %d): %s", attempts, error)
                messages = build_repair_messages(first, raw, [error])
        finally:
            reply.timings["llmMs"] = _ms_since(llm_started)
        reply.warnings.append("Ответ LLM не прошёл проверку — вещь выбрана по релевантности поиска, без модели")
        return candidates[0], "fallback", attempts

    # --- вопрос об образе -----------------------------------------------------------

    async def _answer_question(
        self,
        request: RecommendRequest,
        base: list[WardrobeItem],
        analysis: QueryAnalysis,
        runtime: RuntimeSettings,
        reply: "_Reply",
    ) -> RecommendResponse:
        """Ответ про вещи последней карточки. Карточка не меняется; чего не знаем — говорим прямо."""
        query = normalize(request.query)
        thermal = bool(_THERMAL_QUESTION.search(query))
        if thermal or _FIT_QUESTION.search(query):
            return reply.text(_comfort_answer(base, analysis, thermal=thermal), source="rules")

        notes, unknown = _card_facts(base, analysis)
        text, source, attempts = "", "fallback", 0
        if self._llm.provider != "mock":
            attempts = 1
            messages = build_card_question_messages(
                request.query, base, _context_summary(analysis), notes, unknown, runtime.persona_prompt
            )
            llm_started = time.perf_counter()
            try:
                raw = await self._llm.complete(messages, context=None, temperature=runtime.temperature)
                text = parse_draft(raw).text[:MAX_TEXT_CHARS]
                source = "llm"
            except (LLMError, DraftParseError) as exc:
                logger.warning("Card question LLM failed: %s", exc)
                reply.warnings.append("Языковая модель не ответила — ответ собран из данных о вещах")
            reply.timings["llmMs"] = _ms_since(llm_started)
        else:
            source = "mock"
        if not text:
            text = "Сужу только по данным о вещах образа: " + "; ".join(_item_fact(item) for item in base) + "."
        # Эти две фразы сервер добавляет сам: модель не может «забыть» про ограничения и пробелы.
        if notes:
            text += " По данным вещей: " + "; ".join(notes) + "."
        if unknown:
            text += " Чего я не знаю: " + "; ".join(unknown) + ". Поэтому обещать, что будет комфортно, не могу."
        return reply.text(text, source=source, attempts=attempts)


_NO_OUTFIT = type("_NoOutfit", (), {"item_ids": []})()


class _Reply:
    """Сборка ответа правки: общие тайминги, предупреждения и метаданные."""

    def __init__(
        self, service: "StylistService", analysis: QueryAnalysis,
        timings: dict[str, float], warnings: list[str], started: float,
    ) -> None:
        self._service = service
        self.analysis = analysis
        self.timings = timings
        self.warnings = warnings
        self._started = started
        self.retrieval: dict[str, Any] | None = None

    def _common(self, source: str, attempts: int, revision: str) -> dict[str, Any]:
        self.timings["totalMs"] = _ms_since(self._started)
        return {
            "source": source,
            "warnings": list(dict.fromkeys(self.warnings)),
            "timings": {key: round(value, 1) for key, value in self.timings.items()},
            "meta": self._service._meta(
                attempts=attempts, revision=revision, occasion=self.analysis.occasion_label,
                searched="retrievalMs" in self.timings,
            ),
            "retrieval": self.retrieval,
        }

    def text(
        self, text: str, *, source: str = "none", attempts: int = 0, revision: str = "",
        missing_slots: list[str] | None = None,
    ) -> RecommendResponse:
        return RecommendResponse(
            text=text, missing_slots=missing_slots or [], **self._common(source, attempts, revision)
        )

    def card(
        self, items: list[WardrobeItem], *, source: str,
        attempts: int, revision: str, edit: OutfitEdit, ranked: SlotOutcome | None,
        before: list[WardrobeItem],
    ) -> RecommendResponse:
        from app.services.orchestrator import with_image  # общий помощник карточек

        items = [with_image(item) for item in sort_items(items)]
        temperature = self.analysis.temperature_c
        if temperature is not None and is_severe_frost(temperature):
            weather_only = replace(self.analysis, occasion=DEFAULT_OCCASION)
            gaps = {slot for slot in FROST_CRITICAL_SLOTS if not any(
                item.category == slot and not unsuitable_reason(item, weather_only) for item in items
            )}
            if gaps:
                return self.text(f"{frost_gap_text(temperature, gaps)} Лучше собрать образ заново.",
                                 revision=revision, missing_slots=sorted(gaps))
        text = edit_comment(before, items, edit)
        outfit = OutfitLook(
            id=f"outfit-{uuid.uuid4().hex[:12]}",
            title=f"Образ · {self.analysis.occasion_label}",
            description=text,
            occasion=self.analysis.occasion_label,
            items=items,
            stylist_reasoning="",
            match_score=match_score(items, _edited_as_outcome(items, edit, ranked)),
            confidence_tips=[],
        )
        return RecommendResponse(
            text=text, suggested_outfit=outfit, referenced_item_ids=[item.id for item in items],
            edit=edit, **self._common(source, attempts, revision),
        )


# --- тексты и факты -----------------------------------------------------------------

def edit_comment(before: list[WardrobeItem], after: list[WardrobeItem], edit: OutfitEdit) -> str:
    added = [item for item in after if item.id in edit.added_item_ids]
    removed = [item for item in before if item.id in edit.removed_item_ids]
    if edit.operation == "replace" and removed and added:
        return f"Вместо {quote(removed[0])} — {quote(added[0])}. Остальные вещи оставила."
    if edit.operation == "add" and added:
        return f"Добавила {quote(added[0])}. Остальные вещи оставила."
    if edit.operation == "remove" and removed:
        return f"Убрала {quote(removed[0])}. Остальные вещи оставила."
    changes = []
    if removed:
        changes.append(f"Убрала: {_listing(removed)}.")
    if added:
        changes.append(f"Добавила: {_listing(added)}.")
    if changes and edit.kept_item_ids:
        changes.append(f"Оставила: {_listing([item for item in after if item.id in edit.kept_item_ids])}.")
    return " ".join(changes) or "Другой подходящий комплект не получился: состав остался прежним."


def _count(n: int) -> str:
    return "одной вещи" if n == 1 else f"{n} вещей"


def _ask_which_item(operation: str | None, base: list[WardrobeItem]) -> str:
    verb = {"replace": "заменить", "remove": "убрать"}.get(operation or "")
    if verb is None:
        return "Что добавить к образу: верхнюю одежду или аксессуар?"
    options = ", ".join(f"{quote(item)} ({CATEGORY_LABELS_RU[item.category]})" for item in sort_items(base))
    return f"Уточните, какую вещь {verb}: {options}?"


def _no_alternative_text(
    query: str, operation: str, slot: str, target: WardrobeItem | None
) -> str:
    wants_flat = slot == "shoes" and any(word in normalize(query) for word in _FLAT_WORDS)
    if wants_flat:
        reason = "в гардеробе нет другой пары с пометкой «без каблука» или «плоская подошва»"
    else:
        reason = f"в гардеробе нет другой подходящей вещи в категории «{CATEGORY_LABELS_RU[slot]}»"
    if operation == "replace" and target is not None:
        lead = f"Заменить {quote(target)} нечем: {reason}."
    else:
        lead = f"Добавить {_SLOT_ACC[slot]} не получится: {reason}."
    return f"{lead} Прежний образ оставляю без изменений."


def _comfort_answer(items: list[WardrobeItem], analysis: QueryAnalysis, *, thermal: bool) -> str:
    """Use the facts that change the advice, not an inventory of missing fields."""
    temperature = analysis.temperature_c
    # A question like «Не жарко будет?» is not itself a measurement or a forecast.
    if not thermal or temperature is not None:
        weather_only = replace(analysis, occasion=DEFAULT_OCCASION)
        for item in items:
            reason = unsuitable_reason(item, weather_only)
            if reason is None:
                continue
            limits = item.weather
            if temperature is not None and limits is not None:
                if limits.temperature_max is not None and temperature > limits.temperature_max:
                    return (f"Для {temperature:+d} °C я бы не выбирала {quote(item)}: "
                            f"для этой вещи указано не выше {limits.temperature_max:+g} °C.")
                if limits.temperature_min is not None and temperature < limits.temperature_min:
                    return (f"Для {temperature:+d} °C я бы не выбирала {quote(item)}: "
                            f"для этой вещи указано не ниже {limits.temperature_min:+g} °C.")
            return f"В этом образе стоит обратить внимание на {quote(item)}: {reason}."

    if thermal:
        if temperature is None:
            return "По одному составу образа не скажу, будет ли жарко или холодно. Какая температура ожидается?"
        layers = [item for item in items if item.category != "accessories"]
        fully_rated = layers and all(
            item.weather is not None and item.weather.temperature_min is not None
            and item.weather.temperature_max is not None for item in layers
        )
        if fully_rated:
            return (f"{temperature:+d} °C попадает в указанные диапазоны вещей. "
                    "Если предстоит долго быть на улице, учитывайте ещё ветер и осадки.")
        return (f"Для {temperature:+d} °C не у всех вещей указаны температурные пределы. "
                "Если будете долго на улице, лучше выбрать вещи с указанным диапазоном.")

    for item in items:
        if item.category != "shoes":
            continue
        labels = normalize(" ".join((item.title, *item.tags)))
        if any(marker in labels for marker in ("без каблук", "плоская подошва", "на плоском ходу")):
            return (f"У {quote(item)} указана плоская подошва или отсутствие каблука. "
                    "Перед выходом пройдитесь в этой паре: пальцам должно хватать места, а пятка не должна выскальзывать.")
        if "каблук" in labels:
            return (f"Я бы в первую очередь проверила обувь: {quote(item)} — пара на каблуке. "
                    "Если предстоит много ходить или стоять, примерьте её заранее: важно, чтобы обувь не давила и не натирала.")
    return ("Чтобы оценить удобство, попробуйте сесть и пройтись в этом комплекте: "
            "одежда не должна стеснять движения, а обувь — давить. Вам предстоит много ходить или в основном сидеть?")


def _context_summary(analysis: QueryAnalysis) -> str:
    return f"повод — {analysis.occasion_label}; погода — {analysis.weather_summary()}"


def _item_fact(item: WardrobeItem) -> str:
    details = [d for d in (item.material, {"spring/summer": "весна–лето", "autumn/winter": "осень–зима"}.get(item.season)) if d]
    return quote(item) + (" — " + ", ".join(details) if details else "")


def _card_facts(items: list[WardrobeItem], analysis: QueryAnalysis) -> tuple[list[str], list[str]]:
    """Твёрдые замечания по разметке вещей и список того, чего сервер не знает."""
    notes: list[str] = []
    temperature = analysis.temperature_c
    for item in items:
        if reason := unsuitable_reason(item, replace(analysis, occasion=DEFAULT_OCCASION)):
            notes.append(f"{quote(item)} — {reason}")
    unknown: list[str] = []
    if temperature is None and not analysis.weather:
        unknown.append("температуру и погоду, для которых нужен образ")
    unknown.append("посадку и размер вещей")
    no_material = [item for item in items if not (item.material or "").strip()]
    if no_material:
        unknown.append("материал: " + ", ".join(map(quote, no_material)))
    unrated = [
        item for item in items
        if item.category != "accessories"
        and (item.weather is None or (item.weather.temperature_min is None and item.weather.temperature_max is None))
    ]
    if unrated:
        unknown.append(f"на какую температуру рассчитаны {len(unrated)} из {len(items)} вещей (в данных нет диапазона)")
    return notes, unknown


# --- совместимость с кодом подбора ---------------------------------------------------


def _slot_as_outcome(outcome: SlotOutcome, engine: str) -> RetrievalOutcome:
    """Выдача одного слота в форме обычной выдачи — для схемы ответа LLM и mock-провайдера."""
    return RetrievalOutcome(
        user_id="", query="", engine=engine, mode="",
        candidates_by_slot={outcome.slot: outcome.candidates},
        required_slots=[outcome.slot], missing_slots=[], context=outcome.context,
        anchor_item_id=None, warnings=[], timings_ms={}, revision=outcome.revision, diagnostics={},
    )


def _edited_as_outcome(
    items: list[WardrobeItem], edit: OutfitEdit, ranked: SlotOutcome | None
) -> RetrievalOutcome:
    """Для matchScore: оставленные вещи выбрал пользователь, новая вещь оценивается по её выдаче."""
    by_slot: dict[str, list[SlotCandidate]] = {}
    for item in items:
        if item.id in edit.kept_item_ids:
            by_slot.setdefault(item.category, []).append(SlotCandidate(item=item, score=1.0, anchored=True))
    if ranked is not None:
        by_slot.setdefault(ranked.slot, []).extend(ranked.candidates)
    return RetrievalOutcome(
        user_id="", query="", engine="", mode="", candidates_by_slot=by_slot,
        required_slots=list(CORE_SLOTS), missing_slots=[], context={}, anchor_item_id=None,
        warnings=[], timings_ms={}, revision="", diagnostics={},
    )


def _ms_since(started: float) -> float:
    return (time.perf_counter() - started) * 1000
