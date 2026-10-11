"""Score et dérivés : 100 % déterministes, aucun LLM.

Le LLM juge *si* une compétence est couverte ; le chiffre est calculé ici,
ce qui le rend reproductible, auditable et testable.
"""

from __future__ import annotations

from typing import Iterable, Literal

from .config import ScoringConfig
from .schemas import Assessment, Gap, ScoreResult, Suggestion

Mode = Literal["actual", "potential", "final"]


def _credit(a: Assessment, cfg: ScoringConfig, mode: Mode, approved: set[str]) -> float:
    actual = cfg.credit_actual[a.status]
    if a.status in ("hidden", "implicit") and a.rewrite_ok:
        potential = cfg.credit_potential[a.status]
    else:
        potential = actual  # sans reformulation valide, le score ne peut pas progresser
    if mode == "actual":
        return actual
    if mode == "potential":
        return max(actual, potential)
    return max(actual, potential) if f"sg-{a.requirement.id}" in approved else actual


def compute_score(
    assessments: Iterable[Assessment],
    cfg: ScoringConfig | None = None,
    mode: Mode = "actual",
    approved: set[str] | None = None,
) -> ScoreResult:
    """Somme pondérée des crédits, normalisée sur 100.

    - actual    : le CV tel quel
    - potential : si TOUTES les reformulations valides étaient appliquées
    - final     : seules les reformulations approuvées (`approved`) sont appliquées
    """
    cfg = cfg or ScoringConfig()
    approved = approved or set()
    items = list(assessments)
    max_points = sum(cfg.weight(a.requirement.importance) for a in items)
    points = sum(cfg.weight(a.requirement.importance) * _credit(a, cfg, mode, approved) for a in items)
    musts = [a for a in items if a.requirement.importance == "must"]
    must_cov = (sum(1 for a in musts if a.status != "absent") / len(musts)) if musts else 1.0
    counts: dict[str, int] = {"visible": 0, "hidden": 0, "implicit": 0, "absent": 0}
    for a in items:
        counts[a.status] += 1
    return ScoreResult(
        score=round(100 * points / max_points, 1) if max_points else 0.0,
        points=round(points, 3),
        max_points=round(max_points, 3),
        must_coverage=round(must_cov, 3),
        counts=counts,
    )


def build_suggestions(assessments: Iterable[Assessment], cfg: ScoringConfig | None = None) -> list[Suggestion]:
    """Reformulations proposées, triées par gain décroissant (importance × progression de crédit)."""
    cfg = cfg or ScoringConfig()
    items = list(assessments)
    max_points = sum(cfg.weight(a.requirement.importance) for a in items) or 1.0
    out: list[Suggestion] = []
    for a in items:
        if a.status not in ("hidden", "implicit") or not a.rewrite_ok or not a.suggested_rewrite:
            continue
        gain = cfg.weight(a.requirement.importance) * (cfg.credit_potential[a.status] - cfg.credit_actual[a.status])
        out.append(
            Suggestion(
                id=f"sg-{a.requirement.id}",
                skill_id=a.requirement.id,
                skill_name=a.requirement.name,
                status=a.status,
                importance=a.requirement.importance,
                section=a.section,
                original=a.evidence_quote or "",
                rewrite=a.suggested_rewrite,
                gain=round(100 * gain / max_points, 1),
            )
        )
    return sorted(out, key=lambda s: (-s.gain, s.skill_name))


def ats_keywords(assessments: Iterable[Assessment]) -> list[str]:
    """Termes exacts de l'offre à intégrer au CV : uniquement pour les compétences déjà possédées
    (cachées ou implicites). On ne suggère jamais un mot-clé pour une compétence absente."""
    seen: dict[str, None] = {}
    for a in assessments:
        if a.status in ("hidden", "implicit"):
            for term in a.requirement.offer_terms or [a.requirement.name]:
                seen.setdefault(term, None)
    return list(seen)


def find_gaps(assessments: Iterable[Assessment]) -> list[Gap]:
    """Lacunes honnêtes : compétences sans aucune preuve, indispensables d'abord."""
    gaps = [
        Gap(
            skill_id=a.requirement.id,
            skill_name=a.requirement.name,
            importance=a.requirement.importance,
            offer_quote=a.requirement.offer_quote,
        )
        for a in assessments
        if a.status == "absent"
    ]
    return sorted(gaps, key=lambda g: (g.importance != "must", g.skill_name))
