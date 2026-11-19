"""Canonical documents and shared Russian lexical preprocessing."""

from __future__ import annotations

import re
from functools import lru_cache

from .schemas import WardrobeItem

CATEGORY_LABELS = {
    "tops": "верх",
    "bottoms": "низ",
    "shoes": "обувь",
    "outerwear": "верхняя одежда",
    "accessories": "аксессуары",
}
SEASON_LABELS = {
    "all": "всесезонный",
    "spring/summer": "весна лето",
    "autumn/winter": "осень зима",
}
# Symmetric lexical normalization: aliases apply to corpus AND query.
ALIASES = {
    "business": "деловой", "casual": "повседневный", "minimalism": "минимализм",
    "cozy": "уютный", "classic": "классический", "chic": "элегантный",
    "streetwear": "уличный", "accent": "акцент", "french": "французский",
    "tops": "верх", "bottoms": "низ", "shoes": "обувь",
    "outerwear": "верхняя одежда", "accessories": "аксессуары",
}
STOPWORDS = frozenset("и в во на для с со к ко из по под над а или мне мой моя мои пожалуйста подбери собери образ лук хочу нужен нужна нужно чтобы это как что надеть".split())


def build_document(item: WardrobeItem) -> str:
    """Use current authoritative fields, never a possibly stale embeddingSnippet."""
    parts = [
        CATEGORY_LABELS[item.category], item.title, f"цвет {item.color}",
        f"сезон {SEASON_LABELS[item.season]}",
        "стиль " + " ".join(item.style), "теги " + " ".join(item.tags),
    ]
    if item.material:
        parts.append(f"ткань {item.material}")
    if item.brand:
        parts.append(f"бренд {item.brand}")
    if item.weather is not None:
        if item.weather.waterproof is True:
            parts.append("водонепроницаемый защита от дождя")
        if item.weather.windproof is True:
            parts.append("ветрозащитный")
        if item.weather.open_shoes is True:
            parts.append("открытая обувь")
    return "; ".join(parts)


@lru_cache(maxsize=1)
def _stemmer():
    import snowballstemmer
    return snowballstemmer.stemmer("russian")


@lru_cache(maxsize=32768)
def _stem(token: str) -> str:
    return _stemmer().stemWord(token)


def tokenize(text: str) -> list[str]:
    raw = re.findall(r"[^\W_]+", text.lower().replace("ё", "е"), flags=re.UNICODE)
    expanded: list[str] = []
    for token in raw:
        if token in STOPWORDS:
            continue
        expanded.extend(ALIASES.get(token, token).split())
    return [_stem(token) for token in expanded if token not in STOPWORDS]


def color_tokens(color: str) -> set[str]:
    return set(tokenize(color))
