"""Configuration : variables d'environnement et paramètres du score."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoringConfig:
    """Le score est calculé en code (jamais par le LLM) : somme pondérée de crédits.

    - weight_*  : poids d'une compétence selon son importance dans l'offre.
    - credit_actual    : ce que « voit » un recruteur / un ATS dans le CV tel qu'il est.
    - credit_potential : ce que l'on obtiendrait si la reformulation proposée était appliquée.
    """

    weight_must: float = 3.0
    weight_nice: float = 1.0
    credit_actual: dict = field(
        default_factory=lambda: {"visible": 1.0, "hidden": 0.6, "implicit": 0.3, "absent": 0.0}
    )
    credit_potential: dict = field(
        default_factory=lambda: {"visible": 1.0, "hidden": 1.0, "implicit": 0.85, "absent": 0.0}
    )

    def weight(self, importance: str) -> float:
        return self.weight_must if importance == "must" else self.weight_nice


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "fake"
    llm_model: str = ""
    llm_temperature: str = "0"
    llm_timeout: float = 60.0
    embeddings_provider: str = "none"
    embeddings_model: str = ""
    top_k: int = 4
    max_verify_rounds: int = 2
    max_judge_retries: int = 2
    max_concurrency: int = 5
    scoring: ScoringConfig = field(default_factory=ScoringConfig)

    @classmethod
    def from_env(cls) -> "Settings":
        try:  # python-dotenv est optionnel à l'exécution
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:  # pragma: no cover
            pass
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "fake").strip().lower() or "fake",
            llm_model=os.getenv("LLM_MODEL", "").strip(),
            llm_temperature=os.getenv("LLM_TEMPERATURE", "0").strip().lower() or "0",
            llm_timeout=float(os.getenv("LLM_TIMEOUT", "60")),
            embeddings_provider=os.getenv("EMBEDDINGS_PROVIDER", "none").strip().lower() or "none",
            embeddings_model=os.getenv("EMBEDDINGS_MODEL", "").strip(),
            top_k=int(os.getenv("TOP_K", "4")),
            max_verify_rounds=int(os.getenv("MAX_VERIFY_ROUNDS", "2")),
            max_judge_retries=int(os.getenv("MAX_JUDGE_RETRIES", "2")),
            max_concurrency=int(os.getenv("MAX_CONCURRENCY", "5")),
        )
