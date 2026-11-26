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
    COOL_MAX_C,
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
from app.services.suitability import unsuitable_reason
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
NOTHING_TO_EDIT_TEXT = (
    "Пока нечего менять: сначала попросите собрать образ — например, «Подбери образ в офис», — "
    "а потом скажите, что в нём заменить, добавить или убрать."
)


@dataclass(frozen=True)
class LastCard:
    item_ids: list[str]
    root_request: str | None  # запрос, с которого начался этот образ: его повод и погода


def find_last_card(history: list[HistoryMessage]) -> LastCard | None:
    """Последняя карточка в диалоге, для которой фронтенд прислал ID вещей."""
    index = next(
        (i for i in range(len(history) - 1, -1, -1)
         if history[i].sender == "assistant" and history[i].item_ids),
        None,
    )
    if index is None:
        return None
    root = None
    for position in range(index - 1, -1, -1):
        message = history[position]
        if message.sender != "user":
            continue
        # Правки и «потеплее» продолжают прошлый образ; его повод задан более ранним запросом.
        if classify_followup(message.text) is None and not is_outfit_revision(message.text):
            root = message.text
            break
    return LastCard(item_ids=list(dict.fromkeys(history[index].item_ids)), root_request=root)


def merge_context(
    request: RecommendRequest, root_request: str | None, items: list[WardrobeItem]
) -> QueryAnalysis:
    """Повод и погода прошлого образа, если в новой реплике они не названы заново."""
    current = analyze_query(request.query, request.context, items)
    if not root_request:
        return current
    prior = analyze_query(root_request, None, [])
    explicit_occasion = names_occasion(request.query) or bool(request.context and request.context.occasion)
    # Погода из новой реплики важнее прошлой; чего в реплике нет — берём из запроса образа.
    if current.temperature_c is not None:
        temperature, weather = current.temperature_c, current.weather
    else:
        temperature = prior.temperature_c
        weather = list(dict.fromkeys([*prior.weather, *current.weather]))
        if temperature is not None:
            conflicting = ("cold", "snow") if temperature >= HOT_MIN_C else ("heat",) if temperature <= COOL_MAX_C else ()
            weather = [flag for flag in weather if flag not in conflicting]
    return replace(
        current,
        occasion=current.occasion if explicit_occasion else prior.occasion,
        occasion_label=current.occasion_label if explicit_occasion else prior.occasion_label,
        weather=weather,
        temperature_c=temperature,
    )


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


def describe_changes(before: list[WardrobeItem], after: list[WardrobeItem]) -> tuple[str, OutfitEdit]:
    """Что изменилось между двумя образами — словами и в виде проверяемой структуры."""
    old, new = {item.id: item for item in before}, {item.id: item for item in after}
    kept = [item for item in after if item.id in old]
    parts: list[str] = []
    for slot in CATEGORY_ORDER:
        removed = [item for item in before if item.category == slot and item.id not in new]
        added = [item for item in after if item.category == slot and item.id not in old]
        label = CATEGORY_LABELS_RU[slot]
        if removed and added:
            parts.append(f"{label}: " + ", ".join(map(quote, removed)) + " → " + ", ".join(map(quote, added)))
        elif added:
            parts.append(f"{label} — добавлено: " + ", ".join(map(quote, added)))
        elif removed:
            parts.append(f"{label} — убрано: " + ", ".join(map(quote, removed)))
    if not parts:
        text = "Состав тот же, что и в прошлом образе: более подходящих вещей в гардеробе не нашлось."
    else:
        text = "Что изменилось по сравнению с прошлым образом: " + "; ".join(parts) + "."
        if kept:
            text += " Без изменений: " + _listing(kept) + "."
    edit = OutfitEdit(
        operation="restyle",
        base_item_ids=[item.id for item in before],
        kept_item_ids=[item.id for item in kept],
        added_item_ids=[item.id for item in after if item.id not in old],
        removed_item_ids=[item.id for item in before if item.id not in new],
    )
    return text, edit


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
        analysis = merge_context(request, card.root_request, items)
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
        if follow_up.kind == "ask_item" or follow_up.slot is None:
            return reply.text(_ask_which_item(follow_up.operation, base))

        slot = follow_up.slot
        in_slot = [item for item in base if item.category == slot]
        if follow_up.kind == "remove":
            return self._remove(base, slot, in_slot, follow_up, reply)
        return await self._add_or_replace(
            request, user_id, items, base, slot, in_slot, follow_up, analysis, runtime, reply
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
        lead = f"Убрал {_SLOT_ACC[slot]}: {quote(target)}."
        return reply.card(
            kept, base, lead=lead, source="rules", attempts=0, revision="",
            edit=OutfitEdit(
                operation="remove", slot=slot, base_item_ids=[item.id for item in base],
                kept_item_ids=[item.id for item in kept], removed_item_ids=[target.id],
            ),
            ranked=None,
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
        note = ""
        target: WardrobeItem | None = None
        if operation == "add" and len(in_slot) >= SLOT_LIMITS[slot]:
            if slot == "accessories":
                return reply.text(
                    f"В образе уже два аксессуара: {_listing(in_slot)}. Больше не добавляю — какой из них заменить?"
                )
            operation, target = "replace", in_slot[0]
            note = " В образе уже была вещь этой категории, поэтому я заменил её, а не добавил вторую."
        elif operation == "replace":
            if not in_slot:
                operation = "add"
                note = f" В прошлом образе не было {_SLOT_GEN[slot]}, поэтому я добавил вещь, ничего не убирая."
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
            exclude_item_ids=[item_id for item_id in unsuitable if item_id not in base_ids],
        )
        phase = time.perf_counter()
        outcome = await asyncio.to_thread(self._engine.retrieve_slot, query)
        reply.timings["retrievalMs"] = _ms_since(phase)
        reply.warnings.extend(outcome.warnings)
        reply.retrieval = outcome.diagnostics if request.debug else None

        if not outcome.candidates:
            # Альтернативы нет — прежний комплект остаётся, новой карточки не будет.
            return reply.text(
                _no_alternative_text(request.query, operation, slot, target, base), revision=outcome.revision
            )

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

        if operation == "add":
            lead = f"Добавил {_SLOT_ACC[slot]}: {quote(chosen.item)}."
        else:
            lead = f"Заменил {_SLOT_ACC[slot]}: {quote(target)} → {quote(chosen.item)}."  # type: ignore[arg-type]
        return reply.card(
            final, base, lead=lead + note, source=source, attempts=attempts, revision=outcome.revision,
            edit=OutfitEdit(
                operation=operation, slot=slot, base_item_ids=base_ids,  # type: ignore[arg-type]
                kept_item_ids=[item.id for item in kept], added_item_ids=[chosen.item.id],
                removed_item_ids=[target.id] if target else [],
            ),
            ranked=outcome,
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
                attempts=attempts, revision=revision, occasion=self.analysis.occasion_label
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
        self, items: list[WardrobeItem], base: list[WardrobeItem], *, lead: str, source: str,
        attempts: int, revision: str, edit: OutfitEdit, ranked: SlotOutcome | None,
    ) -> RecommendResponse:
        from app.services.orchestrator import with_image  # общий помощник карточек

        items = [with_image(item) for item in sort_items(items)]
        kept = [item for item in items if item.id in set(edit.kept_item_ids)]
        text = lead + (f" Остальные вещи без изменений: {_listing(kept)}." if kept else "")
        colors = list(dict.fromkeys(item.color.strip().lower() for item in items if item.color.strip()))
        outfit = OutfitLook(
            id=f"outfit-{uuid.uuid4().hex[:12]}",
            title=f"Образ · {self.analysis.occasion_label}",
            description="В образ вошли: " + "; ".join(item.title for item in items) + ".",
            occasion=self.analysis.occasion_label,
            items=items,
            stylist_reasoning="Палитра образа: " + ", ".join(colors) + "." if colors else "",
            match_score=match_score(items, _edited_as_outcome(items, edit, ranked)),
            confidence_tips=[],
        )
        return RecommendResponse(
            text=text, suggested_outfit=outfit, referenced_item_ids=[item.id for item in items],
            edit=edit, **self._common(source, attempts, revision),
        )


# --- тексты и факты -----------------------------------------------------------------


def _count(n: int) -> str:
    return "одной вещи" if n == 1 else f"{n} вещей"


def _ask_which_item(operation: str | None, base: list[WardrobeItem]) -> str:
    verb = {"replace": "заменить", "remove": "убрать"}.get(operation or "")
    if verb is None:
        return "Что добавить к образу: верхнюю одежду или аксессуар?"
    options = ", ".join(f"{quote(item)} ({CATEGORY_LABELS_RU[item.category]})" for item in sort_items(base))
    return f"Уточните, какую вещь {verb}: {options}?"


def _no_alternative_text(
    query: str, operation: str, slot: str, target: WardrobeItem | None, base: list[WardrobeItem]
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
    return f"{lead} Прежний образ оставляю без изменений: {_listing(base)}."


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
