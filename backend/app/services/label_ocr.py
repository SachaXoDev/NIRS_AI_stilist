"""Read verifiable garment metadata from visible text, not visual similarity."""
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import unicodedata
from decimal import Decimal
from functools import lru_cache
from io import BytesIO, StringIO
from typing import Any, TypedDict

from app.schemas import MaterialPart, Season

_BRANDS = (
    "12 STOREEZ", "Arket", "COS", "Massimo Dutti", "Uniqlo", "Levi's", "Veja", "Vagabond",
    "Polène", "Burberry", "Zara", "H&M", "Mango", "Nike", "Adidas", "New Balance", "Puma",
    "Reebok", "ECCO", "Reserved", "Lime", "Lacoste", "Calvin Klein", "Tommy Hilfiger",
)
_FIBERS = {
    "Хлопок": "cotton|хлопок|хлопка|хлопковый|хлопковая|хлопковое",
    "Шерсть": "wool|шерсть|шерсти|шерстяной|шерстяная|шерстяное",
    "Кашемир": "cashmere|кашемир|кашемира|кашемировый|кашемировая|кашемировое",
    "Лён": "linen|flax|лен|льна|льняной|льняная|льняное",
    "Шёлк": "silk|шелк|шелка|шелковый|шелковая|шелковое",
    "Вискоза": "viscose|rayon|вискоза|вискозы",
    "Полиэстер": "polyester|полиэстер|полиэстера|полиэфир|полиэфира",
    "Полиамид": "polyamide|nylon|полиамид|полиамида|нейлон|нейлона",
    "Эластан": "elastane|spandex|эластан|эластана",
    "Акрил": "acrylic|акрил|акрила",
    "Лиоцелл": "lyocell|tencel|лиоцелл|лиоцелла",
    "Модал": "modal|модал|модала",
    "Кожа": "leather|кожа|кожи",
    "Натуральная кожа": "genuine leather|real leather|натуральная кожа|натуральной кожи",
    "Искусственная кожа": "faux leather|synthetic leather|искусственная кожа|искусственной кожи|экокожа|экокожи",
    "Замша": "suede|замша|замши",
    "Нубук": "nubuck|нубук|нубука",
    "Полиуретан": "polyurethane|полиуретан|полиуретана",
    "Текстиль": "textile|текстиль|текстиля",
    "Деним": "denim|деним|денима",
    "Сетка": "mesh|сетка|сетки",
    "Резина": "rubber|резина|резины",
    "Пух": "down|пух|пуха",
}
_FIBER_BY_WORD = {term: name for name, terms in _FIBERS.items() for term in terms.split("|")}
_FIBER = r"\b(" + "|".join(sorted(map(re.escape, _FIBER_BY_WORD), key=len, reverse=True)) + r")\b"
_PERCENT = r"(?<!\d)(?<!\d[.,])(\d{1,3}(?:[,.]\d{1,3})?)\s*%"
_SHARE = re.compile(
    _PERCENT + r"\s*(?:органического |organic |recycled |переработанного )?" + _FIBER
    + "|" + _FIBER + r"\s*" + _PERCENT,
)
_PRIMARY = r"основная ткань|основной материал|материал верха|верх|main fabric|outer fabric|outer shell|shell|upper|exterior"
_PART_HEADINGS: dict[MaterialPart, str] = {
    "lining": r"(?:состав |материал )?подкладк[аи]|lining",
    "sole": r"(?:материал )?подошв[аы]|outsole|sole",
    "insole": r"стелька|insole",
    "insulation": r"наполнитель|утеплитель|padding|filling|insulation",
    "trim": r"отделка|trim",
}
_SECONDARY = "|".join(_PART_HEADINGS.values())
_GENERAL = r"состав|материал|composition|material|fabric"
_SECTION = re.compile(rf"\b(?P<part>{_PRIMARY}|{_SECONDARY}|{_GENERAL})\s*(?:[:：–—]|$)\s*")
_SECONDARY_PROSE = re.compile(rf"^(?:the )?(?:{_SECONDARY})\s+(?:из|выполнен\w*|сшит\w*|is|made)\b")
_PROSE_MATERIAL = re.compile(
    r"\b(?:сшит[аоы]? из|сделан[аоы]? из|изготовлен[аоы]? из|связан[аоы]? из|"
    r"выполнен[аоы]? из|made (?:of|from)|crafted from|woven from)\s+" + _FIBER,
)
_PRIMARY_SECTION = re.compile(_PRIMARY)
_SECONDARY_SECTION = re.compile(_SECONDARY)
_DECLARED_BRAND = re.compile(r"^(?:brand|бренд)\s*[:：]\s*([\w&'’ .-]{2,48})$", re.I)
_DECLARED_COLOR = re.compile(
    r"^(?:colou?r|цвет)\s*[:：-]\s*([^\W\d_]+(?:[ -][^\W\d_]+)*)$", re.I,
)
_DECLARED_SEASON = re.compile(r"^(?:season|сезон(?:ность)?)\s*[:：]\s*(.+)$")
_SEASON_NAMES: dict[str, Season] = {
    "всесезонно": "all", "всесезонный": "all", "всесезонная": "all",
    "круглый год": "all", "all season": "all", "all seasons": "all", "year round": "all",
    "весна лето": "spring/summer", "spring summer": "spring/summer",
    "осень зима": "autumn/winter", "autumn winter": "autumn/winter", "fall winter": "autumn/winter",
}
_COLOR_NAMES = {
    "black": "Чёрный", "черный": "Чёрный", "white": "Белый", "gray": "Серый", "grey": "Серый",
    "red": "Красный", "blue": "Синий", "navy": "Тёмно-синий", "dark blue": "Тёмно-синий",
    "темно-синий": "Тёмно-синий", "light blue": "Голубой", "beige": "Бежевый", "brown": "Коричневый",
    "green": "Зелёный", "зеленый": "Зелёный", "yellow": "Жёлтый", "желтый": "Жёлтый",
    "pink": "Розовый", "orange": "Оранжевый", "purple": "Фиолетовый", "burgundy": "Бордовый",
}


class LabelFields(TypedDict, total=False):
    brand: str
    material: str
    color: str
    season: Season
    materialDetails: dict[MaterialPart, str]


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).lower().replace("ё", "е").replace("’", "'").split())


def is_material_heading(value: str) -> bool:
    return _SECTION.fullmatch(_normalized(value)) is not None


def main_material_segments(lines: list[str]) -> list[tuple[str, bool]]:
    """Return main-material text and whether each fragment is under a material heading."""
    general: list[tuple[str, bool]] = []
    primary: list[tuple[str, bool]] = []
    destination: list[tuple[str, bool]] | None = general
    has_primary = False
    declared = False
    for raw in lines:
        line = _normalized(raw)
        if _SECONDARY_PROSE.match(line):
            continue
        start = 0
        for match in _SECTION.finditer(line):
            if destination is not None and (fragment := line[start:match.start()].strip()):
                destination.append((fragment, declared))
            part = match["part"]
            if _SECONDARY_SECTION.fullmatch(part):
                destination = None
            elif _PRIMARY_SECTION.fullmatch(part):
                has_primary = True
                destination = primary
            else:
                destination = general
            declared = True
            start = match.end()
        if destination is not None and (fragment := line[start:].strip()):
            destination.append((fragment, declared))
    return primary if has_primary else general


def _read_details(lines: list[str]) -> dict[MaterialPart, str]:
    sections: dict[MaterialPart, list[list[tuple[str, bool]]]] = {}
    destination: list[tuple[str, bool]] | None = None
    for raw in lines:
        line = _normalized(raw)
        if _SECONDARY_PROSE.match(line):
            destination = None
            continue
        start = 0
        for match in _SECTION.finditer(line):
            if destination is not None and (fragment := line[start:match.start()].strip()):
                destination.append((fragment, True))
            part = next((key for key, pattern in _PART_HEADINGS.items()
                         if re.fullmatch(pattern, match["part"])), None)
            destination = [] if part is not None else None
            if part is not None and destination is not None:
                sections.setdefault(part, []).append(destination)
            start = match.end()
        if destination is not None and (fragment := line[start:].strip()):
            # Only standalone composition lines may continue a section, not product prose.
            if start or _SHARE.search(fragment) or re.fullmatch(rf"{_FIBER}(?:\s*[,;/]\s*{_FIBER})*", fragment):
                destination.append((fragment, True))
            else:
                destination = None
    details: dict[MaterialPart, str] = {}
    for part, fragments in sections.items():
        values = [_read_material(segment) for segment in fragments]
        if values[0] is not None and len(set(values)) == 1:
            details[part] = values[0]
    return details


def _read_material(segments: list[tuple[str, bool]]) -> str | None:
    composition: dict[str, set[Decimal]] = {}
    named_materials: set[str] = set()
    incomplete = False
    for text, declared in segments:
        matches = list(_SHARE.finditer(text))
        if matches and len(matches) != len(re.findall(_PERCENT, text)):
            incomplete = True
        for match in matches:
            prefix, first, second, suffix = match.groups()
            share = Decimal((prefix or suffix).replace(",", "."))
            if not 0 < share <= 100:
                incomplete = True
                continue
            composition.setdefault(_FIBER_BY_WORD[first or second], set()).add(share)
        if declared and not re.search(_PERCENT, text):
            named_materials.update(_FIBER_BY_WORD[word] for word in re.findall(_FIBER, text))
        elif text in _FIBER_BY_WORD:
            named_materials.add(_FIBER_BY_WORD[text])
        else:
            named_materials.update(_FIBER_BY_WORD[word] for word in _PROSE_MATERIAL.findall(text))
    if incomplete:
        return None
    if not composition:
        return ", ".join(sorted(named_materials)) or None
    if any(len(shares) != 1 for shares in composition.values()):
        return None
    parts = [(name, next(iter(shares))) for name, shares in composition.items()]
    if sum(share for _, share in parts) != 100:
        return None
    return ", ".join(f"{format(share.normalize(), 'f').replace('.', ',')}% {name.lower()}" for name, share in parts)


def parse_label(lines: list[str]) -> LabelFields:
    brands, colors = set(), set()
    seasons: set[Season | None] = set()
    for raw in lines:
        if declared := _DECLARED_SEASON.fullmatch(_normalized(raw)):
            season_name = " ".join(re.split(r"[\s/\-–—]+", declared[1]))
            seasons.add(_SEASON_NAMES.get(season_name))
            continue
        if declared := _DECLARED_COLOR.fullmatch(unicodedata.normalize("NFKC", " ".join(raw.split()))):
            color_name = declared[1]
            if 2 <= len(color_name) <= 48:
                colors.add(_COLOR_NAMES.get(_normalized(color_name), color_name))
            continue
        if declared := _DECLARED_BRAND.fullmatch(raw.strip()):
            brands.add(declared[1].strip())
        else:
            brands.update(known for known in _BRANDS if _normalized(raw) == _normalized(known))
    distinct_brands = {_normalized(brand): brand for brand in sorted(brands)}
    brand = next(iter(distinct_brands.values())) if len(distinct_brands) == 1 else None
    material = _read_material(main_material_segments(lines))
    fields: LabelFields = {}
    if len(seasons) == 1 and (season := next(iter(seasons))) is not None:
        fields["season"] = season
    if brand:
        fields["brand"] = brand
    if material:
        fields["material"] = material
    if details := _read_details(lines):
        fields["materialDetails"] = details
    distinct_colors = {_normalized(color): color for color in sorted(colors)}
    if len(distinct_colors) == 1:
        fields["color"] = next(iter(distinct_colors.values()))
    return fields


@lru_cache(maxsize=1)
def _ocr_command() -> tuple[str, str] | None:
    if not (binary := shutil.which("tesseract")):
        return None
    try:
        languages = subprocess.run([binary, "--list-langs"], capture_output=True, text=True, timeout=3, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    installed = set(languages.stdout.splitlines())
    selected = "+".join(lang for lang in ("eng", "rus") if lang in installed)
    return (binary, selected) if selected else None


def read_text(image: Any) -> list[str]:
    if not (command := _ocr_command()):
        return []
    binary, languages = command
    with BytesIO() as payload:
        image.save(payload, format="PNG")
        try:
            result = subprocess.run(
                [binary, "stdin", "stdout", "-l", languages, "--psm", "11", "tsv"],
                input=payload.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=5, check=True,
            )
        except (OSError, subprocess.SubprocessError):
            return []
    lines: dict[tuple[str, ...], list[tuple[str, bool]]] = {}
    try:
        rows = csv.DictReader(StringIO(result.stdout.decode("utf-8", errors="replace")), delimiter="\t", quoting=csv.QUOTE_NONE)
        for word in rows:
            if word.get("text", "").strip():
                key = tuple(word[field] for field in ("page_num", "block_num", "par_num", "line_num"))
                lines.setdefault(key, []).append((word["text"], float(word["conf"]) >= 65))
    except (KeyError, TypeError, ValueError):
        return []
    return [" ".join(text for text, _ in line) for line in lines.values() if all(ok for _, ok in line)]
