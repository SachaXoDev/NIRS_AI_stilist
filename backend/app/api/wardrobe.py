"""Гардероб на сервере: синхронизация полным снимком (контракт `rag/INTEGRATION.md`).

`user_id` приходит от клиента — это демо-идентификатор, а не защищённая сессия.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_service
from app.rag.base import RagEngineError
from app.schemas import WardrobeItem, WardrobeResponse, WardrobeSyncRequest
from app.services.orchestrator import StylistService
from app.storage.app_store import load_wardrobe_file

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
    return load_wardrobe_file()
