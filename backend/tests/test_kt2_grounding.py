"""Серверная проверка ответа КТ-2: ссылки, числа и пропущенные предложения.

Часть тестов идёт по настоящим ответам Qwen, записанным бенчмарком в `kt2_data/*/per_query.json`:
слой должен исправлять то, что там видно, и ничего не портить в остальных ответах.
"""
import asyncio
import json
import sys
from pathlib import Path

import pytest

from app.kt2_api import REFUSAL, answer_question
from app.kt2_grounding import Part, hard_tokens, render, review_answer, split_sentences, unused_sentences
from app.kt2_search import BM25Index, Document
from app.services.llm.base import LLMError

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "kt2_data"
RUNS = ["results", "stemming_only", "examples_run", "instruct_run", "conclusions_run"]
sys.path.insert(0, str(BACKEND / "scripts"))
import kt2_benchmark as bench  # noqa: E402
from kt2_replay import recorded_draft, replay  # noqa: E402

DOCS = {
    "D20": "Образцы «Шалфей» и «Мох» выглядели одинаковыми при дневном свете. "
           "Под тёплой лампой 2700 К «Мох» стал выглядеть более жёлтым, чем «Шалфей».",
    "D19": "Такой эффект называется метамерией.",
    "D18": "Шов подкладки стоит 220 рублей. Установка одной пуговицы стоит 90 рублей.",
}


def recorded(run: str, question_id: str) -> dict:
    rows = json.loads((DATA / run / "per_query.json").read_text(encoding="utf-8"))
    return next(row for row in rows if row["id"] == question_id)


def review_recorded(run: str, question_id: str):
    row = recorded(run, question_id)
    response = row["response"]
    documents = {hit["id"]: hit["text"] for hit in response["hits"]}
    question = row["request"]["question"]
    return question, documents, review_answer(question, documents, recorded_draft(response["answer"]))


# --- ссылки ------------------------------------------------------------------------------------


def test_document_named_in_the_text_becomes_a_source_of_that_statement():
    """Q08: «…соответствует критерию допуска по Д22. [D23]» — правило из D22 оставалось без ссылки."""
    _, _, review = review_recorded("conclusions_run", "Q08")
    first = review.parts[0]
    assert first.source_ids == ["D23", "D22"] and first.verified
    assert "ссылка на D22 перенесена из текста в источники" in review.notes
    assert render(review.parts).split("\n")[0].endswith("[D23] [D22]")


def test_bracketed_citation_inside_text_is_moved_not_rejected():
    review = review_answer("Какой эффект?", DOCS, [("Это метамерия [D19], см. журнал.", "D20")])
    assert review.parts[0].text == "Это метамерия, см. журнал."
    assert review.parts[0].source_ids == ["D20", "D19"]


@pytest.mark.parametrize("raw, clean", [
    ("Лицо не оставляют в кадре (см. [D19]).", "Лицо не оставляют в кадре."),
    ("Это метамерия, см. [D19].", "Это метамерия."),
    ("Согласно [D19] это метамерия.", "это метамерия."),
    ("Это метамерия [D19]", "Это метамерия"),
])
def test_removed_citation_leaves_no_dangling_words_or_brackets(raw, clean):
    review = review_answer("Какой эффект?", DOCS, [(raw, "D20")])
    assert review.parts[0].text == clean and review.parts[0].source_ids == ["D20", "D19"]


def test_mention_of_a_document_outside_the_hits_is_reported_and_not_cited():
    review = review_answer("Какой эффект?", DOCS, [("Это метамерия, как сказано в D07.", "D19")])
    assert review.parts[0].source_ids == ["D19"]
    assert any("D07" in note and "нет в выдаче" in note for note in review.notes)


def test_item_codes_are_not_mistaken_for_document_ids():
    review = review_answer("Что с П-12?", {"D01": "Плащ П-12 сухой, жакет Д-12 тоже."}, [("Плащ П-12 и жакет Д-12 сухие.", "D01")])
    assert review.parts[0].source_ids == ["D01"] and not review.notes


# --- числа и шифры -------------------------------------------------------------------------------


def test_hard_tokens_are_numbers_from_two_digits_and_item_codes():
    assert hard_tokens("В 09:30 лист Л-14Д, 2700 К и 6 марта") == {"9:30", "л-14д", "2700"}
    assert hard_tokens("по Д22 и [D05] всего 2,5 м и 3 шва") == {"2.5"}, "ID документов и одиночные цифры не считаются"


def test_garbled_copy_of_a_number_is_dropped_when_the_rest_is_already_said():
    """Q07, выбранный прогон: «…под тёплой лампой 27 о К» повторяет первое утверждение с опечаткой."""
    _, _, review = review_recorded("conclusions_run", "Q07")
    text = render(review.parts)
    assert "27 о К" not in text and "2700 К" in text
    assert len(review.parts) == 3 and all(part.verified for part in review.parts)
    assert "убран повтор с искажённым значением (27)" in review.notes


def test_garbled_number_is_replaced_by_the_source_sentence_when_it_is_the_only_statement():
    review = review_answer("Что показало сравнение под лампой?", DOCS,
                           [("Под тёплой лампой 27 К «Мох» стал выглядеть более жёлтым.", "D20")])
    part = review.parts[0]
    assert part.kind == "quote" and part.text == split_sentences(DOCS["D20"])[1] and part.verified
    assert render(review.parts).startswith("Дословно из источника: «Под тёплой лампой 2700 К")


def test_unsupported_number_is_flagged_and_not_shown_as_verified():
    """Исходный прогон, Q06: «Ремонт пальто Р-26 стоит 200 рублей» — суммы 200 нет ни в одном документе."""
    _, _, review = review_recorded("results", "Q06")
    flagged = [part for part in review.parts if not part.verified]
    assert len(flagged) == 1 and "200" in flagged[0].text
    assert "(нет в источниках: 200)" in render(review.parts)


def test_total_computed_from_source_numbers_is_not_flagged():
    draft = [("Всего 400 рублей: шов — 220 рублей, две пуговицы — 180 рублей.", "D18")]
    review = review_answer("Сколько стоит ремонт?", DOCS, draft)
    assert review.parts[0].verified and not review.notes, "400 = 220 + 2 × 90, 180 = 2 × 90"


def test_arithmetic_allowance_does_not_excuse_an_invented_total():
    review = review_answer("Сколько стоит ремонт?", DOCS, [("Ремонт стоит 200 рублей.", "D18")])
    assert not review.parts[0].verified


def test_numbers_from_the_question_are_grounded():
    review = review_answer("Успею ли я в 19:00?", {"D01": "Стойка работает до 18:00."},
                           [("В 19:00 стойка уже закрыта: она работает до 18:00.", "D01")])
    assert review.parts[0].verified


def test_value_taken_from_another_hit_adds_that_document_as_source():
    """Прогон со стеммингом, Q03: бокс Ш-2 назван со ссылкой на D07, хотя он описан в D08."""
    _, documents, review = review_recorded("stemming_only", "Q03")
    assert "ш-2" in hard_tokens(documents["D08"]) and "ш-2" not in hard_tokens(documents["D07"])
    assert any(part.source_ids == ["D07", "D08"] for part in review.parts)
    assert "источник D08 добавлен: из него взято Ш-2" in review.notes


# --- пропущенные предложения ---------------------------------------------------------------------


@pytest.mark.parametrize("question_id, needed", [
    ("Q02", "Размытие лица вместо кадрирования не принимают; если срезаются плечи изделия, снимок переснимают."),
    ("Q05", "После показа выданную одежду принимают только из рук в руки у костюмерной стойки."),
    ("Q05", "Деревянная вешалка остаётся на площадке и в комплект не входит."),
    ("Q07", "Зелёные образцы «Шалфей» и «Мох» выглядели одинаковыми на столе при дневном свете."),
])
def test_omitted_conditions_from_cited_documents_are_found(question_id, needed):
    """Именно эти предложения ручная сверка назвала причиной незачёта при полной выдаче."""
    question, documents, review = review_recorded("conclusions_run", question_id)
    assert needed in [sentence for _, sentence in unused_sentences(question, documents, review.parts)]


def test_unused_sentences_skip_what_the_answer_says_and_what_it_does_not_cite():
    question = "Что показало сравнение «Шалфея» и «Мха» под лампой и как называется эффект?"
    parts = [Part("Под тёплой лампой 2700 К «Мох» выглядел более жёлтым, чем «Шалфей».", ["D20"])]
    unused = unused_sentences(question, DOCS, parts)
    assert unused == [("D20", "Образцы «Шалфей» и «Мох» выглядели одинаковыми при дневном свете.")]
    assert all(doc_id != "D19" for doc_id, _ in unused), "документ, на который ответ не ссылается, не разбирается"


# --- на всех записанных прогонах слой ничего не портит ---------------------------------------------


@pytest.mark.parametrize("run", RUNS)
def test_review_never_loses_facts_or_breaks_citations_on_recorded_answers(run):
    rows = json.loads((DATA / run / "per_query.json").read_text(encoding="utf-8"))
    for row in rows:
        result = replay(row)
        if result is None:
            continue
        before, after = result["before"], result["after"]
        passed = lambda metrics: sum(check["passed"] for check in metrics["fact_checks"])  # noqa: E731
        assert passed(after) >= passed(before), row["id"]
        assert after["citations_match_sources"] and after["expected_evidence"] >= before["expected_evidence"], row["id"]
        assert set(before["source_ids"]) <= set(after["source_ids"]), row["id"]


# --- API -------------------------------------------------------------------------------------------


class ScriptedModel:
    model = "scripted"

    def __init__(self, answer: str, selection: str | Exception | None = None) -> None:
        self.answer, self.selection = answer, selection
        self.select_calls: list[tuple[list[dict], list[str]]] = []

    async def generate(self, messages, source_ids):
        return self.answer

    async def select(self, messages, options):
        self.select_calls.append((messages, options))
        if isinstance(self.selection, Exception):
            raise self.selection
        assert self.selection is not None, "coverage pass must not run"
        return self.selection


@pytest.fixture
def index():
    return BM25Index(Document(doc_id, f"Документ {doc_id}", text) for doc_id, text in DOCS.items())


QUESTION = "Что показало сравнение «Шалфея» и «Мха» под лампой и как называется эффект?"
DRAFT = json.dumps({"parts": [
    {"text": "Под тёплой лампой 2700 К «Мох» выглядел более жёлтым, чем «Шалфей».", "source_id": "D20"},
    {"text": "Это метамерия, см. [D19].", "source_id": "D20"},
]}, ensure_ascii=False)


def ask(index, model, **kwargs):
    return asyncio.run(answer_question(QUESTION, index, model, **kwargs))


def test_inline_citation_no_longer_fails_the_whole_answer(index):
    """Раньше такой ответ целиком превращался в HTTP 502 — из-за этого упал прогон с промптом на полноту."""
    result = ask(index, ScriptedModel(DRAFT))
    assert not result.refused and result.answer.split("\n")[1] == "Это метамерия. [D20] [D19]"
    assert [source.id for source in result.sources] == ["D20", "D19"]
    assert result.checks == ["ссылка на D19 перенесена из текста в источники"]
    assert [part.kind for part in result.parts] == ["model", "model"]
    graded = bench.grade({"relevant_ids": ["D19", "D20"], "required_facts": [["метамерия"]]}, result.model_dump())
    assert graded["citations_match_sources"] and graded["accuracy"], "формат ответа остался понятен бенчмарку"


def test_coverage_pass_is_off_by_default(index):
    model = ScriptedModel(DRAFT)
    ask(index, model)
    assert model.select_calls == []


def test_coverage_pass_adds_only_sentences_the_model_selected_verbatim(index):
    model = ScriptedModel(DRAFT, selection='{"add": ["S1"]}')
    result = ask(index, model, coverage_pass=True)
    messages, options = model.select_calls[0]
    assert options == ["S1", "S2"]
    assert "S1 [D20] Образцы «Шалфей» и «Мох» выглядели одинаковыми" in messages[1]["content"]
    assert "S2 [D19] Такой эффект называется метамерией." in messages[1]["content"]
    assert "- Это метамерия." in messages[1]["content"]
    last = result.parts[-1]
    assert (last.kind, last.source_ids) == ("quote", ["D20"]) and last.text == split_sentences(DOCS["D20"])[0]
    assert result.answer.split("\n")[-1] == f"Дословно из источника: «{last.text}» [D20]"
    assert "добавлено пропущенное предложение из D20" in result.checks


def test_coverage_pass_adds_nothing_when_the_model_says_the_answer_is_complete(index):
    result = ask(index, ScriptedModel(DRAFT, selection='{"add": []}'), coverage_pass=True)
    assert len(result.parts) == 2 and all(part.kind == "model" for part in result.parts)


@pytest.mark.parametrize("selection", [LLMError("timeout"), '{"add": "S1"}', '{"add": ["S9"]}', "не json"])
def test_failed_or_invalid_coverage_pass_keeps_the_answer(index, selection):
    result = ask(index, ScriptedModel(DRAFT, selection=selection), coverage_pass=True)
    assert not result.refused and len(result.parts) == 2
    assert result.answer.split("\n")[0].startswith("Под тёплой лампой 2700 К")


def test_refusal_is_not_touched_by_the_review(index):
    model = ScriptedModel('{"parts": []}')
    result = ask(index, model, coverage_pass=True)
    assert result.refused and result.answer == REFUSAL and not result.sources and not result.parts
    assert model.select_calls == []


def test_document_outside_the_hits_in_source_id_is_still_an_error(index):
    with pytest.raises(LLMError):
        ask(index, ScriptedModel('{"parts":[{"text":"Это метамерия.","source_id":"D99"}]}'))
