"""Клиент для любого OpenAI-совместимого `/chat/completions`.

Один и тот же код работает с OpenAI (GPT-4o), OpenRouter (Llama-3, Qwen), локальными Ollama,
vLLM и LM Studio — меняются только LLM_BASE_URL / LLM_MODEL / LLM_API_KEY.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.services.llm.base import LLMError, Messages
from app.services.prompts import PromptContext, outfit_response_schema


class OpenAICompatLLM:
    provider = "openai"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 30.0,
        json_mode: bool = True,
        outfit_schema: bool = False,
        extra_body: dict[str, Any] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._timeout = httpx.Timeout(timeout_s, connect=min(10.0, timeout_s))
        self._json_mode = json_mode
        self._outfit_schema = outfit_schema
        self._extra_body = dict(extra_body or {})
        self._transport = transport

    def _payload(
        self, messages: Messages, temperature: float, stream: bool, context: PromptContext | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if self._json_mode:
            payload["response_format"] = {"type": "json_object"}
        payload.update(self._extra_body)
        if self._outfit_schema and context is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "stylist_outfit", "schema": outfit_response_schema(context.outcome)},
            }
        return payload

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)

    async def complete(
        self, messages: Messages, *, context: PromptContext | None, temperature: float
    ) -> str:
        try:
            async with self._client() as client:
                response = await client.post(
                    self._url, headers=self._headers, json=self._payload(messages, temperature, False, context)
                )
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"LLM HTTP {exc.response.status_code}: {exc.response.text[:300]}") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError(f"LLM request failed: {exc!r}") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM returned empty content")
        return content

    async def stream(
        self, messages: Messages, *, context: PromptContext | None, temperature: float
    ) -> AsyncIterator[str]:
        try:
            async with self._client() as client:
                async with client.stream(
                    "POST",
                    self._url,
                    headers=self._headers,
                    json=self._payload(messages, temperature, True, context),
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", "replace")
                        raise LLMError(f"LLM HTTP {response.status_code}: {body[:300]}")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {}).get("content")
                        except (ValueError, KeyError, IndexError, AttributeError):
                            continue
                        if delta:
                            yield delta
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM stream failed: {exc!r}") from exc
