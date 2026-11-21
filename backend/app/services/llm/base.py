"""Интерфейс LLM-клиента. Оркестратор знает только про него, а не про конкретного провайдера."""
from __future__ import annotations

from typing import AsyncIterator, Protocol

from app.services.prompts import PromptContext

Messages = list[dict[str, str]]


class LLMError(RuntimeError):
    """Провайдер недоступен или вернул ответ, который нельзя использовать."""


class LLMClient(Protocol):
    provider: str
    model: str

    async def complete(
        self, messages: Messages, *, context: PromptContext, temperature: float
    ) -> str:
        """Вернуть сырой текст ответа модели (ожидается JSON)."""
        ...

    def stream(
        self, messages: Messages, *, context: PromptContext, temperature: float
    ) -> AsyncIterator[str]:
        """То же, но чанками по мере генерации."""
        ...
