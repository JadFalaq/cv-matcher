"""RAG : recherche des passages du CV qui servent de preuve pour une compétence.

Recherche hybride : BM25 (lexical, toujours actif) + embeddings (optionnels),
fusionnés par Reciprocal Rank Fusion. Sans embeddings, tout fonctionne hors ligne.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Sequence

import numpy as np

from .schemas import CVChunk
from .text_utils import tokenize

Embedder = Callable[[Sequence[str]], "np.ndarray | list[list[float]]"]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.avgdl = (sum(len(d) for d in docs) / self.n) if self.n else 1.0
        self.avgdl = self.avgdl or 1.0
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [Counter(d) for d in docs]

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        out = np.zeros(self.n)
        uniq = set(query_tokens)
        for i, (tf, doc) in enumerate(zip(self.tf, self.docs)):
            s = 0.0
            for t in uniq:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(doc) / self.avgdl))
            out[i] = s
        return out


def _rank(scores: np.ndarray) -> list[int]:
    """Indices triés par score décroissant ; à égalité, l'ordre d'origine est conservé."""
    return list(np.argsort(-scores, kind="stable"))


class HybridRetriever:
    def __init__(self, chunks: list[CVChunk], embedder: Embedder | None = None):
        self.chunks = chunks
        self._bm25 = BM25([tokenize(c.text + " " + c.section) for c in chunks])
        self._embedder = embedder
        self._matrix: np.ndarray | None = None
        if embedder is not None and chunks:
            self._matrix = self._normalize(np.asarray(embedder([c.text for c in chunks]), dtype=float))

    @staticmethod
    def _normalize(m: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(m, axis=-1, keepdims=True)
        return m / np.where(norms == 0, 1.0, norms)

    def search(self, query: str, k: int = 4, query_dense: str | None = None) -> list[tuple[CVChunk, float]]:
        if not self.chunks:
            return []
        k = min(k, len(self.chunks))
        lexical = self._bm25.scores(tokenize(query))
        if self._matrix is None or self._embedder is None:
            order = _rank(lexical)[:k]
            return [(self.chunks[i], float(lexical[i])) for i in order]

        q = self._normalize(np.asarray(self._embedder([query_dense or query]), dtype=float))[0]
        dense = self._matrix @ q
        fused = np.zeros(len(self.chunks))
        for scores in (lexical, dense):
            for rank, idx in enumerate(_rank(scores)):
                fused[idx] += 1.0 / (60 + rank + 1)  # Reciprocal Rank Fusion
        order = _rank(fused)[:k]
        return [(self.chunks[i], float(fused[i])) for i in order]
