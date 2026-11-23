"""Тестовый провайдер: выбирает проверенный поиском состав без языковой модели.

Формат выбора совпадает с форматом реальной LLM; текст карточки собирает сервер.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from app.services.analysis import small_talk_reply
from app.services.llm.base import Messages
from app.services.prompts import PromptContext


class MockLLM:
    provider = "mock"
    model = "rule-based-stylist"

    def __init__(self, stream_delay_s: float = 0.0) -> None:
        self._delay = stream_delay_s

    async def complete(
        self, messages: Messages, *, context: PromptContext | None, temperature: float
    ) -> str:
        if context is None:
            text = small_talk_reply(messages[-1]["content"]) or (
                "Обсуждение моды доступно с подключённой языковой моделью. "
                "В деморежиме я могу подобрать образ из гардероба."
            )
            return json.dumps({"text": text, "outfit": None}, ensure_ascii=False)
        return json.dumps({"outfit": {"item_ids": [item.id for item in context.assembly.items]}})

    async def stream(
        self, messages: Messages, *, context: PromptContext | None, temperature: float
    ) -> AsyncIterator[str]:
        raw = await self.complete(messages, context=context, temperature=temperature)
        step = 12
        for start in range(0, len(raw), step):
            if self._delay:
                await asyncio.sleep(self._delay)
            yield raw[start : start + step]
