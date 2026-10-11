"""Propriétés attendues d'un bon système de score (tests sans annotation)."""

import random
import re

from cvmatch.config import Settings
from cvmatch.fake_llm import RuleBasedLLM
from cvmatch.pipeline import analyze
from cvmatch.text_utils import find_quote


def run(cv, offer):
    return analyze(cv, offer, llm=RuleBasedLLM(), settings=Settings())


def test_monotonicity_adding_evidence_never_lowers_the_score(sample_cv, sample_offer):
    base = run(sample_cv, sample_offer)
    absent = [a for a in base.assessments if a.status == "absent"]
    assert absent
    for a in absent:
        term = a.requirement.offer_terms[0]
        cv2 = sample_cv + f"\n\n**Projet ajouté**\n- Réalisation d'un prototype avec {term}.\n"
        r2 = run(cv2, sample_offer)
        assert r2.score_actual.score >= base.score_actual.score, term
        status = next(x for x in r2.assessments if x.requirement.id == a.requirement.id).status
        assert status == "visible", term


def test_section_order_invariance(sample_cv, sample_offer):
    base = run(sample_cv, sample_offer)
    head, *sections = re.split(r"\n(?=## )", sample_cv)
    rng = random.Random(0)
    for _ in range(5):
        rng.shuffle(sections)
        r2 = run("\n".join([head, *sections]), sample_offer)
        assert r2.score_actual.score == base.score_actual.score
        assert {a.requirement.id: a.status for a in r2.assessments} == {a.requirement.id: a.status for a in base.assessments}


def test_same_input_same_output(sample_cv, sample_offer):
    a, b = run(sample_cv, sample_offer), run(sample_cv, sample_offer)
    assert a.model_dump() == b.model_dump()


def test_no_hallucinated_evidence_ever(sample_cv, sample_offer):
    for cv in (sample_cv, sample_cv.upper(), sample_cv.replace("Docker", "Dôcker")):
        for a in run(cv, sample_offer).assessments:
            assert a.status == "absent" or find_quote(a.evidence_quote, cv)


def test_score_bounds_and_ordering(sample_cv, sample_offer):
    r = run(sample_cv, sample_offer)
    assert 0 <= r.score_actual.score <= r.score_final.score <= r.score_potential.score <= 100
