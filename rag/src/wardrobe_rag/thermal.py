"""Soft temperature preferences, not new facts or eligibility constraints."""
from __future__ import annotations

import re

from .query_attributes import material_values, normalize
from .schemas import QueryContext, WardrobeItem

_COOL = re.compile(r"\b(?:потеплее|теплее|прохладно|холодно|мороз\w*|снег\w*|(?:прохладн|холодн)\w*\s+погод\w*|cold|cool weather|snow)\b")
_HOT = re.compile(r"\b(?:жара|жару|жарко|(?:жарк|знойн)\w*\s+погод\w*|hot|heat)\b")
_NO_INSULATION = re.compile(r"\b(?:без\s+утепл\w*|нет\s+утепл\w*|не\s+утепл\w*|нет|отсутствует|не указан\w*|none|no(?:\s+insulation)?|uninsulated|unknown|n/a)\b")
_INSULATION_MATERIAL = re.compile(r"\b(?:синтепон\w*|флис\w*|мех\w*|овчин\w*|холлофайбер\w*|thinsulate|primaloft|fleece|fur)\b")
_WARM_FIBERS = {"шерсть", "кашемир", "пух"}
_INSULATION_FIBERS = _WARM_FIBERS | {"полиэстер", "акрил", "хлопок"}


def thermal_direction(query: str, context: QueryContext) -> int:
    """1 for cool conditions, -1 for heat; an explicit temperature wins."""
    if context.temperature_c is not None:
        return 1 if context.temperature_c <= 12 else -1 if context.temperature_c >= 24 else 0
    for source in (context.weather or "", query):
        text = normalize(source)
        cool, hot = bool(_COOL.search(text)), bool(_HOT.search(text))
        if cool or hot:
            return int(cool) - int(hot)
    return 0


def material_weather_score(item: WardrobeItem, direction: int) -> int:
    if not direction or item.category == "accessories":
        return 0
    details = item.materialDetails or {}
    insulation = normalize(details.get("insulation", "")).strip()
    if not _NO_INSULATION.search(insulation) and (
        material_values(insulation) & _INSULATION_FIBERS or _INSULATION_MATERIAL.search(insulation)
    ):
        return 2 * direction
    main = (item.material or "") if item.category != "shoes" else ""
    if material_values(main) & _WARM_FIBERS or material_values(details.get("lining", "")) & _WARM_FIBERS:
        return direction
    return 0
