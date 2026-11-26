"""Короткий комментарий стилиста по уже проверенным вещам, без пересказа карточки."""
from __future__ import annotations

import re

from app.schemas import CATEGORY_LABELS_RU, WardrobeItem
from app.services.analysis import QueryAnalysis
from app.services.followup import mentioned_garments
from app.services.textutils import normalize, tokenize


def _labels(item: WardrobeItem) -> str:
    # Не используем embeddingSnippet: в нём могут быть упомянуты чужие вещи.
    return normalize(" ".join((item.title, *item.tags)))


def _color_note(first: WardrobeItem | None, second: WardrobeItem | None) -> str:
    a = first.color.strip().lower() if first else ""
    b = second.color.strip().lower() if second else ""
    if not a or not b:
        return ""
    if normalize(a) == normalize(b):
        return f"Оттенок «{a}» повторяется и связывает комплект."
    return f"Оттенки «{a}» и «{b}» задают палитру; дополнительные акценты лучше оставить спокойными."


def styling_comment(items: list[WardrobeItem], analysis: QueryAnalysis) -> str:
    by_slot = {item.category: item for item in items}
    top, bottom = by_slot.get("tops"), by_slot.get("bottoms")
    layer = by_slot.get("outerwear")
    top_labels = _labels(top) if top else ""
    bottom_labels = _labels(bottom) if bottom else ""
    palette = _color_note(top, bottom)
    if layer and analysis.needs_outerwear:
        return "Верхний слой удобно снять в помещении: пропорции и палитра комплекта от этого не меняются." + (f" {palette}" if palette else "")
    if any(term in bottom_labels for term in ("палаццо", "широк", "свободн")):
        return "Свободный низ выглядит собраннее, если обозначить линию талии: попробуйте слегка заправить верх спереди."
    if any(term in top_labels for term in ("оверсайз", "объемн", "свободн")):
        return "Свободный верх задаёт расслабленный силуэт. Чтобы сохранить пропорции, попробуйте обозначить талию спереди."
    if layer:
        return "Верхний слой добавляет силуэту структуру. Если погода позволяет, носите его расстёгнутым, чтобы не скрывать линии комплекта."
    return palette or "Чтобы сохранить чистую линию силуэта, попробуйте слегка заправить верх и оставьте только один заметный аксессуар."


_GENERIC_MENTIONS = frozenset({
    "верх", "верхняя одежда", "слой", "низ", "обувь", "аксессуар",
})
_MENTION_ALIASES = {
    "брюк": "брюки",
    "штан": "брюки",
    "слоя": "слой",
    "аксес": "аксессуар",
    "обув": "обувь",
}
_COLOR_NAMES = {
    "black": "черный", "white": "белый", "gray": "серый", "grey": "серый", "beige": "бежевый",
    "brown": "коричневый", "blue": "синий", "light blue": "голубой", "navy": "темно-синий",
    "olive": "оливковый", "olive green": "оливковый", "green": "зеленый", "red": "красный",
    "pink": "розовый", "yellow": "желтый", "orange": "оранжевый", "purple": "фиолетовый",
}
_COLOR_STEMS = {tuple(tokenize(name)): name for name in (*_COLOR_NAMES.values(), "бордовый", "хаки")}
_NEUTRAL_TONES = frozenset({"черный", "белый", "серый", "бежевый"})
_COMPANIONS = {"tops": "bottoms", "bottoms": "tops", "outerwear": "tops", "shoes": "bottoms"}
_PAIR_CONNECTOR = re.compile(r"\b(?:с|со|к|ко|под|и)\b")


def _garment_key(word: str) -> str:
    if word.startswith("верхн"):
        return "верхняя одежда"
    # У грубого стеммера для поиска нет окончания «-ами».
    key = " ".join(tokenize(re.sub(r"(?:ами|ями)$", "", word), drop_stopwords=False))
    return _MENTION_ALIASES.get(key, key)


def _known_color(value: str) -> str:
    value = normalize(value.strip())
    return _COLOR_NAMES.get(value) or _COLOR_STEMS.get(tuple(tokenize(value)), "")


def _item_color(item: WardrobeItem) -> str:
    if color := _known_color(item.color):
        return color
    title = re.findall(r"[а-я]+(?:-[а-я]+)?", normalize(item.title))
    colors = {_known_color(word) for word in title} - {""}
    return colors.pop() if len(colors) == 1 else ""


def _matches_garment(item: WardrobeItem, word: str, query: str) -> bool:
    key = _garment_key(word)
    labels = _labels(item)
    garment_keys = {_garment_key(match) for slot, match in mentioned_garments(labels) if slot == item.category}
    if key == "брюки":
        # «Штаны» и «брюки» подходят и для чиносов, но не для юбки или шорт.
        if not garment_keys.intersection({"брюки", "чинос", "джинс", "легин", "легги"}):
            return False
    elif key not in _GENERIC_MENTIONS and key not in garment_keys:
        return False

    # Не подставляем вещь из карточки, если в вопросе явно назван другой цвет.
    qualifiers = re.findall(rf"\b([а-я]+(?:-[а-я]+)?)\s+{re.escape(word)}\b", query)
    color = _item_color(item)
    for qualifier in qualifiers:
        requested = _known_color(qualifier)
        if requested and color and requested != color:
            return False
    return True


def _compatibility_reason(first: WardrobeItem, second: WardrobeItem) -> str:
    a, b = _item_color(first), _item_color(second)
    if "оливковый" in (a, b) and {a, b}.intersection({"синий", "темно-синий", "голубой"}):
        blue = "Голубой" if "голубой" in (a, b) else "Синий"
        return f"{blue} даёт прохладный контраст приглушённому оливковому."
    if {a, b} == {"черный", "белый"}:
        return "Чёрный и белый дают чёткий контраст по светлоте, не добавляя других цветов."
    if a and a == b:
        return f"Общий цвет «{a}» связывает вещи; близость оттенков лучше проверить рядом."
    if a and b and ({a, b} & _NEUTRAL_TONES):
        neutral, other = (a, b) if a in _NEUTRAL_TONES else (b, a)
        return (f"Цвет «{neutral}» служит нейтральным фоном для цвета «{other}». "
                "Точный контраст зависит от оттенков.")

    by_slot = {first.category: first, second.category: second}
    top, bottom = by_slot.get("tops"), by_slot.get("bottoms")
    if top and bottom and "рубашк" in _labels(top) and "чинос" in _labels(bottom):
        return "Рубашка делает комплект собраннее, а чиносы снижают формальность — это сочетание в духе smart casual."

    shared_styles = {normalize(style.strip()) for style in first.style} & {
        normalize(style.strip()) for style in second.style
    }
    if shared_styles.intersection({"smart-casual", "smart casual"}):
        return "По стилю обе вещи относятся к smart casual: их можно носить вместе в нестрогом, но собранном образе."
    if shared_styles.intersection({"casual", "повседневный"}):
        return "По степени формальности вещи близки: обе рассчитаны на повседневный образ."
    if shared_styles.intersection({"business", "деловой"}):
        return "По степени формальности вещи близки: обе отмечены как деловые."
    return ""


def compatibility_answer(items: list[WardrobeItem], query: str) -> str:
    """Оценить сочетание именно тех вещей, о которых спросили, не меняя карточку."""
    mentions = mentioned_garments(query)
    text = normalize(query)
    by_slot: dict[str, list[WardrobeItem]] = {}
    for item in items:
        by_slot.setdefault(item.category, []).append(item)

    chosen: list[WardrobeItem] = []
    for slot, word in mentions:
        candidates = [item for item in by_slot.get(slot, []) if _matches_garment(item, word, text)]
        if not candidates:
            if current := by_slot.get(slot):
                titles = ", ".join(f"«{item.title}»" for item in current)
                return f"В текущей карточке есть {titles}, но не нахожу то, что вы назвали. Уточните, какую вещь сравнить."
            return f"В текущей карточке нет вещи в категории «{CATEGORY_LABELS_RU[slot]}». Уточните, что сравнить."
        if len(candidates) > 1:
            return f"Уточните, какую вещь из категории «{CATEGORY_LABELS_RU[slot]}» вы имеете в виду."
        if not any(item.id == candidates[0].id for item in chosen):
            chosen.append(candidates[0])

    if len(chosen) < 2 and _PAIR_CONNECTOR.search(text):
        return "Не удалось определить обе вещи по текущей карточке. Уточните, какую пару вы имеете в виду."

    if not chosen:
        top, bottom = by_slot.get("tops", []), by_slot.get("bottoms", [])
        if len(top) == len(bottom) == 1:
            chosen = [top[0], bottom[0]]
        elif len(items) == 2:
            chosen = items
    elif len(chosen) == 1:
        other = [item for item in items if item.id != chosen[0].id]
        companions = by_slot.get(_COMPANIONS.get(chosen[0].category, ""), [])
        if len(other) == 1:
            chosen = [*chosen, *other]
        elif len(companions) == 1:
            chosen.extend(companions)

    if len(chosen) != 2:
        return "Уточните, какие две вещи вы хотите сравнить. Если одной из них нет в карточке, опишите её."
    first, second = chosen
    pair = f"«{first.title}» и «{second.title}»"
    if reason := _compatibility_reason(first, second):
        return f"{pair} могут сочетаться. {reason} Посадку и пропорции лучше оценить на примерке."
    return f"Для пары {pair} по описанию не хватает данных. Лучше сравнить оттенки рядом, а пропорции — на примерке."
