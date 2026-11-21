from __future__ import annotations

import logging

from app.config import Settings
from app.rag.base import RagEngine
from app.rag.builtin_engine import BuiltinEngine
from app.storage.app_store import AppStore

logger = logging.getLogger(__name__)


def build_engine(settings: Settings, store: AppStore) -> RagEngine:
    if settings.rag_engine == "builtin":
        return BuiltinEngine(store)
    try:
        from app.rag.wardrobe_rag_engine import WardrobeRagEngine

        engine = WardrobeRagEngine.from_settings(settings)
        logger.info("RAG engine: wardrobe_rag (%s)", engine.info().get("model_fingerprint", "")[:12])
        return engine
    except Exception as exc:  # noqa: BLE001 — причина может быть любой: нет пакета, нет кеша моделей
        if settings.rag_engine == "wardrobe_rag":
            raise RuntimeError(
                "RAG_ENGINE=wardrobe_rag, но пакет wardrobe_rag не готов к работе: "
                f"{exc!r}. Установите rag/ и скачайте модели (см. backend/README.md)."
            ) from exc
        logger.warning(
            "wardrobe_rag недоступен (%r) — включён ЗАПАСНОЙ встроенный поиск builtin-bm25. "
            "Для показа установите rag/ и скачайте модели.",
            exc,
        )
        return BuiltinEngine(store)
