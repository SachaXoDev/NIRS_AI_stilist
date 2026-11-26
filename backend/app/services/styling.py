"""Короткий комментарий стилиста по уже проверенным вещам, без пересказа карточки."""
from __future__ import annotations

from app.schemas import WardrobeItem
from app.services.analysis import QueryAnalysis
from app.services.textutils import normalize


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


def styling_comment(items: list[WardrobeItem], analysis: QueryAnalysis, *, focus: WardrobeItem | None = None) -> str:
    by_slot = {item.category: item for item in items}
    top, bottom = by_slot.get("tops"), by_slot.get("bottoms")
    layer = by_slot.get("outerwear")
    if focus is not None:
        labels = _labels(focus)
        if focus.category == "shoes":
            if "кеды" in labels or "кроссовки" in labels:
                return "С этой парой образ выглядит менее формально. Если брюки длинные, проверьте, чтобы край не касался земли."
            if "плоская подошва" in labels or "без каблука" in labels:
                return "Плоская подошва смягчает строгость комплекта. Если низ длинный, проверьте, чтобы край не касался земли."
            return _color_note(focus, bottom) or "Повторите оттенок обуви в небольшой детали, чтобы связать её с остальным образом."
        if focus.category == "outerwear":
            return "Верхний слой обрамляет комплект. В помещении можно снять его, не меняя основу образа."
        if focus.category == "accessories":
            return _color_note(focus, top) or "Пусть этот аксессуар будет единственным заметным акцентом."

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
