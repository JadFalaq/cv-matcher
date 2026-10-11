"""Cas d'évaluation à vérité terrain connue, sans aucune annotation manuelle.

Principe : on *fabrique* le CV et l'offre, donc on connaît la bonne réponse à l'avance.

    mode « templated » : CV et offre assemblés à partir de phrases-modèles. Les 4 statuts
                         (visible / hidden / implicit / absent) sont produits à la demande.
    mode « perturb »   : on part d'un VRAI CV (le tien, anonymisé) et on le perturbe
                         (suppression de lignes, remplacement d'un terme par un synonyme).

Dans les deux cas, la vérité terrain est recalculée à partir du texte FINAL du CV
(`truth_status`), ce qui évite toute incohérence entre ce qu'on a voulu faire et ce qui a été fait.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from cvmatch.taxonomy import SkillEntry, Taxonomy
from cvmatch.text_utils import contains_term, squash

POOL_CATEGORIES = {"technical", "tool"}
MODES = ["visible"] * 30 + ["hidden"] * 25 + ["implicit"] * 20 + ["absent"] * 25

CONTEXTS = [
    "de classification de documents",
    "d'analyse de données clients",
    "de prévision de la demande",
    "de détection d'anomalies",
    "d'assistant interne pour les équipes support",
    "de suivi de production industrielle",
]
VISIBLE_TEMPLATES = [
    "Mise en œuvre de {t} dans un projet {c}.",
    "Utilisation de {t} pour un projet {c}.",
    "Projet {c} réalisé avec {t}.",
]
IMPLICIT_TEMPLATES = [
    "Développement d'un prototype {c} à l'aide de {t}.",
    "Projet {c} réalisé avec {t}.",
]
OFFER_TITLES = ["Ingénieur IA junior", "Data Scientist junior", "Ingénieur logiciel data"]
ABOUT = [
    "Nous accompagnons des équipes métier dans la valorisation de leurs données.",
    "Notre équipe construit des produits utiles pour des clients dans la finance et l'industrie.",
]
MISSIONS = [
    "Participer à la conception et à la livraison de nouvelles fonctionnalités.",
    "Contribuer à la qualité et à la documentation du code.",
    "Présenter vos travaux aux parties prenantes.",
]
MUST_PREFIX = ["Maîtrise de", "Excellente connaissance de", "Expérience avec"]
NICE_PREFIX = ["Connaissance de", "Notions de", "Un plus : "]
FILLERS = ABOUT + MISSIONS + OFFER_TITLES  # vérifié par un test : aucun terme du référentiel dedans


@dataclass
class ExpectedSkill:
    skill_id: str
    status: str
    importance: str
    offer_term: str


@dataclass
class SyntheticCase:
    case_id: str
    mode: str
    cv_text: str
    offer_text: str
    expected: list[ExpectedSkill]


# ------------------------------------------------------------ vérité terrain ---
def truth_status(cv_text: str, entry: SkillEntry, offer_term: str) -> str:
    if contains_term(cv_text, offer_term):
        return "visible"
    if any(contains_term(cv_text, t) for t in entry.terms):
        return "hidden"
    if any(contains_term(cv_text, t) for t in entry.implied_by):
        return "implicit"
    return "absent"


def _pool(tax: Taxonomy) -> list[SkillEntry]:
    return [e for e in tax.entries if e.category in POOL_CATEGORIES]


def _pick_term(rng: random.Random, tax: Taxonomy, entry: SkillEntry) -> str:
    """Terme écrit dans l'offre : le plus souvent le nom canonique, parfois un alias."""
    if entry.aliases and rng.random() < 0.25:
        cand = rng.choice(entry.aliases)
        if tax.resolve(cand) is entry:
            return cand
    return entry.name


def render_offer(items: list[tuple[SkillEntry, str, str]], rng: random.Random) -> str:
    must = [t for _, t, imp in items if imp == "must"]
    nice = [t for _, t, imp in items if imp == "nice"]
    lines = [f"Stage PFE – {rng.choice(OFFER_TITLES)}", "", "À propos", rng.choice(ABOUT), "", "Missions"]
    lines += [f"- {m}" for m in rng.sample(MISSIONS, 2)]
    lines += ["", "Profil recherché (indispensable)"]
    lines += [f"- {rng.choice(MUST_PREFIX)} {t}" for t in must]
    if nice:
        lines += ["", "Compétences appréciées"]
        lines += [f"- {rng.choice(NICE_PREFIX)} {t}".replace(":  ", ": ") for t in nice]
    return "\n".join(lines) + "\n"


def _expected(cv_text: str, items: list[tuple[SkillEntry, str, str]]) -> list[ExpectedSkill]:
    return [ExpectedSkill(e.id, truth_status(cv_text, e, term), imp, term) for e, term, imp in items]


# ------------------------------------------------------------- mode templated ---
def make_templated_case(rng: random.Random, tax: Taxonomy, case_id: str, n_offer: int = 8) -> SyntheticCase:
    pool = _pool(tax)
    chosen = rng.sample(pool, n_offer)
    items = [(e, _pick_term(rng, tax, e), "must" if rng.random() < 0.6 else "nice") for e in chosen]

    sentences: list[str] = []
    skill_line: list[str] = []
    for e, term, _ in items:
        mode = rng.choice(MODES)
        others = [t for t in e.terms if squash(t) != squash(term)]
        if mode == "hidden" and not others:
            mode = "visible"
        if mode == "implicit" and not e.implied_by:
            mode = "visible"
        ctx = rng.choice(CONTEXTS)
        if mode == "visible":
            if e.category == "tool" and rng.random() < 0.5:
                skill_line.append(term)
            else:
                sentences.append(rng.choice(VISIBLE_TEMPLATES).format(t=term, c=ctx))
        elif mode == "hidden":
            sentences.append(rng.choice(VISIBLE_TEMPLATES).format(t=rng.choice(others), c=ctx))
        elif mode == "implicit":
            sentences.append(rng.choice(IMPLICIT_TEMPLATES).format(t=rng.choice(e.implied_by), c=ctx))
        # absent : rien n'est écrit
    rest = [e for e in pool if e not in chosen]
    for e in rng.sample(rest, 3):  # bruit : compétences du CV hors offre
        skill_line.append(e.name)
    rng.shuffle(sentences)

    cv = ["# Candidat Exemple", "Élève ingénieur en dernière année, à la recherche d'un stage de fin d'études.", ""]
    if sentences:
        cv += ["## Expérience", "**Stagiaire – Société Exemple**"] + [f"- {s}" for s in sentences[:3]] + [""]
        for i in range(3, len(sentences), 2):
            cv += [f"**Projet {i // 2}**"] + [f"- {s}" for s in sentences[i : i + 2]] + [""]
    cv += ["## Compétences", ", ".join(skill_line) or "Rigueur et curiosité", ""]
    cv_text = "\n".join(cv)
    return SyntheticCase(case_id, "templated", cv_text, render_offer(items, rng), _expected(cv_text, items))


# --------------------------------------------------------------- mode perturb ---
def _remove_lines(cv: str, entry: SkillEntry) -> str:
    kept = [ln for ln in cv.splitlines() if ln.lstrip().startswith("#") or not any(contains_term(ln, t) for t in entry.terms)]
    return "\n".join(kept)


def _hide_term(cv: str, entry: SkillEntry, rng: random.Random) -> str:
    """Remplace le nom canonique par un alias (le CV dit la même chose avec d'autres mots)."""
    if not entry.aliases:
        return cv
    alias = rng.choice(entry.aliases)
    pattern = r"(?<![A-Za-z0-9])" + re.escape(entry.name) + r"(?![A-Za-z0-9])"
    return re.sub(pattern, alias, cv, flags=re.IGNORECASE)


def make_perturbed_case(
    rng: random.Random,
    tax: Taxonomy,
    base_cv: str,
    case_id: str,
    n_offer: int = 8,
    p_remove: float = 0.25,
    p_hide: float = 0.30,
) -> SyntheticCase:
    present = [e for e, _ in tax.find_in_text(base_cv) if e.category in POOL_CATEGORIES]
    cv = base_cv
    for e in rng.sample(present, len(present)):
        r = rng.random()
        if r < p_remove:
            cv = _remove_lines(cv, e)
        elif r < p_remove + p_hide:
            cv = _hide_term(cv, e, rng)

    n_present = min(len(present), max(1, n_offer * 3 // 4))
    chosen = rng.sample(present, n_present)
    absent_pool = [e for e in _pool(tax) if e not in present]
    chosen += rng.sample(absent_pool, max(0, n_offer - len(chosen)))
    items = [(e, _pick_term(rng, tax, e), "must" if rng.random() < 0.6 else "nice") for e in chosen]
    return SyntheticCase(case_id, "perturb", cv, render_offer(items, rng), _expected(cv, items))


# ------------------------------------------------------------------ jeu complet ---
def generate_cases(
    n: int, seed: int = 0, mode: str = "both", base_cv: str | None = None, tax: Taxonomy | None = None
) -> list[SyntheticCase]:
    from cvmatch.taxonomy import default_taxonomy

    tax = tax or default_taxonomy()
    rng = random.Random(seed)
    cases: list[SyntheticCase] = []
    for i in range(n):
        use_perturb = (mode == "perturb") or (mode == "both" and base_cv is not None and i % 2 == 1)
        if use_perturb:
            if base_cv is None:
                raise ValueError("Le mode « perturb » nécessite --base-cv.")
            cases.append(make_perturbed_case(rng, tax, base_cv, f"p{i:03d}"))
        else:
            cases.append(make_templated_case(rng, tax, f"t{i:03d}"))
    return cases
