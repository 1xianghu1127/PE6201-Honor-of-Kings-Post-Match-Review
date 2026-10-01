"""Provide the local TF-IDF representation used for retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class SearchHit:
    index: int
    score: float


class LocalTfidfEmbeddings:
    """Deterministic local text embeddings for a small, auditable vector index."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
            sublinear_tf=True,
        )
        self.matrix = None

    def fit(self, texts: Iterable[str]) -> None:
        items = list(texts)
        if not items:
            raise ValueError("Cannot build a vector index without knowledge chunks.")
        self.matrix = self.vectorizer.fit_transform(items)

    def search(self, query: str, top_k: int = 4) -> list[SearchHit]:
        if self.matrix is None:
            raise RuntimeError("The vector index has not been built.")
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix)[0]
        order = scores.argsort()[::-1][:top_k]
        return [SearchHit(int(index), float(scores[index])) for index in order]
