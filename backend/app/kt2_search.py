"""Text retrieval for the KT-2 demo, without ranking or embedding libraries."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from snowballstemmer import stemmer

_TOKEN = re.compile(r"[^\W_]+")
_RUSSIAN = re.compile(r"[а-я]+")
# Keep negations and exclusions such as «не» and «без».
_QUERY_STOPWORDS = frozenset("а в во для и из к ко как ли на о об от по под при с со у".split())
K1 = 1.2
B = 0.75
TOP_K = 3
FEEDBACK_DOCS = 2
FEEDBACK_TERMS = 16
FEEDBACK_WEIGHT = 0.5


def _stem_words(words: Iterable[str]) -> list[str]:
    russian = stemmer("russian")
    return [russian.stemWord(word) if _RUSSIAN.fullmatch(word) else word for word in words]


def tokens(text: str) -> list[str]:
    return _stem_words(_TOKEN.findall(text.casefold().replace("ё", "е")))


# Function words and generic interrogatives add little evidence in a second pass.
# The first pass still sees every token, including numbers and short identifiers.
_STOP_STEMS = frozenset(tokens("""
    а без более бы был была были быть в во вам ваш ведь время все всего вы да даже для до его ее если есть
    еще же за зачем и из или им их к как какая какие какой какую кем ко когда кого ком кому которая который
    кроме кто куда либо ли на над надо нам нас не неужели нет ни но ну о об обо один она они оно от перед
    по под пока после почему при про пусть раз с сам самое себя со так такая такой там те тем то того тогда
    тоже той только том тот три тут ты у уже хотя чего чей чем через что чтобы чьи эта эти это этот этого
    этому можно нужно сколько два две двое одна совсем вместе вообще вместо другой дальше
"""))


def _content_term(term: str) -> bool:
    return len(term) >= 3 and term.isalpha() and term not in _STOP_STEMS


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

    def __init__(self, documents: Iterable[Document], *, feedback: bool = False) -> None:
        self._feedback = feedback
        self._documents: dict[str, Document] = {}
        self._lengths: dict[str, int] = {}
        self._terms_by_doc: dict[str, tuple[str, ...]] = {}
        self._postings: dict[str, dict[str, int]] = defaultdict(dict)
        for document in documents:
            if document.id in self._documents:
                raise ValueError(f"Duplicate document ID: {document.id}")
            words = tokens(f"{document.title} {document.text}")
            self._documents[document.id] = document
            self._lengths[document.id] = len(words)
            counts = Counter(words)
            self._terms_by_doc[document.id] = tuple(counts)
            for term, frequency in counts.items():
                self._postings[term][document.id] = frequency

        size = len(self._documents)
        average = (sum(self._lengths.values()) / size if size else 0.0) or 1.0
        self._norms = {doc_id: K1 * (1 - B + B * length / average)
                       for doc_id, length in self._lengths.items()}
        self._idf = {term: math.log1p((size - len(posting) + 0.5) / (len(posting) + 0.5))
                     for term, posting in self._postings.items()}

    def _score(self, terms: Mapping[str, float]) -> dict[str, float]:
        scores: dict[str, float] = defaultdict(float)
        for term, query_weight in terms.items():
            posting = self._postings.get(term)
            if not posting:
                continue
            weight = query_weight * self._idf[term] * (K1 + 1)
            for doc_id, frequency in posting.items():
                scores[doc_id] += weight * frequency / (frequency + self._norms[doc_id])
        return scores

    def _hits(self, scores: Mapping[str, float], k: int) -> list[Hit]:
        ranked = sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))[:k]
        return [Hit(self._documents[doc_id], scores[doc_id]) for doc_id in ranked]

    def search(self, question: str, k: int = TOP_K) -> list[Hit]:
        if self._feedback:
            return self.search_feedback(question, k)
        if k < 1:
            raise ValueError("k must be positive")
        words = _TOKEN.findall(question.casefold().replace("ё", "е"))
        terms = dict.fromkeys(_stem_words(word for word in words if word not in _QUERY_STOPWORDS), 1.0)
        return self._hits(self._score(terms), k)

    def search_stemmed(self, question: str, k: int = TOP_K) -> list[Hit]:
        """Original stemmed BM25, retained as a reproducible baseline."""
        if k < 1:
            raise ValueError("k must be positive")
        return self._hits(self._score(dict.fromkeys(tokens(question), 1.0)), k)

    def _feedback_terms(self, seeds: list[Hit], original_terms: Mapping[str, float]) -> dict[str, float]:
        weights: dict[str, float] = defaultdict(float)
        size = len(self._documents)
        for rank, hit in enumerate(seeds, start=1):
            for term in self._terms_by_doc[hit.document.id]:
                frequency = len(self._postings[term])
                if term not in original_terms and _content_term(term) and 2 <= frequency <= size // 3:
                    weights[term] += 1 / rank
        ranked = sorted(weights, key=lambda term: (-weights[term] * self._idf[term], term))
        return {term: weights[term] for term in ranked[:FEEDBACK_TERMS]}

    def search_feedback(self, question: str, k: int = TOP_K) -> list[Hit]:
        """Keep the first BM25 hit and rank companions using lexical feedback."""
        if k < 1:
            raise ValueError("k must be positive")
        terms = dict.fromkeys(tokens(question), 1.0)
        original = self._score(terms)
        seeds = self._hits(original, FEEDBACK_DOCS)
        content = {term: weight for term, weight in terms.items() if _content_term(term)}
        if k == 1 or len(seeds) < FEEDBACK_DOCS or len(content) < 2:
            return self._hits(original, k)

        feedback = self._feedback_terms(seeds, terms)
        if not feedback:
            return self._hits(original, k)

        first = seeds[0]
        direct = self._score(content)
        expanded = self._score(feedback)
        for channel in (direct, expanded):
            channel.pop(first.document.id, None)
        max_direct = max(direct.values(), default=1.0)
        max_expanded = max(expanded.values(), default=1.0)
        # Each channel is normalized over the companions. Use the first hit's
        # original score as a ceiling so the public list remains score-ordered.
        companions = {
            doc_id: first.score * (
                (1 - FEEDBACK_WEIGHT) * direct.get(doc_id, 0.0) / max_direct
                + FEEDBACK_WEIGHT * expanded.get(doc_id, 0.0) / max_expanded
            )
            for doc_id in direct.keys() | expanded.keys()
        }
        return [first, *self._hits(companions, k - 1)]
