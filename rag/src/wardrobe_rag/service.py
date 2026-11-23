"""Small integration facade; no HTTP framework or LLM dependency."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Sequence

from .constraints import assemble_outfit, validate_selection
from .retrieval import RetrievalEngine
from .schemas import (
    RetrievalRequest, RetrievalResult, SelectionValidation, SlotSearchRequest, SlotSearchResult, SyncResult, WardrobeItem,
)


class RAGService:
    def __init__(self, indexer: Any, retriever: RetrievalEngine) -> None:
        self.indexer = indexer
        self.retriever = retriever

    def sync(self, user_id: str, items: Sequence[WardrobeItem | dict[str, Any]]) -> SyncResult:
        return self.indexer.sync(user_id, [WardrobeItem.model_validate(item) for item in items])

    def retrieve(self, request: RetrievalRequest | dict[str, Any]) -> RetrievalResult:
        return self.retriever.retrieve(request)

    def retrieve_slot(self, request: SlotSearchRequest | dict[str, Any]) -> SlotSearchResult:
        return self.retriever.retrieve_slot(request)

    def validate_selection(self, selected_item_ids: Sequence[str], result: RetrievalResult) -> SelectionValidation:
        store = self.retriever.store
        session = store.read_session() if hasattr(store, "read_session") else nullcontext()
        with session:
            checked = validate_selection(selected_item_ids, result)
            if store.get_revision(result.user_id) != result.wardrobe_revision:
                checked.valid = False
                checked.complete = False
                checked.violations.append("Wardrobe changed since retrieval; retrieve fresh candidates before accepting the outfit")
            return checked

    def assemble(self, result: RetrievalResult) -> SelectionValidation:
        assembled = assemble_outfit(result)
        return self.validate_selection([item.id for item in assembled.selected_items], result)
