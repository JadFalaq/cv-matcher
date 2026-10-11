"""Bout en bout sur l'exemple (CV + offre fictifs), avec le LLM factice."""

import pytest

from cvmatch.config import Settings
from cvmatch.fake_llm import RuleBasedLLM
from cvmatch.graph import RunContext, build_graph
from cvmatch.pipeline import analyze
from cvmatch.taxonomy import default_taxonomy
from cvmatch.text_utils import find_quote

EXPECTED = {
    "python": "visible",
    "docker": "visible",
    "git": "visible",
    "english": "visible",
    "sql": "visible",
    "deep-learning": "hidden",
    "mlops": "implicit",
    "rag": "implicit",
    "rest-api": "implicit",
    "computer-vision": "implicit",
    "llm": "absent",
    "langgraph": "absent",
    "langchain": "absent",
    "agentic-ai": "absent",
    "azure": "absent",
    "teamwork": "absent",
}


@pytest.fixture(scope="module")
def result(sample_cv, sample_offer):
    return analyze(sample_cv, sample_offer, llm=RuleBasedLLM(), settings=Settings())


def by_id(result):
    return {a.requirement.id: a for a in result.assessments}


def test_the_16_skills_are_found_with_the_right_status(result):
    got = {rid: a.status for rid, a in by_id(result).items()}
    assert got == EXPECTED


def test_importance_is_read_from_the_offer_structure(result):
    req = {r.id: r.importance for r in result.requirements}
    assert req["python"] == "must" and req["langgraph"] == "must"  # cité dans « Missions » ET « appréciées »
    assert req["langchain"] == "nice" and req["sql"] == "nice" and req["teamwork"] == "nice"


def test_offer_terms_keep_the_original_casing(result):
    terms = {r.id: r.offer_terms for r in result.requirements}
    assert "RAG" in terms["rag"] and "API REST" in terms["rest-api"]


def test_every_cited_evidence_exists_in_the_cv(result, sample_cv):
    for a in result.assessments:
        if a.status == "absent":
            assert a.evidence_quote is None
        else:
            assert find_quote(a.evidence_quote, sample_cv), a.requirement.id
            assert a.chunk_id and a.verified and not a.needs_review


def test_scores_are_ordered(result):
    assert 0 < result.score_actual.score < result.score_potential.score <= 100
    assert result.score_final.score == result.score_potential.score  # sans revue : tout est accepté


def test_suggestions_are_valid_and_explain_the_potential(result):
    gains = [s.gain for s in result.suggestions]
    assert gains == sorted(gains, reverse=True) and len(result.suggestions) == 5
    delta = result.score_potential.score - result.score_actual.score
    assert abs(sum(gains) - delta) < 0.5
    terms = {r.id: r.offer_terms for r in result.requirements}
    for s in result.suggestions:
        assert any(t.lower() in s.rewrite.lower() for t in terms[s.skill_id])
        assert s.rewrite != s.original


def test_ats_keywords_and_gaps(result):
    assert set(result.ats_keywords) == {"RAG", "API REST", "deep learning", "MLOps", "Computer vision"}
    assert [g.skill_id for g in result.gaps if g.importance == "must"] == ["agentic-ai", "azure", "langgraph", "llm"]


def test_report_is_complete(result):
    md = result.report_md
    assert md.startswith("# Analyse CV ↔ offre") and "## Lacunes" in md and "## Reformulations proposées" in md
    for a in result.assessments:
        assert a.requirement.name in md


# --------------------------------------------------- validation humaine (interrupt) ---
def test_review_partial_approval(sample_cv, sample_offer):
    seen = []

    def review(suggestions):
        seen.append([s["id"] for s in suggestions])
        return [suggestions[0]["id"]]

    r = analyze(sample_cv, sample_offer, llm=RuleBasedLLM(), settings=Settings(), review=review)
    assert len(seen) == 1 and len(seen[0]) == 5  # le graphe s'est interrompu exactement une fois
    assert r.approved_ids == [seen[0][0]]
    assert r.score_actual.score < r.score_final.score < r.score_potential.score
    assert r.report_md.count("appliquée ✅") == 1


def test_review_reject_all_keeps_the_actual_score(sample_cv, sample_offer):
    r = analyze(sample_cv, sample_offer, llm=RuleBasedLLM(), settings=Settings(), review=lambda s: [])
    assert r.approved_ids == [] and r.score_final.score == r.score_actual.score


def test_review_accept_all_with_keyword(sample_cv, sample_offer):
    r = analyze(sample_cv, sample_offer, llm=RuleBasedLLM(), settings=Settings(), review=lambda s: "all")
    assert r.score_final.score == r.score_potential.score and len(r.approved_ids) == 5


def test_review_ignores_unknown_ids(sample_cv, sample_offer):
    r = analyze(sample_cv, sample_offer, llm=RuleBasedLLM(), settings=Settings(), review=lambda s: ["sg-nimporte-quoi"])
    assert r.approved_ids == []


# -------------------------------------------------------------------- cas limites ---
def test_offer_without_skills_does_not_crash(sample_cv):
    r = analyze(sample_cv, "Bienvenue chez nous.", llm=RuleBasedLLM(), settings=Settings())
    assert r.requirements == [] and r.score_actual.score == 0 and "# Analyse" in r.report_md


def test_empty_cv_gives_all_absent(sample_offer):
    r = analyze("", sample_offer, llm=RuleBasedLLM(), settings=Settings())
    assert {a.status for a in r.assessments} == {"absent"} and r.score_actual.score == 0


def test_graph_topology():
    ctx = RunContext(llm=RuleBasedLLM(), settings=Settings(), taxonomy=default_taxonomy())
    nodes = set(build_graph(ctx).get_graph().nodes)
    assert {
        "parse_offer", "verify_exhaustivity", "normalize_requirements", "index_cv",
        "dispatch", "assess_skill", "aggregate", "summarize", "human_review", "finalize",
    } <= nodes


def test_progress_callback_reports_every_skill_and_gives_same_result(sample_cv, sample_offer):
    events: list[str] = []
    totals: list[int] = []

    def on_progress(node, update):
        events.append(node)
        if node == "dispatch":
            totals.append(update["n_requirements"])

    approve_first = lambda suggestions: [suggestions[0]["id"]]
    plain = analyze(sample_cv, sample_offer, llm=RuleBasedLLM(), settings=Settings(), review=approve_first)
    streamed = analyze(
        sample_cv, sample_offer, llm=RuleBasedLLM(), settings=Settings(), review=approve_first, on_progress=on_progress
    )
    assert totals == [16] and events.count("assess_skill") == 16 and events[-1] == "finalize"
    assert streamed.model_dump() == plain.model_dump()
