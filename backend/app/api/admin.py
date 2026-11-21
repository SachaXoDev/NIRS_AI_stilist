"""Настройки куратора: то, что в админке фронтенда сейчас живёт только в состоянии компонента."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps import get_app_settings, get_service
from app.config import Settings
from app.schemas import AdminSettingsResponse, RuntimeSettingsPatch
from app.services.orchestrator import StylistService

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _response(service: StylistService, settings: Settings) -> AdminSettingsResponse:
    provider, model = service.llm_info
    return AdminSettingsResponse(
        settings=service.get_runtime_settings(),
        llm_provider=provider,
        llm_model=model,
        retriever=service.engine_name,
        editable=bool(settings.admin_token),
    )


@router.get("/settings", response_model=AdminSettingsResponse, summary="Текущие настройки пайплайна")
def get_admin_settings(
    service: StylistService = Depends(get_service),
    settings: Settings = Depends(get_app_settings),
) -> AdminSettingsResponse:
    return _response(service, settings)


@router.put("/settings", response_model=AdminSettingsResponse, summary="Изменить режим поиска, веса, температуру, персону")
def update_admin_settings(
    patch: RuntimeSettingsPatch,
    x_admin_token: str | None = Header(default=None),
    service: StylistService = Depends(get_service),
    settings: Settings = Depends(get_app_settings),
) -> AdminSettingsResponse:
    if not settings.admin_token:
        raise HTTPException(
            status_code=403,
            detail="Изменение настроек отключено: задайте ADMIN_TOKEN в окружении сервера",
        )
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Неверный X-Admin-Token")
    service.update_runtime_settings(patch.model_dump(exclude_none=True))
    return _response(service, settings)
