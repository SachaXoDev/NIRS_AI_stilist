"""Точка входа: `uvicorn app.main:app --port 8000` (из каталога backend/)."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, recommend, wardrobe
from app.config import Settings, get_settings
from app.rag.base import RagEngine
from app.rag.factory import build_engine
from app.services.llm.base import LLMClient
from app.services.llm.factory import build_llm
from app.services.orchestrator import StylistService
from app.storage.app_store import DEMO_USER_ID, AppStore, load_base_capsule, load_wardrobe_file

API_VERSION = "0.2.0"
logger = logging.getLogger(__name__)


def _seed_demo_wardrobe(engine: RagEngine, settings: Settings) -> None:
    """Демо-пользователь с базовой капсулой — чтобы запрос с одним `query` сразу работал."""
    if engine.get_items(DEMO_USER_ID):
        return
    items = load_wardrobe_file(settings.seed_wardrobe_path) if settings.seed_wardrobe_path else load_base_capsule()
    report = engine.sync(DEMO_USER_ID, items)
    logger.info(
        "Seeded demo wardrobe: %s items in %.0f ms (encoded %s texts, %s images)",
        report.get("indexed_count"), report.get("timings_ms", {}).get("total_ms", 0.0),
        report.get("encoded_text_count", "?"), report.get("encoded_image_count", "?"),
    )


def create_app(
    settings: Settings | None = None,
    *,
    llm: LLMClient | None = None,
    engine: RagEngine | None = None,
) -> FastAPI:
    """Фабрика приложения. `llm` и `engine` можно подменить — так устроены тесты."""
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    store = AppStore(settings.database_path)
    engine = engine or build_engine(settings, store)
    _seed_demo_wardrobe(engine, settings)
    service = StylistService(settings=settings, store=store, engine=engine, llm=llm or build_llm(settings))

    app = FastAPI(
        title=settings.app_name,
        version=API_VERSION,
        description=(
            "Бэкенд AI-стилиста 12 STOREEZ | AI LOOKBOOK: оркестрация RAG-пайплайна, "
            "интеграция LLM и валидация структурированного ответа."
        ),
    )
    app.state.settings = settings
    app.state.service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(recommend.router)
    app.include_router(wardrobe.router)
    app.include_router(admin.router)

    @app.get("/health", tags=["service"], summary="Проверка живости и текущая конфигурация")
    def health() -> dict:
        provider, model = service.llm_info
        return {
            "status": "ok",
            "version": API_VERSION,
            "llm": {"provider": provider, "model": model},
            "retrieval": service.engine_info(),
        }

    return app


def __getattr__(name: str) -> FastAPI:
    """`uvicorn app.main:app` получает приложение лениво: импорт модуля (например, из тестов)
    не должен грузить модели и создавать файлы в рабочем каталоге."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
