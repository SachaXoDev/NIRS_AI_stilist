"""Проверка ответа модели по найденным документам — без второй модели и без догадок.

Маленькая локальная модель отвечает по существу, но систематически делает три ошибки,
которые видны в записанных прогонах (`kt2_data/*/per_query.json`):

1. упоминает документ в тексте («по Д22») вместо ссылки — вывод остаётся без источника;
2. искажает число при переписывании («27 о К» вместо «2700 К»);
3. пропускает условия и исключения из тех же документов, на которые сама ссылается
   («а не размытием», «вешалка остаётся на площадке»).

Первые два случая исправляются здесь детерминированно, третий — находится:

* ссылка из текста переносится в источники утверждения;
* утверждение с числом или шифром, которых нет ни в его источниках, ни в вопросе, не выдаётся
  за проверенное: значение из другого найденного документа получает свой источник, явную
  опечатку заменяет дословное предложение источника, повтор уже сказанного убирается,
  остальное помечается как неподтверждённое;
* `unused_sentences` перечисляет предложения процитированных документов, которые ответ не
  отразил. Какие из них нужны для ответа, решает не этот модуль: дописывать их все значило бы
  выдавать пересказ документа за ответ. Список идёт модели на повторную проверку и в диагностику.

Слой ничего не сочиняет: он либо переносит ссылку, либо цитирует документ слово в слово.
Отказ модели («в документах нет этой информации») он не трогает.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from app.kt2_search import tokens

PartKind = Literal["model", "quote"]

# Латинская D или кириллическая Д с двумя цифрами: «[D22]», «D22», «по Д22».
# Шифры вещей в корпусе пишутся через дефис («П-4»), поэтому с ними не путается.
_DOC_MENTION = re.compile(r"\[\s*[DД]\s?(\d{2})\s*\]|(?<![\w-])[DД](\d{2})(?![\w-])")
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
_NUMBER = re.compile(r"\d+(?:[:.,]\d+)*")
_CODE = re.compile(r"(?<![\w-])[А-ЯЁA-Z]{1,2}-\d+[А-ЯЁA-Z]?(?![\w-])")
_SPACES = re.compile(r"\s{2,}")

# Предложение считается отражённым, если в ответе есть хотя бы такая доля его содержательных слов.
COVERED_SHARE = 0.5
# Насколько утверждение должно совпадать с предложением источника, чтобы заменить его цитатой.
QUOTE_MATCH_SHARE = 0.5
# Неподтверждённое утверждение убирается, если всё остальное в нём уже сказано в ответе или вопросе.
REDUNDANT_SHARE = 0.8
QUOTE_PREFIX = "Дословно из источника: "
MAX_UNUSED = 8

_STOPWORDS = frozenset(tokens(
    "и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее мне "
    "было вот от меня еще нет о из ему теперь когда даже ну ли если уже или ни быть был него до вас "
    "нибудь уж вам ведь там потом себя ничего ей может они тут где есть надо ней для мы тебя их чем "
    "была сам чтоб без будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой "
    "совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда зачем всех никогда можно "
    "при наконец два об другой хоть после над больше тот через эти нас про всего них какая много "
    "разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть том нельзя такой им более "
    "всегда конечно всю между это эта также который которая которое которые которого которой нужно "
    "нужен нужна должен должна какие какую каком поэтому вместо тут сами само такая такое такие "
    "этих этим этими свой своя свое свои один одна одно оба обе либо однако лишь именно то есть"
))


@dataclass
class Part:
    text: str
    source_ids: list[str]
    kind: PartKind = "model"
    # False — в утверждении есть число или шифр, которых нет в его источниках и в вопросе.
    verified: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass
class Review:
    parts: list[Part]
    notes: list[str] = field(default_factory=list)  # что слой изменил — для журнала и интерфейса


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_END.split(text.strip()) if sentence.strip()]


def content_stems(text: str) -> set[str]:
    """Основы содержательных слов: без служебных слов и слов короче трёх букв (числа остаются)."""
    return {
        token for token in tokens(_DOC_MENTION.sub(" ", text))
        if token not in _STOPWORDS and (len(token) >= 3 or token.isdigit())
    }


def _roots(stems: set[str]) -> set[str]:
    """Грубое сравнение для связи с вопросом: «шалфея» и «шалфей» дают разные основы, но один корень."""
    return {stem[:4] for stem in stems if len(stem) >= 4 or stem.isdigit()}


def _normal_number(raw: str) -> str:
    # «09:30» и «9:30», «2,5» и «2.5» — одно и то же значение.
    return ":".join(piece.lstrip("0") or "0" for piece in raw.replace(",", ".").split(":"))


def hard_tokens(text: str) -> set[str]:
    """Значения, которые нельзя пересказать своими словами: числа от двух цифр и шифры вида «Л-14Д»."""
    text = _DOC_MENTION.sub(" ", text)
    found = {code.casefold() for code in _CODE.findall(text)}
    for number in _NUMBER.findall(_CODE.sub(" ", text)):
        if sum(char.isdigit() for char in number) >= 2:
            found.add(_normal_number(number))
    return found


def _shown(values: set[str]) -> str:
    return ", ".join(sorted(value.upper() for value in values))


def _as_int(token: str) -> int | None:
    return int(token) if token.isdigit() else None


def _derivable(token: str, grounded: set[str]) -> bool:
    """Итог, посчитанный из чисел источников: «400 рублей» = 220 + 2 × 90, «180» = 2 × 90.

    Множители малы намеренно: чем шире правило, тем больше выдуманных чисел оно пропустит.
    """
    target = _as_int(token)
    if target is None:
        return False
    numbers = sorted({value for value in map(_as_int, grounded) if value})
    if any(a * count == target for a in numbers for count in range(1, 13)):  # «две пуговицы по 90»
        return True
    few = range(1, 4)
    return any(
        a * m + b * n == target or a * m - b * n == target
        for a in numbers for b in numbers for m in few for n in few
    )


def _looks_garbled(token: str, grounded: set[str]) -> bool:
    """«27» при «2700» в источнике — обрывок настоящего числа, а не самостоятельное значение."""
    digits = re.sub(r"\D", "", token)
    return any(
        digits != plain and len(plain) > len(digits) and (plain.startswith(digits) or plain.endswith(digits))
        for plain in (re.sub(r"\D", "", value) for value in grounded) if plain
    )


# Ссылка в скобках вместе с вводным словом и круглыми скобками: «(см. [D06])», «согласно [D22]».
_BRACKETED = re.compile(r"\(?\s*(?:(?:см\.?|согласно|по|из)\s*)?\[\s*[DД]\s?\d{2}\s*\]\s*\)?", re.IGNORECASE)


def _extract_mentions(text: str) -> tuple[str, list[str]]:
    """Убрать из текста ссылки в скобках и вернуть ID всех упомянутых документов."""
    mentioned = [f"D{bracketed or bare}" for bracketed, bare in _DOC_MENTION.findall(text)]
    cleaned = _SPACES.sub(" ", _BRACKETED.sub(" ", text))
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[,;:]+([.!?])", r"\1", cleaned)  # «…метамерия, [D19].» → «…метамерия.»
    cleaned = re.sub(r"([.,;:!?])\1+", r"\1", cleaned).strip()
    return cleaned, list(dict.fromkeys(mentioned))


def _best_sentence(stems: set[str], sentences: list[tuple[str, str, set[str]]]) -> tuple[str, str, float] | None:
    """Предложение источника, ближе всего к утверждению: (id документа, текст, доля совпадения)."""
    best: tuple[str, str, float] | None = None
    for doc_id, sentence, sentence_stems in sentences:
        if not stems or not sentence_stems:
            continue
        share = len(stems & sentence_stems) / min(len(stems), len(sentence_stems))
        if best is None or share > best[2]:
            best = (doc_id, sentence, share)
    return best


def review_answer(question: str, documents: dict[str, str], draft: list[tuple[str, str]]) -> Review:
    """Проверить черновик `[(текст, id документа)]` по найденным документам `{id: текст}`."""
    review = Review(parts=[])
    by_doc = {
        doc_id: [(doc_id, sentence, content_stems(sentence)) for sentence in split_sentences(text)]
        for doc_id, text in documents.items()
    }
    doc_tokens = {doc_id: hard_tokens(text) for doc_id, text in documents.items()}
    question_tokens = hard_tokens(question)

    # 1. Ссылки: то, что модель написала в тексте, становится источником утверждения.
    for raw_text, source_id in draft:
        text, mentioned = _extract_mentions(raw_text)
        if not text:
            continue
        sources = [source_id]
        for doc_id in mentioned:
            if doc_id in documents and doc_id not in sources:
                sources.append(doc_id)
                review.notes.append(f"ссылка на {doc_id} перенесена из текста в источники")
            elif doc_id not in documents:
                review.notes.append(f"в тексте упомянут {doc_id}, которого нет в выдаче")
        review.parts.append(Part(text=text, source_ids=sources))

    # 2. Числа и шифры: каждое значение должно быть в источниках утверждения или в вопросе.
    checked: list[Part] = []
    for index, part in enumerate(review.parts):
        own = set().union(*(doc_tokens[doc_id] for doc_id in part.source_ids)) | question_tokens
        missing = {token for token in hard_tokens(part.text) if token not in own and not _derivable(token, own)}
        # Значение взято из другого найденного документа — у вывода появляется второй источник.
        for doc_id, values in doc_tokens.items():
            if missing & values and doc_id not in part.source_ids:
                part.source_ids.append(doc_id)
                review.notes.append(f"источник {doc_id} добавлен: из него взято {_shown(missing & values)}")
                own |= values
                missing -= values
        if not missing:
            checked.append(part)
            continue

        shown = _shown(missing)
        stems = content_stems(part.text) - missing
        elsewhere = content_stems(question).union(
            *(content_stems(other.text) for position, other in enumerate(review.parts) if position != index)
        )
        cited = [row for doc_id in part.source_ids for row in by_doc[doc_id]]
        match = _best_sentence(stems, cited)
        if stems and len(stems & elsewhere) / len(stems) >= REDUNDANT_SHARE:
            review.notes.append(f"убран повтор с искажённым значением ({shown})")
        elif all(_looks_garbled(token, own) for token in missing) and match and match[2] >= QUOTE_MATCH_SHARE:
            doc_id, sentence, _ = match
            review.notes.append(f"утверждение с искажённым значением ({shown}) заменено цитатой из {doc_id}")
            checked.append(Part(text=sentence, source_ids=[doc_id], kind="quote"))
        else:
            part.verified = False
            part.notes.append(f"нет в источниках: {shown}")
            review.notes.append(f"не подтверждено источниками: {shown}")
            checked.append(part)
    review.parts = checked
    return review


def unused_sentences(question: str, documents: dict[str, str], parts: list[Part]) -> list[tuple[str, str]]:
    """Предложения процитированных документов, которых нет в ответе: `[(id документа, текст)]`.

    Это кандидаты на пропущенные условия и исключения, а не готовые дополнения: среди них бывают
    и пояснения, не нужные для ответа. Предложения, не связанные с вопросом ни одним
    содержательным словом, сюда не попадают.
    """
    answer_stems = set().union(*(content_stems(part.text) for part in parts)) if parts else set()
    question_roots = _roots(content_stems(question))
    found: list[tuple[int, int, str, str]] = []
    position = 0
    for doc_id in dict.fromkeys(doc_id for part in parts for doc_id in part.source_ids):
        for sentence in split_sentences(documents[doc_id]):
            position += 1
            stems = content_stems(sentence)
            shared = len(_roots(stems) & question_roots)
            if shared and len(stems & answer_stems) / len(stems) < COVERED_SHARE:
                found.append((-shared, position, doc_id, sentence))
    # При длинном списке остаются предложения, теснее всего связанные с вопросом.
    kept = sorted(sorted(found)[:MAX_UNUSED], key=lambda row: row[1])
    return [(doc_id, sentence) for _, _, doc_id, sentence in kept]


def render(parts: list[Part]) -> str:
    """Текст ответа: одно утверждение на строку, ссылки в конце строки."""
    lines = []
    for part in parts:
        text = f"{QUOTE_PREFIX}«{part.text}»" if part.kind == "quote" else part.text
        if not part.verified:
            text += f" ({'; '.join(part.notes)})"
        lines.append(f"{text} " + " ".join(f"[{doc_id}]" for doc_id in part.source_ids))
    return "\n".join(lines)
