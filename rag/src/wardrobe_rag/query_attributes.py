"""Conservative Russian attribute grammar for wardrobe retrieval (no model call)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, cast

from .schemas import Category, MaterialPart, WardrobeItem


def normalize(text: str) -> str:
    return text.casefold().replace("ё", "е")


# The same families match the request and the saved fields. Keep the OCR text as-is on the card.
COLORS = {
    "черный": r"черн\w*|black", "белый": r"бел\w*|white", "серый": r"сер(?:ый|ая|ое|ые|ого|ой|ых|ую|ым|ыми)|графит\w*|gr[ae]y",
    "бежевый": r"бежев\w*|беж|beige", "синий": r"син(?:ий|яя|ее|ие|его|ей|их|юю|им|ими)|navy|blue",
    "голубой": r"голуб\w*", "красный": r"красн\w*|red", "зеленый": r"зелен\w*|green", "желтый": r"желт\w*|yellow",
    "розовый": r"розов\w*|pink", "коричневый": r"коричнев\w*|шоколад\w*|brown", "бордовый": r"бордов\w*",
    "молочный": r"молочн\w*|кремов\w*|айвори|ivory", "фиолетовый": r"фиолетов\w*", "оранжевый": r"оранжев\w*",
    "темный": r"темн(?:ый|ая|ое|ые|ого|ой|ых|ую|ым|ыми)|dark", "светлый": r"светл(?:ый|ая|ое|ые|ого|ой|ых|ую|ым|ыми)|light",
}
FIBERS = {
    "искусственная кожа": r"(?:искусственн\w*|синтетическ\w*|веганск\w+)\s+кож\w+|экокож\w+|faux leather|synthetic leather",
    "натуральная кожа": r"натуральн\w+\s+кож\w+|genuine leather|real leather",
    "кожа": r"кож(?:а|и|е|у|ей|ан\w+)|leather",
    "хлопок": r"хлоп(?:ок|к\w+)|cotton", "шерсть": r"шерст\w*|wool|меринос\w*|альпак\w*",
    "кашемир": r"кашемир\w*|cashmere", "лен": r"лен|льн\w*|linen|flax", "шелк": r"шелк\w*|silk",
    "вискоза": r"вискоз\w*|viscose|rayon", "полиэстер": r"полиэстер\w*|polyester",
    "полиамид": r"полиамид\w*|нейлон\w*|polyamide|nylon", "эластан": r"эластан\w*|elastane|spandex",
    "акрил": r"акрил\w*|acrylic", "лиоцелл": r"лиоцелл\w*|lyocell|tencel", "модал": r"модал\w*|modal",
    "замша": r"замш\w*|suede", "нубук": r"нубук\w*|nubuck", "деним": r"деним\w*|denim",
    "текстиль": r"текстил\w*|textile", "пух": r"пух(?:а|ом|ов\w+)?|down", "резина": r"резин\w*|rubber",
    "полиуретан": r"полиуретан\w*|polyurethane", "сетка": r"сетк\w*|mesh",
}

# Explicit garment nouns, independent of clothing titles in a particular wardrobe.
GARMENTS: dict[Category, dict[str, str]] = {
    "tops": {"верх": r"верх(?:а|у|ом)?(?!\s+(?:из|состоит|без))", "рубашка": r"рубашк\w*", "блузка": r"блуз\w*", "футболка": r"футболк\w*", "свитер": r"свитер\w*", "джемпер": r"джемпер\w*", "топ": r"топ(?:а|у|ом|ы|ов)?", "кардиган": r"кардиган\w*", "водолазка": r"водолазк\w*", "худи": r"худи", "майка": r"майк\w*", "свитшот": r"свитшот\w*"},
    "bottoms": {"низ": r"низ(?:а|у|ом)?", "брюки": r"брюк\w*|штан\w*", "джинсы": r"джинс(?:ы|ами|ах|ов|ам)?", "юбка": r"юбк\w*", "шорты": r"шорт\w*", "легинсы": r"лег{1,2}инс\w*"},
    "shoes": {"обувь": r"обув\w*", "кроссовки": r"кроссов(?:к\w*|ок)", "кеды": r"кед(?:ы|а|ами|ах|ам)?", "лоферы": r"лофер\w*", "ботинки": r"ботин\w*", "туфли": r"туфл\w*|туфель", "сапоги": r"сапог\w*|сапожк\w*", "сандалии": r"сандал\w*", "босоножки": r"босонож\w*", "балетки": r"балетк\w*", "мокасины": r"мокасин\w*"},
    "outerwear": {"верхняя одежда": r"верхн\w+\s+(?:одежд\w+|слой)", "пальто": r"пальто", "куртка": r"куртк\w*|курток", "тренч": r"тренч\w*", "плащ": r"плащ\w*", "жакет": r"жакет\w*|блейзер\w*|пиджак\w*", "пуховик": r"пуховик\w*", "ветровка": r"ветровк\w*", "бомбер": r"бомбер\w*"},
    "accessories": {"аксессуары": r"аксессуар\w*", "сумка": r"сумк\w*|сумок|сумочк\w*|тоут\w*", "шарф": r"шарф\w*", "платок": r"плат(?:ок|к\w*)", "рюкзак": r"рюкзак\w*", "ремень": r"рем(?:ень|н\w+)", "шапка": r"шапк\w*", "кепка": r"кепк\w*", "серьги": r"серьг\w*|сережк\w*"},
}
GENERIC = {"верх", "низ", "обувь", "верхняя одежда", "аксессуары"}
PART_NAMES: dict[MaterialPart, str] = dict(lining="подкладка", insulation="утеплитель наполнитель", sole="подошва", insole="стелька", trim="отделка")
Part = MaterialPart | Literal["main", "any"]
_PART_RE = re.compile(r"\b(?:(?P<lining>подкладк\w*)|(?P<insulation>утеплител\w*|наполнител\w*)|(?P<sole>подошв\w*)|(?P<insole>стельк\w*)|(?P<trim>отделк\w*)|(?P<main>материал\w*\s+верх\w*|основн\w+\s+ткан\w*|верх(?:а|ом|у)?))\b")
_PREFERENCE = re.compile(r"\b(?:желательно|предпочтительно|по возможности|в идеале|лучше бы|необязательно|не обязательно)\b")
_NEGATION = re.compile(r"\b(?:без|никако(?:й|го|е|их)|не(?:\s+из|\s+должн\w*\s+быть)?|исключи\w*)\s+(?:содержания\s+)?$")
_WHOLE = re.compile(r"\b(?:вообще|совсем|полностью|строго)\s+без\s*$")
_BOUNDARY = re.compile(r"[;!?\n]|(?<!\d)\.|\.(?!\d)|,\s*(?:а\b|плюс\b)")
_GLOBAL = re.compile(r"\b(?:образ\w*|лук\w*|комплект\w*|везде|нигде|в целом|в(?:о)? всем)\b")
_ALTERNATIVE = re.compile(r"\b(?:или|либо)\b")
_NEGATIVE_LIST = re.compile(r"\s*(?:,|и|или|либо|ни)\s*$")
_INTENT = re.compile(r"^\s*(?:(?:я\s+)?(?:хочу|ищу)|нуж(?:ен|на|но|ны)|подбери\w*|предложи\w*)\b")
_SHARE = re.compile(r"(?:(?P<op>не менее|не меньше|от|минимум|не более|не больше|до|максимум)\s+)?(?P<value>\d{1,3}(?:[,.]\d+)?)\s*%\s*$")
_SHARES_IN_VALUE = re.compile(r"(?P<value>\d{1,3}(?:[,.]\d+)?)\s*%\s*(?P<fiber>[^,;]+)")


def _matcher(patterns: dict[str, str]) -> tuple[re.Pattern[str], tuple[str, ...]]:
    return re.compile(r"\b(?:" + "|".join(f"(?P<p{i}>{pattern})" for i, pattern in enumerate(patterns.values())) + r")\b"), tuple(patterns)


def _matches(matcher: tuple[re.Pattern[str], tuple[str, ...]], text: str):
    pattern, keys = matcher
    for match in pattern.finditer(text):
        assert match.lastgroup is not None
        yield match, keys[int(match.lastgroup[1:])]


_COLOR = _matcher(COLORS)
_FIBER = _matcher(FIBERS)
_GARMENT = _matcher({key: pattern for entries in GARMENTS.values() for key, pattern in entries.items()})
_CATEGORY = {key: category for category, entries in GARMENTS.items() for key in entries}


@dataclass(frozen=True)
class Condition:
    slot: Category | None
    kind: Literal["color", "material", "type"]
    value: str
    exclude: bool = False
    preferred: bool = False
    part: Part = "main"
    whole: bool = False
    share: float | None = None
    comparison: str = "="


def is_detailed_selection(query: str) -> bool:
    return bool(_INTENT.match(normalize(query)) and any(condition.slot for condition in query_conditions(query)))


@lru_cache(maxsize=512)
def query_conditions(query: str, target: Category | None = None) -> tuple[Condition, ...]:
    conditions: list[Condition] = []
    # Exact quoted garment titles are anchors, not conditions to reinterpret.
    text = re.sub(r'«[^»]+»|"[^"\n]+"', ' ', normalize(query))
    for clause in _BOUNDARY.split(text):
        nouns = list(_matches(_GARMENT, clause))
        mentions = []
        for noun, name in nouns:
            prefix = clause[:noun.start()]
            if _NEGATION.search(prefix):
                continue
            # «хлопковый верх пальто» / «пальто с хлопковым верхом»: a part, not a second garment.
            if name == "верх" and any(other not in GENERIC for _, other in nouns):
                adjacent = re.search(r"\b(?:материал\w*|основн\w*|хлопк\w*|кожан\w*|шерстян\w*|льнян\w*|шелков\w*)\s+$", prefix)
                suffix = clause[noun.end():]
                looks_like_part = re.match(r"\s*(?:[:—–]|из\b|(?:не\s+)?(?:менее|более|меньше|больше)\b|\d+\s*%)", suffix)
                independent = re.search(r"\b(?:и|а)\s+(?:\w+\s+)?$", prefix)
                if (adjacent or looks_like_part) and not independent:
                    continue
            mentions.append((noun, name))
        prefer = list(_PREFERENCE.finditer(clause))
        # Do not turn disjunctions into simultaneous hard requirements.
        alternative = bool(_ALTERNATIVE.search(clause))
        for kind, matcher in (("color", _COLOR), ("material", _FIBER)):
            last_negative_end = -1
            for match, value in _matches(matcher, clause):
                before = clause[:match.start()]
                share = _SHARE.search(before) if kind == "material" else None
                prefix = before[:share.start()] if share else before
                negative = bool(_NEGATION.search(prefix))
                if not negative and last_negative_end >= 0 and _NEGATIVE_LIST.fullmatch(clause[last_negative_end:match.start()]):
                    negative = True
                last_negative_end = match.end() if negative else -1
                previous = next(((m, name) for m, name in reversed(mentions) if m.end() <= match.start()), None)
                following = next(((m, name) for m, name in mentions if m.start() >= match.end()), None)
                # Prefix adjectives belong to the next noun; «из льна» / «без кожи» follow their noun.
                next_words = clause[match.end():following[0].start()] if following else ""
                prefix_adjective = bool(following and re.fullmatch(r"(?:[\s-]+[а-я]+){0,2}\s*", next_words)
                                        and not re.search(r"\b(?:и|с|к|для|под|а|на)\b", next_words)
                                        and not negative and not re.search(r"\bиз\s*$", prefix))
                owner = following if prefix_adjective else previous or following
                if kind == "material" and previous and following and _PART_RE.match(next_words.lstrip()):
                    owner = previous
                gap = clause[owner[0].end():match.start()] if owner and owner == previous else ""
                if negative and (
                    (previous is None and _GLOBAL.search(before))
                    or (previous is not None and _GLOBAL.search(gap))
                    or (previous is None and following and re.match(r"\s+(?:с|под|к)\b", next_words))
                ):
                    owner = None
                slot = _CATEGORY[owner[1]] if owner else target
                if not negative and slot is None:
                    continue
                # Adjectives or explicit composition phrases, not occurrences like «в стиле кожа и металл».
                explicit = (
                    re.search(r"\b(?:из|с|цвет\w*|подклад\w*|верх\w*|наполнител\w*|утеплител\w*)\b|[:–—]", gap)
                    or (kind == "color" and owner == previous and not gap.strip())
                    or share or prefer or target
                    or (following is None and re.search(r"(?:,|\b(?:именно|обязательно)\b)", gap))
                )
                if not negative and not prefix_adjective and not explicit:
                    continue
                start = previous[0].end() if prefix_adjective and previous else (owner[0].start() if owner else 0)
                if owner and not prefix_adjective:
                    start = max(0, clause.rfind(",", 0, owner[0].start()) + 1)
                preferred = (alternative and not negative) or any(start <= p.start() <= match.start() for p in prefer)
                part: Part = "any" if negative else "main"
                if kind == "material":
                    suffix = clause[match.end():following[0].start() if following else len(clause)]
                    early_part = list(_PART_RE.finditer(gap))
                    late_part = _PART_RE.match(re.sub(r"^\s+(?:(?:в|на|для)\s+)?", "", suffix))
                    part_match = late_part or (early_part[-1] if early_part else None)
                    if part_match and part_match.lastgroup:
                        part = cast(Part, part_match.lastgroup)
                op = share["op"] if share else None
                amount = float(share["value"].replace(",", ".")) if share else None
                comparison = ">=" if op in {"не менее", "не меньше", "от", "минимум"} else "<=" if op else "="
                conditions.append(Condition(slot, kind, value, negative, preferred, part,
                                            kind == "material" and negative and bool(_WHOLE.search(prefix)), amount, comparison))
                if owner and owner[1] not in GENERIC:
                    kind_soft = (alternative and not negative) or (
                        preferred and any(p.start() < owner[0].start() for p in prefer)
                    )
                    conditions.append(Condition(slot, "type", owner[1], preferred=kind_soft))
    return tuple(dict.fromkeys(conditions))


def _color_values(text: str) -> set[str]:
    colors = {value for _, value in _matches(_COLOR, normalize(text))}
    if colors & {"черный", "бордовый"} or re.search(r"\b(?:темно[- ]|navy\b|графит)", normalize(text)):
        colors.add("темный")
    if colors & {"белый", "молочный"} or re.search(r"\bсветло[- ]", normalize(text)):
        colors.add("светлый")
    return colors


def color_families(text: str) -> set[str]:
    return _color_values(text) - {"темный", "светлый"}


def _fiber_values(text: str) -> set[str]:
    return {value for _, value in _matches(_FIBER, normalize(text))}


def _contains_fiber(values: set[str], wanted: str) -> bool:
    aliases = {"кожа": {"натуральная кожа", "замша", "нубук"}, "шерсть": {"кашемир"},
               "натуральная кожа": {"кожа", "замша", "нубук"}}
    return wanted in values or bool(values & aliases.get(wanted, set()))


def material_values(text: str) -> set[str]:
    return _fiber_values(text)


def _evidence(item: WardrobeItem, condition: Condition) -> bool | None:
    if condition.kind == "color":
        colors = _color_values(item.color)
        return condition.value in colors if colors else None
    if condition.kind == "type":
        facts = " ".join([item.title, *item.tags])
        return any(value == condition.value for _, value in _matches(_GARMENT, normalize(facts)))
    details = item.materialDetails or {}
    if condition.part == "any":
        texts = [item.material or "", *details.values()]
    elif condition.part == "main":
        texts = [item.material or ""]
    else:
        texts = [details.get(condition.part, "")]
    fibers = _fiber_values("; ".join(texts))
    if condition.share is not None:
        shares = [float(match["value"].replace(",", ".")) for text in texts
                  for match in _SHARES_IN_VALUE.finditer(normalize(text))
                  if _contains_fiber(_fiber_values(match["fiber"]), condition.value)]
        if not shares:
            return False if fibers and not _contains_fiber(fibers, condition.value) else None
        value = shares[0]
        return value >= condition.share if condition.comparison == ">=" else value <= condition.share if condition.comparison == "<=" else value == condition.share
    if _contains_fiber(fibers, condition.value):
        return True
    # A label normally describes individual components, not every potentially present trim.
    if condition.whole:
        return None
    known = _fiber_values(texts[0])
    return False if known and normalize(texts[0]).strip() not in {"текстиль", "textile", "сетка", "mesh"} else None


def attribute_violations(item: WardrobeItem, conditions: tuple[Condition, ...]) -> list[str]:
    violations = []
    for condition in conditions:
        if condition.preferred or condition.slot not in (None, item.category):
            continue
        evidence = _evidence(item, condition)
        if condition.exclude:
            rejected = evidence is True or (
                evidence is None and condition.kind == "material" and (condition.slot is not None or condition.whole)
            )
        else:
            rejected = evidence is not True
        if rejected:
            violations.append(f"{condition.kind}: {condition.value} ({'unknown' if evidence is None else 'conflict'})")
    return violations


def preference_score(item: WardrobeItem, conditions: tuple[Condition, ...]) -> int:
    return sum(condition.preferred and condition.slot in (None, item.category)
               and _evidence(item, condition) is (not condition.exclude) for condition in conditions)
