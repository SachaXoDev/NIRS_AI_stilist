"""Адаптер к пакету `wardrobe_rag` (каталог `rag/`), подключение по `rag/INTEGRATION.md`.

Пакет импортируется лениво: бэкенд должен запускаться и там, где тяжёлых зависимостей
(torch, sentence-transformers, chromadb) нет — тогда фабрика выберет встроенный движок.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.config import Settings
from app.rag.base import (
    AnchorRejected,
    RagEngineError,
    RetrievalOutcome,
    RetrievalQuery,
    SelectionCheck,
    SlotCandidate,
    SlotOutcome,
    SlotQuery,
)
from app.schemas import PhotoSuggestion, WardrobeItem
from app.services.photo_recognition import PhotoRecognizer

logger = logging.getLogger(__name__)


def _to_api_item(rag_item: Any) -> WardrobeItem:
    return WardrobeItem.model_validate(rag_item.model_dump(mode="json"))


def _to_rag_payload(item: WardrobeItem) -> dict[str, Any]:
    # by_alias даёт ровно те имена полей, которые ждёт wardrobe_rag.schemas.WardrobeItem
    return item.model_dump(by_alias=True, mode="json")


class WardrobeRagEngine:
    name = "wardrobe_rag"

    def __init__(self, service: Any, *, details: dict[str, Any] | None = None) -> None:
        self._service = service
        self._details = details or {}
        # Кодировщики и Chroma вызываются из пула потоков FastAPI — сериализуем обращения.
        self._lock = threading.RLock()
        # user_id -> (отпечаток присланного снимка, результат sync): повторный снимок не переиндексируем
        self._sync_cache: dict[str, tuple[str, dict[str, Any]]] = {}
        self._photo_recognizer = PhotoRecognizer(service.retriever.embedder)

    def recognize_photo(self, image: Any) -> PhotoSuggestion | None:
        image.thumbnail((768, 768))
        with self._lock:
            return self._photo_recognizer.suggest(image)

    @classmethod
    def from_settings(cls, settings: Settings) -> "WardrobeRagEngine":
        from wardrobe_rag.config import RAGConfig
        from wardrobe_rag.embedding import SentenceTransformerEmbedder
        from wardrobe_rag.embedding_cache import EmbeddingCache
        from wardrobe_rag.images import ImageLoader
        from wardrobe_rag.indexing import IndexingPipeline
        from wardrobe_rag.retrieval import RetrievalEngine
        from wardrobe_rag.service import RAGService
        from wardrobe_rag.store import ChromaWardrobeStore

        public_root = Path(settings.rag_public_root).resolve()
        upload_root = Path(settings.rag_upload_root).resolve() if settings.rag_upload_root else None
        cache_dir = Path(settings.rag_cache_dir).resolve()
        data_dir = Path(settings.rag_data_dir).resolve()

        images = ImageLoader(public_root, upload_root)
        embedder = SentenceTransformerEmbedder(
            cache_dir=cache_dir, device=settings.rag_device, offline=settings.rag_offline
        )
        # Грузим модели на старте, а не на первом запросе: ошибка кеша должна быть видна сразу.
        fingerprint = embedder.fingerprint
        store = ChromaWardrobeStore(data_dir)
        # Правка одной вещи создаёт новую ревизию гардероба; без кеша это перекодирование
        # всего каталога, с кешем — только изменившейся вещи.
        cache = (
            EmbeddingCache(data_dir / "embedding_cache.sqlite3") if settings.rag_embedding_cache else None
        )
        indexer = IndexingPipeline(store, embedder, images, cache)
        retriever = RetrievalEngine(store, embedder, images, RAGConfig())
        return cls(
            RAGService(indexer, retriever),
            details={
                "model_fingerprint": fingerprint,
                "offline": settings.rag_offline,
                "device": settings.rag_device,
                "data_dir": str(data_dir),
                "embedding_cache": cache is not None,
            },
        )

    # --- RagEngine ----------------------------------------------------------------

    def info(self) -> dict[str, Any]:
        return {"engine": self.name, **self._details}

    def sync(self, user_id: str, items: list[WardrobeItem]) -> dict[str, Any]:
        unique: dict[str, WardrobeItem] = {}
        for item in items:
            unique.setdefault(item.id, item)
        payload = [_to_rag_payload(item) for item in unique.values()]
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        store = self._service.retriever.store
        with self._lock:
            cached = self._sync_cache.get(user_id)
            if cached and cached[0] == digest and store.get_revision(user_id) == cached[1]["revision"]:
                return {
                    **cached[1],
                    "added_count": 0,
                    "updated_count": 0,
                    "deleted_count": 0,
                    "unchanged_count": len(payload),
                    # Снимок тот же: ничего не кодировалось и не переиндексировалось.
                    "encoded_text_count": 0,
                    "reused_text_count": 0,
                    "encoded_image_count": 0,
                    "reused_image_count": 0,
                    "timings_ms": {"total_ms": 0.0},
                    "cached": True,
                }
            try:
                result = self._service.sync(user_id, payload).model_dump(mode="json")
            except ValueError as exc:
                raise RagEngineError(f"Не удалось синхронизировать гардероб: {exc}") from exc
            self._sync_cache[user_id] = (digest, result)
            return result

    def get_items(self, user_id: str) -> list[WardrobeItem]:
        with self._lock:
            return [_to_api_item(item) for item in self._service.retriever.store.get_items(user_id)]

    def retrieve(self, query: RetrievalQuery) -> RetrievalOutcome:
        from wardrobe_rag.schemas import QueryContext, RetrievalRequest

        try:
            request = RetrievalRequest(
                user_id=query.user_id,
                query=query.query,
                query_image=query.query_image,
                mode=query.mode,
                alpha=query.alpha,
                visual_weight=query.visual_weight,
                context=QueryContext(
                    occasion=query.occasion, weather=query.weather, vibe=query.vibe,
                    temperature_c=query.temperature_c,
                ),
                anchor_item_id=query.anchor_item_id,
                exclude_item_ids=[i for i in query.exclude_item_ids if i != query.anchor_item_id],
                require_outerwear=True if query.require_outerwear else None,
            )
            with self._lock:
                result = self._service.retrieve(request)
        except ValueError as exc:  # включает pydantic.ValidationError
            if "anchor_item_id" in str(exc):
                raise AnchorRejected(str(exc)) from exc
            raise RagEngineError(f"Поиск отклонил запрос: {exc}") from exc

        return RetrievalOutcome(
            user_id=result.user_id,
            query=result.query,
            engine=self.name,
            mode=result.mode,
            candidates_by_slot={
                slot: [
                    SlotCandidate(
                        item=_to_api_item(candidate.item),
                        score=candidate.score,
                        anchored=candidate.anchored,
                        fallback=candidate.fallback,
                        preference_score=candidate.preference_score,
                        material_weather_score=candidate.material_weather_score,
                    )
                    for candidate in candidates
                ]
                for slot, candidates in result.candidates_by_slot.items()
            },
            required_slots=list(result.required_slots),
            missing_slots=list(result.missing_slots),
            context=result.context.model_dump(mode="json"),
            anchor_item_id=result.anchor_item_id,
            warnings=list(result.warnings),
            timings_ms=dict(result.timings_ms),
            revision=result.wardrobe_revision,
            diagnostics={"engine": self.name, **result.model_dump(mode="json")},
            raw=result,
        )

    def _check(self, validation: Any) -> SelectionCheck:
        return SelectionCheck(
            valid=validation.valid,
            complete=validation.complete,
            items=[_to_api_item(item) for item in validation.selected_items],
            missing_slots=list(validation.missing_slots),
            violations=list(validation.violations),
            warnings=list(validation.warnings),
            stale=any("changed since retrieval" in v for v in validation.violations),
        )

    def validate_selection(self, item_ids: list[str], outcome: RetrievalOutcome) -> SelectionCheck:
        with self._lock:
            return self._check(self._service.validate_selection(list(item_ids), outcome.raw))

    def assemble(self, outcome: RetrievalOutcome) -> SelectionCheck:
        with self._lock:
            return self._check(self._service.assemble(outcome.raw))

    def get_revision(self, user_id: str) -> str:
        with self._lock:
            return self._service.retriever.store.get_revision(user_id)

    def retrieve_slot(self, query: SlotQuery) -> SlotOutcome:
        from wardrobe_rag.schemas import QueryContext, SlotSearchRequest

        try:
            request = SlotSearchRequest(
                user_id=query.user_id,
                query=query.query,
                slot=query.slot,
                operation=query.operation,
                outfit_item_ids=query.outfit_item_ids,
                replace_item_id=query.replace_item_id,
                context=QueryContext(
                    occasion=query.occasion, weather=query.weather, vibe=query.vibe,
                    temperature_c=query.temperature_c, rain=query.rain, wind=query.wind,
                ),
                exclude_item_ids=query.exclude_item_ids,
                # Поиск одной вещи не поддерживает чисто визуальный режим.
                mode="hybrid" if query.mode == "visual" else query.mode,
                alpha=query.alpha,
                visual_weight=query.visual_weight,
            )
            with self._lock:
                result = self._service.retrieve_slot(request)
        except ValueError as exc:  # включает pydantic.ValidationError
            raise RagEngineError(f"Поиск вещи для правки образа отклонил запрос: {exc}") from exc

        return SlotOutcome(
            slot=result.slot,
            candidates=[
                SlotCandidate(
                    item=_to_api_item(candidate.item), score=candidate.score,
                    anchored=candidate.anchored, fallback=candidate.fallback,
                    preference_score=candidate.preference_score,
                    material_weather_score=candidate.material_weather_score,
                )
                for candidate in result.candidates
            ],
            kept_item_ids=list(result.kept_item_ids),
            replaced_item_id=result.replaced_item_id,
            context=result.context.model_dump(mode="json"),
            warnings=list(result.warnings),
            timings_ms=dict(result.timings_ms),
            revision=result.wardrobe_revision,
            diagnostics={"engine": self.name, **result.model_dump(mode="json")},
        )
