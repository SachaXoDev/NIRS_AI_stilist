"""Small deterministic adapters used ONLY by tests, never by the application."""

from __future__ import annotations

import base64
import hashlib
import io
import re
from collections import Counter

import numpy as np
import pytest
from PIL import Image

from wardrobe_rag.schemas import WardrobeItem


class DeterministicTestEmbedder:
    """Cheap, explicitly artificial vectors to test plumbing without model downloads."""

    fingerprint = "test-only-deterministic-v1"

    def __init__(self) -> None:
        self.calls: Counter[str] = Counter()

    def _text(self, texts: list[str], channel: str) -> np.ndarray:
        self.calls[channel] += len(texts)
        vectors = []
        for text in texts:
            vector = np.full(16, 0.001, dtype=np.float32)
            for token in re.findall(r"\w+", text.lower()):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                vector[digest[0] % len(vector)] += 1.0
            vectors.append(vector / np.linalg.norm(vector))
        return np.asarray(vectors, dtype=np.float32).reshape(len(texts), 16)

    def encode_text(self, texts: list[str]) -> np.ndarray:
        return self._text(texts, "text")

    def encode_visual_text(self, texts: list[str]) -> np.ndarray:
        return self._text(texts, "visual_text")

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        self.calls["image"] += len(images)
        vectors = []
        for image in images:
            vector = np.full(16, 0.001, dtype=np.float32)
            vector[:3] = np.asarray(image.convert("RGB"), dtype=np.float32).mean(axis=(0, 1)) + 1.0
            vectors.append(vector / np.linalg.norm(vector))
        return np.asarray(vectors, dtype=np.float32).reshape(len(images), 16)


@pytest.fixture
def embedder() -> DeterministicTestEmbedder:
    return DeterministicTestEmbedder()


@pytest.fixture
def image_data_url() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (24, 32), (30, 100, 200)).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


@pytest.fixture
def make_item(image_data_url: str):
    def factory(item_id: str, category: str = "tops", title: str = "Белая рубашка", **changes):
        data = {
            "id": item_id,
            "title": title,
            "category": category,
            "color": "Белый",
            "season": "all",
            "style": ["casual"],
            "tags": [],
            "imageUrl": image_data_url,
            "material": "Хлопок",
            "uploadedAt": "2026-11-19",
        }
        data.update(changes)
        return WardrobeItem.model_validate(data)

    return factory


@pytest.fixture
def wardrobe(make_item):
    return [
        make_item("top", "tops", "Изумрудная рубашка"),
        make_item("bottom", "bottoms", "Серые брюки"),
        make_item("shoe", "shoes", "Кожаные лоферы"),
        make_item("coat", "outerwear", "Пальто"),
    ]
