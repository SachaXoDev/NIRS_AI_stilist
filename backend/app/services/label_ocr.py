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
    "The North Face", "Columbia", "Patagonia", "Mammut", "Helly Hansen", "Arc'teryx", "Carhartt",
    "Marks & Spencer", "GAP", "Wrangler", "Diesel", "L.L.Bean", "Decathlon", "Quechua", "Salomon",
    "Polo Ralph Lauren", "Ralph Lauren", "Moncler", "Timberland", "Clarks", "Dr. Martens",
)
_FIBERS = {
    "Хлопок": "cotton|coton|baumwolle|algodón|algodao|хлопок|хлопка|хлопковый|хлопковая|хлопковое",
    "Шерсть": "wool|laine|wolle|lana|шерсть|шерсти|шерстяной|шерстяная|шерстяное",
    "Кашемир": "cashmere|кашемир|кашемира|кашемировый|кашемировая|кашемировое",
    "Лён": "linen|flax|лен|льна|льняной|льняная|льняное",
    "Шёлк": "silk|шелк|шелка|шелковый|шелковая|шелковое",
    "Вискоза": "viscose|rayon|вискоза|вискозы",
    "Полиэстер": "polyester|полиэстер|полиэстера|полиэфир|полиэфира",
    "Полиамид": "polyamide|nylon|полиамид|полиамида|нейлон|нейлона",
    "Эластан": "elastane|élasthanne|elasthan|spandex|эластан|эластана",
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
    "Резина": "rubber|caoutchouc|goma|резина|резины|каучук|каучука",
    "Пух": "down|duvet|пух|пуха|duck down|goose down|утиный пух|гусиный пух",
    "Перо": "feather|feathers|plumes|перо|пера|перья|duck feather|duck feathers|goose feather|goose feathers",
    "ЭВА": "eva|ethylene vinyl acetate|этиленвинилацетат|эва",
    "Термопластичная резина": "tpr|thermoplastic rubber|термопластичная резина|терморезина",
}
_FIBER_BY_WORD = {term: name for name, terms in _FIBERS.items() for term in terms.split("|")}
_FIBER = r"\b(" + "|".join(sorted(map(re.escape, _FIBER_BY_WORD), key=len, reverse=True)) + r")\b"
_PERCENT = r"(?<![\w.,+\-−])(\d{1,3}(?:[,.]\d{1,3})?)\s*%"
_QUALIFIER = r"(?:органического |органический |organic |recycled |переработанного |переработанный |virgin )?"
_SHARE = re.compile(rf"{_PERCENT}\s*{_QUALIFIER}{_FIBER}|{_QUALIFIER}{_FIBER}\s*(?:\s[-–—]\s+)?{_PERCENT}")
_PRIMARY = (r"основн(?:ая ткань|ой материал)|(?:состав|материал) верха|внешн(?:яя ткань|ий материал)|верх"
            r"|(?:main|outer|exterior) (?:fabric|material|shell)|shell(?: fabric)?|upper(?: material)?"
            r"|outer|exterior|body|tissu principal|stoff außen|oberstoff")
_PART_HEADINGS: dict[MaterialPart, str] = {
    "lining": r"(?:состав |материал )?подкладк[аи]|lining(?: material)?|doublure|futter|forro",
    "sole": r"(?:материал )?подошв[аы]|outer sole|outsole|sole(?: material)?|semelle extérieure|laufsohle",
    "insole": r"стельк[аи]|sockliner|sock lining|insole|innensohle|semelle intérieure",
    "insulation": r"(?:состав )?(?:наполнитель|наполнителя|утеплитель|утеплителя)|padding|fill(?:ing)?|insulation|garnissage|füllung|relleno",
    "trim": r"(?:состав )?отделк[аи]|trim|trimming|garniture",
}
_SECONDARY = "|".join(_PART_HEADINGS.values())
_GENERAL = r"состав|материал|composition|material|fabric|fibre content|fiber content|fabric content"
# Consume unrepresented parts as boundaries instead of attributing their shares to an adjacent component.
_OTHER = (r"contrast(?: fabric)?|sleeve lining|body lining|pocket lining|lining \d+|midsole|rib(?:bing)?|"
          r"плечевые накладки|"
          r"pockets?|cuffs?|hood|sleeves?|панел[ьи]|капюшон|карманы?|манжеты?|рукава?")
_HEADING = rf"(?:{_OTHER}|{_PRIMARY}|{_SECONDARY}|{_GENERAL})"
_SEPARATOR = r"[:：–—]|\s+-|[|]"
_UNLINED = re.compile(r"(?:без подкладки|подкладка отсутствует|unlined|(?:no|without) lining)")
_SECTION = re.compile(
    rf"(?<!\w)(?<!без )(?<!no )(?<!without )(?P<part>{_HEADING})(?P<aliases>(?:\s*[/|]\s*{_HEADING})*)(?!\w)"
    rf"(?:\s*,\s*%)?(?:\s*(?:{_SEPARATOR})\s*|(?=\s*$)|(?=\s+(?:{_PERCENT}|{_QUALIFIER}{_FIBER}|{_UNLINED.pattern})))"
)
_SECONDARY_PROSE = re.compile(rf"^(?:the )?(?:{_OTHER}|{_SECONDARY})\s+(?:из|выполнен\w*|сшит\w*|is|made)\b")
_PROSE_MATERIAL = re.compile(
    r"\b(?:сшит[аоы]? из|сделан[аоы]? из|изготовлен[аоы]? из|связан[аоы]? из|"
    r"выполнен[аоы]? из|made (?:of|from)|crafted from|woven from)\s+" + _FIBER,
)
_PART_PATTERNS = {part: re.compile(pattern) for part, pattern in _PART_HEADINGS.items()}
_DECLARED_BRAND = re.compile(r"^(?:brand(?: name)?|марка|бренд|товарный знак)\s*(?:[:：–—-]\s*(.*))?$", re.I)
_ATTRIBUTED_BRAND = re.compile(
    r"^(?:модель от|designed by)\s+(.+?)(?=\s+(?:[bв] (?:цвете|оттенке)|in (?:the )?(?:colou?r|shade))\b|[.!]?$)",
    re.I,
)
_BRAND_VALUE = re.compile(r"[^\W_][\w&'’ .-]{0,46}[^\W_]", re.UNICODE)
_TRADEMARK = re.compile(r"\s*[®™]\s*$")
_LABEL_METADATA = re.compile(r"^(?:made in|care instructions|machine wash|wash|do not|dry clean|"
                             r"изготовлено|произведено|уход|стирка|артикул|size|размер)\b")
_COLOR_HEADING = r"colou?r|цвет"
_COLOR_VALUE = r"[^\W\d_]+(?:[ -][^\W\d_]+)*"
_DECLARED_COLOR = re.compile(rf"^(?:{_COLOR_HEADING})\s*[:：\-–—]\s*({_COLOR_VALUE})$", re.I)
_TABLE_COLOR = re.compile(rf"^(?:{_COLOR_HEADING})(?:\s+({_COLOR_VALUE}))?$", re.I)
_DECLARED_SEASON = re.compile(r"^(?:season|сезон(?:ность)?)(?:\s*[:：–—]\s*|\s+)(.+)$")
_SEASON_NAMES: dict[str, Season] = {
    "всесезонно": "all", "всесезонный": "all", "всесезонная": "all",
    "круглый год": "all", "all season": "all", "all seasons": "all", "year round": "all",
    "мульти": "all",
    "весна лето": "spring/summer", "spring summer": "spring/summer",
    "осень зима": "autumn/winter", "autumn winter": "autumn/winter", "fall winter": "autumn/winter",
    "весна": "spring/summer", "лето": "spring/summer", "spring": "spring/summer", "summer": "spring/summer",
    "осень": "autumn/winter", "зима": "autumn/winter", "autumn": "autumn/winter", "fall": "autumn/winter",
    "winter": "autumn/winter",
}
_COLOR_NAMES = {
    "black": "Чёрный", "черный": "Чёрный", "white": "Белый", "gray": "Серый", "grey": "Серый",
    "red": "Красный", "blue": "Синий", "navy": "Тёмно-синий", "dark blue": "Тёмно-синий",
    "темно-синий": "Тёмно-синий", "light blue": "Голубой", "beige": "Бежевый", "brown": "Коричневый",
    "green": "Зелёный", "зеленый": "Зелёный", "yellow": "Жёлтый", "желтый": "Жёлтый",
    "pink": "Розовый", "orange": "Оранжевый", "purple": "Фиолетовый", "burgundy": "Бордовый",
}
_COLOR_NAMES.update({name.lower().replace("ё", "е"): name for name in tuple(_COLOR_NAMES.values())})


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


_NAMED = re.compile(rf"{_QUALIFIER}{_FIBER}(?:\s*[,;/+]\s*{_QUALIFIER}{_FIBER})*")
_SHARE_FRAGMENT = re.compile(rf"{_PERCENT}|{_QUALIFIER}{_FIBER}")
_PERCENT_ONLY = re.compile(_PERCENT)
_PRIMARY_SECTION = re.compile(_PRIMARY)
_GENERAL_SECTION = re.compile(_GENERAL)


def _section_key(heading: str) -> str:
    if _PRIMARY_SECTION.fullmatch(heading):
        return "primary"
    if _GENERAL_SECTION.fullmatch(heading):
        return "general"
    return next((part for part, pattern in _PART_PATTERNS.items() if pattern.fullmatch(heading)), "other")


def _material_sections(lines: list[str]) -> dict[str, list[list[str]]]:
    sections: dict[str, list[list[str]]] = {}
    destination: list[str] | None = None
    seen_heading = False

    def append(fragment: str, *, inline: bool = False) -> None:
        nonlocal destination
        fragment = fragment.strip(" \t:;,.|/")
        if not fragment:
            return
        if destination is not None:
            if inline or "%" in fragment or _NAMED.fullmatch(fragment) or _UNLINED.fullmatch(fragment):
                destination.append(fragment)
                return
            destination = None
        if not seen_heading and ("%" in fragment or _NAMED.fullmatch(fragment) or _PROSE_MATERIAL.search(fragment)):
            sections.setdefault("unheaded", [[]])[0].append(fragment)

    for raw in lines:
        line = _normalized(raw)
        if _SECONDARY_PROSE.match(line) or _LABEL_METADATA.match(line):
            destination = None
            continue
        start = 0
        for match in _SECTION.finditer(line):
            append(line[start:match.start()], inline=start > 0)
            key = _section_key(match["part"])
            aliases = [part.strip() for part in re.split(r"[/|]", match["aliases"]) if part.strip()]
            if any(_section_key(alias) != key for alias in aliases):
                key = "other"  # A shared heading for different components is not assignable.
            destination = []
            sections.setdefault(key, []).append(destination)
            seen_heading = True
            start = match.end()
        append(line[start:], inline=start > 0)
    return sections


def _read_material(segments: list[str], *, declared: bool) -> str | None:
    composition: dict[str, set[Decimal]] = {}
    named_materials: set[str] = set()
    # Printed labels can wrap between the share and fiber. Join only those adjacent fragments.
    pending: list[str] = []
    for text in segments:
        if pending and _SHARE_FRAGMENT.fullmatch(pending[-1]) and _SHARE_FRAGMENT.fullmatch(text):
            if bool(_PERCENT_ONLY.fullmatch(pending[-1])) != bool(_PERCENT_ONLY.fullmatch(text)):
                pending[-1] += " " + text
                continue
        pending.append(text)
    for text in pending:
        matches = list(_SHARE.finditer(text))
        if text.count("%") != len(matches):
            return None
        for match in matches:
            prefix, first, second, suffix = match.groups()
            share = Decimal((prefix or suffix).replace(",", "."))
            if not 0 < share <= 100:
                return None
            composition.setdefault(_FIBER_BY_WORD[first or second], set()).add(share)
        if not matches and _NAMED.fullmatch(text):
            named_materials.update(_FIBER_BY_WORD[word] for word in re.findall(_FIBER, text))
        elif not matches and not declared:
            named_materials.update(_FIBER_BY_WORD[word] for word in _PROSE_MATERIAL.findall(text))
        elif not matches:
            return None
    if not composition:
        return ", ".join(sorted(named_materials)) or None
    if named_materials - composition.keys() or any(len(shares) != 1 for shares in composition.values()):
        return None
    parts = [(name, next(iter(shares))) for name, shares in composition.items()]
    if sum(share for _, share in parts) != 100:
        return None
    return ", ".join(f"{format(share.normalize(), 'f').replace('.', ',')}% {name.lower()}" for name, share in parts)


def _agreed_material(sections: list[list[str]], *, declared: bool = True, part: MaterialPart | None = None) -> str | None:
    values = ["Без подкладки" if part == "lining" and section and all(_UNLINED.fullmatch(line) for line in section)
              else _read_material(section, declared=declared) for section in sections]
    if not values or any(value is None for value in values):
        return None
    # Parallel language blocks can list the same fibers in a different order.
    if len({frozenset((value or "").split(", ")) for value in values}) == 1:
        return values[0]
    return None


def _brand_key(value: str) -> str:
    return re.sub(r"\s*&\s*", "&", _normalized(_TRADEMARK.sub("", value)).strip(" .-"))


_BRAND_BY_KEY = {_brand_key(brand): brand for brand in _BRANDS}


def _declared_brand(value: str) -> str | None:
    value = " ".join(_TRADEMARK.sub("", value).split())
    if (_BRAND_VALUE.fullmatch(value) and any(c.isalpha() for c in value)
            and not _LABEL_METADATA.match(_normalized(value)) and not is_material_heading(value)):
        return value
    return None


def _read_brand(lines: list[str]) -> str | None:
    candidates: dict[str, str] = {}
    for index, line in enumerate(lines):
        if declaration := _DECLARED_BRAND.fullmatch(line.strip()):
            value = declaration[1] or (lines[index + 1] if index + 1 < len(lines) else "")
            if brand := _declared_brand(value):
                key = _brand_key(brand)
                candidates[key] = _BRAND_BY_KEY.get(key, brand)
        elif (attribution := _ATTRIBUTED_BRAND.match(line.strip())) and (brand := _declared_brand(attribution[1])):
            key = _brand_key(brand)
            candidates[key] = _BRAND_BY_KEY.get(key, brand)
        elif (key := _brand_key(line)) in _BRAND_BY_KEY:
            candidates[key] = _BRAND_BY_KEY[key]
        elif index + 1 < len(lines) and (key := _brand_key(f"{line} {lines[index + 1]}")) in _BRAND_BY_KEY:
            candidates[key] = _BRAND_BY_KEY[key]
    return next(iter(candidates.values())) if len(candidates) == 1 else None


def parse_label(lines: list[str]) -> LabelFields:
    colors = set()
    seasons: set[Season | None] = set()
    for index, raw in enumerate(lines):
        line = _normalized(raw)
        if declared := _DECLARED_SEASON.fullmatch(line):
            season_name = " ".join(re.split(r"[\s/\-–—]+", declared[1]))
            seasons.add(_SEASON_NAMES.get(season_name))
        elif line in ("сезон", "сезонность", "season") and index + 1 < len(lines):
            season_name = " ".join(re.split(r"[\s/\-–—]+", _normalized(lines[index + 1])))
            seasons.add(_SEASON_NAMES.get(season_name))

        if declared_color := _DECLARED_COLOR.fullmatch(unicodedata.normalize("NFKC", " ".join(raw.split()))):
            color_name = declared_color[1]
            if 2 <= len(color_name) <= 48:
                colors.add(_COLOR_NAMES.get(_normalized(color_name), color_name))
        elif table_color := _TABLE_COLOR.fullmatch(line):
            color_name = table_color[1] or (_normalized(lines[index + 1]) if index + 1 < len(lines) else "")
            if color_name in _COLOR_NAMES:
                colors.add(_COLOR_NAMES[color_name])
    sections = _material_sections(lines)
    main = next((key for key in ("primary", "general", "unheaded") if key in sections), "unheaded")
    material = _agreed_material(sections.get(main, []), declared=main != "unheaded")
    fields: LabelFields = {}
    if len(seasons) == 1 and (season := next(iter(seasons))) is not None:
        fields["season"] = season
    if brand := _read_brand(lines):
        fields["brand"] = brand
    if material:
        fields["material"] = material
    if details := {part: value for part in _PART_HEADINGS
                   if (value := _agreed_material(sections.get(part, []), part=part)) is not None}:
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


def read_text(image: Any, *, dense: bool = False) -> list[str]:
    if not (command := _ocr_command()):
        return []
    from PIL import Image, ImageOps

    binary, languages = command
    # Preserve small print and text on dark or slightly shadowed labels.
    image = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=0.5)
    if 160 <= max(image.size) < 1200:
        scale = min(2, 1200 / max(image.size))
        image = image.resize(tuple(round(side * scale) for side in image.size), Image.Resampling.LANCZOS)
    with BytesIO() as payload:
        image.save(payload, format="PNG")
        png = payload.getvalue()
    if dense:
        # Keep the layout of aligned tag rows when possible. Never concatenate competing reads.
        lines = _ocr_lines(binary, languages, png, "6")
        if parse_label(lines):
            return lines
        return _ocr_lines(binary, languages, png, "11") or lines
    return _ocr_lines(binary, languages, png, "11")


def _ocr_lines(binary: str, languages: str, png: bytes, mode: str) -> list[str]:
    try:
        result = subprocess.run(
            [binary, "stdin", "stdout", "-l", languages, "--psm", mode, "tsv"],
            input=png, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    lines: dict[tuple[str, ...], list[tuple[str, float]]] = {}
    try:
        rows = csv.DictReader(StringIO(result.stdout.decode("utf-8", errors="replace")), delimiter="\t", quoting=csv.QUOTE_NONE)
        for word in rows:
            if word.get("text", "").strip():
                key = tuple(word[field] for field in ("page_num", "block_num", "par_num", "line_num"))
                lines.setdefault(key, []).append((word["text"], float(word["conf"])))
    except (KeyError, TypeError, ValueError):
        return []
    return [" ".join(text for text, _ in line) for line in lines.values()
            if all(confidence >= 65 for text, confidence in line if any(c.isalnum() for c in text))
            and any(confidence >= 65 and any(c.isalnum() for c in text) for text, confidence in line)]
