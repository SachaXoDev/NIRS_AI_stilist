"""Конфигурация сервера. Все значения читаются из переменных окружения или файла .env."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PERSONA_PROMPT = (
    "Ты — ведущий стилист бренда 12 STOREEZ. Подбираешь образы только из вещей гардероба "
    "клиента, которые переданы в контексте. Соблюдаешь правила колористики, многослойности "
    "(smart layering) и эстетики спокойного минимализма. Отвечаешь по-русски, лаконично и по делу."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Stylist Backend"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"

    # LLM
    llm_provider: Literal["mock", "openai"] = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.6, ge=0.0, le=2.0)
    llm_timeout_s: float = Field(default=30.0, gt=0)
    llm_max_repairs: int = Field(default=1, ge=0, le=3)
    llm_json_mode: bool = True
    llm_outfit_schema: bool = False
    # Пауза между чанками mock-стрима, чтобы на фронте был виден «эффект печатания»
    mock_stream_delay_s: float = Field(default=0.03, ge=0.0)

    # Опциональные поля, которые добавляются в тело запроса к LLM как есть (JSON-объект).
    # Нужны, например, чтобы выключить «размышления» у reasoning-моделей конкретного провайдера.
    llm_extra_body: str = ""

    # Поиск (RAG)
    # auto         — wardrobe_rag, если пакет и модели доступны; иначе встроенный BM25 с пометкой
    # wardrobe_rag — только пакет из rag/ (ошибка старта, если он не готов)
    # builtin      — встроенный лексический поиск без нейросетевых моделей
    rag_engine: Literal["auto", "wardrobe_rag", "builtin"] = "auto"
    rag_mode: Literal["bm25", "dense", "hybrid", "visual", "multimodal"] = "hybrid"
    rag_alpha: float = Field(default=0.65, ge=0.0, le=1.0)
    rag_visual_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    rag_data_dir: str = "../rag/.rag_data"
    rag_cache_dir: str = "../rag/.model_cache"
    rag_public_root: str = "../public"
    rag_upload_root: str = ""
    rag_offline: bool = False
    rag_device: str = "cpu"
    # Переиспользовать эмбеддинги неизменённых вещей между ревизиями гардероба. Выключается
    # только чтобы воспроизвести замер «до»: тогда любая правка перекодирует весь каталог.
    rag_embedding_cache: bool = True
    # Гардероб демо-пользователя (user_id="demo"), который создаётся при первом старте
    seed_wardrobe_path: str = ""

    # Хранилище и админка
    database_path: str = "data/stylist.db"
    admin_token: str = ""
    persona_prompt: str = DEFAULT_PERSONA_PROMPT

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
