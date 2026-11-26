"""Шаг 1 пайплайна — Query Processing: повод, погода, температура, «якорные» вещи."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from app.schemas import RecommendContext, WardrobeItem
from app.services.textutils import normalize


@dataclass(frozen=True)
class OccasionSpec:
    key: str
    label: str
    stems: tuple[str, ...]
    styles: frozenset[str]
    expansion: tuple[str, ...]


OCCASIONS: tuple[OccasionSpec, ...] = (
    OccasionSpec(
        key="beach",
        label="Пляж",
        stems=("пляж", "beach"),
        styles=frozenset({"beach", "пляж"}),
        expansion=("пляж", "летний", "легкий", "сандалии"),
    ),
    OccasionSpec(
        key="business",
        label="Деловой выход",
        stems=("работ", "офис", "делов", "встреч", "презентац", "собеседован", "переговор",
               "совещан", "конференц", "бизнес", "business"),
        styles=frozenset({"business", "smart-casual", "classic", "old-money", "preppy",
                          "деловой", "классика", "офис"}),
        expansion=("офис", "деловой", "строгий", "блейзер", "жакет", "брюки", "рубашка",
                   "лоферы", "business", "smart-casual"),
    ),
    OccasionSpec(
        key="evening",
        label="Вечерний выход",
        stems=("свидан", "вечер", "ресторан", "ужин", "элегант", "театр", "праздн", "вечеринк",
               "коктейл", "торжеств", "выставк", "рожден", "юбиле"),
        styles=frozenset({"chic", "classic", "old-money", "accent", "french", "evening",
                          "smart-casual", "preppy", "вечерний", "тихая роскошь"}),
        expansion=("элегантный", "вечерний", "шелк", "акцент", "блейзер", "платок", "брюки",
                   "туфли", "лоферы", "chic"),
    ),
    OccasionSpec(
        key="travel",
        label="Поездка",
        stems=("поездк", "путешеств", "самолет", "перелет", "отпуск", "дорогу", "дороге", "командировк"),
        styles=frozenset({"casual", "cozy", "minimalism", "streetwear"}),
        expansion=("удобный", "базовый", "кеды", "джинсы", "сумка", "casual"),
    ),
    OccasionSpec(
        key="sport",
        label="Активный день",
        stems=("спорт", "трениров", "пробежк", "фитнес", "йог", "велосипед"),
        styles=frozenset({"sport", "streetwear", "casual", "спорт"}),
        expansion=("спортивный", "кроссовки", "кеды", "удобный", "streetwear"),
    ),
    OccasionSpec(
        key="casual",
        label="Повседневный выход",
        stems=("прогулк", "гулять", "повседнев", "город", "кофе", "выходн", "друзь", "друзей",
               "расслаблен", "casual", "кино"),
        styles=frozenset({"casual", "minimalism", "cozy", "streetwear", "smart-casual",
                          "минимализм", "повседневный"}),
        expansion=("повседневный", "базовый", "джинсы", "кеды", "casual", "минимализм"),
    ),
)
OCCASION_BY_KEY = {spec.key: spec for spec in OCCASIONS}
DEFAULT_OCCASION = "casual"

WEATHER_STEMS: dict[str, tuple[str, ...]] = {
    "rain": ("дожд", "ливен", "ливн", "сыро", "мокр", "слякот", "морос"),
    "snow": ("снег", "снеж", "метел", "мороз", "гололед"),
    "wind": ("ветр", "ветер"),
    "cold": ("холод", "прохлад", "зябк", "осен", "зим", "замерз", "мерзн", "пасмурн"),
    "heat": ("жар", "зной", "духот", "пекл", "лето", "летн"),
}
WEATHER_LABELS = {
    "rain": "дождь",
    "snow": "снег",
    "wind": "ветер",
    "cold": "прохладно",
    "heat": "жарко",
}
WEATHER_EXPANSION: dict[str, tuple[str, ...]] = {
    "rain": ("водоотталкивающий", "тренч", "плащ", "кожа", "демисезонный"),
    "snow": ("теплый", "шерсть", "пальто", "пуховик", "ботинки"),
    "wind": ("тренч", "плащ", "платок", "многослойность"),
    "cold": ("теплый", "шерсть", "кашемир", "свитер", "джемпер", "пальто", "тренч"),
    "heat": ("легкий", "лен", "хлопок", "шелк", "дышащий"),
}

# «+12°C», «-5», «−5» (типографский минус), «12 градусов». Знак не должен стоять сразу после
# буквы/цифры («5-6 вещей»); en dash считается минусом, только если приклеен к числу.
_TEMPERATURE_RE = re.compile(
    r"(?<!\w)(?P<signed>(?:[+\-−]\s*|–|минус\s+)\d{1,2})(?!\d)"
    r"|(?<![\w.,])(?P<plain>\d{1,2})\s*(?:°|град)"
)

COLD_MAX_C = 12
COOL_MAX_C = 17
HOT_MIN_C = 24


_SMALL_TALK_REPLIES = {
    **dict.fromkeys(
        ("привет", "приветик", "здравствуй", "здравствуйте", "добрый день", "доброе утро", "добрый вечер"),
        "Здравствуйте! Для какого повода или погоды подбираем образ?",
    ),
    **dict.fromkeys(
        ("спасибо", "большое спасибо", "спасибо большое", "благодарю", "благодарю вас"),
        "Пожалуйста! Если понадобится ещё один образ, обращайтесь.",
    ),
}


def small_talk_reply(query: str) -> str | None:
    """Распознаём только отдельную реплику, не начало запроса на подбор."""
    phrase = " ".join(normalize(query).strip(" \t\r\n.!?,…").split())
    return _SMALL_TALK_REPLIES.get(phrase)


_ADVICE_RE = re.compile(r"\b(?:что такое|как (?:носить|сочетать|выбрать)|с чем носить|какие? (?:цвета|тренды)|объясни\w*|расскажи\w*)\b")
_WARDROBE_RE = re.compile(r"\b(?:из (?:моих вещей|моей капсулы|(?:моего )?гардероба)|в мо[её]м гардеробе)\b")
_OUTFIT_RE = re.compile(
    r"\b(?:(?:собери\w*|подбери\w*|составь\w*|предложи\w*)[^.!?]*\b(?:образ\w*|лук\w*|комплект\w*|аутфит\w*)"
    r"|(?:что|как) (?:надеть|одеться)|(?:образ|лук|комплект|аутфит)(?:\s+(?:в|для|на|под|к)\b|[.!?]*$))"
)
_REVISION_RE = re.compile(
    r"\b(?:потеплее|полегче|прохладнее|теплее|наряднее|строже|попроще|удобнее|сделай его|замени\w*|"
    r"другой (?:образ|вариант)|еще (?:один |вариант)|а если|а на|а в|а для|а без)\b"
)
# «А на пикник?», «а для театра?» — пользователь сам назвал другой повод.
_NEW_OCCASION_RE = re.compile(r"^\s*а\s+(?:на|в|для)\s+\w+")
_WARMER_RE = re.compile(r"\b(?:потеплее|теплее|добавь\w* (?:слой|пальто|тренч|куртку))\b")


def is_outfit_query(query: str) -> bool:
    """Совет по стилю не означает подбор из гардероба."""
    text = normalize(query)
    if small_talk_reply(query):
        return False
    if _WARDROBE_RE.search(text) or _OUTFIT_RE.search(text):
        return True
    if _ADVICE_RE.search(text):
        return False
    return _detect_temperature(text) is not None or any(
        _has_stem(text, stem) for stems in WEATHER_STEMS.values() for stem in stems
    )


def outfit_revision(query: str, prior_request: str | None) -> tuple[str | None, bool]:
    """Для короткой правки сохраняем повод, если пользователь его не менял."""
    text = normalize(query)
    if not prior_request or _ADVICE_RE.search(text) or not _REVISION_RE.search(text):
        return None, False
    occasion = _detect_occasion(text)
    if occasion is None and not _NEW_OCCASION_RE.search(text):
        occasion = _detect_occasion(normalize(prior_request))
    return occasion, bool(_WARMER_RE.search(text))


def starts_new_topic(query: str) -> bool:
    """Явный новый подбор («подбери образ…») или самостоятельный вопрос о стиле («с чем носить…»):
    такая реплика не правит прошлую карточку и не наследует её повод."""
    text = normalize(query)
    return bool(_OUTFIT_RE.search(text) or _ADVICE_RE.search(text))


def names_occasion(query: str) -> bool:
    return _detect_occasion(normalize(query)) is not None


def is_outfit_revision(query: str) -> bool:
    text = normalize(query)
    return bool(_REVISION_RE.search(text)) and not _ADVICE_RE.search(text)


@dataclass
class QueryAnalysis:
    occasion: str = DEFAULT_OCCASION
    occasion_label: str = OCCASION_BY_KEY[DEFAULT_OCCASION].label
    weather: list[str] = field(default_factory=list)
    temperature_c: int | None = None
    vibe: str | None = None
    expansion_terms: list[str] = field(default_factory=list)
    anchor_item_ids: list[str] = field(default_factory=list)

    @property
    def is_hot(self) -> bool:
        if self.temperature_c is not None:
            return self.temperature_c >= HOT_MIN_C
        return "heat" in self.weather

    @property
    def is_cold(self) -> bool:
        if self.temperature_c is not None:
            return self.temperature_c <= COLD_MAX_C
        return "cold" in self.weather or "snow" in self.weather

    @property
    def needs_outerwear(self) -> bool:
        if self.is_hot:
            return False
        if self.temperature_c is not None and self.temperature_c <= COOL_MAX_C:
            return True
        return any(w in self.weather for w in ("rain", "snow", "wind", "cold"))

    @property
    def occasion_styles(self) -> frozenset[str]:
        return OCCASION_BY_KEY[self.occasion].styles

    def weather_summary(self) -> str:
        parts = [WEATHER_LABELS[w] for w in self.weather]
        if self.temperature_c is not None:
            parts.append(f"{self.temperature_c:+d}°C")
        return ", ".join(parts) if parts else "не указана"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["needs_outerwear"] = self.needs_outerwear
        return data


def _has_stem(text: str, stem: str) -> bool:
    """Основа должна стоять в начале слова: «лето» не должно находиться в «перелетом»."""
    return re.search(rf"(?<![a-zа-я]){re.escape(stem)}", text) is not None


def _detect_occasion(text: str) -> str | None:
    if any(_has_stem(text, stem) for stem in OCCASION_BY_KEY["beach"].stems):
        return "beach"
    best_key, best_hits = None, 0
    for spec in OCCASIONS:  # порядок в OCCASIONS задаёт приоритет при равенстве
        hits = sum(1 for s in spec.stems if _has_stem(text, s))
        if hits > best_hits:
            best_key, best_hits = spec.key, hits
    return best_key


def _detect_temperature(text: str) -> int | None:
    match = _TEMPERATURE_RE.search(text)
    if not match:
        return None
    raw = match.group("signed") or match.group("plain")
    raw = raw.replace("минус", "-").replace("−", "-").replace("–", "-")
    try:
        temperature = int("".join(raw.split()))
        return temperature if -80 <= temperature <= 65 else None
    except ValueError:
        return None


def _detect_anchors(text: str, wardrobe: list[WardrobeItem]) -> list[str]:
    """Вещи, названные в запросе целиком — сценарий «С чем носить в моём гардеробе?»."""
    anchors = []
    for item in wardrobe:
        title = normalize(item.title).strip()
        if len(title) >= 4 and title in text:
            anchors.append(item.id)
    return anchors


def analyze_query(
    query: str,
    context: RecommendContext | None = None,
    wardrobe: list[WardrobeItem] | None = None,
) -> QueryAnalysis:
    query_text = normalize(query)
    ctx_occasion = normalize(context.occasion).strip() if context and context.occasion else ""
    ctx_weather = normalize(context.weather) if context and context.weather else ""

    # Явный контекст из UI важнее, чем эвристика по тексту запроса.
    occasion = (
        (ctx_occasion if ctx_occasion in OCCASION_BY_KEY else _detect_occasion(ctx_occasion))
        or _detect_occasion(query_text)
        or DEFAULT_OCCASION
    )
    spec = OCCASION_BY_KEY[occasion]

    weather_text = f"{ctx_weather} {query_text}"
    weather = [
        key for key, stems in WEATHER_STEMS.items() if any(_has_stem(weather_text, s) for s in stems)
    ]
    temperature = _detect_temperature(ctx_weather) if ctx_weather else None
    if temperature is None:
        temperature = _detect_temperature(query_text)
    if temperature is not None:
        if temperature >= HOT_MIN_C:
            weather = [w for w in weather if w not in ("cold", "snow")]
            if "heat" not in weather:
                weather.append("heat")
        elif temperature <= COOL_MAX_C:
            weather = [w for w in weather if w != "heat"]
            if "cold" not in weather:
                weather.append("cold")

    expansion = list(spec.expansion)
    for key in weather:
        expansion.extend(WEATHER_EXPANSION[key])

    analysis = QueryAnalysis(
        occasion=occasion,
        # Ключ повода («business») — служебное значение: человеку показываем название.
        occasion_label=(
            context.occasion.strip()
            if context and context.occasion and context.occasion.strip() and ctx_occasion not in OCCASION_BY_KEY
            else spec.label
        ),
        weather=weather,
        temperature_c=temperature,
        vibe=(context.vibe.strip() if context and context.vibe and context.vibe.strip() else None),
        expansion_terms=list(dict.fromkeys(expansion)),
        anchor_item_ids=_detect_anchors(query_text, wardrobe or []),
    )
    return analysis
