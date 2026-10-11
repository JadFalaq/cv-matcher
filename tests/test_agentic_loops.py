"""Les boucles agentiques et les garde-fous, testés avec un LLM qui se trompe ou ment volontairement."""

from cvmatch.config import Settings
from cvmatch.fake_llm import RuleBasedLLM
from cvmatch.pipeline import analyze
from cvmatch.schemas import ExhaustivityCheck, ExtractionResult, JudgeVerdict, RequirementDraft, Summary
from tests.helpers import ScriptedLLM

OFFER_DOCKER = "Profil recherché (indispensable)\n- Maîtrise de Docker\n"
CV_DOCKER = "## Projets\n- Conteneurisation avec Docker et FastAPI.\n"

OFFER_DL = "Profil recherché (indispensable)\n- Connaissance du deep learning\n"
CV_DL = "## Projets\n- Réseaux de neurones, apprentissage profond sur 5 000 images.\n"


def run(llm, cv, offer, **kw):
    return analyze(cv, offer, llm=llm, settings=kw.pop("settings", Settings()), **kw)


def only(result):
    [a] = result.assessments
    return a


# ======================================================== boucle d'exhaustivité ===
def test_exhaustivity_loop_recovers_skills_the_first_pass_missed(sample_cv, sample_offer):
    def lazy_extract(n, schema, ctx):
        return schema(requirements=RuleBasedLLM()._extract(ctx["offer_text"])[:1])  # n'extrait qu'une compétence

    llm = ScriptedLLM({"extract": lazy_extract})
    r = run(llm, sample_cv, sample_offer)
    assert len(r.requirements) == 16
    assert llm.calls["exhaustivity"] == 2  # 1er passage : 15 trouvées -> on reboucle ; 2e : plus rien


def test_exhaustivity_loop_is_bounded(sample_cv, sample_offer):
    def always_something_new(n, schema, ctx):
        return schema(missing=[RequirementDraft(name=f"inconnue-{n}")])

    llm = ScriptedLLM({"exhaustivity": always_something_new})
    settings = Settings(max_verify_rounds=2)
    r = run(llm, sample_cv, sample_offer, settings=settings)
    assert llm.calls["exhaustivity"] == 2  # jamais de boucle infinie
    assert len(r.requirements) == 16 + 2


# ================================================ boucle juge <-> vérification ===
FABRICATED = "Expert Docker certifié par Google"


def test_fabricated_quote_triggers_a_retry_then_succeeds():
    def liar_then_honest(n, schema, ctx):
        if n == 1:
            return schema(status="visible", evidence_quote=FABRICATED, reasoning="j'invente")

    llm = ScriptedLLM({"judge": liar_then_honest})
    a = only(run(llm, CV_DOCKER, OFFER_DOCKER))
    assert llm.calls["judge"] == 2 and a.attempts == 2
    assert a.status == "visible" and "Docker" in a.evidence_quote and a.verified


def test_persistent_liar_is_contained_never_trusted():
    llm = ScriptedLLM({"judge": lambda n, schema, ctx: schema(status="visible", evidence_quote=FABRICATED)})
    a = only(run(llm, CV_DOCKER, OFFER_DOCKER))
    assert llm.calls["judge"] == Settings().max_judge_retries + 1
    assert a.status == "absent" and a.evidence_quote is None  # jamais de preuve inventée dans le rapport
    assert a.needs_review and not a.verified


def test_wrongly_absent_is_corrected_on_retry():
    llm = ScriptedLLM({"judge": lambda n, schema, ctx: schema(status="absent") if n == 1 else None})
    a = only(run(llm, CV_DOCKER, OFFER_DOCKER))
    assert llm.calls["judge"] == 2 and a.status == "visible" and not a.needs_review


def test_persistently_wrong_absent_falls_back_to_lexical_evidence():
    llm = ScriptedLLM({"judge": lambda n, schema, ctx: schema(status="absent")})
    a = only(run(llm, CV_DOCKER, OFFER_DOCKER))
    assert a.status == "visible" and "Docker" in a.evidence_quote and a.needs_review


def test_invented_number_in_rewrite_is_rejected_then_fixed():
    quote = "Réseaux de neurones, apprentissage profond sur 5 000 images."

    def inventive(n, schema, ctx):
        if n == 1:
            return schema(status="hidden", evidence_quote=quote, suggested_rewrite="Deep learning sur 5 000 images, +40% de précision")

    llm = ScriptedLLM({"judge": inventive})
    a = only(run(llm, CV_DL, OFFER_DL))
    assert llm.calls["judge"] == 2 and a.status == "hidden" and a.rewrite_ok
    assert "40" not in a.suggested_rewrite and "deep learning" in a.suggested_rewrite


def test_persistently_bad_rewrite_is_dropped_but_status_kept():
    quote = "Réseaux de neurones, apprentissage profond sur 5 000 images."
    bad = lambda n, schema, ctx: schema(status="hidden", evidence_quote=quote, suggested_rewrite="Deep learning, +40% de précision")
    r = run(ScriptedLLM({"judge": bad}), CV_DL, OFFER_DL)
    a = only(r)
    assert a.status == "hidden" and a.suggested_rewrite is None and not a.rewrite_ok
    assert r.suggestions == [] and r.score_potential.score == r.score_actual.score  # pas de gain sans reformulation valide


def test_overconfident_visible_is_downgraded_by_code():
    quote = "Réseaux de neurones, apprentissage profond sur 5 000 images."
    llm = ScriptedLLM({"judge": lambda n, schema, ctx: schema(status="visible", evidence_quote=quote) if n == 1 else None})
    a = only(run(llm, CV_DL, OFFER_DL))
    assert a.status == "hidden" and a.attempts == 2  # « visible » refusé : le terme de l'offre n'est pas dans la preuve


# ============================================================== autres pannes ===
def test_summary_failure_does_not_break_the_analysis(sample_cv, sample_offer):
    def boom(n, schema, ctx):
        raise RuntimeError("API indisponible")

    r = run(ScriptedLLM({"summary": boom}), sample_cv, sample_offer)
    assert r.summary is None and r.score_actual.score > 0 and "# Analyse" in r.report_md


def test_llm_summary_is_included_when_available(sample_cv, sample_offer):
    r = run(RuleBasedLLM(), sample_cv, sample_offer)
    assert isinstance(r.summary, Summary) and "Score actuel" in r.report_md


def test_absent_is_checked_against_the_whole_cv_not_only_retrieved_chunks():
    # top_k=1 : le bloc d'outils (déclencheurs implicites de python) est mieux classé que la ligne qui
    # contient « Python » ; un « absent » ne doit pas être accepté pour autant.
    offer = "Profil recherché (indispensable)\n- Maîtrise de Python\n"
    cv = (
        "## Outils\n- pandas, numpy, pytorch, fastapi, flask, jupyter\n\n"
        "## Expérience\n- Développement de scripts d'automatisation en Python pour l'équipe support, "
        "documentation, revue de code et maintenance applicative au quotidien.\n"
    )
    llm = ScriptedLLM({"judge": lambda n, schema, ctx: schema(status="absent") if n == 1 else None})
    a = only(run(llm, cv, offer, settings=Settings(top_k=1)))
    assert a.status == "visible" and "Python" in a.evidence_quote


def test_parallel_skill_assessment_respects_max_concurrency(sample_cv, sample_offer):
    import threading
    import time

    lock, state = threading.Lock(), {"now": 0, "peak": 0}

    def slow_judge(n, schema, ctx):
        with lock:
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
        time.sleep(0.02)
        with lock:
            state["now"] -= 1
        return None  # puis réponse normale du LLM factice

    r = run(ScriptedLLM({"judge": slow_judge}), sample_cv, sample_offer, settings=Settings(max_concurrency=3))
    assert len(r.assessments) == 16 and 1 < state["peak"] <= 3


def test_one_failing_skill_does_not_block_the_analysis(sample_cv, sample_offer):
    class RateLimitError(Exception):  # même nom que l'erreur du SDK OpenAI
        pass

    def flaky(n, schema, ctx):
        if ctx["requirement"]["id"] == "docker":
            raise RateLimitError("429")

    r = run(ScriptedLLM({"judge": flaky}), sample_cv, sample_offer)
    failed = [a for a in r.assessments if a.attempts == 0]
    assert [a.requirement.id for a in failed] == ["docker"]
    assert failed[0].status == "absent" and failed[0].needs_review and not failed[0].verified
    assert len(r.assessments) == 16 and r.score_actual.score > 0


def test_invalid_key_still_stops_the_analysis(sample_cv, sample_offer):
    import pytest

    class AuthenticationError(Exception):
        pass

    def bad_key(n, schema, ctx):
        raise AuthenticationError("401")

    with pytest.raises(AuthenticationError):
        run(ScriptedLLM({"judge": bad_key}), sample_cv, sample_offer)
