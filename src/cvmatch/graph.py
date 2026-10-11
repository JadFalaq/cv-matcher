"""Graphe LangGraph du pipeline.

    START ─┬─> parse_offer ─> verify_exhaustivity ⟲ ─> normalize_requirements ─┐
           └─> index_cv (chunking + index RAG) ───────────────────────────────┤
                                                                               v
                         dispatch ──Send (une branche PAR compétence, en parallèle)──> assess_skill
                                                                                          │
              assess_skill = sous-graphe : retrieve ─> judge ─> verify ⟲ judge             │
                                                                                          v
                          aggregate ─> summarize ─> human_review (interrupt) ─> finalize ─> END

Les états ne contiennent que des dict/listes JSON (pas d'objets Pydantic) : ils sont donc
sérialisables par n'importe quel checkpointer (mémoire, SQLite, Postgres).
"""

from __future__ import annotations

import logging
import operator
import threading
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from . import prompts as P
from .config import Settings
from .ingestion import chunk_cv
from .llm import FATAL_ERRORS, LLM
from .retrieval import Embedder, HybridRetriever
from .schemas import (
    Assessment,
    CVChunk,
    ExhaustivityCheck,
    ExtractionResult,
    JudgeVerdict,
    Requirement,
    Summary,
)
from .scoring import ats_keywords, build_suggestions, compute_score, find_gaps
from .taxonomy import Taxonomy
from .verification import build_assessment, lexical_hit, normalize_requirements

log = logging.getLogger("cvmatch.graph")


# ======================================================================= état ===
class GraphState(TypedDict, total=False):
    cv_text: str
    offer_text: str
    require_review: bool
    # extraction
    requirements_raw: list[dict]
    verify_round: int
    new_found: int
    requirements: list[dict]
    # RAG
    chunks: list[dict]
    n_requirements: int
    # évaluation (réducteur : chaque branche Send ajoute son résultat)
    assessments: Annotated[list[dict], operator.add]
    # sorties
    results: list[dict]
    score_actual: dict
    score_potential: dict
    suggestions: list[dict]
    ats_keywords: list[str]
    gaps: list[dict]
    summary: dict | None
    approved_ids: list[str]
    score_final: dict


class AssessState(TypedDict, total=False):
    requirement: dict
    chunks: list[dict]
    retrieved: list[dict]
    verdict: dict
    feedback: str
    attempts: int
    result: dict


@dataclass
class RunContext:
    """Dépendances d'un run (LLM, config, référentiel, index RAG). Un contexte par exécution."""

    llm: LLM
    settings: Settings
    taxonomy: Taxonomy
    embedder: Embedder | None = None
    retriever: HybridRetriever | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def ensure_retriever(self, chunks: list[dict]) -> HybridRetriever:
        with self._lock:
            if self.retriever is None:  # ex. reprise après redémarrage avec un checkpointer persistant
                self.retriever = HybridRetriever([CVChunk.model_validate(c) for c in chunks], self.embedder)
            return self.retriever


# ============================================== sous-graphe : une compétence ===
def build_assess_graph(ctx: RunContext):
    """retrieve -> judge -> verify -> (judge si rejeté, sinon fin).  C'est la boucle agentique."""

    def retrieve(state: AssessState) -> dict:
        req = Requirement.model_validate(state["requirement"])
        retriever = ctx.ensure_retriever(state["chunks"])
        entry = ctx.taxonomy.get(req.id)
        terms = [req.name, *req.offer_terms]
        if entry:  # expansion de requête : synonymes + déclencheurs implicites
            terms += [*entry.aliases, *entry.implied_by]
        query = " ".join(dict.fromkeys(terms))
        dense = req.name + (f" : {req.offer_quote}" if req.offer_quote else "")
        hits = retriever.search(query, ctx.settings.top_k, query_dense=dense)
        return {"retrieved": [c.model_dump() for c, _ in hits]}

    def judge(state: AssessState) -> dict:
        req = Requirement.model_validate(state["requirement"])
        chunks = [CVChunk.model_validate(c) for c in state["retrieved"]]
        feedback = state.get("feedback", "")
        verdict = ctx.llm.structured(
            JudgeVerdict,
            system=P.JUDGE_SYSTEM,
            user=P.judge_user(req, chunks, feedback),
            tag="judge",
            context={"requirement": req.model_dump(), "chunks": state["retrieved"], "feedback": feedback},
        )
        return {"verdict": verdict.model_dump(), "attempts": state.get("attempts", 0) + 1}

    def verify(state: AssessState) -> dict:
        req = Requirement.model_validate(state["requirement"])
        verdict = JudgeVerdict.model_validate(state["verdict"])
        retrieved = state["retrieved"]
        if verdict.status == "absent":
            # « absent » est vérifié sur TOUT le CV : si la preuve lexicale est dans un bloc non retrouvé
            # par le RAG, on l'ajoute aux extraits pour que le juge la voie au prochain essai.
            hit = lexical_hit(req, [CVChunk.model_validate(c) for c in state["chunks"]], ctx.taxonomy)
            if hit and hit[2].id not in {c["id"] for c in retrieved}:
                retrieved = [*retrieved, hit[2].model_dump()]
        chunks = [CVChunk.model_validate(c) for c in retrieved]
        attempts = state["attempts"]
        final = attempts > ctx.settings.max_judge_retries
        assessment, feedback = build_assessment(req, verdict, chunks, ctx.taxonomy, attempts, final)
        if assessment is not None:
            return {"result": assessment.model_dump()}
        return {"feedback": feedback, "retrieved": retrieved}

    def route(state: AssessState) -> str:
        return END if state.get("result") else "judge"

    g = StateGraph(AssessState)
    g.add_node("retrieve", retrieve)
    g.add_node("judge", judge)
    g.add_node("verify", verify)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "judge")
    g.add_edge("judge", "verify")
    g.add_conditional_edges("verify", route, ["judge", END])
    return g.compile()


# ================================================================ graphe principal ===
def build_graph(ctx: RunContext, checkpointer: Any = None):
    assess_graph = build_assess_graph(ctx)
    cfg = ctx.settings.scoring

    # ---- extraction de l'offre ------------------------------------------------
    def parse_offer(state: GraphState) -> dict:
        res = ctx.llm.structured(
            ExtractionResult,
            system=P.EXTRACT_SYSTEM,
            user=P.extract_user(state["offer_text"]),
            tag="extract",
            context={"offer_text": state["offer_text"]},
        )
        return {"requirements_raw": [r.model_dump() for r in res.requirements], "verify_round": 0, "new_found": 0}

    def verify_exhaustivity(state: GraphState) -> dict:
        """Relit l'offre avec la liste déjà extraite : « que manque-t-il ? »."""
        raw = state["requirements_raw"]
        res = ctx.llm.structured(
            ExhaustivityCheck,
            system=P.EXHAUSTIVITY_SYSTEM,
            user=P.exhaustivity_user(state["offer_text"], [r["name"] for r in raw]),
            tag="exhaustivity",
            context={"offer_text": state["offer_text"], "known": [r["name"] for r in raw]},
        )
        known = {ctx.taxonomy.resolve_id(r["name"]) for r in raw}
        fresh: list[dict] = []
        for m in res.missing:
            rid = ctx.taxonomy.resolve_id(m.name)
            if rid not in known:
                known.add(rid)
                fresh.append(m.model_dump())
        return {
            "requirements_raw": raw + fresh,
            "verify_round": state.get("verify_round", 0) + 1,
            "new_found": len(fresh),
        }

    def route_after_verify(state: GraphState) -> str:
        again = state.get("new_found", 0) > 0 and state.get("verify_round", 0) < ctx.settings.max_verify_rounds
        return "verify_exhaustivity" if again else "normalize_requirements"

    def normalize_node(state: GraphState) -> dict:
        reqs = normalize_requirements(state["requirements_raw"], state["offer_text"], ctx.taxonomy)
        return {"requirements": [r.model_dump() for r in reqs]}

    # ---- indexation du CV (en parallèle de l'extraction) ----------------------
    def index_cv(state: GraphState) -> dict:
        chunks = chunk_cv(state["cv_text"])
        ctx.retriever = HybridRetriever(chunks, ctx.embedder)
        return {"chunks": [c.model_dump() for c in chunks]}

    # ---- fan-out : une branche par compétence ---------------------------------
    def dispatch(state: GraphState) -> dict:
        return {"n_requirements": len(state.get("requirements", []))}

    def route_to_assess(state: GraphState):
        reqs = state.get("requirements", [])
        if not reqs:
            return "aggregate"
        return [Send("assess_skill", {"requirement": r, "chunks": state["chunks"]}) for r in reqs]

    def assess_skill(payload: dict) -> dict:
        try:
            out = assess_graph.invoke(
                {"requirement": payload["requirement"], "chunks": payload["chunks"], "attempts": 0, "feedback": ""},
                # retrieve + (judge, verify) x essais : marge confortable, mais bornée
                {"recursion_limit": 10 + 3 * (ctx.settings.max_judge_retries + 1)},
            )
            return {"assessments": [out["result"]]}
        except Exception as exc:
            if type(exc).__name__ in FATAL_ERRORS:  # clé ou déploiement invalide : inutile de continuer
                raise
            # Une compétence en échec (quota, délai…) ne bloque pas l'analyse : repli prudent, signalé.
            req = Requirement.model_validate(payload["requirement"])
            log.error("Compétence '%s' non évaluée : %s", req.name, type(exc).__name__)
            failed = Assessment(
                requirement=req,
                status="absent",
                verified=False,
                needs_review=True,
                attempts=0,  # 0 = aucun verdict obtenu
                notes=[f"Évaluation impossible (erreur du fournisseur LLM : {type(exc).__name__}) : à vérifier."],
            )
            return {"assessments": [failed.model_dump()]}

    # ---- agrégation (fan-in) et sorties déterministes -------------------------
    def _ordered(state: GraphState) -> list[Assessment]:
        reqs = [Requirement.model_validate(r) for r in state.get("requirements", [])]
        by_id = {a["requirement"]["id"]: a for a in state.get("assessments", [])}
        return [Assessment.model_validate(by_id[r.id]) for r in reqs if r.id in by_id]

    def aggregate(state: GraphState) -> dict:
        items = _ordered(state)
        return {
            "results": [a.model_dump() for a in items],
            "score_actual": compute_score(items, cfg, "actual").model_dump(),
            "score_potential": compute_score(items, cfg, "potential").model_dump(),
            "suggestions": [s.model_dump() for s in build_suggestions(items, cfg)],
            "ats_keywords": ats_keywords(items),
            "gaps": [g.model_dump() for g in find_gaps(items)],
        }

    def summarize(state: GraphState) -> dict:
        items = _ordered(state)
        sa, sp = state["score_actual"]["score"], state["score_potential"]["score"]
        # noms tels qu'écrits dans l'offre (« MLOps », « API REST ») plutôt que normalisés (« mlops »)
        shown = {a.requirement.id: (a.requirement.offer_terms or [a.requirement.name])[0] for a in items}
        visible = [shown[a.requirement.id] for a in items if a.status == "visible" and a.requirement.importance == "must"]
        to_rewrite = [shown[s["skill_id"]] for s in state.get("suggestions", [])]
        gaps = [shown[g["skill_id"]] for g in state.get("gaps", []) if g["importance"] == "must"]
        lines = [f"- {shown[a.requirement.id]} | {a.requirement.importance} | {a.status}" for a in items]
        payload = f"Score actuel : {sa}/100 ; potentiel : {sp}/100\n" + "\n".join(lines)
        try:
            summary = ctx.llm.structured(
                Summary,
                system=P.SUMMARY_SYSTEM,
                user=P.summary_user(payload),
                tag="summary",
                context={
                    "visible": visible,
                    "to_rewrite": to_rewrite,
                    "gaps": gaps,
                    "score_actual": sa,
                    "score_potential": sp,
                },
            )
            return {"summary": summary.model_dump()}
        except Exception:  # la synthèse est un bonus : ne jamais faire échouer l'analyse
            return {"summary": None}

    # ---- validation humaine ---------------------------------------------------
    def human_review(state: GraphState) -> dict:
        suggestions = state.get("suggestions", [])
        if not suggestions:
            return {"approved_ids": []}
        if not state.get("require_review"):
            return {"approved_ids": [s["id"] for s in suggestions]}
        decision = interrupt(
            {
                "type": "review_suggestions",
                "suggestions": suggestions,
                "score_actual": state["score_actual"]["score"],
                "score_potential": state["score_potential"]["score"],
            }
        )
        valid = [s["id"] for s in suggestions]
        if decision == "all":
            approved = valid
        elif decision in (None, "none"):
            approved = []
        else:
            wanted = set(decision)
            approved = [i for i in valid if i in wanted]
        return {"approved_ids": approved}

    def finalize(state: GraphState) -> dict:
        items = _ordered(state)
        final = compute_score(items, cfg, "final", set(state.get("approved_ids", [])))
        return {"score_final": final.model_dump()}

    # ---- câblage ----------------------------------------------------------------
    b = StateGraph(GraphState)
    for name, fn in (
        ("parse_offer", parse_offer),
        ("verify_exhaustivity", verify_exhaustivity),
        ("normalize_requirements", normalize_node),
        ("index_cv", index_cv),
        ("dispatch", dispatch),
        ("assess_skill", assess_skill),
        ("aggregate", aggregate),
        ("summarize", summarize),
        ("human_review", human_review),
        ("finalize", finalize),
    ):
        b.add_node(name, fn)

    b.add_edge(START, "parse_offer")
    b.add_edge(START, "index_cv")  # exécuté en parallèle de l'extraction
    b.add_edge("parse_offer", "verify_exhaustivity")
    b.add_conditional_edges("verify_exhaustivity", route_after_verify, ["verify_exhaustivity", "normalize_requirements"])
    b.add_edge(["normalize_requirements", "index_cv"], "dispatch")
    b.add_conditional_edges("dispatch", route_to_assess, ["assess_skill", "aggregate"])
    b.add_edge("assess_skill", "aggregate")
    b.add_edge("aggregate", "summarize")
    b.add_edge("summarize", "human_review")
    b.add_edge("human_review", "finalize")
    b.add_edge("finalize", END)
    return b.compile(checkpointer=checkpointer)
