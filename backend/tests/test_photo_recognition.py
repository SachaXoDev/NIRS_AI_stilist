"""The photo API must not turn malformed or ambiguous uploads into wardrobe metadata."""
import asyncio
from io import BytesIO

import pytest

from app.services.label_ocr import parse_label
from app.services.photo_recognition import MAX_PHOTO_BYTES
from app.services.product_text import suggest_from_text

PATH = "/api/wardrobe/recognize"


def test_builtin_engine_has_no_fake_recognition(client):
    response = client.post(PATH, headers={"Content-Type": "image/jpeg"}, content=b"placeholder")
    assert response.status_code == 503


@pytest.mark.parametrize("media_type", ["image/png", "image/svg+xml", "application/json"])
def test_photo_endpoint_rejects_non_images(make_client, rag_engine, media_type):
    client = make_client(engine=rag_engine)
    response = client.post(PATH, headers={"Content-Type": media_type}, content=b'https://example.com/shoe.png')
    assert response.status_code == 422


def test_photo_endpoint_rejects_oversized_upload(make_client, rag_engine):
    client = make_client(engine=rag_engine)
    response = client.post(PATH, headers={"Content-Type": "image/jpeg"}, content=b"x" * (MAX_PHOTO_BYTES + 1))
    assert response.status_code == 413


def test_photo_recognition_abstains_when_category_scores_tie(make_client, rag_engine, monkeypatch):
    import numpy as np
    from PIL import Image

    embedder = rag_engine._service.retriever.embedder
    client = make_client(engine=rag_engine)
    monkeypatch.setattr(embedder, "encode_visual_text", lambda labels: np.ones((len(labels), 1)))
    monkeypatch.setattr(embedder, "encode_images", lambda images: np.ones((len(images), 1)))
    photo = BytesIO()
    Image.new("RGB", (32, 32)).save(photo, format="PNG")
    response = client.post(PATH, headers={"Content-Type": "image/png"}, content=photo.getvalue())
    assert response.status_code == 200
    assert response.json()["suggestion"] is None


def test_photo_recognition_suggests_best_color_even_when_scores_are_close(make_client, rag_engine, monkeypatch):
    import numpy as np
    from PIL import Image

    def encode_labels(labels):
        weights = {
            "A photo of long coat or trench coat.": 0.32,
            "A photo of long coat or trench coat. The item is black.": 0.25,
            "A photo of long coat or trench coat. The item is brown.": 0.249,
        }
        return np.array([[weights.get(label, 0.1)] for label in labels])

    embedder = rag_engine._service.retriever.embedder
    monkeypatch.setattr(embedder, "encode_visual_text", encode_labels)
    monkeypatch.setattr(embedder, "encode_images", lambda images: np.ones((len(images), 1)))
    photo = BytesIO()
    Image.new("RGB", (32, 32)).save(photo, format="PNG")
    response = make_client(engine=rag_engine).post(PATH, headers={"Content-Type": "image/png"}, content=photo.getvalue())
    assert response.status_code == 200
    assert response.json()["suggestion"]["color"] == "Чёрный"


@pytest.mark.parametrize(("lines", "expected"), [
    (["UNIQLO", "95% COTTON", "5% ELASTANE"], {"brand": "Uniqlo", "material": "95% хлопок, 5% эластан"}),
    (["Бренд: Север", "Состав:100% ЛЁН"], {"brand": "Север", "material": "100% лён"}),
    (["Made in Portugal", "Machine wash cold"], {}),
    (["UNIQLO", "COS", "100% COTTON", "100% WOOL"], {}),
    (["Shell: 80% WOOL", "20% unknown fiber"], {}),
    (["Colour: Navy", "Цвет: тёмно-синий"], {"color": "Тёмно-синий"}),
    (["Color: Oat Milk"], {"color": "Oat Milk"}),
    (["Color: 401", "Wash with dark colors"], {}),
    (["Color: Black", "Color: Navy"], {}),
])
def test_label_parser_requires_explicit_evidence(lines, expected):
    assert parse_label(lines) == expected


def test_label_only_never_mistakes_printed_tag_for_garment(make_client, rag_engine, monkeypatch):
    from PIL import Image

    def unexpected_visual_inference(*args):
        pytest.fail("Label upload must not infer visual fields")

    monkeypatch.setattr(rag_engine._photo_recognizer, "suggest", unexpected_visual_inference)
    photo = BytesIO()
    Image.new("RGB", (64, 64), "white").save(photo, format="PNG")
    response = make_client(engine=rag_engine).post(
        f"{PATH}?label_only=true", headers={"Content-Type": "image/png"}, content=photo.getvalue(),
    )
    assert response.status_code == 200
    assert response.json() == {"suggestion": None}


def test_product_prose_preserves_ocr_evidence():
    class Reader:
        async def complete(self, *args, **kwargs):
            return '{"title":"Пальто прямого кроя","category":"outerwear","brand":"Atelier North","material":"100% хлопок"}'

    suggestion = asyncio.run(suggest_from_text([
        "Пальто прямого кроя",
        "Модель от Atelier North B оттенке графит.",
    ], Reader()))
    assert suggestion.model_dump(exclude_none=True) == {
        "title": "Пальто прямого кроя", "category": "outerwear", "brand": "Atelier North", "color": "графит",
    }
