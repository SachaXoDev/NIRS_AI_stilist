"""Что пользователь хочет сделать с уже показанным образом.

* правка готового образа: меняются названные вещи, остальные остаются;
* вопрос об образе: состав не меняется;
* новый самостоятельный запрос: прежний образ не используется;
* «потеплее» — правка текущего комплекта; «наряднее» — переподбор (см. `analysis.outfit_revision`).

Разбор детерминированный: его можно проверить тестами, он не добавляет вызов LLM и не зависит
от того, что маленькая локальная модель решит в этот раз. Если из реплики не ясно, о какой
вещи речь, сервер не угадывает, а задаёт один уточняющий вопрос.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas import HistoryMessage
from app.services.analysis import analyze_query
from app.services.textutils import normalize

Operation = Literal["add", "replace", "remove"]
FollowUpKind = Literal["add", "replace", "remove", "ask_item", "card_question", "compatibility", "restore",
                       "cold_feedback", "warmer"]

_W = r"(?<![a-zа-я])"  # начало слова

# Порядок важен: «верхнюю одежду» нужно узнать раньше, чем «верх».
_SLOT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("outerwear", _W + r"(?:верхн\w+\s+(?:одежд\w*|сло\w+)|куртк\w*|пальто|тренч\w*|плащ\w*|жакет\w*|блейзер\w*"
                       r"|пиджак\w*|ветровк\w*|пуховик\w*|парк[ауи]\b|дождевик\w*|бомбер\w*|жилет\w*|накидк\w*"
                       r"|джинсовк\w*|сло[йя]\b)"),
    ("shoes", _W + r"(?:обув\w*|туфл\w*|ботин\w*|ботильон\w*|кроссовк\w*|кед[ыа]?\b|кедами|лофер\w*|сапог\w*|сапожк\w*"
                   r"|сандал\w*|босонож\w*|балетк\w*|каблук\w*|лодочк\w*|дерби|мокасин\w*|слипон\w*|шлепанц\w*)"),
    ("tops", _W + r"(?:верх(?!н)\w{0,2}\b|рубашк\w*|блуз\w*|футболк\w*|топ(?:ик)?\w{0,2}\b|свитер\w*|джемпер\w*"
                  r"|водолазк\w*|лонгслив\w*|майк\w*|худи|свитшот\w*|кардиган\w*|поло\b)"),
    ("bottoms", _W + r"(?:низ[ау]?\b|брюк\w*|джинс\w*|юбк\w*|шорт\w*|штан\w*|лег{1,2}инс\w*|чинос\w*)"),
    ("accessories", _W + r"(?:сумк\w*|сумочк\w*|аксессуар\w*|шарф\w*|платок\w*|платк\w*|шапк\w*|кепк\w*|бейсболк\w*"
                         r"|шляп\w*|серьг\w*|сереж\w*|рем(?:ень|н\w+)\b|украшени\w*|очк\w+|рюкзак\w*|тоут\w*|клатч\w*"
                         r"|бини\b|панам\w*)"),
)
_SLOT_RES = tuple((slot, re.compile(pattern)) for slot, pattern in _SLOT_PATTERNS)

_REPLACE_RE = re.compile(_W + r"(?:замени\w*|заменить|заменим|поменя\w+|смени\w*|сменить|вместо)")
_REMOVE_RE = re.compile(_W + r"(?:убери\w*|убрать|уберем|сними\w*|снять|исключи\w*)")
_ADD_RE = re.compile(_W + r"(?:добав\w+|накин\w+|дополни\w*)")
_REJECT_RE = re.compile(r"^(?:а\s+)?(?:я\s+)?не\s+хочу\s+(?:носить\s+)?(?:эт\w+\s+)?")
_PAIR_JOIN = re.compile(r"\s*(?:,\s*(?:и\s+)?|и\s+)")
_WARMER_RE = re.compile(r"^(?:а\s+)?(?:может(?:\s+быть)?[,\s]+)?"
                        r"(?:(?:можно|сделай(?:те)?|хочу|нужно|давай(?:те)?)\s+)?"
                        r"(?:(?:образ|комплект)\s+)?(?:чуть\s+|немного\s+)?(?:потеплее|теплее)\b")
_COMPATIBILITY_RE = re.compile(r"\b(?:сочета(?:ется|ются|ть|емы)|сочетаемость|"
                               r"(?:идет|идут|подходит|подходят)\s+(?:ли\s+)?(?:к|под))\b")
EDIT_QUESTION_PREFIX = "Уточните, какую вещь"
WARMER_TEMPERATURE_QUESTION = "На какую температуру нужен образ?"
_RESTORE_RE = re.compile(
    r"^(?:пожалуйста[, ]+)?(?:верни(?:те)?|возврати(?:те)?|восстанови(?:те)?|покажи(?:те)?)\s+"
    r"(?:мне\s+)?(?:предыдущ\w*|прошл\w*|прежн\w*)\s+(?:образ\w*|комплект\w*|лук\w*|вариант\w*)\b"
    r"|^(?:отмени(?:те)?\s+(?:последнюю\s+)?(?:правку|замену)|верни(?:те)?\s+как\s+было)[.!\s]*$"
)
_COLD_FEEDBACK_RE = re.compile(
    r"(?:^|[.!,:;–—-]\s*|\b(?:мне|на улице|в них|в этом|в шортах)\s+)(?:слишком\s+)?"
    r"(?:холодно|прохладно|мороз)(?:\s+на улице)?(?:[.!\s]*$|\s*[,.;!—–-])"
    r"|\b(?:зачем|почему)\s+(?:мне\s+)?шорт\w*\b[^.]*\b(?:холодно|прохладно|мороз)\b"
)
# Эти обороты значат правку, только если сразу за ними названа вещь: «без сумки», «не надо шарф»,
# «другую обувь». Иначе «не надо, спасибо» или «другие варианты?» — обычный разговор.
_BOUND_RES = (
    (re.compile(_W + r"(?:без|не\s+надо|не\s+нужн\w+)\s+(?:эт\w+\s+)?"), "remove"),
    (re.compile(_W + r"друг(?:ую|ие|ой|ое|ими|их)\s+"), "replace"),
)

# Тот же оборот с обратным порядком слов: «а обувь другую можно?».
_OTHER_AFTER_RE = re.compile(r"\s+друг(?:ую|ие|ой|ое)\b")

# «Без каблука» описывает нужную замену обуви, а не просьбу что-то убрать.
_HEEL_RE = re.compile(_W + r"каблук\w*")

# Указание на показанный образ: «в этом», «этот образ» или реплика, начинающаяся с «(а) это…».
# «Это» в середине фразы («туфли на каблуке — это уместно?») — связка, а не ссылка на карточку.
_ANAPHORA_RE = re.compile(
    r"^(?:а\s+)?(?:это|этот|он)\b|" + _W + r"(?:в\s+(?:этом|нем|таком)\b|этот\s+(?:образ|комплект|лук))"
)
_COMFORT_RE = re.compile(
    _W + r"(?:комфортн\w*|удобн\w*|жарко|холодно|прохладно|тепло\b|замерзн\w*|замерз\w*|вспотею|уместн\w*"
         r"|подойдет|подходит|подходящ\w*|не\s+слишком)"
)


@dataclass(frozen=True)
class FollowUp:
    kind: FollowUpKind
    slot: str | None = None
    # Слово, которым пользователь назвал вещь («сумк»): по нему выбираем один из двух аксессуаров.
    mention: str | None = None
    # Какое действие осталось неясным для уточняющего вопроса
    operation: Operation | None = None
    extra_targets: tuple[tuple[str, str], ...] = ()
    reject_type: bool = False


def _slot_mentions(text: str) -> list[tuple[int, str, str]]:
    found = []
    for slot, pattern in _SLOT_RES:
        for match in pattern.finditer(text):
            found.append((match.start(), slot, match.group(0)))
    return sorted(found)


def mentioned_garments(query: str) -> list[tuple[str, str]]:
    return [(slot, word) for _, slot, word in _slot_mentions(normalize(query))]


def _targets(text: str, mentions: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    """Читаем список через «и»/запятую, но не цель замены после «на»."""
    targets = mentions[:1]
    for start, slot, word in mentions[1:]:
        prev_start, prev_slot, prev_word = targets[-1]
        end = prev_start + len(prev_word)
        if start < end:  # «верхняя одежда» — одно упоминание
            continue
        gap = text[end:start]
        if not _PAIR_JOIN.fullmatch(gap) or slot in {target[1] for target in targets}:
            break
        targets.append((start, slot, word))
    return targets


def clarify_followup(query: str, previous_query: str, previous_answer: str) -> FollowUp | None:
    """Дополняем последнюю незавершённую правку только в ответ на наш вопрос."""
    previous = classify_followup(previous_query)
    if previous is None:
        return None
    if previous.kind == "warmer" and previous_answer.endswith(WARMER_TEMPERATURE_QUESTION):
        return previous if analyze_query(query).temperature_c is not None else None
    if previous.kind != "ask_item" or previous.operation not in {"replace", "remove"}:
        return None
    if not previous_answer.startswith(EDIT_QUESTION_PREFIX):
        return None
    text = normalize(query).strip(" .!")
    targets = _targets(text, _slot_mentions(text))
    if not targets or targets[0][0] != 0 or targets[-1][0] + len(targets[-1][2]) != len(text):
        return None
    if len(targets) > 1 and previous.operation != "replace":
        return None
    _, slot, word = targets[0]
    return FollowUp(kind=previous.operation, slot=slot, mention=word[:4], operation=previous.operation,
                    extra_targets=tuple((other_slot, name[:4]) for _, other_slot, name in targets[1:]))


def followup_in_dialogue(query: str, history: list[HistoryMessage], end: int) -> FollowUp | None:
    follow_up = classify_followup(query)
    if follow_up is not None or end < 2:
        return follow_up
    question, answer = history[end - 2:end]
    if question.sender == "user" and answer.sender == "assistant" and not answer.has_outfit and not answer.item_ids:
        return clarify_followup(query, question.text, answer.text)
    return None


def _first_operation(text: str) -> tuple[int, str] | None:
    candidates: list[tuple[int, str]] = []
    for pattern, operation in ((_REPLACE_RE, "replace"), (_REMOVE_RE, "remove"), (_ADD_RE, "add")):
        if match := pattern.search(text):
            candidates.append((match.start(), operation))
    for pattern, operation in _BOUND_RES:
        for match in pattern.finditer(text):
            rest = text[match.end():]
            if not _HEEL_RE.match(rest) and any(slot_re.match(rest) for _, slot_re in _SLOT_RES):
                candidates.append((match.start(), operation))
                break
    for start, _, word in _slot_mentions(text):
        if _OTHER_AFTER_RE.match(text, start + len(word)):
            candidates.append((start, "replace"))
            break
    return min(candidates) if candidates else None


def classify_followup(query: str) -> FollowUp | None:
    """Точечная правка или вопрос о последнем образе; None — всё остальное."""
    text = normalize(query)
    if _RESTORE_RE.search(text.strip()):
        return FollowUp(kind="restore")
    cold_feedback = bool(_COLD_FEEDBACK_RE.search(text.strip()))
    if rejection := _REJECT_RE.match(text.strip()):
        rest = text.strip()[rejection.end():]
        mentions = _slot_mentions(rest)
        if mentions and mentions[0][0] == 0 and not _HEEL_RE.match(rest):
            _, slot, word = mentions[0]
            kind = "replace" if slot in {"tops", "bottoms", "shoes"} else "remove"
            return FollowUp(kind=kind, slot=slot, mention=word[:4], operation=kind, reject_type=True)
    operation = _first_operation(text)
    if operation is not None:
        position, name = operation
        mentions = [m for m in _slot_mentions(text) if not (name == "remove" and _HEEL_RE.match(m[2]))]
        # Вещь обычно названа сразу после глагола: «замени туфли на кеды».
        after = [m for m in mentions if m[0] >= position]
        targets = _targets(text, after or mentions) if name == "replace" else (after or mentions)[:1]
        if not targets:
            return FollowUp(kind="ask_item", operation=name)  # type: ignore[arg-type]
        _, slot, word = targets[0]
        if name == "remove" and slot == "bottoms" and word.startswith("шорт") and cold_feedback:
            return FollowUp(kind="replace", slot=slot, mention="шорт", operation="replace")
        return FollowUp(kind=name, slot=slot, mention=word[:4], operation=name,  # type: ignore[arg-type]
                        extra_targets=tuple((other_slot, label[:4]) for _, other_slot, label in targets[1:]))

    if cold_feedback:
        return FollowUp(kind="cold_feedback")
    if _WARMER_RE.match(text.strip()):
        return FollowUp(kind="warmer")
    if _COMPATIBILITY_RE.search(text) and (_slot_mentions(text) or _ANAPHORA_RE.search(text)):
        return FollowUp(kind="compatibility")

    # «В этом будет удобно?» — про образ. Короткая реплика без «в этом» считается вопросом об
    # образе, только если это вопрос: «удобно, спасибо» — не он.
    if _COMFORT_RE.search(text) and (
        _ANAPHORA_RE.search(text) or (len(text.split()) <= 5 and text.rstrip().endswith("?"))
    ):
        return FollowUp(kind="card_question")
    return None


_CONTEXT_RE = re.compile(
    r"^(?:а|и|но|ну|тогда|ладно|хорошо)\b|" + _W
    + r"(?:эт\w+|так\w+\s+же|он[аои]?\b|его\b|ее\b|их\b|нем\b|ней\b|ним\b|тоже|еще|прошл\w+|предыдущ\w+|выше\b"
      r"|вместо|ты\s+(?:говорил|сказал|советовал)\w*)"
)


def refers_to_dialogue(query: str) -> bool:
    """Нужна ли реплике история диалога. Самостоятельный вопрос («с чем носить чёрные ботинки
    на день рождения?») отправляется модели без прошлых сообщений, чтобы старый повод
    (например, пляж) не просочился в ответ."""
    text = normalize(query).strip()
    return len(text.split()) <= 3 or bool(_CONTEXT_RE.search(text))
