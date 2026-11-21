"""Нормализация и грубый стемминг русского текста без внешних зависимостей.

Это база для встроенного BM25 и разбора запроса. В боевом ретривере (см. `spec/tech/rag.md`)
морфология делается через pymorphy3/Snowball — здесь задача проще: чтобы «деловой» и
«деловая», «кашемир» и «кашемировый» попадали в один токен.
"""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-zа-я0-9]+")

STOPWORDS = frozenset(
    """
    и в во на с со к ко по из за от до для о об у а но или же ли бы не ни что чтобы как
    это этот эта эти тот та те мой моя мое мои моей моего мне меня я ты вы мы он она они
    его ее их есть быть был была было буду будет очень самый самая всего всегда уже еще
    при над под про без через между там тут здесь так тоже также если то где когда
    подбери подобрать подберите собери собрать соберите составь составить образ образа
    лук аутфит комплект вещь вещью вещи вещей хочу хочется нужен нужна нужно надо можно
    пожалуйста посоветуй посоветуйте что-нибудь какой какая какие чем ней нее
    """.split()
)

# Окончания, от длинных к коротким. Отрезаем только если остаётся основа ≥ 3 символов.
_SUFFIXES = tuple(
    sorted(
        """
        овыми евыми овому евому овую евую овый евый овая евая овое евое овые евые овых евых
        овым евым овой евой ового евого
        иями ями ами ией иях ого его ому ему ыми ими
        ая яя ое ее ые ие ый ий ой ую юю ых их ым им ом ем ей ам ям ах ях ов ев
        а я ы и о е у ю ь й
        """.split(),
        key=len,
        reverse=True,
    )
)
_STEM_LEN = 5


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е")


def stem(token: str) -> str:
    if len(token) <= 3 or not ("а" <= token[0] <= "я"):
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    return token[:_STEM_LEN]


def tokenize(text: str, *, drop_stopwords: bool = True) -> list[str]:
    tokens = _TOKEN_RE.findall(normalize(text))
    if drop_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return [stem(t) for t in tokens]
