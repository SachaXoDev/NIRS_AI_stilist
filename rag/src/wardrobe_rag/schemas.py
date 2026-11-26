"""Validated public contracts shared by indexing, retrieval and the future API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["tops", "bottoms", "shoes", "outerwear", "accessories"]
RetrievalMode = Literal["bm25", "dense", "hybrid", "visual", "multimodal"]
MaterialPart = Literal["lining", "insulation", "sole", "insole", "trim"]
CATEGORIES: tuple[Category, ...] = ("tops", "bottoms", "shoes", "outerwear", "accessories")
REQUIRED_SLOTS: tuple[Category, ...] = ("tops", "bottoms", "shoes")


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class WeatherAttributes(Contract):
    """Curated facts; None means unknown, never an inferred guarantee."""

    temperature_min: float | None = None
    temperature_max: float | None = None
    waterproof: bool | None = None
    windproof: bool | None = None
    open_shoes: bool | None = None

    @model_validator(mode="after")
    def valid_range(self) -> WeatherAttributes:
        if self.temperature_min is not None and self.temperature_max is not None:
            if self.temperature_min > self.temperature_max:
                raise ValueError("temperature_min must not exceed temperature_max")
        return self


class WardrobeItem(Contract):
    """Frontend-compatible item. Ownership belongs to the containing user snapshot."""

    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=1000)
    category: Category
    color: str = ""
    season: Literal["unknown", "all", "spring/summer", "autumn/winter"] = "unknown"
    style: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    imageUrl: str = ""
    brand: str | None = None
    material: str | None = None
    materialDetails: dict[MaterialPart, str] | None = None
    embeddingSnippet: str | None = None
    uploadedAt: str = ""
    imagePath: str | None = None
    weather: WeatherAttributes | None = None


class QueryContext(Contract):
    occasion: str | None = None
    weather: str | None = None
    vibe: str | None = None
    temperature_c: float | None = Field(default=None, ge=-80, le=65)
    rain: bool | None = None
    wind: bool | None = None


class RetrievalRequest(Contract):
    user_id: str = Field(min_length=1, max_length=200)
    query: str = Field(default="", max_length=10000)
    query_image: str | None = None
    mode: RetrievalMode = "hybrid"
    alpha: float = Field(default=0.65, ge=0, le=1)
    visual_weight: float = Field(default=0.35, ge=0, le=1)
    context: QueryContext = Field(default_factory=QueryContext)
    anchor_item_id: str | None = None
    exclude_item_ids: list[str] = Field(default_factory=list)
    exclude_colors: list[str] = Field(default_factory=list)
    exclude_materials: list[str] = Field(default_factory=list)
    require_outerwear: bool | None = None

    @model_validator(mode="after")
    def query_is_supported(self) -> RetrievalRequest:
        if not self.query and not self.query_image:
            raise ValueError("query or query_image is required")
        if self.mode in {"bm25", "dense", "hybrid"} and not self.query:
            raise ValueError(f"{self.mode} requires a non-empty text query")
        if self.anchor_item_id in self.exclude_item_ids:
            raise ValueError("anchor_item_id cannot also be excluded")
        return self


class SlotSearchRequest(Contract):
    """Search for a single change to an existing outfit from this user's wardrobe."""

    user_id: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=10000)
    slot: Category
    operation: Literal["add", "replace"]
    outfit_item_ids: list[str] = Field(min_length=1, max_length=8)
    replace_item_id: str | None = None
    context: QueryContext = Field(default_factory=QueryContext)
    exclude_item_ids: list[str] = Field(default_factory=list)
    exclude_colors: list[str] = Field(default_factory=list)
    exclude_materials: list[str] = Field(default_factory=list)
    without_heel: bool = False
    mode: Literal["bm25", "dense", "hybrid", "multimodal"] = "hybrid"
    alpha: float = Field(default=0.65, ge=0, le=1)
    visual_weight: float = Field(default=0.35, ge=0, le=1)

    @model_validator(mode="after")
    def validate_edit(self) -> SlotSearchRequest:
        if len(set(self.outfit_item_ids)) != len(self.outfit_item_ids):
            raise ValueError("outfit_item_ids must be unique")
        if self.replace_item_id is not None and (
            self.operation != "replace" or self.replace_item_id not in self.outfit_item_ids
        ):
            raise ValueError("replace_item_id must belong to the outfit and requires operation=replace")
        if self.without_heel and self.slot != "shoes":
            raise ValueError("without_heel applies to the shoes slot")
        return self


class VectorHit(Contract):
    item_id: str
    distance: float


class Candidate(Contract):
    item: WardrobeItem
    score: float
    bm25_score: float | None = None
    bm25_rank: int | None = None
    dense_distance: float | None = None
    dense_rank: int | None = None
    visual_distance: float | None = None
    visual_rank: int | None = None
    bm25_contribution: float = 0
    dense_contribution: float = 0
    visual_contribution: float = 0
    preference_score: int = 0
    material_weather_score: int = 0
    anchored: bool = False
    fallback: bool = False

    @property
    def item_id(self) -> str:
        return self.item.id


class RetrievalResult(Contract):
    user_id: str
    query: str
    mode: RetrievalMode
    alpha: float
    visual_weight: float
    rrf_c: int
    candidates_by_slot: dict[Category, list[Candidate]]
    required_slots: list[Category] = Field(default_factory=lambda: list(REQUIRED_SLOTS))
    missing_slots: list[Category] = Field(default_factory=list)
    context: QueryContext = Field(default_factory=QueryContext)
    anchor_item_id: str | None = None
    exclude_colors: list[str] = Field(default_factory=list)
    exclude_materials: list[str] = Field(default_factory=list)
    attribute_blocked_slots: list[Category] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
    wardrobe_revision: str
    model_fingerprint: str
    score_method: str = "weighted_rrf"


class SlotSearchResult(Contract):
    user_id: str
    slot: Category
    candidates: list[Candidate]
    kept_item_ids: list[str]
    replaced_item_id: str | None = None
    context: QueryContext
    warnings: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
    wardrobe_revision: str
    model_fingerprint: str


class SyncResult(Contract):
    user_id: str
    revision: str
    indexed_count: int
    image_count: int
    added_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    unchanged_count: int = 0
    # How much encoder work this sync needed. With an EmbeddingCache unchanged items are reused;
    # all four stay 0 when the revision did not change and nothing was re-indexed.
    encoded_text_count: int = 0
    reused_text_count: int = 0
    encoded_image_count: int = 0
    reused_image_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)


class SelectionValidation(Contract):
    """No LLM text or fictional confidence percentage is generated here."""

    valid: bool
    complete: bool
    selected_items: list[WardrobeItem] = Field(default_factory=list)
    missing_slots: list[Category] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    wardrobe_revision: str
