import asyncio
import json

import httpx
import pytest

from app.services.llm.base import LLMError
from app.services.llm.openai_compat import OpenAICompatLLM

MESSAGES = [{"role": "user", "content": "привет"}]


def _llm(handler, **kwargs) -> OpenAICompatLLM:
    return OpenAICompatLLM(
        base_url="http://llm.local/v1/",
        api_key="secret",
        model="qwen2.5:7b",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_complete_sends_openai_payload_and_returns_content():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"text": "ок"}'}}]})

    result = asyncio.run(_llm(handler).complete(MESSAGES, context=None, temperature=0.3))

    assert result == '{"text": "ок"}'
    assert seen["url"] == "http://llm.local/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "qwen2.5:7b"
    assert seen["body"]["temperature"] == 0.3
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["stream"] is False


def test_json_mode_can_be_disabled():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    asyncio.run(_llm(handler, json_mode=False).complete(MESSAGES, context=None, temperature=0.3))
    assert "response_format" not in seen["body"]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="boom"),
        httpx.Response(401, json={"error": "bad key"}),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}),
        httpx.Response(200, text="not json"),
    ],
)
def test_complete_wraps_failures_in_llm_error(response):
    with pytest.raises(LLMError):
        asyncio.run(_llm(lambda request: response).complete(MESSAGES, context=None, temperature=0.3))


def test_network_error_becomes_llm_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    with pytest.raises(LLMError):
        asyncio.run(_llm(handler).complete(MESSAGES, context=None, temperature=0.3))


def test_stream_parses_sse_deltas():
    body = (
        'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"{\\"text\\": \\"При"}}]}\n\n'
        ": keep-alive\n\n"
        'data: {"choices":[{"delta":{"content":"вет\\"}"}}]}\n\n'
        'data: {"choices":[]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, content=body.encode(), headers={"content-type": "text/event-stream"})

    async def collect() -> str:
        return "".join([c async for c in _llm(handler).stream(MESSAGES, context=None, temperature=0.3)])

    assert asyncio.run(collect()) == '{"text": "Привет"}'


def test_stream_http_error_becomes_llm_error():
    async def collect() -> list[str]:
        llm = _llm(lambda request: httpx.Response(429, text="rate limit"))
        return [c async for c in llm.stream(MESSAGES, context=None, temperature=0.3)]

    with pytest.raises(LLMError):
        asyncio.run(collect())


def test_extra_body_is_merged_into_payload():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    llm = _llm(handler, extra_body={"reasoning": {"enabled": False}})
    asyncio.run(llm.complete(MESSAGES, context=None, temperature=0.3))
    assert seen["body"]["reasoning"] == {"enabled": False}
    assert seen["body"]["model"] == "qwen2.5:7b"
