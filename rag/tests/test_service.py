from __future__ import annotations

from wardrobe_rag.retrieval import RetrievalEngine
from wardrobe_rag.schemas import RetrievalRequest, VectorHit
from wardrobe_rag.service import RAGService


def test_final_validation_rejects_a_snapshot_changed_during_generation(embedder, wardrobe):
    class MutableStore:
        revision = "before-llm"

        def get_items(self, user_id):
            return wardrobe

        def get_revision(self, user_id):
            return self.revision

        def query(self, channel, vector, user_id, category, k):
            return [VectorHit(item_id=item.id, distance=0.1) for item in wardrobe if item.category == category]

    store = MutableStore()
    service = RAGService(None, RetrievalEngine(store, embedder))
    result = service.retrieve(RetrievalRequest(user_id="alice", query="город", mode="dense"))
    assert service.validate_selection(["top", "bottom", "shoe"], result).complete
    store.revision = "after-sync"
    stale = service.validate_selection(["top", "bottom", "shoe"], result)
    assert not stale.valid and not stale.complete
    assert any("changed" in violation.lower() for violation in stale.violations)
