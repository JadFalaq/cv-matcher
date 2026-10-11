"""LLM factice à règles lexicales (aucune clé API, déterministe).

Sert à : développer et tester le graphe hors ligne, faire tourner la CI, et vérifier que
la plomberie (RAG, boucles, garde-fous, score) est correcte.

⚠ Il s'appuie sur la même taxonomie que le reste du code : les chiffres obtenus avec lui
valident le *pipeline*, pas la qualité d'un vrai LLM. Pour mesurer un vrai modèle, lance
l'évaluation avec LLM_PROVIDER=azure|openai|anthropic|ollama.
"""

from __future__ import annotations

import re
from typing import Any, TypeVar

from pydantic import BaseModel

from .schemas import RequirementDraft
from .taxonomy import Taxonomy, default_taxonomy
from .text_utils import contains_term, normalize, squash, strip_bullet

T = TypeVar("T", bound=BaseModel)

_NICE_CUES = ("souhait", "apprecie", "un plus", "atout", "bonus", "nice to have", "optionnel")
_MUST_CUES = ("indispensable", "requis", "obligatoire", "must have", "required", "exige", "profil recherche", "prerequis")


class RuleBasedLLM:
    def __init__(self, taxonomy: Taxonomy | None = None):
        self.tax = taxonomy or default_taxonomy()

    # --------------------------------------------------------- interface ---
    def structured(
        self, schema: type[T], *, system: str, user: str, tag: str, context: dict[str, Any] | None = None
    ) -> T:
        ctx = context or {}
        if tag == "extract":
            return schema(requirements=self._extract(ctx["offer_text"]))
        if tag == "exhaustivity":
            known = {self.tax.resolve_id(n) for n in ctx.get("known", [])}
            missing = [d for d in self._extract(ctx["offer_text"]) if self.tax.resolve_id(d.name) not in known]
            return schema(missing=missing)
        if tag == "judge":
            return schema(**self._judge(ctx))
        if tag == "summary":
            return schema(**self._summary(ctx))
        raise ValueError(f"tag inconnu : {tag!r}")

    # -------------------------------------------------------- extraction ---
    def _extract(self, offer_text: str) -> list[RequirementDraft]:
        importance = "must"
        drafts: dict[str, RequirementDraft] = {}
        for raw in offer_text.splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            is_bullet = stripped[0] in "-*•"
            line = strip_bullet(stripped.lstrip("#").strip())
            norm = normalize(line)
            found = self.tax.find_in_text(line)
            nice = any(c in norm for c in _NICE_CUES)
            must = any(c in norm for c in _MUST_CUES)
            if not found:
                if not is_bullet and len(norm) <= 70 and not norm.endswith("."):  # titre de section
                    importance = "nice" if nice else "must"
                continue
            line_importance = "nice" if nice else ("must" if must else importance)
            for entry, _ in found:
                terms = self.tax.terms_in_text(entry, line)
                prev = drafts.get(entry.id)
                if prev:
                    if line_importance == "must":
                        prev.importance = "must"
                    prev.offer_terms.extend(t for t in terms if t not in prev.offer_terms)
                else:
                    drafts[entry.id] = RequirementDraft(
                        name=entry.name,
                        category=entry.category,  # type: ignore[arg-type]
                        importance=line_importance,
                        offer_terms=list(terms),
                        offer_quote=line,
                    )
        return list(drafts.values())

    # -------------------------------------------------------------- juge ---
    def _judge(self, ctx: dict[str, Any]) -> dict[str, Any]:
        req = ctx["requirement"]
        terms = req.get("offer_terms") or [req["name"]]
        entry = self.tax.get(req["id"]) or self.tax.resolve(req["name"])
        known = {squash(t) for t in terms}
        aliases = [t for t in (entry.terms if entry else (req["name"],)) if squash(t) not in known]
        triggers = entry.implied_by if entry else ()
        lines = [strip_bullet(ln) for c in ctx["chunks"] for ln in c["text"].splitlines() if ln.strip()]

        for s in lines:
            if any(contains_term(s, t) for t in terms):
                return {"status": "visible", "evidence_quote": s, "reasoning": "Le terme de l'offre figure dans le CV."}
        for s in lines:
            for alias in aliases:
                if contains_term(s, alias):
                    return {
                        "status": "hidden",
                        "evidence_quote": s,
                        "reasoning": f"Le CV emploie « {alias} » au lieu du terme de l'offre.",
                        "suggested_rewrite": self._swap(s, alias, terms[0]),
                    }
        for s in lines:
            for trig in triggers:
                if contains_term(s, trig):
                    return {
                        "status": "implicit",
                        "evidence_quote": s,
                        "reasoning": f"« {trig} » implique la compétence sans la nommer.",
                        "suggested_rewrite": f"{s.rstrip('. ')} ({terms[0]})",
                    }
        return {"status": "absent", "evidence_quote": None, "reasoning": "Aucune preuve dans les extraits fournis."}

    @staticmethod
    def _swap(line: str, alias: str, term: str) -> str:
        pattern = r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])"
        out, n = re.subn(pattern, term, line, count=1, flags=re.IGNORECASE)
        return out if n else f"{line.rstrip('. ')} ({term})"

    # ------------------------------------------------------------ synthèse ---
    @staticmethod
    def _summary(ctx: dict[str, Any]) -> dict[str, Any]:
        strengths = [f"{n} est bien visible dans ton CV." for n in ctx.get("visible", [])[:3]]
        priorities = [f"Reformule la ligne liée à « {n} » avec les mots de l'offre." for n in ctx.get("to_rewrite", [])[:3]]
        priorities += [f"« {n} » n'apparaît pas : à combler par un projet, pas à inventer." for n in ctx.get("gaps", [])[:2]]
        return {
            "headline": f"Score actuel {ctx.get('score_actual', 0)}/100, potentiel {ctx.get('score_potential', 0)}/100 après adaptation.",
            "strengths": strengths,
            "priorities": priorities,
        }
