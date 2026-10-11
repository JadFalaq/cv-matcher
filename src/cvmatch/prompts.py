"""Prompts des nœuds LLM. Les sorties sont contraintes par des schémas Pydantic."""

from __future__ import annotations

from .schemas import CVChunk, Requirement

# --------------------------------------------------------------- extraction ---
EXTRACT_SYSTEM = """Tu es un analyste de recrutement rigoureux.
Ta tâche : extraire TOUTES les compétences et exigences d'une offre d'emploi, sans en oublier.

Règles
- Une entrée par compétence : langages, frameworks, outils, cloud, méthodes, domaines techniques,
  langues, diplômes, soft skills. Ignore la présentation de l'entreprise et les avantages.
- name : nom court et normalisé, en minuscules (ex. « machine learning », « docker »).
- importance : « must » si l'offre dit indispensable / requis / obligatoire / maîtrise, ou si rien n'est
  précisé ; « nice » si elle dit souhaité / apprécié / un plus / atout / bonus.
- offer_terms : le NOM de la compétence tel qu'il est écrit dans l'offre (1 à 4 mots), SANS qualificatif :
  « Python » et non « Excellente maîtrise de Python » ; « MLOps » et non « Bonnes bases en MLOps ».
- offer_quote : la phrase ou ligne EXACTE de l'offre, copiée sans modification.
- N'invente aucune compétence absente du texte. Ne regroupe pas deux compétences distinctes.
"""


def extract_user(offer_text: str) -> str:
    return f"OFFRE D'EMPLOI :\n\"\"\"\n{offer_text}\n\"\"\"\n\nExtrais toutes les compétences et exigences."


EXHAUSTIVITY_SYSTEM = """Tu contrôles l'exhaustivité d'une extraction de compétences.
On te donne une offre et la liste déjà extraite. Retourne UNIQUEMENT les compétences ou exigences de
l'offre qui ne figurent PAS dans la liste (liste vide si rien ne manque). Mêmes règles de format que
l'extraction (name, importance, offer_terms, offer_quote exacts). N'ajoute rien qui ne soit dans l'offre."""


def exhaustivity_user(offer_text: str, known: list[str]) -> str:
    listing = "\n".join(f"- {k}" for k in known) or "(aucune)"
    return (
        f"OFFRE D'EMPLOI :\n\"\"\"\n{offer_text}\n\"\"\"\n\n"
        f"COMPÉTENCES DÉJÀ EXTRAITES :\n{listing}\n\nQue manque-t-il ?"
    )


# -------------------------------------------------------------------- juge ---
JUDGE_SYSTEM = """Tu aides un candidat à adapter son CV à une offre. Tu évalues UNE compétence à la fois,
uniquement à partir des extraits de CV fournis (tu ne vois pas le reste du CV).

Statuts
- visible  : le CV nomme la compétence avec les mots de l'offre.
- hidden   : le CV prouve la compétence mais avec d'autres mots (synonyme, traduction, paraphrase).
- implicit : la compétence se déduit d'un projet ou d'un outil sans être nommée (ex. FastAPI -> API REST).
- absent   : aucune preuve dans les extraits.

Règles strictes
- evidence_quote : copie MOT POUR MOT une ligne ou un fragment d'un extrait (jamais de paraphrase).
  Elle doit être vérifiable par simple recherche de texte. Mets null si le statut est « absent ».
- N'invente jamais d'expérience, d'outil, de chiffre ni de responsabilité. En cas de doute sur une
  déduction implicite, choisis « absent ».
- suggested_rewrite (hidden et implicit uniquement) : reformule la ligne citée en employant le
  vocabulaire exact de l'offre. N'ajoute AUCUN fait, chiffre ou outil absent de la citation. Garde la
  langue du CV et une longueur voisine de l'original.
- reasoning : une ou deux phrases."""


def judge_user(req: Requirement, chunks: list[CVChunk], feedback: str = "") -> str:
    terms = ", ".join(req.offer_terms) or req.name
    excerpts = "\n\n".join(f"[{c.id}] (section : {c.section})\n{c.text}" for c in chunks) or "(aucun extrait)"
    parts = [
        "COMPÉTENCE DE L'OFFRE",
        f"- nom : {req.name}",
        f"- termes exacts de l'offre : {terms}",
        f"- importance : {'indispensable' if req.importance == 'must' else 'souhaitée'}",
        f"- passage de l'offre : {req.offer_quote or '(non précisé)'}",
        "",
        "EXTRAITS DU CV",
        excerpts,
    ]
    if feedback:
        parts += ["", "CORRECTIONS À APPORTER (ta réponse précédente a été rejetée par un contrôle automatique)", feedback]
    return "\n".join(parts)


# ------------------------------------------------------------------ synthèse ---
SUMMARY_SYSTEM = """Tu rédiges la synthèse d'une analyse CV/offre pour le candidat, en français, ton direct et
bienveillant. Appuie-toi UNIQUEMENT sur les données fournies (statuts, scores). Ne cite aucune compétence
qui n'y figure pas. headline : une phrase. strengths : 2 à 4 points. priorities : 2 à 4 actions concrètes,
les plus rentables d'abord."""


def summary_user(payload: str) -> str:
    return f"DONNÉES DE L'ANALYSE :\n{payload}\n\nRédige la synthèse."
