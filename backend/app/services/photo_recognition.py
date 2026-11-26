"""Zero-shot suggestions for one garment using the already-loaded CLIP encoders."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from app.schemas import Category, PhotoSuggestion

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTO_SIDE = 1600
PHOTO_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}

# A short vocabulary, not a catalog lookup. Labels describe visible types only.
_TYPES: tuple[tuple[Category | None, str, str], ...] = (
    ("shoes", "Кеды или кроссовки", "sneakers or trainers"),
    ("shoes", "Туфли", "low-cut dress shoes without an ankle shaft"),
    ("shoes", "Ботинки или сапоги", "ankle boots or knee-high boots"),
    ("shoes", "Сандалии", "open toe sandals"),
    ("outerwear", "Жакет", "tailored blazer or suit jacket"),
    ("outerwear", "Пальто", "long coat or trench coat"),
    ("outerwear", "Куртка", "casual jacket or puffer jacket"),
    ("tops", "Футболка или топ", "t-shirt or sleeveless top"),
    ("tops", "Рубашка или блуза", "button-up shirt or blouse"),
    ("tops", "Свитер", "knit sweater, cardigan or sweatshirt"),
    ("bottoms", "Брюки или джинсы", "trousers, pants or jeans"),
    ("bottoms", "Юбка", "skirt"),
    ("bottoms", "Шорты", "shorts"),
    ("accessories", "Сумка", "handbag, tote, backpack or purse"),
    ("accessories", "Шарф или платок", "scarf or neckerchief"),
    ("accessories", "Ремень", "a clothing belt"),
    ("accessories", "Головной убор", "hat or cap"),
    (None, "", "a person wearing a whole outfit with several garments"),
    (None, "", "a dress, jumpsuit or one-piece garment"),  # no corresponding wardrobe slot
    (None, "", "an animal, a pet or a face"),
    (None, "", "a room, landscape, food or vehicle"),
    (None, "", "a document, screenshot, or an indistinct abstract image"),
)
_CATEGORY_NAMES: dict[Category, tuple[str, str]] = {
    "shoes": ("Обувь", "a pair of shoes"),
    "outerwear": ("Верхняя одежда", "a jacket or coat"),
    "tops": ("Верх", "a top garment"),
    "bottoms": ("Брюки или юбка", "a bottom garment"),
    "accessories": ("Аксессуар", "a fashion accessory"),
}
_COLORS = (
    ("Чёрный", "black"), ("Белый", "white"), ("Серый", "gray"), ("Бежевый", "beige"),
    ("Коричневый", "brown"), ("Синий", "blue"), ("Голубой", "light blue"), ("Зелёный", "green"),
    ("Красный", "red"), ("Розовый", "pink"), ("Жёлтый", "yellow"), ("Оранжевый", "orange"),
    ("Фиолетовый", "purple"), ("Разноцветный", "multicolored"),
)


class InvalidPhoto(ValueError):
    pass


def decode_photo(photo: bytes | bytearray, media_type: str) -> Any:
    from PIL import Image, ImageOps

    try:
        with Image.open(BytesIO(photo), formats=list(PHOTO_FORMATS.values())) as opened:
            if opened.format != PHOTO_FORMATS[media_type] or getattr(opened, "is_animated", False):
                raise InvalidPhoto("Загрузите одно фото в формате JPEG, PNG или WebP.")
            if opened.width * opened.height > 25_000_000:
                raise InvalidPhoto("Слишком большое разрешение фотографии.")
            if opened.format == "JPEG":
                opened.draft("RGB", (MAX_PHOTO_SIDE, MAX_PHOTO_SIDE))
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((MAX_PHOTO_SIDE, MAX_PHOTO_SIDE))
            if "A" in image.getbands() or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, "white")
                background.alpha_composite(rgba)
                image = background
            return image.convert("RGB")
    except (OSError, Image.DecompressionBombError) as exc:
        raise InvalidPhoto("Не удалось открыть фотографию.") from exc


class PhotoRecognizer:
    """Called under the engine's model lock; lazily cache only label vectors, never user images."""

    def __init__(self, embedder: Any) -> None:
        self._embedder = embedder
        self._type_vectors = None
        self._color_vectors: dict[str, Any] = {}

    def suggest(self, image: Any) -> PhotoSuggestion | None:
        if self._type_vectors is None:
            self._type_vectors = self._embedder.encode_visual_text([
                f"A photo of {label}." for _, _, label in _TYPES
            ])
        vector = self._embedder.encode_images([image])[0]
        scores = self._type_vectors @ vector
        best = int(scores.argmax())
        category, title, label = _TYPES[best]
        competing = max(score for score, (other, _, _) in zip(scores, _TYPES) if other != category)
        # Heuristics on cosine similarity, not calibrated probabilities.
        if category is None or scores[best] < 0.19 or scores[best] - competing < 0.018:
            return None
        if any(
            other == category and index != best and scores[best] - scores[index] < 0.012
            for index, (other, _, _) in enumerate(_TYPES)
        ):
            title, label = _CATEGORY_NAMES[category]

        if label not in self._color_vectors:
            self._color_vectors[label] = self._embedder.encode_visual_text([
                f"A photo of {label}. The item is {color}." for _, color in _COLORS
            ])
        colors = self._color_vectors[label] @ vector
        # Offer the top color even when shades score closely; the user can edit it.
        color = _COLORS[int(colors.argmax())][0]
        return PhotoSuggestion(title=title, category=category, color=color)
