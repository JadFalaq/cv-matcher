"""Contrôles déterministes appliqués aux sorties du LLM.

C'est ici que le projet se distingue d'une simple chaîne de prompts : le LLM *propose*,
le code *vérifie*. Tout verdict est confronté au texte réel du CV avant d'être accepté.

Garanties :
  1. une preuve citée doit exister mot pour mot dans le CV ;
  2. « visible » vs « hidden » est arbitré par le code (le terme exact de l'offre est-il dans la preuve ?) ;
  3. « absent » est rejeté si le terme de l'offre apparaît pourtant dans les extraits ;
  4. une reformulation ne peut ni inventer de chiffres, ni ajouter d'outils absents de la preuve.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import Assessment, CVChunk, JudgeVerdict, Requirement, RequirementDraft, Status
from .taxonomy import Taxonomy
from .text_utils import (
    contains_term,
    find_quote,
    numbers_in,
    original_surface,
    slugify,
    squash,
    strip_bullet,
    strip_qualifiers,
)

MAX_TERM_WORDS = 4


# ------------------------------------------------------------ exigences ---
def match_terms(req: Requirement) -> list[str]:
    """Termes de l'offre servant d'étalon pour décider « visible » (repli : le nom de la compétence)."""
    return req.offer_terms or [req.name]


def _same(a: str, b: str) -> bool:
    return squash(a) == squash(b)


def _drop_included(terms: list[str]) -> list[str]:
    """Retire un terme s'il est contenu dans un terme plus long (« modèles de langage » vs « grands modèles de langage »)."""
    return [t for t in terms if not any(not _same(t, o) and f" {squash(t)} " in f" {squash(o)} " for o in terms)]


def normalize_requirements(drafts: list, offer_text: str, taxonomy: Taxonomy) -> list[Requirement]:
    """Dédoublonne, normalise via le référentiel et vérifie citations/termes contre l'offre."""
    merged: dict[str, Requirement] = {}
    for item in drafts:
        draft = item if isinstance(item, RequirementDraft) else RequirementDraft.model_validate(item)
        if not draft.name.strip():
            continue
        draft_terms = [strip_qualifiers(t) for t in draft.offer_terms]
        entry = taxonomy.resolve(strip_qualifiers(draft.name))
        if entry is None:
            for t in draft_terms:
                entry = taxonomy.resolve(t)
                if entry:
                    break
        rid = entry.id if entry else slugify(draft.name)
        name = entry.name if entry else draft.name.strip()

        terms: list[str] = list(taxonomy.terms_in_text(entry, offer_text)) if entry else []
        for t in draft_terms:
            if t and len(t.split()) <= MAX_TERM_WORDS and contains_term(offer_text, t) and not any(_same(t, x) for x in terms):
                terms.append(t)
        if not terms and contains_term(offer_text, name):
            terms = [name]
        # graphie d'origine de l'offre (« RAG », « API REST ») : utile pour les mots-clés et reformulations
        terms = [original_surface(offer_text, t) or t for t in terms]
        quote = draft.offer_quote.strip() if draft.offer_quote and find_quote(draft.offer_quote, offer_text) else None
        category = entry.category if entry else draft.category

        if rid in merged:
            cur = merged[rid]
            cur.importance = "must" if "must" in (cur.importance, draft.importance) else "nice"
            for t in terms:
                if not any(_same(t, x) for x in cur.offer_terms):
                    cur.offer_terms.append(t)
            cur.offer_quote = cur.offer_quote or quote
        else:
            merged[rid] = Requirement(
                id=rid, name=name, category=category, importance=draft.importance, offer_terms=terms, offer_quote=quote
            )
    for req in merged.values():
        req.offer_terms = _drop_included(req.offer_terms)
    return list(merged.values())


# -------------------------------------------------------------- verdicts ---
@dataclass
class Problem:
    kind: str  # "quote" | "absent" | "rewrite"
    message: str


@dataclass
class Verification:
    problems: list[Problem]
    status: Status
    quote: str | None
    chunk: CVChunk | None
    rewrite: str | None
    rewrite_ok: bool
    notes: list[str] = field(default_factory=list)
    lexical: tuple[Status, str, CVChunk] | None = None


def lexical_hit(req: Requirement, chunks: list[CVChunk], taxonomy: Taxonomy) -> tuple[Status, str, CVChunk] | None:
    """Preuve lexicale directe : terme de l'offre (visible) puis alias du référentiel (hidden)."""
    terms = match_terms(req)
    entry = taxonomy.get(req.id)
    aliases = [t for t in (entry.terms if entry else ()) if not any(_same(t, x) for x in terms)]
    for status, candidates in (("visible", terms), ("hidden", aliases)):
        if not candidates:
            continue
        for chunk in chunks:
            for line in chunk.text.splitlines():
                s = strip_bullet(line)
                if s and any(contains_term(s, t) for t in candidates):
                    return status, s, chunk  # type: ignore[return-value]
    return None


def check_rewrite(rewrite: str | None, quote: str, req: Requirement, taxonomy: Taxonomy) -> list[str]:
    if not rewrite:
        return ["Propose une reformulation (suggested_rewrite) de la ligne citée avec le vocabulaire de l'offre."]
    terms = match_terms(req)
    msgs: list[str] = []
    if _same(rewrite, quote):
        msgs.append("La reformulation est identique à la citation.")
    if not any(contains_term(rewrite, t) for t in terms):
        msgs.append(f"La reformulation doit employer le terme exact de l'offre ({', '.join(terms)}).")
    invented_numbers = numbers_in(rewrite) - numbers_in(quote) - numbers_in(" ".join(terms))
    if invented_numbers:
        msgs.append(f"La reformulation introduit des chiffres absents de la citation : {', '.join(sorted(invented_numbers))}.")
    if len(rewrite) > 2 * len(quote) + 60:
        msgs.append("La reformulation est beaucoup plus longue que la ligne d'origine : ne rajoute aucun contenu.")
    allowed = {e.id for e, _ in taxonomy.find_in_text(quote)} | {req.id}
    invented = [e.name for e, _ in taxonomy.find_in_text(rewrite) if e.id not in allowed]
    if invented:
        msgs.append(f"La reformulation ajoute des compétences absentes de la citation : {', '.join(invented)}.")
    return msgs


def verify_verdict(req: Requirement, verdict: JudgeVerdict, chunks: list[CVChunk], taxonomy: Taxonomy) -> Verification:
    terms = match_terms(req)
    problems: list[Problem] = []
    notes: list[str] = []
    status: Status = verdict.status
    quote = verdict.evidence_quote
    chunk: CVChunk | None = None
    lexical = None
    rewrite = (verdict.suggested_rewrite or "").strip() or None
    rewrite_ok = False

    if status != "absent":
        chunk = next((c for c in chunks if find_quote(quote, c.text)), None)
        if chunk is None:
            problems.append(
                Problem("quote", "La citation fournie n'existe dans aucun extrait du CV : copie une ligne MOT POUR MOT.")
            )
            quote = None
        else:
            has_term = any(contains_term(quote or "", t) for t in terms)
            if has_term and status != "visible":
                notes.append("Statut relevé à « visible » : le terme exact de l'offre figure dans la preuve.")
                status = "visible"
            elif not has_term and status == "visible":
                notes.append("Statut ramené à « hidden » : le terme exact de l'offre ne figure pas dans la preuve.")
                status = "hidden"
    else:
        quote = None
        lexical = lexical_hit(req, chunks, taxonomy)
        if lexical:
            problems.append(
                Problem(
                    "absent",
                    f"Tu as répondu « absent » mais l'extrait [{lexical[2].id}] contient la compétence : « {lexical[1]} ».",
                )
            )

    if status in ("hidden", "implicit") and chunk is not None and quote:
        rw_problems = check_rewrite(rewrite, quote, req, taxonomy)
        problems.extend(Problem("rewrite", m) for m in rw_problems)
        rewrite_ok = not rw_problems
    if status in ("visible", "absent"):
        rewrite = None

    return Verification(problems, status, quote, chunk, rewrite, rewrite_ok, notes, lexical)


def build_assessment(
    req: Requirement,
    verdict: JudgeVerdict,
    chunks: list[CVChunk],
    taxonomy: Taxonomy,
    attempts: int,
    final: bool,
) -> tuple[Assessment | None, str]:
    """Retourne (Assessment, "") si le verdict est accepté (ou si `final` impose un repli sûr),
    sinon (None, retour d'erreur à renvoyer au juge)."""
    v = verify_verdict(req, verdict, chunks, taxonomy)
    if not v.problems:
        return (
            Assessment(
                requirement=req,
                status=v.status,
                evidence_quote=v.quote,
                chunk_id=v.chunk.id if v.chunk else None,
                section=v.chunk.section if v.chunk else None,
                reasoning=verdict.reasoning,
                suggested_rewrite=v.rewrite if v.rewrite_ok else None,
                rewrite_ok=v.rewrite_ok,
                attempts=attempts,
                notes=v.notes,
            ),
            "",
        )
    if not final:
        return None, "\n".join(f"- {p.message}" for p in v.problems)

    # Épuisement des essais : repli prudent, jamais d'invention.
    kinds = {p.kind for p in v.problems}
    notes = list(v.notes)
    status, quote, chunk = v.status, v.quote, v.chunk
    verified, needs_review = True, False
    if "quote" in kinds:
        status, quote, chunk, verified, needs_review = "absent", None, None, False, True
        notes.append("Citation introuvable dans le CV après plusieurs essais : compétence ramenée à « absente » (à vérifier).")
    elif "absent" in kinds and v.lexical:
        status, quote, chunk = v.lexical
        needs_review = True
        notes.append("Le LLM a conclu « absent » alors que le CV contient le terme : preuve lexicale retenue (à vérifier).")
    else:
        notes.append("Reformulation rejetée par les contrôles : " + " ".join(p.message for p in v.problems))
    return (
        Assessment(
            requirement=req,
            status=status,
            evidence_quote=quote,
            chunk_id=chunk.id if chunk else None,
            section=chunk.section if chunk else None,
            reasoning=verdict.reasoning,
            suggested_rewrite=None,
            rewrite_ok=False,
            verified=verified,
            needs_review=needs_review,
            attempts=attempts,
            notes=notes,
        ),
        "",
    )
