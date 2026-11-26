"""Conservative category mapping for garment titles, independent of retrieval."""
import re

from app.schemas import Category

_TYPES: dict[Category, str] = {
    "shoes": (r"обувь|кроссовк\w*|кроссовок|кед(?:ы|а|ов)?|туфл\w*|лофер\w*|лодочки|балетк\w*|"
              r"ботин\w*|сапог\w*|ботильон\w*|сандал\w*|босоножк\w*|мокасин\w*|shoes?|sneakers?|trainers?|boots?|sandals?|loafers?"),
    "outerwear": (r"верхн\w+\s+одежд\w*|пальто|тренч\w*|плащ\w*|куртк\w*|парка|пуховик\w*|ветровк\w*|"
                  r"жакет\w*|блейзер\w*|пиджак\w*|бомбер\w*|джинсовк\w*|coats?|jackets?|blazers?|parkas?"),
    "tops": (r"верх|футболк\w*|топ(?:ы|ик\w*)?|майк\w*|рубашк\w*|блуз\w*|свитер\w*|худи|джемпер\w*|"
             r"кардиган\w*|свитшот\w*|водолазк\w*|t[- ]?shirts?|shirts?|blouses?|sweaters?|hoodies?|cardigans?|tops?"),
    "bottoms": r"брюк\w*|джинс(?:ы|ами|ов)?|юбк\w*|шорт\w*|штан\w*|лег[г]?инс\w*|jeans|trousers|pants|skirts?|shorts|leggings",
    "accessories": (r"аксессуар\w*|сумк\w*|рюкзак\w*|шарф\w*|платок|платк\w*|ремень|ремни|шапк\w*|кепк\w*|"
                    r"головн\w+\s+убор\w*|шляп\w*|bags?|backpacks?|scar(?:f|ves)|belts?|hats?|caps?"),
}
_PATTERNS = [(category, re.compile(rf"\b(?:{types})\b", re.IGNORECASE)) for category, types in _TYPES.items()]


def category_from_title(title: str) -> Category | None:
    matches = [category for category, pattern in _PATTERNS if pattern.search(title)]
    return matches[0] if len(matches) == 1 else None
