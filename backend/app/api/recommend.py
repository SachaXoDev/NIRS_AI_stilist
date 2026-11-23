"""Рекомендация образа: обычный JSON-эндпоинт (контракт КТ-1) и потоковый SSE-вариант."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_service
from app.rag.base import RagEngineError
from app.schemas import RecommendRequest, RecommendResponse
from app.services.orchestrator import StylistService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["stylist"])

GENERIC_ERROR = "Не удалось получить ответ стилиста. Повторите запрос."


@router.post(
    "/recommend-outfit",
    response_model=RecommendResponse,
    response_model_exclude_none=True,
    summary="Подобрать образ из гардероба пользователя",
    responses={503: {"description": "Поисковый движок не смог обработать запрос"}},
)
async def recommend_outfit(
    payload: RecommendRequest, service: StylistService = Depends(get_service)
) -> RecommendResponse:
    try:
        return await service.recommend(payload)
    except RagEngineError as exc:
        logger.warning("RAG engine error: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post(
    "/recommend-outfit/stream",
    summary="То же, но с этапами и текстом через Server-Sent Events",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": (
                "События: `status` {stage}, `retrieval` (диагностика поиска), `delta` {text}, "
                "`result` (полный ответ, как у /api/recommend-outfit), `error` {message}."
            ),
        }
    },
)
async def recommend_outfit_stream(
    payload: RecommendRequest, service: StylistService = Depends(get_service)
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        # Заголовки ответа уже отправлены, поэтому об ошибке сообщаем событием.
        try:
            async for event, data in service.recommend_stream(payload):
                yield _sse(event, data)
        except RagEngineError as exc:
            logger.warning("RAG engine error: %s", exc)
            yield _sse("error", {"message": str(exc)})
        except Exception:  # noqa: BLE001
            logger.exception("Streaming recommendation failed")
            yield _sse("error", {"message": GENERIC_ERROR})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
