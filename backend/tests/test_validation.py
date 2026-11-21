import json

import pytest

from app.services.validation import DraftParseError, field_errors, parse_draft


def _draft(item_ids, **outfit_overrides) -> str:
    outfit = {
        "title": "Деловой минимализм",
        "description": "Строгий силуэт.",
        "occasion": "Офис",
        "item_ids": item_ids,
        "stylistReasoning": "Контраст чёрного и серого.",
        "confidenceTips": ["Подверните рукава.", "Сумку держите в руке."],
    }
    outfit.update(outfit_overrides)
    return json.dumps({"text": "Собрал образ.", "outfit": outfit}, ensure_ascii=False)


def test_parse_tolerates_markdown_fences_and_chatter():
    raw = "Вот ответ:\n```json\n" + _draft(["item-1"]) + "\n```\nНадеюсь, помог!"
    draft = parse_draft(raw)
    assert draft.text == "Собрал образ." and draft.outfit.item_ids == ["item-1"]


def test_parse_strips_reasoning_block():
    raw = '<think>\nСначала подумаю: {"text": "черновик"}\n</think>\n' + _draft(["item-1"])
    assert parse_draft(raw).text == "Собрал образ."


def test_parse_accepts_alternative_key_spellings():
    raw = json.dumps({
        "text": "Ок",
        "outfit": {"title": "T", "itemIds": [{"id": "item-1"}, "item-3"],
                   "stylist_reasoning": "R", "tips": "Один совет"},
    })
    outfit = parse_draft(raw).outfit
    assert outfit.item_ids == ["item-1", "item-3"]
    assert outfit.stylist_reasoning == "R" and outfit.confidence_tips == ["Один совет"]


@pytest.mark.parametrize("raw", ["", "просто текст без json", '{"text": "обрыв', "[1, 2, 3]"])
def test_parse_rejects_non_json(raw):
    with pytest.raises(DraftParseError):
        parse_draft(raw)


def test_complete_draft_has_no_field_errors():
    assert field_errors(parse_draft(_draft(["item-1", "item-4", "item-8"]))) == []


def test_empty_fields_are_reported():
    raw = json.dumps({"text": "", "outfit": {"item_ids": []}})
    assert len(field_errors(parse_draft(raw))) == 5  # text, item_ids, title, reasoning, tips


def test_overlong_text_is_reported():
    raw = json.dumps({"text": "а" * 2000, "outfit": None})
    assert any("длиннее" in error for error in field_errors(parse_draft(raw)))


def test_small_talk_without_outfit_is_valid():
    assert field_errors(parse_draft('{"text": "Рад помочь!", "outfit": null}')) == []
