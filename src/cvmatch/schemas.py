"""Schémas Pydantic : sorties structurées des LLM et objets du pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Importance = Literal["must", "nice"]
Category = Literal["technical", "tool", "soft", "language", "education", "experience", "domain"]
Status = Literal["visible", "hidden", "implicit", "absent"]

STATUS_LABELS = {
    "visible": "Couverte et visible",
    "hidden": "Couverte mais cachée",
    "implicit": "Implicite",
    "absent": "Absente",
}


# ----------------------------------------------------------------- offre ---
class RequirementDraft(BaseModel):
    """Sortie brute du LLM d'extraction (avant normalisation)."""

    name: str = Field(description="Nom court et normalisé de la compétence (ex. « machine learning »).")
    category: Category = Field(default="technical")
    importance: Importance = Field(
        default="must",
        description="must = indispensable/requis ; nice = souhaité/un plus.",
    )
    offer_terms: list[str] = Field(
        default_factory=list,
        description="Expressions EXACTES de l'offre désignant cette compétence (courtes, 1 à 4 mots).",
    )
    offer_quote: str | None = Field(
        default=None, description="Phrase ou ligne EXACTE de l'offre qui mentionne la compétence."
    )


class ExtractionResult(BaseModel):
    requirements: list[RequirementDraft] = Field(default_factory=list)


class ExhaustivityCheck(BaseModel):
    missing: list[RequirementDraft] = Field(
        default_factory=list, description="Compétences de l'offre absentes de la liste fournie."
    )
    comment: str = ""


class Requirement(RequirementDraft):
    """Exigence normalisée, dédoublonnée et vérifiée contre le texte de l'offre."""

    id: str


# -------------------------------------------------------------------- CV ---
class CVChunk(BaseModel):
    id: str
    section: str
    text: str


# ----------------------------------------------------------------- juge ---
class JudgeVerdict(BaseModel):
    status: Status
    evidence_quote: str | None = Field(
        default=None,
        description="Citation copiée MOT POUR MOT depuis un extrait du CV (null si absent).",
    )
    reasoning: str = Field(default="", description="Justification en une ou deux phrases.")
    suggested_rewrite: str | None = Field(
        default=None,
        description="Pour hidden/implicit : la ligne du CV reformulée avec le vocabulaire de l'offre, "
        "sans aucun fait nouveau.",
    )


class Assessment(BaseModel):
    requirement: Requirement
    status: Status
    evidence_quote: str | None = None
    chunk_id: str | None = None
    section: str | None = None
    reasoning: str = ""
    suggested_rewrite: str | None = None
    rewrite_ok: bool = False
    verified: bool = True
    needs_review: bool = False
    attempts: int = 1
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- sorties ---
class Suggestion(BaseModel):
    id: str
    skill_id: str
    skill_name: str
    status: Status
    importance: Importance
    section: str | None = None
    original: str
    rewrite: str
    gain: float = Field(description="Gain estimé sur le score (points sur 100).")


class ScoreResult(BaseModel):
    score: float = Field(description="Score sur 100.")
    points: float
    max_points: float
    must_coverage: float = Field(description="Part des compétences indispensables non absentes (0 à 1).")
    counts: dict[str, int] = Field(default_factory=dict)


class Gap(BaseModel):
    skill_id: str
    skill_name: str
    importance: Importance
    offer_quote: str | None = None


class Summary(BaseModel):
    headline: str
    strengths: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    requirements: list[Requirement]
    assessments: list[Assessment]
    score_actual: ScoreResult
    score_potential: ScoreResult
    score_final: ScoreResult
    suggestions: list[Suggestion]
    approved_ids: list[str]
    ats_keywords: list[str]
    gaps: list[Gap]
    summary: Summary | None = None
    report_md: str = ""
