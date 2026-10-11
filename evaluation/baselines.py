"""Baselines de comparaison.

1. `tfidf_cosine`   : similarité TF-IDF globale CV/offre. Un seul chiffre, aucune explication.
2. `direct_llm`     : UN seul appel LLM avec le CV entier, sans RAG, sans boucle, sans garde-fou.
                      (nécessite un vrai LLM : le LLM factice ne l'implémente pas, volontairement,
                      pour ne pas fabriquer une baseline artificiellement mauvaise.)
"""

from __future__ import annotations

import math
from collections import Counter

from pydantic import BaseModel, Field

from cvmatch.llm import LLM
from cvmatch.schemas import Status
from cvmatch.text_utils import tokenize


# ------------------------------------------------------------------ TF-IDF ---
def build_idf(docs: list[str]) -> dict[str, float]:
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(tokenize(d)))
    n = len(docs)
    return {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}


def _vec(text: str, idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokenize(text))
    return {t: c * idf.get(t, 1.0) for t, c in tf.items()}


def tfidf_cosine(cv: str, offer: str, idf: dict[str, float]) -> float:
    a, b = _vec(cv, idf), _vec(offer, idf)
    dot = sum(v * b.get(t, 0.0) for t, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


# ------------------------------------------------------------ LLM en un coup ---
class DirectItem(BaseModel):
    skill: str
    status: Status


class DirectResult(BaseModel):
    items: list[DirectItem] = Field(default_factory=list)


DIRECT_SYSTEM = """Pour chaque compétence listée, indique son statut dans le CV :
visible (nommée avec les mots de l'offre), hidden (prouvée avec d'autres mots), implicit (déductible d'un
projet ou d'un outil), absent. Réponds pour TOUTES les compétences."""


def direct_llm(llm: LLM, cv: str, skills: list[str]) -> dict[str, str]:
    user = f"CV :\n\"\"\"\n{cv}\n\"\"\"\n\nCompétences :\n" + "\n".join(f"- {s}" for s in skills)
    res = llm.structured(DirectResult, system=DIRECT_SYSTEM, user=user, tag="direct", context={})
    return {i.skill.strip().lower(): i.status for i in res.items}
