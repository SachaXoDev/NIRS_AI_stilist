"""Инкрементальное извлечение строкового поля из потока JSON.

LLM стримит JSON-объект целиком, а пользователю нужно показывать только человеческий текст
из поля "text" — по мере генерации. Экстрактор получает сырые чанки и отдаёт уже
раскодированные фрагменты значения этого поля.
"""
from __future__ import annotations

import re

_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


class JsonStringFieldExtractor:
    def __init__(self, field: str = "text") -> None:
        self._start_re = re.compile(r'"%s"\s*:\s*"' % re.escape(field))
        self._buffer = ""
        self._pos: int | None = None
        self._high_surrogate: int | None = None
        self.done = False

    def feed(self, chunk: str) -> str:
        if self.done or not chunk:
            return ""
        self._buffer += chunk
        if self._pos is None:
            match = self._start_re.search(self._buffer)
            if not match:
                return ""
            self._pos = match.end()

        out: list[str] = []
        buf, i, n = self._buffer, self._pos, len(self._buffer)
        while i < n:
            ch = buf[i]
            if ch == '"':
                self.done = True
                i += 1
                break
            if ch != "\\":
                out.append(ch)
                i += 1
                continue
            if i + 1 >= n:
                break  # экранирование разорвано границей чанка — ждём продолжения
            esc = buf[i + 1]
            if esc != "u":
                out.append(_ESCAPES.get(esc, esc))
                i += 2
                continue
            if i + 6 > n:
                break
            try:
                code = int(buf[i + 2 : i + 6], 16)
            except ValueError:
                i += 6
                continue
            i += 6
            if 0xD800 <= code <= 0xDBFF:
                self._high_surrogate = code
                continue
            if 0xDC00 <= code <= 0xDFFF:
                if self._high_surrogate is None:
                    continue
                code = 0x10000 + ((self._high_surrogate - 0xD800) << 10) + (code - 0xDC00)
            self._high_surrogate = None
            out.append(chr(code))
        self._pos = i
        return "".join(out)
