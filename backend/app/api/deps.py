from __future__ import annotations

from fastapi import Request

from app.config import Settings
from app.services.orchestrator import StylistService


def get_service(request: Request) -> StylistService:
    return request.app.state.service


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings
