"""Référentiel de compétences : normalisation des synonymes et déclencheurs implicites."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from .taxonomy_default import DEFAULT_SKILLS
from .text_utils import contains_term, slugify, squash


@dataclass(frozen=True)
class SkillEntry:
    id: str
    name: str
    category: str
    aliases: tuple[str, ...] = ()
    implied_by: tuple[str, ...] = ()

    @property
    def terms(self) -> tuple[str, ...]:
        """Nom canonique + alias."""
        return (self.name, *self.aliases)


class Taxonomy:
    def __init__(self, entries: Iterable[SkillEntry]):
        self.entries: list[SkillEntry] = list(entries)
        self._by_term: dict[str, SkillEntry] = {}
        for entry in self.entries:
            for term in entry.terms:
                self._by_term.setdefault(squash(term), entry)
        self._by_id = {e.id: e for e in self.entries}

    # ---------------------------------------------------------- chargement ---
    @classmethod
    def default(cls) -> "Taxonomy":
        return cls(
            SkillEntry(slugify(name), name, cat, tuple(aliases), tuple(implied))
            for name, cat, aliases, implied in DEFAULT_SKILLS
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "Taxonomy":
        """Format : [{"name": "...", "category": "technical", "aliases": [...], "implied_by": [...]}]"""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            SkillEntry(
                slugify(item["name"]),
                item["name"],
                item.get("category", "technical"),
                tuple(item.get("aliases", [])),
                tuple(item.get("implied_by", [])),
            )
            for item in raw
        )

    # ------------------------------------------------------------ requêtes ---
    def get(self, skill_id: str) -> SkillEntry | None:
        return self._by_id.get(skill_id)

    def resolve(self, term: str) -> SkillEntry | None:
        return self._by_term.get(squash(term))

    def resolve_id(self, term: str) -> str:
        entry = self.resolve(term)
        return entry.id if entry else slugify(term)

    def _hits(self, text: str) -> list[tuple[SkillEntry, str, tuple[int, int]]]:
        """Occurrences (entrée, terme, position) dans `text`.

        Règle « la mention la plus longue gagne » : une occurrence couverte par une occurrence plus
        longue d'une AUTRE compétence est ignorée (« machine learning operations » ne compte pas
        comme « machine learning » ; « API REST » ne compte pas comme « REST »).
        """
        padded = f" {squash(text)} "
        raw: list[tuple[SkillEntry, str, tuple[int, int]]] = []
        for entry in self.entries:
            for term in entry.terms:
                needle = f" {squash(term)} "
                if needle.strip() == "":
                    continue
                start = padded.find(needle)
                while start != -1:
                    raw.append((entry, term, (start + 1, start + len(needle) - 1)))
                    start = padded.find(needle, start + 1)
        kept = []
        for entry, term, (s, e) in raw:
            covered = any(
                o_entry is not entry and o_s <= s and e <= o_e and (o_e - o_s) > (e - s)
                for o_entry, _, (o_s, o_e) in raw
            )
            if not covered:
                kept.append((entry, term, (s, e)))
        return kept

    def find_in_text(self, text: str) -> list[tuple[SkillEntry, str]]:
        """Compétences du référentiel mentionnées dans `text`, avec le premier terme trouvé."""
        first: dict[str, str] = {}
        for entry, term, _ in self._hits(text):
            first.setdefault(entry.id, term)
        return [(e, first[e.id]) for e in self.entries if e.id in first]

    def terms_in_text(self, entry: SkillEntry, text: str) -> list[str]:
        """Tous les termes (nom + alias) de `entry` présents dans `text`, sans les termes inclus dans un plus long."""
        hits: list[str] = []
        for e, term, _ in self._hits(text):
            if e is entry and not any(squash(term) == squash(h) for h in hits):
                hits.append(term)
        return [t for t in hits if not any(squash(t) != squash(o) and f" {squash(t)} " in f" {squash(o)} " for o in hits)]


@lru_cache(maxsize=1)
def default_taxonomy() -> Taxonomy:
    return Taxonomy.default()
