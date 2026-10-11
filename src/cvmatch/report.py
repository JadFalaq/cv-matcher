"""Rendu du rapport (Markdown). Aucun LLM : tout vient des données vérifiées."""

from __future__ import annotations

from .schemas import AnalysisResult

STATUS_BADGES = {
    "visible": "✅ Visible",
    "hidden": "🟡 Cachée",
    "implicit": "🟠 Implicite",
    "absent": "❌ Absente",
}


def _cell(text: str | None) -> str:
    return (text or "—").replace("|", "\\|").replace("\n", " ")


def action_label(a) -> str:
    terms = " / ".join(a.requirement.offer_terms) or a.requirement.name
    if a.status == "visible":
        return "Rien à faire"
    if a.status == "hidden":
        return f"Reformuler avec « {terms} »" if a.rewrite_ok else "À reformuler (voir notes)"
    if a.status == "implicit":
        return f"Rendre explicite : « {terms} »" if a.rewrite_ok else "À expliciter (voir notes)"
    return "Lacune : ne pas inventer"


def render_markdown(r: AnalysisResult) -> str:
    out: list[str] = ["# Analyse CV ↔ offre", ""]
    out.append(
        f"**Score actuel : {r.score_actual.score:g}/100** · "
        f"**potentiel après adaptation : {r.score_potential.score:g}/100** · "
        f"**après tes validations : {r.score_final.score:g}/100**"
    )
    c = r.score_actual.counts
    out.append(
        f"\n{len(r.assessments)} compétences analysées : {c.get('visible', 0)} visibles, {c.get('hidden', 0)} cachées, "
        f"{c.get('implicit', 0)} implicites, {c.get('absent', 0)} absentes. "
        f"Couverture des indispensables : {r.score_actual.must_coverage:.0%}."
    )
    if r.summary:
        out += ["", f"> {r.summary.headline}"]
        if r.summary.strengths:
            out += ["", "**Points forts**"] + [f"- {s}" for s in r.summary.strengths]
        if r.summary.priorities:
            out += ["", "**Priorités**"] + [f"- {s}" for s in r.summary.priorities]

    out += ["", "## Couverture compétence par compétence", ""]
    out.append("| Compétence | Importance | Statut | Preuve dans le CV | Action |")
    out.append("|---|---|---|---|---|")
    for a in r.assessments:
        flag = " ⚠" if a.needs_review else ""
        out.append(
            f"| {_cell(a.requirement.name)} | {'indispensable' if a.requirement.importance == 'must' else 'souhaité'} "
            f"| {STATUS_BADGES[a.status]}{flag} | {_cell(a.evidence_quote)} | {_cell(action_label(a))} |"
        )

    if r.suggestions:
        approved = set(r.approved_ids)
        out += ["", "## Reformulations proposées", ""]
        for i, s in enumerate(r.suggestions, 1):
            mark = "appliquée ✅" if s.id in approved else "non retenue"
            out += [
                f"### {i}. {s.skill_name} (+{s.gain:g} pts) : {mark}",
                f"- **Avant** : {s.original}",
                f"- **Après** : {s.rewrite}",
                "",
            ]

    if r.ats_keywords:
        out += ["## Mots-clés de l'offre à intégrer naturellement", "", ", ".join(r.ats_keywords), ""]

    if r.gaps:
        out += ["## Lacunes (aucune preuve dans le CV : rien à inventer)", ""]
        for g in r.gaps:
            level = "indispensable" if g.importance == "must" else "souhaité"
            out.append(f"- **{g.skill_name}** ({level})" + (f" : « {g.offer_quote} »" if g.offer_quote else ""))
        out += ["", "Pour les lacunes importantes : un mini-projet ou une formation courte, à ajouter au CV seulement une fois réalisé.", ""]

    flagged = [a for a in r.assessments if a.needs_review or a.notes]
    if flagged:
        out += ["## Notes de contrôle", ""]
        for a in flagged:
            out.append(f"- **{a.requirement.name}** : " + " ".join(a.notes))
        out.append("")

    out += [
        "---",
        "*Chaque preuve citée a été vérifiée mot pour mot dans le CV ; le score est calculé par du code, pas par le LLM.*",
    ]
    return "\n".join(out)
