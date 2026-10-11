"""Outils de test : un LLM « scénarisé » qui peut mentir, se tromper ou tomber en panne."""

from __future__ import annotations

from collections import Counter

from cvmatch.fake_llm import RuleBasedLLM


class ScriptedLLM:
    """Délègue au LLM factice, sauf pour les tags surchargés.

    `overrides[tag](n, schema, context)` reçoit le numéro de l'appel (1, 2, 3…) pour ce tag et
    retourne soit une instance du schéma (réponse forcée), soit None (on délègue au LLM factice).
    """

    def __init__(self, overrides: dict | None = None):
        self.base = RuleBasedLLM()
        self.overrides = overrides or {}
        self.calls: Counter = Counter()

    def structured(self, schema, *, system, user, tag, context=None):
        self.calls[tag] += 1
        fn = self.overrides.get(tag)
        if fn is not None:
            out = fn(self.calls[tag], schema, context or {})
            if out is not None:
                return out
        return self.base.structured(schema, system=system, user=user, tag=tag, context=context)
