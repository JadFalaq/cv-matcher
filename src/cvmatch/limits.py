"""Garde-fous d'usage pour une instance publique (API, interface web).

Chaque analyse déclenche 20 à 50 appels LLM payants : on borne la taille des entrées, le nombre
d'analyses par client et par heure, et le nombre total d'analyses par jour (filet de sécurité budgétaire).
Compteurs en mémoire : suffisant pour une instance unique (démo / portfolio).
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


class InputTooLarge(ValueError):
    pass


@dataclass(frozen=True)
class Limits:
    max_cv_chars: int = 15_000
    max_offer_chars: int = 8_000
    max_pdf_pages: int = 5
    per_client_per_hour: int = 5
    per_day: int = 100

    @classmethod
    def from_env(cls) -> "Limits":
        d = cls()
        return cls(
            max_cv_chars=int(os.getenv("MAX_CV_CHARS", d.max_cv_chars)),
            max_offer_chars=int(os.getenv("MAX_OFFER_CHARS", d.max_offer_chars)),
            max_pdf_pages=int(os.getenv("MAX_PDF_PAGES", d.max_pdf_pages)),
            per_client_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", d.per_client_per_hour)),
            per_day=int(os.getenv("DAILY_ANALYSIS_CAP", d.per_day)),
        )


def check_sizes(cv_text: str, offer_text: str, limits: Limits) -> None:
    if len(cv_text) > limits.max_cv_chars:
        raise InputTooLarge(f"CV trop long : {len(cv_text)} caractères (maximum {limits.max_cv_chars}).")
    if len(offer_text) > limits.max_offer_chars:
        raise InputTooLarge(f"Offre trop longue : {len(offer_text)} caractères (maximum {limits.max_offer_chars}).")


class UsageGuard:
    """Fenêtre glissante d'une heure par client + plafond global par jour (UTC)."""

    def __init__(self, limits: Limits, clock=time.time):
        self.limits = limits
        self._clock = clock
        self._lock = threading.Lock()
        self._recent: dict[str, deque[float]] = defaultdict(deque)
        self._day = ""
        self._day_count = 0

    def acquire(self, client_id: str) -> str | None:
        """Enregistre une analyse et renvoie None si elle est autorisée, sinon la raison du refus."""
        now = self._clock()
        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        with self._lock:
            if day != self._day:
                self._day, self._day_count = day, 0
            if self._day_count >= self.limits.per_day:
                return "Le quota quotidien de la démo est atteint, reviens demain."
            recent = self._recent[client_id]
            while recent and now - recent[0] >= 3600:
                recent.popleft()
            if len(recent) >= self.limits.per_client_per_hour:
                wait = int(3600 - (now - recent[0])) // 60 + 1 if recent else 60
                return f"Limite de {self.limits.per_client_per_hour} analyses par heure atteinte, réessaie dans {wait} min."
            recent.append(now)
            self._day_count += 1
            return None
