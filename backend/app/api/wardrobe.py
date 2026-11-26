"""Гардероб на сервере: синхронизация полным снимком (контракт `rag/INTEGRATION.md`).

`user_id` приходит от клиента — это демо-идентификатор, а не защищённая сессия.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_service
from app.rag.base import RagEngineError
from app.schemas import PhotoRecognitionResponse, WardrobeItem, WardrobeResponse, WardrobeSyncRequest
from app.services.label_ocr import read_text
from app.services.orchestrator import StylistService
from app.services.photo_recognition import MAX_PHOTO_BYTES, PHOTO_FORMATS, InvalidPhoto, decode_photo
from app.services.product_text import suggest_from_text
from app.storage.app_store import load_base_capsule

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wardrobe", tags=["wardrobe"])


@router.post(
    "/sync",
    summary="Заменить гардероб пользователя полным снимком и переиндексировать",
    response_description=(
        "SyncResult: revision, indexed_count, image_count, added/updated/deleted/unchanged_count, "
        "warnings, timings_ms"
    ),
)
async def sync_wardrobe(
    payload: WardrobeSyncRequest, service: StylistService = Depends(get_service)
) -> dict[str, Any]:
    """Повторный снимок идемпотентен; отсутствующие в нём вещи удаляются из индекса;
    пустой массив очищает гардероб только этого пользователя."""
    try:
        return await service.sync_wardrobe(payload.user_id, payload.items)
    except RagEngineError as exc:
        logger.warning("Wardrobe sync failed: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=WardrobeResponse, summary="Текущий снимок гардероба на сервере")
async def get_wardrobe(
    user_id: str = Query(min_length=1, max_length=200),
    service: StylistService = Depends(get_service),
) -> WardrobeResponse:
    return WardrobeResponse(user_id=user_id, items=await service.get_wardrobe(user_id))


@router.get("/base-capsule", response_model=list[WardrobeItem], summary="Базовая капсула бренда")
def base_capsule() -> list[WardrobeItem]:
    return load_base_capsule()


@router.post(
    "/recognize",
    response_model=PhotoRecognitionResponse,
    summary="Предложить поля гардероба по фото вещи или бирки",
    openapi_extra={"requestBody": {"required": True, "content": {
        media_type: {"schema": {"type": "string", "format": "binary"}} for media_type in PHOTO_FORMATS
    }}},
)
async def recognize_photo(request: Request, label_only: bool = False) -> PhotoRecognitionResponse:
    recognizer = request.app.state.photo_recognizer
    if recognizer is None:
        raise HTTPException(status_code=503, detail="Модель распознавания фото недоступна.")
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type not in PHOTO_FORMATS:
        raise HTTPException(status_code=422, detail="Загрузите фото в формате JPEG, PNG или WebP.")
    photo = bytearray()
    async for chunk in request.stream():
        if len(photo) + len(chunk) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="Размер фото не должен превышать 10 МБ.")
        photo.extend(chunk)
    try:
        image = await run_in_threadpool(decode_photo, photo, media_type)
        lines = await run_in_threadpool(read_text, image)
        suggestion = None if label_only else await run_in_threadpool(recognizer, image)
    except InvalidPhoto as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        logger.exception("Photo inference failed")
        raise HTTPException(status_code=503, detail="Не удалось запустить распознавание фото.") from exc
    if lines and (text_suggestion := await suggest_from_text(lines, request.app.state.product_reader)):
        if suggestion:
            update = text_suggestion.model_dump(exclude_none=True)
            if not (text_suggestion.title and text_suggestion.category):
                # Don't pair a title from one source with a category from another.
                update.pop("title", None)
                update.pop("category", None)
            suggestion = suggestion.model_copy(update=update)
        else:
            suggestion = text_suggestion
    return PhotoRecognitionResponse(suggestion=suggestion)
