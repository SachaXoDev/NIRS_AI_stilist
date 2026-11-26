"""Standalone KT-2 demo. Does not read or write a user's wardrobe or chats."""
from __future__ import annotations

import json
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.kt2_search import BM25Index, Document, Hit
from app.services.llm.base import LLMError, Messages
from app.services.llm.openai_compat import OpenAICompatLLM

_DATA = Path(__file__).resolve().parents[1] / "kt2_data"
_CITATION = re.compile(r"\[(D\d{2})\]")
REFUSAL = "В документах нет этой информации."
logger = logging.getLogger(__name__)

_PROMPT = """Ответь по-русски исключительно по документам. Сначала найди сведения для всех частей вопроса. Если не хватает хотя бы одного факта, верни {"parts": []}. Не отвечай на другой вопрос и не используй догадки. Если сведений достаточно, перечисли короткие части ответа: для каждой укажи текст и ID документа, который подтверждает этот текст. Не добавляй ссылки в сами тексты. Для вывода из нескольких документов приведи подтверждённые факты с их источниками.
Пример для вопроса о цвете и цене сумки, если известны оба: {"parts":[{"text":"Сумка синяя.","source_id":"D08"},{"text":"Она стоит 500 рублей.","source_id":"D09"}]}"""


class DemoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KT2_")

    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "qwen2.5:3b"
    llm_timeout_s: float = Field(default=90.0, gt=0)


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=1000)


class Citation(BaseModel):
    id: str
    title: str
    text: str
    score: float

    @classmethod
    def from_hit(cls, hit: Hit) -> Citation:
        return cls(id=hit.document.id, title=hit.document.title, text=hit.document.text, score=hit.score)


class AnswerPart(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True, extra="forbid")

    text: str = Field(min_length=1, max_length=1000)
    source_id: str


class ModelAnswer(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    parts: list[AnswerPart] = Field(max_length=6)


class AskResponse(BaseModel):
    answer: str
    refused: bool
    sources: list[Citation]
    hits: list[Citation]
    model: str


class AnswerModel(Protocol):
    model: str

    async def generate(self, messages: Messages, source_ids: list[str]) -> str: ...


class QwenAnswerModel:
    def __init__(self, settings: DemoSettings) -> None:
        self.settings = settings
        self.model = settings.llm_model

    async def generate(self, messages: Messages, source_ids: list[str]) -> str:
        schema = ModelAnswer.model_json_schema()
        schema["$defs"]["AnswerPart"]["properties"]["source_id"]["enum"] = source_ids
        client = OpenAICompatLLM(
            base_url=self.settings.llm_base_url, api_key="", model=self.model,
            timeout_s=self.settings.llm_timeout_s,
            extra_body={"max_tokens": 700, "response_format": {"type": "json_schema", "json_schema": {
                "name": "kt2_answer", "schema": schema,
            }}},
        )
        return await client.complete(messages, context=None, temperature=0)


async def answer_question(question: str, index: BM25Index, llm: AnswerModel) -> AskResponse:
    hits = [Citation.from_hit(hit) for hit in index.search(question)]
    if not hits:
        return AskResponse(answer=REFUSAL, refused=True, sources=[], hits=[], model=llm.model)

    context = "\n\n".join(f"[{hit.id}] {hit.title}\n{hit.text}" for hit in hits)
    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": f"Документы:\n{context}\n\nВопрос: {question}"},
    ]
    by_id = {hit.id: hit for hit in hits}
    draft = ModelAnswer.model_validate_json(await llm.generate(messages, list(by_id)))
    if not draft.parts:
        return AskResponse(answer=REFUSAL, refused=True, sources=[], hits=hits, model=llm.model)

    cited: dict[str, Citation] = {}
    paragraphs: list[str] = []
    for part in draft.parts:
        if part.source_id not in by_id or _CITATION.search(part.text):
            raise LLMError("Answer has foreign or inconsistent citations")
        cited[part.source_id] = by_id[part.source_id]
        paragraphs.append(f"{part.text} [{part.source_id}]")
    return AskResponse(answer="\n".join(paragraphs), refused=False, sources=list(cited.values()),
                       hits=hits, model=llm.model)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = DemoSettings()
    documents = json.loads((_DATA / "corpus.json").read_text(encoding="utf-8"))
    app.state.index = BM25Index(Document(**document) for document in documents)
    app.state.llm = QwenAnswerModel(settings)
    yield


app = FastAPI(title="AI LOOKBOOK — КТ-2", lifespan=lifespan)


@app.get("/kt2", include_in_schema=False)
async def demo() -> FileResponse:
    return FileResponse(Path(__file__).with_name("kt2_demo.html"), media_type="text/html")


@app.post("/api/kt2/ask", response_model=AskResponse)
async def ask(payload: AskRequest, request: Request) -> AskResponse:
    try:
        return await answer_question(payload.question, request.app.state.index, request.app.state.llm)
    except ValidationError as exc:
        logger.warning("Invalid KT-2 LLM output: %s", exc)
        raise HTTPException(502, "Модель вернула ответ некорректного формата. Повторите запрос.") from exc
    except LLMError as exc:
        logger.warning("KT-2 model failed: %s", exc)
        raise HTTPException(502, "Не удалось получить ответ модели с корректными источниками.") from exc
