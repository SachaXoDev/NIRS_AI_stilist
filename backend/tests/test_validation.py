import json

import pytest

from app.services.validation import DraftParseError, parse_draft


def _draft(item_ids) -> str:
    outfit = {"item_ids": item_ids}
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
                   "description": "Свободный текст не участвует в подборе"},
    })
    outfit = parse_draft(raw).outfit
    assert outfit.item_ids == ["item-1", "item-3"]


@pytest.mark.parametrize("raw", ["", "просто текст без json", '{"text": "обрыв', "[1, 2, 3]"])
def test_parse_rejects_non_json(raw):
    with pytest.raises(DraftParseError):
        parse_draft(raw)
