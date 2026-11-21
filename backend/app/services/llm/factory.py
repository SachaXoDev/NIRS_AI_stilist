from __future__ import annotations

import json

from app.config import Settings
from app.services.llm.base import LLMClient
from app.services.llm.mock import MockLLM
from app.services.llm.openai_compat import OpenAICompatLLM


def _extra_body(raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except ValueError as exc:
        raise ValueError(f"LLM_EXTRA_BODY должен быть JSON-объектом: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("LLM_EXTRA_BODY должен быть JSON-объектом")
    return value


def build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "openai":
        return OpenAICompatLLM(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_s=settings.llm_timeout_s,
            json_mode=settings.llm_json_mode,
            extra_body=_extra_body(settings.llm_extra_body),
        )
    return MockLLM(stream_delay_s=settings.mock_stream_delay_s)
