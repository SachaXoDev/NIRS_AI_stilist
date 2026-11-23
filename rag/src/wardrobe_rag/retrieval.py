"""Per-user BM25, text/visual vector search and explainable weighted RRF."""

from __future__ import annotations

import math
from contextlib import nullcontext
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Protocol, Sequence

from rank_bm25 import BM25Okapi

from .config import RAGConfig
from .constraints import (
    is_documented_flat, item_violations, requests_flat_shoes, required_slots, resolve_context, weather_warnings,
)
from .schemas import (
    CATEGORIES, Candidate, Category, RetrievalRequest, RetrievalResult, SlotSearchRequest, SlotSearchResult,
    VectorHit, WardrobeItem,
)
from .text import build_document, tokenize


class Store(Protocol):
    def get_items(self, user_id: str) -> list[WardrobeItem]: ...
    def get_revision(self, user_id: str) -> str: ...
    def query(self, channel: str, vector: Sequence[float], user_id: str, category: str, k: int) -> list[VectorHit]: ...


class Embedder(Protocol):
    fingerprint: str

    def encode_text(self, texts: list[str]) -> Any: ...
    def encode_visual_text(self, texts: list[str]) -> Any: ...
    def encode_images(self, images: list[Any]) -> Any: ...


@dataclass(frozen=True)
class _SlotScope:
    target: Category
    kept: list[WardrobeItem]
    flat_only: bool


def _vector(encoded: Any) -> list[float]:
    row = encoded[0]
    values = row.tolist() if hasattr(row, "tolist") else list(row)
    if not values or not all(math.isfinite(float(value)) for value in values):
        raise ValueError("Encoder returned an empty or non-finite query vector")
    return [float(value) for value in values]


def _rank_scores(values: dict[str, float], *, descending: bool) -> dict[str, int]:
    """Competition ranks give equal evidence equal contribution; ID breaks output ties."""
    ordered = sorted(values, key=lambda key: ((-values[key] if descending else values[key]), key))
    ranks: dict[str, int] = {}
    previous: float | None = None
    rank = 0
    for position, item_id in enumerate(ordered, start=1):
        value = values[item_id]
        if previous is None or not math.isclose(previous, value, rel_tol=1e-10, abs_tol=1e-12):
            rank = position
        ranks[item_id] = rank
        previous = value
    return ranks


class RetrievalEngine:
    def __init__(
        self, store: Store, embedder: Embedder, image_loader: Callable[[str], Any] | None = None,
        config: RAGConfig | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.image_loader = image_loader
        self.config = config or RAGConfig()

    def retrieve(self, request: RetrievalRequest | dict[str, Any]) -> RetrievalResult:
        request = RetrievalRequest.model_validate(request)
        session = self.store.read_session() if hasattr(self.store, "read_session") else nullcontext()
        with session:
            return self._retrieve(request)

    def retrieve_slot(self, edit: SlotSearchRequest | dict[str, Any]) -> SlotSearchResult:
        edit = SlotSearchRequest.model_validate(edit)
        session = self.store.read_session() if hasattr(self.store, "read_session") else nullcontext()
        with session:
            items = self.store.get_items(edit.user_id)
            by_id = {item.id: item for item in items}
            if set(edit.outfit_item_ids) - by_id.keys():
                raise ValueError("The existing outfit contains IDs outside this user's current wardrobe")
            in_slot = [item_id for item_id in edit.outfit_item_ids if by_id[item_id].category == edit.slot]
            replaced = edit.replace_item_id
            if edit.operation == "replace":
                if replaced is None and len(in_slot) == 1:
                    replaced = in_slot[0]
                if replaced is None or replaced not in in_slot:
                    raise ValueError("Choose one existing item from the requested slot to replace")
            elif len(in_slot) >= (2 if edit.slot == "accessories" else 1):
                raise ValueError("The requested slot is full; use operation=replace")

            kept = [by_id[item_id] for item_id in edit.outfit_item_ids if item_id != replaced]
            request = RetrievalRequest(
                user_id=edit.user_id, query=edit.query, mode=edit.mode,
                context=edit.context, alpha=edit.alpha, visual_weight=edit.visual_weight,
                exclude_item_ids=list(dict.fromkeys([*edit.outfit_item_ids, *edit.exclude_item_ids])),
                exclude_colors=edit.exclude_colors, exclude_materials=edit.exclude_materials,
            )
            # Weather explicitly mentioned in this edit supersedes the prior context.
            current = resolve_context(RetrievalRequest(user_id=edit.user_id, query=edit.query))
            request.context = edit.context.model_copy(update=current.model_dump(exclude_none=True))
            flat_only = edit.slot == "shoes" and (edit.without_heel or requests_flat_shoes(edit.query))
            scope = _SlotScope(edit.slot, kept, flat_only)
            result = self._retrieve(request, scope=scope, items=items)
            return SlotSearchResult(
                user_id=edit.user_id, slot=edit.slot, candidates=result.candidates_by_slot[edit.slot],
                kept_item_ids=[item.id for item in kept], replaced_item_id=replaced,
                context=result.context, warnings=result.warnings, timings_ms=result.timings_ms,
                wardrobe_revision=result.wardrobe_revision, model_fingerprint=result.model_fingerprint,
            )

    def _retrieve(self, request: RetrievalRequest, *, scope: _SlotScope | None = None,
                  items: list[WardrobeItem] | None = None) -> RetrievalResult:
        started = perf_counter()
        timings: dict[str, float] = {}
        warnings: list[str] = []
        preparation_started = perf_counter()
        model_fingerprint = self.embedder.fingerprint
        timings["model_prepare"] = (perf_counter() - preparation_started) * 1000
        if hasattr(self.store, "get_fingerprint"):
            stored_fingerprint = self.store.get_fingerprint()
            if stored_fingerprint and stored_fingerprint != model_fingerprint:
                raise ValueError("Embedding model fingerprint changed; use the indexed encoders or reindex in a fresh data directory")
        items = self.store.get_items(request.user_id) if items is None else items
        revision = self.store.get_revision(request.user_id)
        context = resolve_context(request)
        slots = [scope.target] if scope else required_slots(request, context, self.config)
        by_id = {item.id: item for item in items}
        if len(by_id) != len(items):
            raise ValueError("Store returned duplicate IDs within one user's snapshot")
        if request.anchor_item_id is not None and request.anchor_item_id not in by_id:
            raise ValueError("anchor_item_id is not present in this user's wardrobe")
        pool = [item for item in items if item.category == scope.target] if scope else items
        allowed = {item.id: item for item in pool if not item_violations(item, request, context)}
        if request.anchor_item_id is not None and request.anchor_item_id not in allowed:
            raise ValueError("anchor_item_id conflicts with explicit item or weather constraints")
        filtered_count = len(pool) - len(allowed)
        if filtered_count:
            warnings.append(f"Filtered {filtered_count} items by explicit exclusions or curated weather attributes")
        if not items:
            warnings.append("The user's wardrobe is empty; no demo-catalog items were substituted")
        if scope and scope.flat_only:
            allowed = {item_id: item for item_id, item in allowed.items() if is_documented_flat(item)}
            warnings.append("Flat footwear required; candidates without an explicit flat-sole annotation were excluded")

        search_parts = [request.query, context.occasion, context.weather, context.vibe]
        if scope:
            if context.temperature_c is not None:
                search_parts.append(f"{context.temperature_c:g} °C")
            if context.rain:
                search_parts.append("дождь защита от дождя")
            if context.wind:
                search_parts.append("ветер ветрозащита")
            retained = "; ".join(" ".join(filter(None, [i.title, i.color, i.material, " ".join(i.style)])) for i in scope.kept)
            if retained:
                search_parts.append(f"Сочетать с {retained}")
        search_text = " ".join(filter(None, search_parts))
        use_bm25 = request.mode in {"bm25", "hybrid", "multimodal"} and bool(search_text)
        use_dense = request.mode in {"dense", "hybrid", "multimodal"} and bool(search_text)
        use_visual = request.mode in {"visual", "multimodal"}

        bm25_scores: dict[str, float] = {}
        if use_bm25 and pool:
            phase = perf_counter()
            documents = [tokenize(build_document(item)) for item in pool]
            query_tokens = tokenize(search_text)
            if any(documents) and query_tokens:
                scores = BM25Okapi(documents).get_scores(query_tokens)
                query_set = set(query_tokens)
                # No-overlap documents never receive a spurious RRF rank, even at zero IDF.
                bm25_scores = {
                    item.id: float(score) for item, tokens, score in zip(pool, documents, scores)
                    if item.id in allowed and query_set.intersection(tokens)
                }
            timings["bm25"] = (perf_counter() - phase) * 1000
            if not bm25_scores:
                warnings.append("BM25 found no lexical overlap; its fusion contribution is zero")

        dense_vector: list[float] | None = None
        visual_vector: list[float] | None = None
        if use_dense and allowed:
            phase = perf_counter()
            dense_vector = _vector(self.embedder.encode_text([search_text]))
            timings["embedding_text"] = (perf_counter() - phase) * 1000
        if use_visual and allowed:
            phase = perf_counter()
            if request.query_image:
                if self.image_loader is None:
                    raise ValueError("An image_loader is required for query_image")
                image = self.image_loader(request.query_image)
                try:
                    visual_vector = _vector(self.embedder.encode_images([image]))
                finally:
                    if hasattr(image, "close"):
                        image.close()
            elif search_text:
                visual_vector = _vector(self.embedder.encode_visual_text([search_text]))
            timings["embedding_visual"] = (perf_counter() - phase) * 1000

        candidates_by_slot = {}
        dense_search_ms = 0.0
        visual_search_ms = 0.0
        fusion_ms = 0.0
        for category in ((scope.target,) if scope else CATEGORIES):
            anchor_category = by_id[request.anchor_item_id].category if request.anchor_item_id else None
            if not scope and category == "accessories" and not self.config.include_accessories and anchor_category != "accessories":
                candidates_by_slot[category] = []
                continue
            category_items = {item.id: item for item in allowed.values() if item.category == category}
            total_in_category = sum(item.category == category for item in items)
            # Oversampling accounts for excluded items before the allowed-ID filter.
            query_k = min(total_in_category, self.config.candidate_pool + total_in_category - len(category_items))
            dense_distances: dict[str, float] = {}
            visual_distances: dict[str, float] = {}
            if category_items and dense_vector is not None:
                phase = perf_counter()
                hits = self.store.query(channel="text", vector=dense_vector, user_id=request.user_id, category=category, k=query_k)
                dense_distances = self._verified_hits(hits, category_items)
                dense_search_ms += (perf_counter() - phase) * 1000
            if category_items and visual_vector is not None:
                phase = perf_counter()
                hits = self.store.query(channel="image", vector=visual_vector, user_id=request.user_id, category=category, k=query_k)
                visual_distances = self._verified_hits(hits, category_items)
                visual_search_ms += (perf_counter() - phase) * 1000
            phase = perf_counter()
            lexical = {item_id: score for item_id, score in bm25_scores.items() if item_id in category_items}
            bm25_ranks = _rank_scores(lexical, descending=True)
            dense_ranks = _rank_scores(dense_distances, descending=False)
            visual_ranks = _rank_scores(visual_distances, descending=False)
            weights = self._weights(request, bool(dense_ranks), bool(visual_ranks))
            candidate_ids = set(bm25_ranks) | set(dense_ranks) | set(visual_ranks)
            # Explicit anchor is pinned as a constraint, not presented as retrieval evidence.
            if request.anchor_item_id in category_items:
                candidate_ids.add(request.anchor_item_id)
            candidates = []
            for item_id in candidate_ids:
                bm25_contribution = self._contribution(weights[0], bm25_ranks.get(item_id))
                dense_contribution = self._contribution(weights[1], dense_ranks.get(item_id))
                visual_contribution = self._contribution(weights[2], visual_ranks.get(item_id))
                score = bm25_contribution + dense_contribution + visual_contribution
                anchored = item_id == request.anchor_item_id
                if score == 0 and not anchored:
                    continue
                candidates.append(Candidate(
                    item=category_items[item_id], score=score,
                    bm25_score=lexical.get(item_id) if score else None, bm25_rank=bm25_ranks.get(item_id) if score else None,
                    dense_distance=dense_distances.get(item_id) if score else None, dense_rank=dense_ranks.get(item_id) if score else None,
                    visual_distance=visual_distances.get(item_id) if score else None, visual_rank=visual_ranks.get(item_id) if score else None,
                    bm25_contribution=bm25_contribution, dense_contribution=dense_contribution,
                    visual_contribution=visual_contribution, anchored=anchored, fallback=score == 0,
                ))
            candidates.sort(key=lambda candidate: (-candidate.score, candidate.item.id))
            selected = candidates[:self.config.top_k[category]]
            if request.anchor_item_id in category_items and not any(candidate.anchored for candidate in selected):
                anchor = next(candidate for candidate in candidates if candidate.anchored)
                selected = selected[:-1] + [anchor]
                selected.sort(key=lambda candidate: (-candidate.score, candidate.item.id))
            selected_ids = {candidate.item.id for candidate in selected}
            # Guarantee slot coverage without fabricating retrieval scores. Evaluators
            # must ignore fallback=True rows when computing ranked HitRate/MRR.
            for item_id in (() if scope else sorted(category_items)):
                if len(selected) >= self.config.top_k[category]:
                    break
                if item_id not in selected_ids:
                    selected.append(Candidate(item=category_items[item_id], score=0, fallback=True))
                    selected_ids.add(item_id)
            fallbacks = [candidate.item.id for candidate in selected if candidate.fallback]
            if fallbacks:
                warnings.append(f"Unranked fallback candidates for slot {category}: " + ", ".join(fallbacks))
            candidates_by_slot[category] = selected
            fusion_ms += (perf_counter() - phase) * 1000
            if use_visual and category_items and not visual_ranks:
                warnings.append(f"No indexed images for slot {category}; visual evidence is unavailable")

        if use_dense:
            timings["dense_search"] = dense_search_ms
        if use_visual:
            timings["visual_search"] = visual_search_ms
        timings["fusion_constraints"] = fusion_ms
        missing = [slot for slot in slots if not candidates_by_slot.get(slot)]
        if missing:
            warnings.append("No eligible retrieved candidates for required slots: " + ", ".join(missing))
        all_candidates = [candidate.item for candidates in candidates_by_slot.values() for candidate in candidates]
        warnings.extend(weather_warnings(all_candidates, context))
        if request.mode == "multimodal":
            warnings.append("Multimodal RRF weights: BM25=(1-alpha), text=alpha*(1-visual_weight), image=alpha*visual_weight; unavailable Dense channels redistribute within the Dense group")
        if scope is None and (context.temperature_c is not None or context.rain is True):
            warnings.append("Outerwear requirement uses an explicit demo heuristic (temperature threshold/rain), not a physiological comfort guarantee")
        timings["total"] = (perf_counter() - started) * 1000
        return RetrievalResult(
            user_id=request.user_id, query=request.query, mode=request.mode,
            alpha=request.alpha, visual_weight=request.visual_weight, rrf_c=self.config.rrf_c,
            candidates_by_slot=candidates_by_slot, required_slots=slots, missing_slots=missing,
            context=context, anchor_item_id=request.anchor_item_id,
            warnings=list(dict.fromkeys(warnings)), timings_ms=timings,
            wardrobe_revision=revision, model_fingerprint=model_fingerprint,
        )

    @staticmethod
    def _verified_hits(hits: Sequence[VectorHit], allowed: dict[str, WardrobeItem]) -> dict[str, float]:
        # Treat the vector adapter as an untrusted boundary: discard wrong-user IDs.
        verified: dict[str, float] = {}
        for raw_hit in hits:
            hit = VectorHit.model_validate(raw_hit)
            if hit.item_id in allowed:
                verified[hit.item_id] = min(hit.distance, verified.get(hit.item_id, float("inf")))
        return verified

    def _contribution(self, weight: float, rank: int | None) -> float:
        return weight / (self.config.rrf_c + rank) if rank is not None else 0.0

    @staticmethod
    def _weights(request: RetrievalRequest, has_dense: bool, has_visual: bool) -> tuple[float, float, float]:
        if request.mode == "bm25":
            return 1.0, 0.0, 0.0
        if request.mode == "dense":
            return 0.0, 1.0, 0.0
        if request.mode == "visual":
            return 0.0, 0.0, 1.0
        if request.mode == "hybrid":
            return 1 - request.alpha, request.alpha, 0.0
        if has_dense and has_visual:
            return 1 - request.alpha, request.alpha * (1 - request.visual_weight), request.alpha * request.visual_weight
        if has_visual:
            # Image-only multimodal requests cannot use lexical/semantic text channels.
            return (1 - request.alpha if request.query else 0.0), 0.0, (request.alpha if request.query else 1.0)
        return 1 - request.alpha, request.alpha, 0.0
