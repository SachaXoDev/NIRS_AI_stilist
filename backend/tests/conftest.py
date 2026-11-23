from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.llm.base import LLMError
from app.storage.app_store import load_wardrobe_file

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_CAPSULE_PATH = REPO_ROOT / "rag" / "data" / "wardrobe_seed.json"


class ScriptedLLM:
    """LLM-заглушка: отдаёт заранее заданные ответы по очереди и запоминает запросы."""

    provider = "scripted"
    model = "scripted-1"

    def __init__(self, answers: list[str | Exception]) -> None:
        self.answers = list(answers)
        self.calls: list[list[dict[str, str]]] = []

    def _next(self, messages) -> str:
        self.calls.append(messages)
        if not self.answers:
            raise LLMError("no scripted answers left")
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def complete(self, messages, *, context, temperature) -> str:
        return self._next(messages)

    async def stream(self, messages, *, context, temperature) -> AsyncIterator[str]:
        answer = self._next(messages)
        for start in range(0, len(answer), 7):
            yield answer[start : start + 7]


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        llm_provider="mock",
        rag_engine="builtin",
        database_path=str(tmp_path / "test.db"),
        seed_wardrobe_path=str(TEST_CAPSULE_PATH),
        mock_stream_delay_s=0.0,
        admin_token="",
    )


@pytest.fixture
def make_client(settings):
    def factory(*, llm=None, engine=None, **overrides) -> TestClient:
        cfg = settings.model_copy(update=overrides)
        return TestClient(create_app(cfg, llm=llm, engine=engine))

    return factory


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


@pytest.fixture
def capsule():
    return load_wardrobe_file(TEST_CAPSULE_PATH)


@pytest.fixture
def capsule_json(capsule):
    return [item.model_dump(by_alias=True, mode="json") for item in capsule]


# --- настоящий пакет wardrobe_rag с тестовым кодировщиком ---------------------------


class DeterministicTestEmbedder:
    """Искусственные векторы ТОЛЬКО для тестов связки (как в rag/tests/conftest.py):
    проверяем интеграцию, а не качество поиска, поэтому веса моделей не скачиваются."""

    fingerprint = "test-only-deterministic-v1"

    def _text(self, texts):
        import numpy as np

        vectors = []
        for text in texts:
            vector = np.full(16, 0.001, dtype=np.float32)
            for token in re.findall(r"\w+", text.lower()):
                vector[hashlib.sha256(token.encode("utf-8")).digest()[0] % 16] += 1.0
            vectors.append(vector / np.linalg.norm(vector))
        return np.asarray(vectors, dtype=np.float32).reshape(len(texts), 16)

    encode_text = _text
    encode_visual_text = _text

    def encode_images(self, images):
        import numpy as np

        vectors = []
        for image in images:
            vector = np.full(16, 0.001, dtype=np.float32)
            vector[:3] = np.asarray(image.convert("RGB"), dtype=np.float32).mean(axis=(0, 1)) + 1.0
            vectors.append(vector / np.linalg.norm(vector))
        return np.asarray(vectors, dtype=np.float32).reshape(len(images), 16)


@pytest.fixture
def rag_engine(tmp_path):
    """WardrobeRagEngine поверх настоящих Chroma, BM25, RRF и проверок из каталога rag/."""
    pytest.importorskip("wardrobe_rag", reason="пакет rag/ не установлен в окружение")
    pytest.importorskip("chromadb")
    from wardrobe_rag.config import RAGConfig
    from wardrobe_rag.images import ImageLoader
    from wardrobe_rag.indexing import IndexingPipeline
    from wardrobe_rag.retrieval import RetrievalEngine
    from wardrobe_rag.service import RAGService
    from wardrobe_rag.store import ChromaWardrobeStore

    from app.rag.wardrobe_rag_engine import WardrobeRagEngine

    images = ImageLoader(REPO_ROOT / "public")
    embedder = DeterministicTestEmbedder()
    store = ChromaWardrobeStore(tmp_path / "rag_data")
    service = RAGService(
        IndexingPipeline(store, embedder, images),
        RetrievalEngine(store, embedder, images, RAGConfig()),
    )
    return WardrobeRagEngine(service, details={"model_fingerprint": embedder.fingerprint})
