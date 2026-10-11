"""API FastAPI : `uvicorn cvmatch.api:app --reload`  (nécessite `pip install -e .[api]`).

Si `API_KEY` est défini, chaque appel (hors /health et /example) doit fournir l'en-tête `X-API-Key`.
`ALLOWED_ORIGINS` (séparées par des virgules) autorise le frontend web à appeler l'API depuis le navigateur.
Le texte des CV n'est jamais journalisé (données personnelles).
"""

from __future__ import annotations

import json
import logging
import os
import queue
import secrets
import threading
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import Settings
from .ingestion import read_bytes
from .limits import InputTooLarge, Limits, UsageGuard, check_sizes
from .pipeline import analyze
from .report import render_markdown
from .schemas import AnalysisResult, Assessment, ScoreResult
from .scoring import compute_score

log = logging.getLogger("cvmatch.api")

app = FastAPI(title="cvmatch", version="0.1.0", description="Adapter son CV à une offre, compétence par compétence.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)
limits = Limits.from_env()
guard = UsageGuard(limits)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
HEARTBEAT_SECONDS = 15  # garde la connexion ouverte derrière les proxys pendant une longue analyse
STEP_LABELS = {
    "parse_offer": "Lecture de l'offre",
    "index_cv": "Lecture de ton CV",
    "verify_exhaustivity": "Vérification qu'aucune compétence n'a été oubliée",
    "normalize_requirements": "Regroupement des compétences",
    "dispatch": "Recherche des preuves dans ton CV",
    "aggregate": "Calcul des scores",
    "summarize": "Rédaction de la synthèse",
    "finalize": "Finalisation",
}


class AnalyzeRequest(BaseModel):
    cv_text: str = Field(min_length=20, description="Texte du CV")
    offer_text: str = Field(min_length=20, description="Texte de l'offre")


class ScoreRequest(BaseModel):
    assessments: list[Assessment]
    approved_ids: list[str] = Field(default_factory=list)


class ReportRequest(BaseModel):
    result: AnalysisResult
    approved_ids: list[str] = Field(default_factory=list)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_KEY")
    if expected and not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante (en-tête X-API-Key).")


# ------------------------------------------------------------------ outils ---
async def _cv_from_form(cv_file: UploadFile | None, cv_text: str | None) -> str:
    """Texte du CV : fichier envoyé (pdf/md/txt) en priorité, sinon texte collé."""
    if cv_file is None or not cv_file.filename:
        return cv_text or ""
    data = await cv_file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (5 Mo maximum).")
    try:
        return read_bytes(data, cv_file.filename, max_pages=limits.max_pdf_pages)
    except InputTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Fichier illisible : essaie un autre format ou colle le texte.") from exc


def _admit(request: Request, cv_text: str, offer_text: str) -> None:
    """Contrôles avant de lancer une analyse payante : contenu, taille, débit."""
    if len(cv_text.strip()) < 20:
        raise HTTPException(status_code=422, detail="Aucun texte trouvé dans le CV (un PDF scanné ne contient que des images).")
    if len(offer_text.strip()) < 20:
        raise HTTPException(status_code=422, detail="L'offre est vide ou trop courte.")
    try:
        check_sizes(cv_text, offer_text, limits)
    except InputTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    refused = guard.acquire(request.client.host if request.client else "inconnu")
    if refused:
        raise HTTPException(status_code=429, detail=refused)


def _run(request: Request, cv_text: str, offer_text: str) -> AnalysisResult:
    _admit(request, cv_text, offer_text)
    try:
        return analyze(cv_text, offer_text, settings=Settings.from_env())
    except Exception as exc:  # erreur fournisseur LLM, clé manquante…
        log.error("Échec de l'analyse : %s", type(exc).__name__)  # jamais le contenu (il peut citer le CV)
        raise HTTPException(status_code=502, detail="Échec de l'analyse (fournisseur LLM indisponible ?).") from exc


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_analysis(cv_text: str, offer_text: str) -> Iterator[str]:
    """Exécute l'analyse dans un thread et relaie l'avancement en Server-Sent Events."""
    events: queue.Queue = queue.Queue()
    progress = {"done": 0, "total": 0}

    def on_progress(node: str, update: dict) -> None:
        if node == "dispatch":
            progress["total"] = update.get("n_requirements", 0)
        if node == "assess_skill":
            progress["done"] += 1
            skill = (update.get("assessments") or [{}])[0].get("requirement", {}).get("name")
            events.put(("progress", {"step": node, "label": f"Compétence vérifiée : {skill}", **progress}))
        elif node in STEP_LABELS:
            events.put(("progress", {"step": node, "label": STEP_LABELS[node], **progress}))

    def worker() -> None:
        try:
            result = analyze(cv_text, offer_text, settings=Settings.from_env(), on_progress=on_progress)
            events.put(("result", result.model_dump(mode="json")))
        except Exception as exc:
            log.error("Échec de l'analyse : %s", type(exc).__name__)
            events.put(("error", {"detail": "L'analyse a échoué (fournisseur LLM indisponible ou mal configuré). Réessaie dans une minute."}))
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()
    while True:
        try:
            item = events.get(timeout=HEARTBEAT_SECONDS)
        except queue.Empty:
            yield ": ping\n\n"
            continue
        if item is None:
            return
        yield _sse(*item)


# ------------------------------------------------------------------ routes ---
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": Settings.from_env().llm_provider}


@app.get("/example")
def example() -> dict:
    """CV et offre fictifs pour essayer l'outil sans ses propres documents."""
    data = Path(os.getenv("CVMATCH_DATA_DIR", Path.cwd() / "data"))
    try:
        return {
            "cv_text": (data / "sample_cv.md").read_text(encoding="utf-8"),
            "offer_text": (data / "sample_offer.txt").read_text(encoding="utf-8"),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Exemple indisponible sur ce serveur.") from exc


@app.post("/analyze", response_model=AnalysisResult, dependencies=[Depends(require_api_key)])
def analyze_endpoint(req: AnalyzeRequest, request: Request) -> AnalysisResult:
    return _run(request, req.cv_text, req.offer_text)


@app.post("/analyze/upload", response_model=AnalysisResult, dependencies=[Depends(require_api_key)])
async def analyze_upload(
    request: Request,
    cv_file: UploadFile = File(description="CV (.pdf, .md ou .txt)"),
    offer_text: str = Form(min_length=20),
) -> AnalysisResult:
    return _run(request, await _cv_from_form(cv_file, None), offer_text)


@app.post("/analyze/stream", dependencies=[Depends(require_api_key)])
async def analyze_stream(
    request: Request,
    offer_text: str = Form(),
    cv_text: str | None = Form(default=None),
    cv_file: UploadFile | None = File(default=None),
) -> StreamingResponse:
    """Comme /analyze, avec l'avancement en direct (text/event-stream).

    Événements : `progress` {step, label, done, total}, puis `result` (AnalysisResult) ou `error` {detail}.
    Les erreurs de saisie, de taille ou de débit sont renvoyées AVANT le flux, en JSON (422, 413, 429).
    """
    cv = await _cv_from_form(cv_file, cv_text)
    _admit(request, cv, offer_text)
    return StreamingResponse(
        _stream_analysis(cv, offer_text),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/score", response_model=ScoreResult, dependencies=[Depends(require_api_key)])
def score_endpoint(req: ScoreRequest) -> ScoreResult:
    """Score final pour un choix de reformulations (sans LLM) : à rappeler à chaque case cochée."""
    return compute_score(req.assessments, Settings().scoring, "final", set(req.approved_ids))


@app.post("/report", response_class=PlainTextResponse, dependencies=[Depends(require_api_key)])
def report_endpoint(req: ReportRequest) -> str:
    """Rapport Markdown reflétant les reformulations retenues (sans LLM)."""
    approved = set(req.approved_ids) & {s.id for s in req.result.suggestions}
    final = compute_score(req.result.assessments, Settings().scoring, "final", approved)
    return render_markdown(req.result.model_copy(update={"approved_ids": sorted(approved), "score_final": final}))
