"""Read verifiable garment metadata from visible text, not visual similarity."""
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import unicodedata
from functools import lru_cache
from io import BytesIO, StringIO
from typing import Any, TypedDict

_BRANDS = (
    "12 STOREEZ", "Arket", "COS", "Massimo Dutti", "Uniqlo", "Levi's", "Veja", "Vagabond",
    "Polène", "Burberry", "Zara", "H&M", "Mango", "Nike", "Adidas", "New Balance", "Puma",
    "Reebok", "ECCO", "Reserved", "Lime", "Lacoste", "Calvin Klein", "Tommy Hilfiger",
)
_FIBERS = {
    "Хлопок": r"cotton|хлопок",
    "Шерсть": r"wool|шерсть",
    "Кашемир": r"cashmere|кашемир",
    "Лён": r"linen|flax|лен",
    "Шёлк": r"silk|шелк",
    "Вискоза": r"viscose|rayon|вискоза",
    "Полиэстер": r"polyester|полиэстер",
    "Полиамид": r"polyamide|nylon|полиамид|нейлон",
    "Эластан": r"elastane|spandex|эластан",
    "Акрил": r"acrylic|акрил",
    "Лиоцелл": r"lyocell|лиоцелл",
    "Модал": r"modal|модал",
    "Кожа": r"leather|кожа",
    "Замша": r"suede|замша",
    "Полиуретан": r"polyurethane|полиуретан",
}
_FIBER_BY_WORD = {term: name for name, terms in _FIBERS.items() for term in terms.split("|")}
_FIBER = r"\b(" + "|".join(_FIBER_BY_WORD) + r")\b"
_PERCENT = r"(?<![\d.,])(100|[1-9][0-9]?)\s*%"
_SHARE = re.compile(_PERCENT + r"\s*" + _FIBER + "|" + _FIBER + r"\s*" + _PERCENT)
_DECLARED_MATERIAL = re.compile(r"^(?:material|composition|fabric|состав|материал)(?:\s*[:：]\s*|\s+)(.+)$", re.I)
_DECLARED_BRAND = re.compile(r"^(?:brand|бренд)\s*[:：]\s*([\w&'’ .-]{2,48})$", re.I)
_DECLARED_COLOR = re.compile(
    r"^(?:colou?r|цвет)\s*[:：-]\s*([^\W\d_]+(?:[ -][^\W\d_]+)*)$", re.I,
)
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


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).lower().replace("ё", "е").replace("’", "'").split())


def parse_label(lines: list[str]) -> LabelFields:
    brands, colors, composition, named_materials = set(), set(), {}, set()
    for raw in lines:
        line = _normalized(raw)
        if declared := _DECLARED_COLOR.fullmatch(unicodedata.normalize("NFKC", " ".join(raw.split()))):
            color_name = declared[1]
            if 2 <= len(color_name) <= 48:
                colors.add(_COLOR_NAMES.get(_normalized(color_name), color_name))
            continue
        if declared := _DECLARED_BRAND.fullmatch(raw.strip()):
            brands.add(declared[1].strip())
        else:
            brands.update(known for known in _BRANDS if line == _normalized(known))
        for match in _SHARE.finditer(line):
            prefix, first, second, suffix = match.groups()
            composition.setdefault(_FIBER_BY_WORD[first or second], set()).add(int(prefix or suffix))
        if declared := _DECLARED_MATERIAL.match(line):
            named_materials.update(_FIBER_BY_WORD[word] for word in re.findall(_FIBER, declared[1]))
        elif line in _FIBER_BY_WORD:
            named_materials.add(_FIBER_BY_WORD[line])
    distinct_brands = {_normalized(brand): brand for brand in sorted(brands)}
    brand = next(iter(distinct_brands.values())) if len(distinct_brands) == 1 else None
    if composition:
        material = None
        if all(len(shares) == 1 for shares in composition.values()):
            parts = [(name, next(iter(shares))) for name, shares in composition.items()]
            if sum(share for _, share in parts) == 100:
                material = ", ".join(f"{share}% {name.lower()}" for name, share in parts)
    else:
        material = ", ".join(sorted(named_materials)) or None
    fields: LabelFields = {}
    if brand:
        fields["brand"] = brand
    if material:
        fields["material"] = material
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
