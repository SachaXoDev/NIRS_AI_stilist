"""Разбор ответа LLM и проверка его формы.

В подборе модель возвращает ID, а поисковый движок проверяет выбор. Текст
подбора строится из проверенных вещей. Свободный текст используется только в диалоге.
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, field_validator

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
# Reasoning-модели (в т.ч. Qwen3) могут прислать размышления перед ответом.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
MAX_TEXT_CHARS = 1200


class OutfitDraft(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    item_ids: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices("item_ids", "itemIds", "items")
    )

    @field_validator("item_ids", mode="before")
    @classmethod
    def _coerce_ids(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, (str, int)):
            return [str(value)]
        if not isinstance(value, list):
            raise ValueError("ожидается список ID вещей")
        ids = []
        for entry in value:
            if isinstance(entry, dict):
                entry = entry.get("id")
            if entry is not None and str(entry).strip():
                ids.append(str(entry).strip())
        return ids


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
