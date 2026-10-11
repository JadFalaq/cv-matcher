"""Point d'entrée Python : `analyze(cv_text, offer_text)`."""

from __future__ import annotations

import uuid
from typing import Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from .config import Settings
from .graph import RunContext, build_graph
from .llm import LLM, get_embedder, get_llm
from .report import render_markdown
from .retrieval import Embedder
from .schemas import AnalysisResult
from .taxonomy import Taxonomy, default_taxonomy

# Reçoit les suggestions (liste de dict) et renvoie les ids approuvés (ou "all" / "none").
ReviewCallback = Callable[[list[dict]], "list[str] | str"]
# Appelé après chaque nœud terminé : (nom du nœud, mise à jour d'état renvoyée par le nœud).
ProgressCallback = Callable[[str, dict], None]


def analyze(
    cv_text: str,
    offer_text: str,
    *,
    llm: LLM | None = None,
    settings: Settings | None = None,
    taxonomy: Taxonomy | None = None,
    embedder: Embedder | None = None,
    review: ReviewCallback | None = None,
    thread_id: str | None = None,
    on_progress: ProgressCallback | None = None,
) -> AnalysisResult:
    """Analyse un CV face à une offre.

    - sans `review` : toutes les reformulations valides sont considérées comme acceptées ;
    - avec `review` : le graphe s'interrompt (human-in-the-loop) avant la finalisation et
      appelle `review(suggestions)` pour savoir lesquelles tu valides ;
    - avec `on_progress` : le graphe est exécuté en streaming et chaque nœud terminé est signalé
      (une fois par compétence pour `assess_skill`), pour afficher une progression.
    """
    settings = settings or Settings.from_env()
    ctx = RunContext(
        llm=llm or get_llm(settings),
        settings=settings,
        taxonomy=taxonomy or default_taxonomy(),
        embedder=embedder if embedder is not None else get_embedder(settings),
    )
    graph = build_graph(ctx, checkpointer=MemorySaver())
    # Filet de sécurité : un bug de boucle lève GraphRecursionError au lieu de tourner indéfiniment
    # (≈12 étapes normales + 1 par tour de vérification d'exhaustivité).
    config = {
        "configurable": {"thread_id": thread_id or uuid.uuid4().hex},
        "recursion_limit": 30 + 4 * settings.max_verify_rounds,
        # compétences évaluées en parallèle : borné pour rester sous le quota du fournisseur (requêtes/minute)
        "max_concurrency": settings.max_concurrency,
    }

    def run(graph_input) -> dict:
        if on_progress is None:
            return graph.invoke(graph_input, config)
        interrupts = None
        for update in graph.stream(graph_input, config, stream_mode="updates"):
            for node, value in update.items():
                if node == "__interrupt__":
                    interrupts = value
                else:
                    on_progress(node, value or {})
        out = dict(graph.get_state(config).values)
        if interrupts:
            out["__interrupt__"] = interrupts
        return out

    out = run({"cv_text": cv_text, "offer_text": offer_text, "require_review": review is not None, "assessments": []})
    while "__interrupt__" in out:
        payload = out["__interrupt__"][0].value
        decision = review(payload["suggestions"]) if review else "all"
        out = run(Command(resume=decision))

    result = AnalysisResult(
        requirements=out.get("requirements", []),
        assessments=out.get("results", []),
        score_actual=out["score_actual"],
        score_potential=out["score_potential"],
        score_final=out["score_final"],
        suggestions=out.get("suggestions", []),
        approved_ids=out.get("approved_ids", []),
        ats_keywords=out.get("ats_keywords", []),
        gaps=out.get("gaps", []),
        summary=out.get("summary"),
    )
    result.report_md = render_markdown(result)
    return result
