"""Какую вещь пользователь назвал в правке образа: «добавь сумку», «замени брюки на юбку».

Нужно запасному встроенному поиску. `wardrobe_rag` разбирает названные типы сам
(`query_attributes`), а лексический BM25 ранжирует кандидатов слота по сочетаемости и мог
предложить бейсболку на просьбу о сумке или джинсы вместо юбки. Здесь тот же принцип в
простом виде: просили юбку — среди кандидатов остаются только юбки; если такой вещи нет,
кандидатов нет, и редактор оставляет образ без изменений.
"""
from __future__ import annotations

import re
from functools import lru_cache

from snowballstemmer import stemmer

from app.schemas import WardrobeItem
from app.services.followup import classify_followup, mentioned_garments
from app.services.textutils import normalize

_WORD = re.compile(r"[a-zа-я]+")
_RUSSIAN = stemmer("russian")


@lru_cache(maxsize=4096)
def _stem(word: str) -> str:
    return _RUSSIAN.stemWord(word)


def _stems(*words: str) -> frozenset[str]:
    return frozenset(_stem(word) for word in words)


# Одна и та же вещь под разными названиями.
_SYNONYMS: tuple[frozenset[str], ...] = (
    _stems("пиджак", "жакет", "блейзер"),
    _stems("свитер", "джемпер", "пуловер"),
    _stems("блуза", "блузка"),
    _stems("плащ", "тренч", "тренчкот"),
    _stems("кепка", "бейсболка"),
    _stems("сумка", "сумочка"),
    _stems("легинсы", "леггинсы", "лосины"),
)
# Общее название включает частные: просили брюки — джинсы подходят, но не наоборот.
_INCLUDES: dict[str, frozenset[str]] = {
    general: _stems(*specific.split())
    for names, specific in (
        ("брюки штаны", "джинсы чиносы легинсы леггинсы палаццо кюлоты"),
        ("куртка", "ветровка бомбер парка пуховик джинсовка дождевик косуха"),
        ("туфли", "лодочки лоферы дерби балетки мокасины"),
        ("ботинки", "ботильоны челси"),
        ("сумка сумочка", "тоут клатч шопер"),
        ("шапка", "бини"),
    )
    for general in _stems(*names.split())
}
# Название категории («обувь», «аксессуар») и признак («на каблуке») — не тип вещи.
_NOT_A_TYPE = re.compile(r"обув|аксессуар|верх|низ|сло[йяею]|одежд|каблук")


_OR = re.compile(r"\b(?:или|либо)\b")


def requested_types(query: str, slot: str) -> list[str]:
    """Слова, которыми пользователь назвал нужную вещь слота; пусто — тип не задан.

    Для замены это вещь после «на» («замени брюки на юбку» → «юбку»), для добавления — сама
    названная вещь («добавь сумку» → «сумку»); через «или» можно назвать несколько. Правка
    нескольких слотов сразу и отказ от вещи («не хочу кеды») нужного типа не задают.
    """
    follow_up = classify_followup(query)
    if follow_up is None or follow_up.slot is None or follow_up.reject_type or follow_up.extra_targets:
        return []
    text = normalize(query)
    if follow_up.kind == "replace":
        _, separator, text = text.partition(" на ")
        if not separator:
            return []
    elif follow_up.kind != "add":
        return []
    words = [word for found, word in mentioned_garments(text) if found == slot and not _NOT_A_TYPE.match(word)]
    return words if _OR.search(text) else words[:1]


def _close(left: str, right: str) -> bool:
    if left == right:
        return True
    # «платок» / «платком»: беглая гласная даёт разные основы. Короткие основы так не
    # сравниваем, иначе «платок» совпадёт с «платьем».
    shortest = min(len(left), len(right))
    if shortest < 5:
        return False
    common = next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), shortest)
    return common >= shortest - 1


def is_type(item: WardrobeItem, word: str) -> bool:
    """Относится ли вещь к названному типу — по словам названия и тегов."""
    stem = _stem(normalize(word))
    wanted = {stem} | _INCLUDES.get(stem, frozenset())
    for group in _SYNONYMS:
        if stem in group:
            wanted |= group
    labels = {_stem(token) for label in (item.title, *item.tags) for token in _WORD.findall(normalize(label))}
    return any(_close(a, b) for a in wanted for b in labels)
