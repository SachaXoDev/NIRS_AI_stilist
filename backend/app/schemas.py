"""Pydantic-схемы: зеркало `src/types/index.ts` и контракт REST API.

Объекты предметной области (вещь, образ, ответ стилиста) сериализуются в camelCase —
ровно так, как их ждёт фронтенд. Поля верхнего уровня запроса — snake_case, как в
`spec/tech/architecture.md` (camelCase тоже принимается).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

Category = Literal["tops", "bottoms", "outerwear", "shoes", "accessories"]
Season = Literal["all", "spring/summer", "autumn/winter"]

CATEGORY_ORDER: tuple[str, ...] = ("outerwear", "tops", "bottoms", "shoes", "accessories")
CATEGORY_LABELS_RU: dict[str, str] = {
    "tops": "верх",
    "bottoms": "низ",
    "outerwear": "верхняя одежда",
    "shoes": "обувь",
    "accessories": "аксессуары",
}


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class WeatherAttributes(BaseModel):
    """Размеченные погодные факты о вещи (контракт `wardrobe_rag`). None — «неизвестно»."""

    model_config = ConfigDict(extra="ignore")

    temperature_min: float | None = None
    temperature_max: float | None = None
    waterproof: bool | None = None
    windproof: bool | None = None
    open_shoes: bool | None = None


class WardrobeItem(CamelModel):
    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=1000)
    category: Category
    color: str = ""
    season: Season = "all"
    style: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    image_url: str = ""
    brand: str | None = None
    material: str | None = None
    embedding_snippet: str | None = None
    uploaded_at: str = ""
    image_path: str | None = None
    weather: WeatherAttributes | None = None

    @field_validator("id", "title", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("season", mode="before")
    @classmethod
    def _lenient_season(cls, value: Any) -> Any:
        return value if value in ("all", "spring/summer", "autumn/winter") else "all"

    @field_validator("style", "tags", mode="before")
    @classmethod
    def _lenient_list(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(v) for v in value if v is not None and str(v).strip()]

    @field_validator("color", "image_url", "uploaded_at", mode="before")
    @classmethod
    def _none_to_empty(cls, value: Any) -> Any:
        return "" if value is None else value


class OutfitLook(CamelModel):
    id: str
    title: str
    description: str
    occasion: str
    items: list[WardrobeItem]
    stylist_reasoning: str
    match_score: int = Field(ge=0, le=100)
    confidence_tips: list[str]


class RecommendContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    occasion: str | None = Field(default=None, max_length=200)
    weather: str | None = Field(default=None, max_length=200)
    vibe: str | None = Field(default=None, max_length=200)


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: Literal["user", "assistant"]
    text: str = Field(max_length=4000)
    has_outfit: bool = Field(default=False, validation_alias=AliasChoices("has_outfit", "hasOutfit"))
    # ID вещей из карточки этого ответа. По ним сервер правит образ точечно, а не
    # восстанавливает состав по названиям в тексте.
    item_ids: list[str] = Field(
        default_factory=list, max_length=8, validation_alias=AliasChoices("item_ids", "itemIds")
    )


RetrievalMode = Literal["bm25", "dense", "hybrid", "visual", "multimodal"]
# Кто собрал ответ: настоящая LLM, mock-провайдер, детерминированный фолбэк, правила сервера
# (точечная правка, где выбирать было не из чего: убрать вещь или единственный кандидат)
# или никто (образа нет).
ResponseSource = Literal["llm", "mock", "fallback", "rules", "none"]


class OutfitEdit(CamelModel):
    """Что именно изменилось относительно прошлой карточки — чтобы правку можно было проверить."""

    operation: Literal["add", "replace", "remove", "restyle"]
    slot: Category | None = None
    base_item_ids: list[str]
    kept_item_ids: list[str] = Field(default_factory=list)
    added_item_ids: list[str] = Field(default_factory=list)
    removed_item_ids: list[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    """Тело `POST /api/recommend-outfit`.

    Гардероб можно передать двумя способами:
    * `wardrobe` — полный снимок вещей (так делает фронтенд: гардероб живёт в localStorage).
      Сервер синхронизирует его с индексом и ищет по нему;
    * `wardrobe_ids` — только id (контракт КТ-1): поиск идёт по ранее синхронизированному
      снимку пользователя, ограниченному этими id.

    `user_id` — демо-идентификатор из тела запроса, а не защищённая сессия: авторизации нет.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    query: str = Field(min_length=1, max_length=2000)
    wardrobe_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
        validation_alias=AliasChoices("wardrobe_ids", "wardrobeIds"),
    )
    wardrobe: list[WardrobeItem] | None = Field(default=None, max_length=500)
    user_id: str | None = Field(
        default=None, max_length=200, validation_alias=AliasChoices("user_id", "userId")
    )
    context: RecommendContext | None = None
    history: list[HistoryMessage] = Field(default_factory=list, max_length=50)

    # Необязательные параметры поиска — для панели защиты. По умолчанию берутся из настроек.
    anchor_item_id: str | None = Field(
        default=None, max_length=200, validation_alias=AliasChoices("anchor_item_id", "anchorItemId")
    )
    mode: RetrievalMode | None = None
    alpha: float | None = Field(default=None, ge=0, le=1)
    visual_weight: float | None = Field(
        default=None, ge=0, le=1, validation_alias=AliasChoices("visual_weight", "visualWeight")
    )
    query_image: str | None = Field(
        default=None, validation_alias=AliasChoices("query_image", "queryImage")
    )
    # true — вернуть полную диагностику поиска в поле `retrieval`
    debug: bool = False

    @field_validator("query")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value.strip()


class ResponseMeta(CamelModel):
    llm_provider: str
    llm_model: str
    llm_attempts: int = 0
    retriever: str | None = None
    wardrobe_revision: str = ""
    occasion: str = ""
    # matchScore — прозрачная эвристика, а не вероятность и не «процент совместимости» модели
    match_score_method: str = ""


class RecommendResponse(CamelModel):
    """Ответ стилиста. `text`, `suggestedOutfit`, `referencedItemIds` — контракт КТ-1;
    остальные поля добавочные, фронтенд может их игнорировать."""

    text: str
    suggested_outfit: OutfitLook | None = None
    referenced_item_ids: list[str] = Field(default_factory=list)

    source: ResponseSource = "none"
    missing_slots: list[Category] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)
    meta: ResponseMeta | None = None
    # Заполняется, когда новая карточка получена правкой предыдущей
    edit: OutfitEdit | None = None
    # Диагностика поиска в формате RetrievalResult (snake_case, как в rag/contracts) + поле engine
    retrieval: dict[str, Any] | None = None


# --- Гардероб ---------------------------------------------------------------


class WardrobeSyncRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    user_id: str = Field(
        min_length=1, max_length=200, validation_alias=AliasChoices("user_id", "userId")
    )
    items: list[WardrobeItem] = Field(max_length=500)


class WardrobeResponse(CamelModel):
    user_id: str
    items: list[WardrobeItem]


# --- Настройки куратора (админка) ---------------------------------------------


class RuntimeSettings(CamelModel):
    mode: RetrievalMode
    alpha: float = Field(ge=0.0, le=1.0)
    visual_weight: float = Field(ge=0.0, le=1.0)
    temperature: float = Field(ge=0.0, le=2.0)
    persona_prompt: str = Field(min_length=10, max_length=4000)


class RuntimeSettingsPatch(CamelModel):
    mode: RetrievalMode | None = None
    alpha: float | None = Field(default=None, ge=0.0, le=1.0)
    visual_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    persona_prompt: str | None = Field(default=None, min_length=10, max_length=4000)


class AdminSettingsResponse(CamelModel):
    settings: RuntimeSettings
    llm_provider: str
    llm_model: str
    retriever: str
    editable: bool
