"""Text retrieval for the KT-2 demo, without ranking or embedding libraries."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from snowballstemmer import stemmer

_TOKEN = re.compile(r"[^\W_]+")
_RUSSIAN = re.compile(r"[а-я]+")
K1 = 1.2
B = 0.75
TOP_K = 3


def tokens(text: str) -> list[str]:
    russian = stemmer("russian")
    return [russian.stemWord(word) if _RUSSIAN.fullmatch(word) else word
            for word in _TOKEN.findall(text.casefold().replace("ё", "е"))]


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str


@dataclass(frozen=True)
class Hit:
    document: Document
    score: float


class BM25Index:
    """Build once at startup; a query visits only postings for its distinct terms."""

    def __init__(self, documents: Iterable[Document]) -> None:
        self._documents: dict[str, Document] = {}
        self._lengths: dict[str, int] = {}
        self._postings: dict[str, dict[str, int]] = defaultdict(dict)
        for document in documents:
            if document.id in self._documents:
                raise ValueError(f"Duplicate document ID: {document.id}")
            words = tokens(f"{document.title} {document.text}")
            self._documents[document.id] = document
            self._lengths[document.id] = len(words)
            for term, frequency in Counter(words).items():
                self._postings[term][document.id] = frequency

        size = len(self._documents)
        average = (sum(self._lengths.values()) / size if size else 0.0) or 1.0
        self._norms = {doc_id: K1 * (1 - B + B * length / average)
                       for doc_id, length in self._lengths.items()}
        self._idf = {term: math.log1p((size - len(posting) + 0.5) / (len(posting) + 0.5))
                     for term, posting in self._postings.items()}

    def search(self, question: str, k: int = TOP_K) -> list[Hit]:
        if k < 1:
            raise ValueError("k must be positive")
        scores: dict[str, float] = defaultdict(float)
        for term in dict.fromkeys(tokens(question)):
            posting = self._postings.get(term)
            if not posting:
                continue
            weight = self._idf[term] * (K1 + 1)
            for doc_id, frequency in posting.items():
                scores[doc_id] += weight * frequency / (frequency + self._norms[doc_id])
        ranked = sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))[:k]
        return [Hit(self._documents[doc_id], scores[doc_id]) for doc_id in ranked]
