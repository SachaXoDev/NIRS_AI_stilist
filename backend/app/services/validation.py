"""Разбор ответа LLM и проверка его формы.

Модель возвращает только id вещей и тексты. Сами id проверяет поисковый движок
(`RagEngine.validate_selection`), а полные объекты вещей сервер подставляет из гардероба —
поэтому «галлюцинированная» вещь не может попасть в ответ.
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, field_validator

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
# Reasoning-модели (в т.ч. Qwen3) могут прислать размышления перед ответом.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
MAX_TIPS = 3
MAX_TEXT_CHARS = 1200


class OutfitDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str = ""
    description: str = ""
    occasion: str = ""
    item_ids: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices("item_ids", "itemIds", "items")
    )
    stylist_reasoning: str = Field(
        default="",
        validation_alias=AliasChoices("stylistReasoning", "stylist_reasoning", "reasoning"),
    )
    confidence_tips: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("confidenceTips", "confidence_tips", "tips"),
    )

    @field_validator("item_ids", mode="before")
    @classmethod
    def _coerce_ids(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, (str, int)):
            return [str(value)]
        ids = []
        for entry in value:
            if isinstance(entry, dict):
                entry = entry.get("id")
            if entry is not None and str(entry).strip():
                ids.append(str(entry).strip())
        return ids

    @field_validator("confidence_tips", mode="before")
    @classmethod
    def _coerce_tips(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(v).strip() for v in value if v is not None and str(v).strip()]

    @field_validator("title", "description", "occasion", "stylist_reasoning", mode="before")
    @classmethod
    def _none_to_empty(cls, value: Any) -> Any:
        return "" if value is None else str(value).strip()


class StylistDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = ""
    outfit: OutfitDraft | None = None

    @field_validator("text", mode="before")
    @classmethod
    def _text_to_str(cls, value: Any) -> Any:
        return "" if value is None else str(value).strip()


class DraftParseError(ValueError):
    pass


def parse_draft(raw: str) -> StylistDraft:
    """Достать JSON из ответа модели: терпим <think>-блоки, ```-ограждения и текст вокруг."""
    text = _FENCE_RE.sub("", _THINK_RE.sub("", raw).strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise DraftParseError("ответ не содержит JSON-объекта")
    try:
        data = json.loads(text[start : end + 1])
    except ValueError as exc:
        raise DraftParseError(f"невалидный JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DraftParseError("ожидался JSON-объект")
    try:
        return StylistDraft.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:5])
        raise DraftParseError(f"JSON не соответствует схеме: {problems}") from exc


def field_errors(draft: StylistDraft) -> list[str]:
    """Ошибки текстовых полей. Пустой список — форма ответа в порядке."""
    errors: list[str] = []
    if not draft.text:
        errors.append('поле "text" пустое')
    elif len(draft.text) > MAX_TEXT_CHARS:
        errors.append(f'поле "text" длиннее {MAX_TEXT_CHARS} символов — нужно 1–2 предложения')
    outfit = draft.outfit
    if outfit is None:
        return errors  # разговорная реплика без образа — допустимый ответ
    if not outfit.item_ids:
        errors.append('"outfit.item_ids" пуст: выбери вещи из кандидатов или верни "outfit": null')
    if not outfit.title:
        errors.append('поле "outfit.title" пустое')
    if not outfit.stylist_reasoning:
        errors.append('поле "outfit.stylistReasoning" пустое')
    if not outfit.confidence_tips:
        errors.append('в "outfit.confidenceTips" нужен хотя бы один совет')
    return errors
