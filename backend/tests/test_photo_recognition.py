"""The photo API must not turn malformed or ambiguous uploads into wardrobe metadata."""
import asyncio
import json
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


@pytest.mark.parametrize(("lines", "expected"), [
    (["Основная ткань: 97,5% хлопка, 2,5% эластана", "Подкладка: 100% полиэстер"],
     "97,5% хлопок, 2,5% эластан"),
    (["Upper: genuine leather; lining: synthetic leather; sole: rubber"], "Натуральная кожа"),
    (["Состав", "90% шерсти", "10% кашемира", "Состав подкладки", "100% вискозы"],
     "90% шерсть, 10% кашемир"),
    (["Рубашка сшита из льна."], "Лён"),
    (["Подкладка: 100% полиэстер"], None),
    (["Верх: 80% шерсти, 20% неразборчиво", "Подкладка: 100% хлопок"], None),
])
def test_main_material_read_from_product_text(lines, expected):
    assert parse_label(lines).get("material") == expected


def test_component_compositions_remain_independent():
    assert parse_label([
        'Upper: 100% Cotton; Lining: 97,5% viscose, 2,5% elastane; Sole: rubber',
        'Insulation: 90% down, 10% unknown',
        'Made in Italy, wash with similar colours',
    ]) == {
        'material': '100% хлопок',
        'materialDetails': {'lining': '97,5% вискоза, 2,5% эластан', 'sole': 'Резина'},
    }


def test_incomplete_explicit_composition_does_not_become_exact_suggestion():
    class Reader:
        async def complete(self, *args, **kwargs):
            return '{"material":"90% wool"}'

    assert asyncio.run(suggest_from_text(['Shell: 90% wool'], Reader())) is None


def test_component_heading_is_not_a_product_name():
    class Reader:
        async def complete(self, *args, **kwargs):
            return '{"title":"Shell","category":"outerwear"}'

    suggestion = asyncio.run(suggest_from_text(['Shell: 100% Cotton', 'Lining: 100% Wool'], Reader()))
    assert suggestion.title is None and suggestion.category is None
    assert suggestion.materialDetails == {'lining': '100% шерсть'}


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


def test_model_cannot_use_lining_as_main_material():
    class Reader:
        async def complete(self, *args, **kwargs):
            return '{"title":"Куртка","category":"outerwear","material":"100% полиэстер"}'

    suggestion = asyncio.run(suggest_from_text(["Куртка", "Подкладка: 100% полиэстер"], Reader()))
    assert suggestion.title == "Куртка"
    assert suggestion.material is None


def test_ocr_composition_does_not_replace_product_name():
    class Reader:
        async def complete(self, *args, **kwargs):
            return '{"title":"80% Cotton, 20% Polyester","category":"outerwear"}'

    suggestion = asyncio.run(suggest_from_text(["80% Cotton, 20% Polyester"], Reader()))
    assert suggestion.model_dump(exclude_none=True) == {"material": "80% хлопок, 20% полиэстер"}


@pytest.mark.parametrize(("result", "title", "category"), [
    ('{"title":"Кроссовки North","category":"outerwear"}', "Кроссовки North", "shoes"),
    ('{"title":"North Sneakers"}', "North Sneakers", "shoes"),
    ('{"title":"North Trail","category":"outerwear"}', "Куртка", "outerwear"),
    ('{"title":"Куртка и кроссовки","category":"shoes"}', "Куртка", "outerwear"),
])
def test_photo_api_replaces_garment_identity_only_with_a_grounded_pair(
    client, monkeypatch, result, title, category,
):
    from PIL import Image

    from app.schemas import PhotoSuggestion

    class Reader:
        async def complete(self, *args, **kwargs):
            return result

    monkeypatch.setattr(client.app.state, "photo_recognizer", lambda image: PhotoSuggestion(
        title="Куртка", category="outerwear", color="Чёрный",
    ))
    monkeypatch.setattr(client.app.state, "product_reader", Reader())
    source_title = json.loads(result)["title"]
    monkeypatch.setattr("app.api.wardrobe.read_text", lambda image: [source_title, "Season: Spring/Summer"])
    photo = BytesIO()
    Image.new("RGB", (32, 32)).save(photo, format="PNG")
    response = client.post(PATH, headers={"Content-Type": "image/png"}, content=photo.getvalue())
    assert response.status_code == 200
    suggestion = response.json()["suggestion"]
    assert (suggestion["title"], suggestion["category"]) == (title, category)
    assert suggestion["color"] == "Чёрный"
    assert suggestion["season"] == "spring/summer"


@pytest.mark.parametrize(("lines", "season"), [
    (["Зимние кроссовки", "Утеплитель: 100% полиэстер"], None),
    (["Сезонность: Всесезонно"], "all"),
    (["Сезон: осень — зима", "Season: Spring/Summer"], None),
    (["Season: All-season", "Season: Summer"], None),
])
def test_season_can_only_be_suggested_from_unambiguous_label(lines, season):
    assert parse_label(lines).get("season") == season
