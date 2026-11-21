import json

import pytest

from app.services.streaming import JsonStringFieldExtractor

TEXT = 'Собрал образ: тренч «оверсайз», "кавычки", слэш \\ и перенос\nстроки 👗 готово.'


def _run(raw: str, size: int) -> str:
    extractor = JsonStringFieldExtractor("text")
    return "".join(extractor.feed(raw[i : i + size]) for i in range(0, len(raw), size))


@pytest.mark.parametrize("ensure_ascii", [False, True])
@pytest.mark.parametrize("size", [1, 2, 3, 5, 7, 64, 10_000])
def test_extracts_text_regardless_of_chunk_boundaries(size, ensure_ascii):
    raw = json.dumps({"text": TEXT, "outfit": {"title": "не это", "text": "и не это"}},
                     ensure_ascii=ensure_ascii, indent=2)
    assert _run(raw, size) == TEXT


def test_ignores_everything_after_the_field():
    extractor = JsonStringFieldExtractor("text")
    assert extractor.feed('{"text": "готово"') == "готово"
    assert extractor.done
    assert extractor.feed(', "outfit": {"text": "лишнее"}}') == ""


def test_no_field_no_output():
    assert _run('{"outfit": null}', 4) == ""
