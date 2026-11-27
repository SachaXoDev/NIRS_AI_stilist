import asyncio
from math import log1p

import pytest

from app.kt2_api import REFUSAL, answer_question
from app.kt2_search import BM25Index, Document
from app.services.llm.base import LLMError


class ScriptedAnswer:
    model = "scripted"

    def __init__(self, response: str) -> None:
        self.response = response

    async def generate(self, messages, source_ids):
        assert self.response, "Model should not be called without hits"
        return self.response


def test_bm25_matches_hand_calculation_and_breaks_ties_by_id():
    index = BM25Index([
        Document("D03", "Возврат", "билета через кассу"),
        Document("D01", "Возврат", "оплаты на карту"),
        Document("D02", "Статус", "оплаты в приложении"),
    ])
    result = index.search("Как происходит возврат оплаты? Оплаты!", k=2)
    idf = log1p(1.5 / 2.5)
    assert [hit.document.id for hit in result] == ["D01", "D02"]
    assert [hit.score for hit in result] == pytest.approx([2 * idf, idf])


def test_bm25_matches_russian_inflection_and_preserves_numbers():
    index = BM25Index([
        Document("D01", "Шерстяная водолазка", "Стирка при 30 градусах"),
        Document("D02", "Брюки", "Стирка при 40 градусах"),
    ])
    assert [hit.document.id for hit in index.search("водолазкой 30")] == ["D01"]


def test_query_function_words_do_not_promote_unrelated_cards():
    index = BM25Index([
        Document("D01", "Водолазка", "В комплекте как теплый слой"),
        Document("D02", "Шорты", "Разрезы сбоку"),
    ])
    assert [hit.document.id for hit in index.search("Как в капсуле найти шорты с разрезами?")] == ["D02"]


def test_feedback_retrieves_companion_without_query_terms_and_preserves_first_hit():
    index = BM25Index([
        Document("record", "Калибровка датчика С-28", "Лист настройки. В коробке лежит эталонный резистор."),
        Document("procedure", "Настройка и калибровка оборудования", "Подберите эталонный резистор для сверки."),
        Document("inventory", "Место хранения", "Эталонный резистор находится в лаборатории."),
        Document("unrelated", "Как получить справку", "Заявление подают через окно."),
        Document("D05", "Литьё", "Опока для формовки."),
        Document("D06", "Архив", "Стеллажи с папками."),
        Document("D07", "Покраска", "Валик с ручкой."),
        Document("D08", "Сборка", "Струбцина."),
        Document("D09", "Точение", "Державка резца."),
    ], feedback=True)
    question = "Как выполнить настройку и калибровку датчика С-28?"
    before = index.search_stemmed(question)
    after = index.search(question)
    assert before[0] == after[0] and after[0].document.id == "record"
    assert "inventory" not in {hit.document.id for hit in before}
    assert {hit.document.id for hit in after} == {"record", "procedure", "inventory"}
    assert all(a.score >= b.score > 0 for a, b in zip(after, after[1:]))
    assert index.search("С-28") == index.search_stemmed("С-28")


def test_empty_retrieval_refuses_without_using_model_knowledge():
    index = BM25Index([Document("D01", "Рубашка", "Хлопок")])
    llm = ScriptedAnswer("")
    result = asyncio.run(answer_question("Абракадабра", index, llm))
    assert result.refused and result.answer == REFUSAL
    assert not result.hits and not result.sources


def test_model_cannot_cite_unretrieved_document():
    index = BM25Index([Document("D01", "Рубашка", "Хлопок")])
    llm = ScriptedAnswer('{"parts":[{"text":"Хлопок","source_id":"D02"}]}')
    with pytest.raises(LLMError):
        asyncio.run(answer_question("Рубашка", index, llm))


def test_model_refusal_retains_hits_but_does_not_cite_them():
    index = BM25Index([Document("D01", "Рубашка", "Хлопок")])
    llm = ScriptedAnswer('{"parts":[]}')
    result = asyncio.run(answer_question("Рубашка: какая застёжка?", index, llm))
    assert result.refused and result.answer == REFUSAL
    assert [hit.id for hit in result.hits] == ["D01"] and not result.sources


def test_retrieved_but_unused_document_does_not_become_a_source():
    index = BM25Index([Document("D01", "Рубашка", "Хлопок"), Document("D02", "Рубашка", "Стирка")])
    llm = ScriptedAnswer('{"parts":[{"text":"Из хлопка.","source_id":"D01"}]}')
    result = asyncio.run(answer_question("Рубашка", index, llm))
    assert not result.refused
    assert result.answer == "Из хлопка. [D01]"
    assert [hit.id for hit in result.hits] == ["D01", "D02"]
    assert [doc.id for doc in result.sources] == ["D01"]
