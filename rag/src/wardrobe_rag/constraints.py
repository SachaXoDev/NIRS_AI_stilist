"""Transparent slot constraints and post-LLM selection checks."""

from __future__ import annotations

import itertools
import re
from collections import Counter
from collections.abc import Sequence

from .config import RAGConfig
from .schemas import (
    Category, QueryContext, REQUIRED_SLOTS, RetrievalRequest, RetrievalResult,
    SelectionValidation, WardrobeItem,
)
from .text import color_tokens, tokenize


def resolve_context(request: RetrievalRequest) -> QueryContext:
    """Parse only explicit temperature/weather expressions; caller fields win."""
    context = request.context.model_copy()
    text = " ".join(filter(None, [request.query, context.weather])).lower().replace("ё", "е")
    # Typographic minus (U+2212) always means "below zero"; an en dash does only when glued
    # to a number and not part of a range like "10–15°C". Otherwise "−5°C" was read as +5.
    text = re.sub(r"(?<!\d)–(?=\d)", "-", text).replace("−", "-")
    if context.temperature_c is None:
        match = re.search(r"(?<!\w)([+-]\s*\d{1,2}(?:[.,]\d+)?)\s*(?:°\s*[cс]?|[cс]\b)?", text)
        if match is None:
            match = re.search(r"(?<!\w)(-?\d{1,2}(?:[.,]\d+)?)\s*°\s*[cс]?", text)
        if match:
            temperature = float(match.group(1).replace(" ", "").replace(",", "."))
            if -80 <= temperature <= 65:
                context.temperature_c = temperature
    if context.rain is None:
        if re.search(r"без\s+дожд|дожд\w*\s+нет|сухая?\s+погод|no\s+rain|dry\b", text):
            context.rain = False
        elif "дожд" in text or "rain" in text:
            context.rain = True
    if context.wind is None:
        if "безветр" in text or re.search(r"без\s+ветр|no\s+wind", text):
            context.wind = False
        elif any(word in text for word in ("ветр", "ветер", "wind")):
            context.wind = True
    return context


def required_slots(request: RetrievalRequest, context: QueryContext, config: RAGConfig) -> list[Category]:
    slots: list[Category] = list(REQUIRED_SLOTS)
    needs_coat = request.require_outerwear
    if needs_coat is None:
        needs_coat = (
            context.temperature_c is not None and context.temperature_c <= config.outerwear_below_c
        ) or context.rain is True
    if needs_coat:
        slots.append("outerwear")
    return slots


def inferred_exclusions(request: RetrievalRequest) -> tuple[list[str], list[str]]:
    """A small documented grammar, rather than pretending to do full NLP."""
    text = request.query.lower().replace("ё", "е")
    colors = list(request.exclude_colors)
    materials = list(request.exclude_materials)
    prefix = r"(?:без|не)\s+"
    colors.extend(re.findall(prefix + r"(черн\w*|бел\w*|красн\w*|син\w*|зелен\w*|желт\w*|розов\w*|сер\w*|бежев\w*|коричнев\w*)", text))
    materials.extend(re.findall(prefix + r"(шерст\w*|кож\w*|шелк\w*|кашемир\w*|хлоп\w*|деним\w*)", text))
    return colors, materials


_FLAT_SHOE = re.compile(r"\b(?:без\s+каблук\w*|плоск\w*\s+подошв\w*|на\s+плоском\s+ходу|flat[ -]sole|no[ -]heel|heel[- ]free)\b")
_HEEL = re.compile(r"\b(?:на|с)\s+(?:\w+\s+){0,2}каблук(?:е|ом)\b|\bheels\b")


def requests_flat_shoes(query: str) -> bool:
    return bool(_FLAT_SHOE.search(query.casefold().replace("ё", "е")))


def is_documented_flat(item: WardrobeItem) -> bool:
    parts = [part.casefold().replace("ё", "е") for part in (item.title, *item.tags)]
    return any(_FLAT_SHOE.search(part) for part in parts) and not any(_HEEL.search(part) for part in parts)


def item_violations(
    item: WardrobeItem, request: RetrievalRequest, context: QueryContext,
) -> list[str]:
    violations: list[str] = []
    if item.id in request.exclude_item_ids:
        violations.append("item explicitly excluded")
    colors, materials = inferred_exclusions(request)
    actual_color = color_tokens(item.color)
    if any(actual_color & color_tokens(color) for color in colors):
        violations.append("excluded color")
    actual_material = set(tokenize(item.material or ""))
    if any(actual_material & set(tokenize(material)) for material in materials):
        violations.append("excluded material")
    facts = item.weather
    if facts is None:
        return violations
    if context.temperature_c is not None:
        if facts.temperature_min is not None and context.temperature_c < facts.temperature_min:
            violations.append("below documented temperature range")
        if facts.temperature_max is not None and context.temperature_c > facts.temperature_max:
            violations.append("above documented temperature range")
    if context.rain is True and item.category in {"shoes", "outerwear"} and facts.waterproof is False:
        violations.append("documented as not waterproof")
    if context.wind is True and item.category == "outerwear" and facts.windproof is False:
        violations.append("documented as not windproof")
    if item.category == "shoes" and facts.open_shoes is True:
        if context.rain is True or (context.temperature_c is not None and context.temperature_c <= 12):
            violations.append("open shoes in cold or rain")
    return violations


def weather_warnings(items: Sequence[WardrobeItem], context: QueryContext) -> list[str]:
    unknown: list[str] = []
    has_weather = context.temperature_c is not None or context.rain is True or context.wind is True
    if not has_weather:
        return []
    for item in items:
        if item.category == "accessories":
            continue
        facts = item.weather
        missing = facts is None
        if facts is not None:
            if context.temperature_c is not None and (facts.temperature_min is None or facts.temperature_max is None):
                missing = True
            if context.rain is True and item.category in {"shoes", "outerwear"} and facts.waterproof is None:
                missing = True
            if context.wind is True and item.category == "outerwear" and facts.windproof is None:
                missing = True
        if missing:
            unknown.append(item.id)
    if not unknown:
        return []
    return ["Weather suitability is unverified for items with missing curated attributes: " + ", ".join(sorted(unknown))]


def validate_selection(selected_item_ids: Sequence[str], result: RetrievalResult) -> SelectionValidation:
    """Validate LLM-selected IDs against this retrieval snapshot, never its free text."""
    allowed = {candidate.item.id: candidate.item for candidates in result.candidates_by_slot.values() for candidate in candidates}
    violations: list[str] = []
    if len(set(selected_item_ids)) != len(selected_item_ids):
        violations.append("Duplicate item IDs are not allowed")
    unknown = sorted(set(selected_item_ids) - allowed.keys())
    if unknown:
        violations.append("IDs are outside this user's retrieved candidate set: " + ", ".join(unknown))
    selected = [allowed[item_id] for item_id in dict.fromkeys(selected_item_ids) if item_id in allowed]
    counts = Counter(item.category for item in selected)
    for category in ("tops", "bottoms", "shoes", "outerwear"):
        if counts[category] > 1:
            violations.append(f"At most one item is allowed in slot {category}")
    if counts["accessories"] > 2:
        violations.append("At most two accessories are allowed")
    mandatory = list(dict.fromkeys([*REQUIRED_SLOTS, *result.required_slots]))
    missing: list[Category] = [slot for slot in mandatory if counts[slot] == 0]
    if result.anchor_item_id is not None and result.anchor_item_id not in selected_item_ids:
        violations.append("Required anchor item is missing")
    # Recheck documented weather facts even if a caller constructed the result manually.
    request = RetrievalRequest(
        user_id=result.user_id, query=result.query or "selection", context=result.context,
        require_outerwear="outerwear" in result.required_slots,
    )
    for item in selected:
        for violation in item_violations(item, request, result.context):
            violations.append(f"{item.id}: {violation}")
    warnings = list(dict.fromkeys(result.warnings + weather_warnings(selected, result.context)))
    return SelectionValidation(
        valid=not violations, complete=not violations and not missing,
        selected_items=selected, missing_slots=missing, violations=violations,
        warnings=warnings, wardrobe_revision=result.wardrobe_revision,
    )


def _accent_penalty(items: Sequence[WardrobeItem]) -> float:
    """A deliberately modest, explicit palette heuristic, not a fashion probability."""
    neutrals = {"черн", "бел", "сер", "бежев", "молочн", "коричнев", "шоколадн", "кремов"}
    families = set()
    for item in items:
        tokens = color_tokens(item.color)
        if tokens & neutrals:
            continue
        families.update(tokens)
    return max(0, len(families) - 2) * 0.08


def assemble_outfit(result: RetrievalResult) -> SelectionValidation:
    """Deterministic candidate assembly for demos/tests before the LLM is connected."""
    slots = list(dict.fromkeys([*REQUIRED_SLOTS, *result.required_slots]))
    query = result.query.lower().replace("ё", "е")
    if result.candidates_by_slot.get("accessories") and any(
        stem in query for stem in ("аксессуар", "платок", "шарф", "сумк", "акцент", "шелк")
    ):
        slots.append("accessories")
    if "outerwear" not in slots and result.candidates_by_slot.get("outerwear") and any(
        stem in query for stem in ("тренч", "пальто", "плащ", "куртк", "блейзер", "жакет")
    ):
        slots.append("outerwear")
    anchor_category = None
    if result.anchor_item_id:
        anchor_category = next((slot for slot, candidates in result.candidates_by_slot.items()
                                if any(c.item.id == result.anchor_item_id for c in candidates)), None)
        if anchor_category is not None and anchor_category not in slots:
            slots.append(anchor_category)
    pools = []
    for slot in slots:
        candidates = result.candidates_by_slot.get(slot, [])
        if slot == anchor_category:
            candidates = [c for c in candidates if c.item.id == result.anchor_item_id]
        # Keep existing categories in an incomplete result, never invent a missing item.
        if candidates:
            pools.append(candidates)
    if not pools:
        return validate_selection([], result)
    best_ids: list[str] = []
    best_objective = float("-inf")
    for combination in itertools.product(*pools):
        items = [candidate.item for candidate in combination]
        objective = sum(candidate.score / max((c.score for c in pool), default=1.0)
                        if max((c.score for c in pool), default=0) > 0 else 0
                        for candidate, pool in zip(combination, pools)) - _accent_penalty(items)
        ids = [item.id for item in items]
        if objective > best_objective or (objective == best_objective and ids < best_ids):
            best_objective, best_ids = objective, ids
    return validate_selection(best_ids, result)
