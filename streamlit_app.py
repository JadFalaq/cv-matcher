"""Interface web (Streamlit) : `streamlit run streamlit_app.py`.

Appelle directement le pipeline Python (pas besoin de l'API). Les secrets (clé Azure…) viennent des
variables d'environnement ou de `st.secrets` (Streamlit Community Cloud).
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))  # fonctionne aussi sans `pip install -e .`

st.set_page_config(page_title="cvmatch : adapte ton CV à une offre", page_icon="🎯", layout="wide")

try:  # Streamlit Cloud : les secrets deviennent des variables d'environnement
    for key, value in st.secrets.items():
        if isinstance(value, (str, int, float)):
            os.environ.setdefault(key, str(value))
except Exception:  # pas de secrets.toml : on reste sur l'environnement
    pass

from cvmatch.config import Settings  # noqa: E402
from cvmatch.ingestion import read_bytes  # noqa: E402
from cvmatch.limits import InputTooLarge, Limits, UsageGuard, check_sizes  # noqa: E402
from cvmatch.pipeline import analyze  # noqa: E402
from cvmatch.report import STATUS_BADGES, action_label, render_markdown  # noqa: E402
from cvmatch.schemas import AnalysisResult  # noqa: E402
from cvmatch.scoring import compute_score  # noqa: E402

log = logging.getLogger("cvmatch.ui")
# Journal du terminal : avancement, essais et erreurs (jamais le contenu du CV).
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
logging.getLogger("cvmatch").setLevel(logging.INFO)
logging.getLogger("openai._base_client").setLevel(logging.INFO)  # « Retrying request … in N seconds » (429, délais)

STEPS = {
    "parse_offer": "Lecture de l'offre",
    "index_cv": "Découpage et indexation du CV",
    "verify_exhaustivity": "Contrôle d'exhaustivité des compétences",
    "normalize_requirements": "Normalisation des compétences",
    "aggregate": "Calcul des scores",
    "summarize": "Rédaction de la synthèse",
    "finalize": "Finalisation",
}


@st.cache_resource
def usage_guard() -> UsageGuard:
    """Un seul compteur pour toutes les sessions du serveur."""
    return UsageGuard(Limits.from_env())


def client_id() -> str:
    headers = getattr(st.context, "headers", None) or {}
    forwarded = headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    ip = getattr(st.context, "ip_address", None)
    return ip or st.session_state.setdefault("session_id", uuid.uuid4().hex)


def load_sample() -> None:
    st.session_state.cv_text = (ROOT / "data" / "sample_cv.md").read_text(encoding="utf-8")
    st.session_state.offer_text = (ROOT / "data" / "sample_offer.txt").read_text(encoding="utf-8")
    st.session_state.pop("result", None)


# ======================================================================= barre latérale ===
settings = Settings.from_env()
limits = Limits.from_env()

with st.sidebar:
    st.header("🎯 cvmatch")
    st.write(
        "Pour chaque compétence de l'offre, cvmatch cherche la **preuve** dans ton CV, propose des "
        "**reformulations** de tes propres lignes et liste honnêtement tes **lacunes**. Il n'invente jamais d'expérience."
    )
    st.markdown(
        "- ✅ **Visible** : mots exacts de l'offre\n"
        "- 🟡 **Cachée** : prouvée avec d'autres mots\n"
        "- 🟠 **Implicite** : se déduit d'un outil ou projet\n"
        "- ❌ **Absente** : aucune preuve"
    )
    st.divider()
    st.caption(
        "**Comment ça marche** : LangGraph orchestre l'extraction, puis une branche par compétence "
        "(RAG BM25 → juge LLM → vérification). Chaque citation est vérifiée mot pour mot dans le CV "
        "et le score est calculé par du code, pas par le LLM."
    )
    if url := os.getenv("GITHUB_URL"):
        st.markdown(f"[Code source sur GitHub]({url})")
    st.divider()
    st.caption(
        "🔒 **Confidentialité** : ton CV est traité en mémoire et n'est pas conservé. "
        + ("Il est envoyé à Azure OpenAI pour l'analyse." if settings.llm_provider == "azure" else "")
    )

# ============================================================================ saisie ===
st.title("Adapte ton CV à une offre, compétence par compétence")
if settings.llm_provider == "fake":
    st.info("Mode démo : LLM factice à règles (aucune clé configurée). Les résultats sont limités au référentiel.")

st.button("Charger un exemple (CV et offre fictifs)", on_click=load_sample)

col_cv, col_offer = st.columns(2)
with col_cv:
    st.subheader("Ton CV")
    upload = st.file_uploader("PDF, Markdown ou texte", type=["pdf", "md", "txt"], key="cv_file")
    cv_text = st.text_area("…ou colle-le ici", key="cv_text", height=260, disabled=upload is not None)
with col_offer:
    st.subheader("L'offre d'emploi")
    offer_text = st.text_area("Colle le texte de l'offre", key="offer_text", height=330)

access_code = os.getenv("APP_ACCESS_CODE")
code_ok = True
if access_code:
    code_ok = st.text_input("Code d'accès", type="password") == access_code

if st.button("Analyser", type="primary", disabled=not code_ok):
    try:
        if upload is not None:
            cv_text = read_bytes(upload.getvalue(), upload.name, max_pages=limits.max_pdf_pages)
        if len(cv_text.strip()) < 20 or len(offer_text.strip()) < 20:
            st.error("Il faut un CV et une offre (au moins quelques lignes chacun). Un PDF scanné ne contient pas de texte.")
            st.stop()
        check_sizes(cv_text, offer_text, limits)
    except InputTooLarge as exc:
        st.error(str(exc))
        st.stop()
    except Exception:
        st.error("Impossible de lire ce fichier. Essaie un autre format ou colle le texte.")
        st.stop()

    refused = usage_guard().acquire(client_id())
    if refused:
        st.warning(refused)
        st.stop()

    with st.status("Analyse en cours…", expanded=True) as status:
        bar = st.progress(0.0, text="Démarrage")
        progress = {"total": 0, "done": 0}

        def on_progress(node: str, update: dict) -> None:
            if node == "dispatch":
                progress["total"] = update.get("n_requirements", 0)
                st.write(f"{progress['total']} compétences trouvées dans l'offre, évaluation en parallèle…")
            elif node == "assess_skill":
                progress["done"] += 1
                total = max(progress["total"], 1)
                bar.progress(0.15 + 0.75 * progress["done"] / total, text=f"Compétence {progress['done']}/{total} vérifiée")
            elif node in STEPS:
                st.write(f"✓ {STEPS[node]}")

        started = time.monotonic()
        try:
            result = analyze(cv_text, offer_text, settings=settings, on_progress=on_progress)
            log.info("Analyse terminée en %.1f s (%d compétences)", time.monotonic() - started, len(result.assessments))
        except Exception as exc:
            log.error("Échec de l'analyse : %s", type(exc).__name__)  # jamais le contenu du CV
            status.update(label="Échec de l'analyse", state="error")
            st.error("L'analyse a échoué (fournisseur LLM indisponible ou mal configuré). Réessaie dans un instant.")
            st.stop()
        bar.progress(1.0, text="Terminé")
        status.update(label="Analyse terminée", state="complete", expanded=False)
    st.session_state.result = result.model_dump()

# ========================================================================= résultats ===
if "result" not in st.session_state:
    st.stop()

result = AnalysisResult.model_validate(st.session_state.result)
st.divider()

not_assessed = [a.requirement.name for a in result.assessments if a.attempts == 0]  # 0 = aucun verdict obtenu
if not_assessed:
    st.warning(
        f"{len(not_assessed)} compétence(s) n'ont pas pu être évaluées (quota ou délai du fournisseur LLM) : "
        + ", ".join(not_assessed)
        + ". Elles sont comptées comme absentes ; relance l'analyse dans une minute."
    )

if result.summary:
    st.subheader(result.summary.headline)
    left, right = st.columns(2)
    with left:
        st.markdown("**Points forts**\n" + "\n".join(f"- {s}" for s in result.summary.strengths))
    with right:
        st.markdown("**Priorités**\n" + "\n".join(f"- {s}" for s in result.summary.priorities))

metrics_slot = st.container()  # rempli plus bas : dépend des cases cochées dans l'onglet Reformulations
tab_cov, tab_rw, tab_gaps, tab_dl = st.tabs(["Couverture", "Reformulations", "Lacunes et mots-clés", "Télécharger"])

with tab_rw:
    approved: set[str] = set()
    if not result.suggestions:
        st.write("Aucune reformulation proposée : rien de caché à faire ressortir.")
    for s in result.suggestions:
        with st.container(border=True):
            if st.checkbox(f"**{s.skill_name}** (+{s.gain:g} pts)", value=True, key=f"ok-{s.id}"):
                approved.add(s.id)
            st.markdown(f"**Avant** : {s.original}")
            st.markdown(f"**Après** : {s.rewrite}")
    st.caption("Décoche une reformulation si elle ne te ressemble pas : le score final se met à jour.")

final = compute_score(result.assessments, settings.scoring, "final", approved)
final_result = result.model_copy(update={"approved_ids": sorted(approved), "score_final": final})

m1, m2, m3, m4 = metrics_slot.columns(4)
m1.metric("Score actuel", f"{result.score_actual.score:g}/100")
m2.metric("Avec tes choix", f"{final.score:g}/100", delta=f"{final.score - result.score_actual.score:+.1f}")
m3.metric("Potentiel max", f"{result.score_potential.score:g}/100")
m4.metric("Indispensables couverts", f"{result.score_actual.must_coverage:.0%}")

with tab_cov:
    rows = [
        {
            "Compétence": a.requirement.name,
            "Importance": "indispensable" if a.requirement.importance == "must" else "souhaitée",
            "Statut": STATUS_BADGES[a.status] + (" ⚠" if a.needs_review else ""),
            "Preuve dans le CV": a.evidence_quote or "—",
            "Action": action_label(a),
        }
        for a in result.assessments
    ]
    st.dataframe(rows, width="stretch", hide_index=True)
    flagged = [a for a in result.assessments if a.needs_review]
    if flagged:
        st.caption("⚠ = verdict à vérifier : " + " ".join(f"**{a.requirement.name}** : {' '.join(a.notes)}" for a in flagged))

with tab_gaps:
    if result.ats_keywords:
        st.markdown("**Mots-clés de l'offre à intégrer** (uniquement pour des compétences que tu as déjà)")
        st.write(", ".join(result.ats_keywords))
    if result.gaps:
        st.markdown("**Lacunes** : aucune preuve dans le CV, rien à inventer")
        for g in result.gaps:
            level = "indispensable" if g.importance == "must" else "souhaitée"
            st.markdown(f"- **{g.skill_name}** ({level})" + (f" : « {g.offer_quote} »" if g.offer_quote else ""))
        st.caption("Pour une lacune importante : un mini-projet ou une formation courte, à ajouter au CV une fois réalisé.")

with tab_dl:
    report = render_markdown(final_result)
    c1, c2 = st.columns(2)
    c1.download_button("Rapport Markdown", report, file_name="cvmatch_rapport.md", mime="text/markdown")
    c2.download_button(
        "Résultat complet (JSON)",
        final_result.model_dump_json(indent=2),
        file_name="cvmatch_resultat.json",
        mime="application/json",
    )
    with st.expander("Aperçu du rapport"):
        st.markdown(report)
