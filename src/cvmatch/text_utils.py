"""Utilitaires de texte : normalisation, recherche de termes et de citations.

Tout le contrôle anti-hallucination repose sur ces fonctions : une citation
n'est acceptée que si elle existe *réellement* dans le CV.
"""

from __future__ import annotations

import re
import unicodedata

_BULLET_RE = re.compile(r"^\s*(?:[-*•▪‣◦●·]|\d+[.)])\s+")

_STOPWORDS = frozenset(
    """
    le la les un une des de du d l et ou en au aux a à dans sur pour par avec sans
    the of and or in on for with to an is are as at by from
    ce cette ces son sa ses leur leurs qui que dont
    """.split()
)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Minuscules, sans accents, apostrophes/tirets unifiés, espaces compactés."""
    text = text.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae")
    text = strip_accents(text).lower()
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), (" ", " ")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def squash(text: str) -> str:
    """Forme de comparaison : alphanumérique (+ et # conservés pour c++ / c#), mots séparés par un espace."""
    text = normalize(text)
    return re.sub(r"[^a-z0-9+#]+", " ", text).strip()


def contains_term(text: str, term: str) -> bool:
    """Vrai si `term` apparaît dans `text` comme mot(s) entier(s) (insensible casse/accents/ponctuation)."""
    t = squash(term)
    return bool(t) and f" {t} " in f" {squash(text)} "


def find_quote(quote: str | None, source: str) -> bool:
    """Vrai si la citation existe dans la source (tolérant à la ponctuation, aux puces et à la casse)."""
    if not quote:
        return False
    q = squash(quote)
    return len(q) >= 2 and f" {q} " in f" {squash(source)} "


_WORD_RE = re.compile(r"[\w+#]+", re.UNICODE)


def original_surface(text: str, term: str) -> str | None:
    """Graphie d'origine de `term` dans `text` (ex. « RAG », « API REST », « Esprit d'équipe »).

    Cherche la suite de mots qui correspond au terme (insensible casse/accents/ponctuation) et
    renvoie le fragment tel qu'il est écrit dans le texte.
    """
    wanted = squash(term).split()
    if not wanted:
        return None
    words = [(m.start(), m.end(), squash(m.group())) for m in _WORD_RE.finditer(text)]
    # un « mot » peut se réduire à du vide après squash (ex. « _ ») : on les ignore
    words = [w for w in words if w[2]]
    flat: list[tuple[int, int, str]] = []
    for start, end, sq in words:
        for tok in sq.split():
            flat.append((start, end, tok))
    n = len(wanted)
    for i in range(len(flat) - n + 1):
        if [t for _, _, t in flat[i : i + n]] == wanted:
            return text[flat[i][0] : flat[i + n - 1][1]]
    return None


# Qualificatifs d'offre devant le nom d'une compétence : « Excellente maîtrise de », « Bonnes bases en »,
# « Expérience avec », « Strong experience with »… Un vrai LLM les recopie souvent dans les termes.
_QUALIFIER_RE = re.compile(
    r"^\s*(?:un plus\s*:\s*)?(?:(?:une?|des|la|le|les|a|an)\s+)?"
    r"(?:(?:tr[eè]s|excellente?s?|bonnes?|solides?|fortes?|premi[eè]re|strong|solid|good|excellent|deep|proven|hands-on)\s+)*"
    r"(?:ma[iî]trise|connaissances?|bases|notions|exp[eé]riences?|comp[eé]tences?|pratique|expertise|familiarit[eé]|"
    r"knowledge|experience|proficiency|skills?|understanding|background)\s+"
    r"(?:(?:de la|du|des|de|en|avec|sur|dans|of|with|in)\s+|(?:de l|d)['’]\s*)",
    re.IGNORECASE,
)


def strip_qualifiers(term: str) -> str:
    """« Excellente maîtrise de Python » -> « Python » (inchangé si aucun qualificatif reconnu)."""
    return _QUALIFIER_RE.sub("", term, count=1).strip() or term.strip()


def slugify(text: str) -> str:
    s = squash(text).replace("+", "p").replace("#", "sharp")
    return re.sub(r"\s+", "-", s).strip("-") or "skill"


def strip_bullet(line: str) -> str:
    return _BULLET_RE.sub("", line).strip()


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def tokenize(text: str) -> list[str]:
    """Tokens pour la recherche lexicale : sans mots vides, pluriel simplifié."""
    out: list[str] = []
    for tok in squash(text).split():
        if tok in _STOPWORDS or len(tok) < 2:
            continue
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        out.append(tok)
    return out
