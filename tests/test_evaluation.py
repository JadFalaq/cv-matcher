import json

from cvmatch.taxonomy import default_taxonomy
from evaluation.baselines import build_idf, tfidf_cosine
from evaluation.run_eval import main, spearman
from evaluation.synthetic import (
    CONTEXTS,
    FILLERS,
    IMPLICIT_TEMPLATES,
    MISSIONS,
    MUST_PREFIX,
    NICE_PREFIX,
    VISIBLE_TEMPLATES,
    generate_cases,
    make_perturbed_case,
    truth_status,
)

from tests.conftest import ROOT


def test_generator_vocabulary_never_leaks_skills():
    """Si un gabarit contenait un terme du référentiel, il fausserait précision et vérité terrain."""
    tax = default_taxonomy()
    texts = [*FILLERS, *MISSIONS, *MUST_PREFIX, *NICE_PREFIX, *CONTEXTS]
    texts += [t.format(t="xx", c="") for t in VISIBLE_TEMPLATES + IMPLICIT_TEMPLATES]
    texts += ["Élève ingénieur en dernière année, à la recherche d'un stage de fin d'études.", "Rigueur et curiosité"]
    for text in texts:
        assert tax.find_in_text(text) == [], text


def test_generator_is_deterministic_and_covers_all_statuses(sample_cv):
    a = generate_cases(40, seed=3, mode="both", base_cv=sample_cv)
    b = generate_cases(40, seed=3, mode="both", base_cv=sample_cv)
    assert [(c.cv_text, c.offer_text) for c in a] == [(c.cv_text, c.offer_text) for c in b]
    assert {e.status for c in a for e in c.expected} == {"visible", "hidden", "implicit", "absent"}
    assert {c.mode for c in a} == {"templated", "perturb"}


def test_truth_is_recomputed_from_the_final_cv(sample_cv):
    import random

    tax = default_taxonomy()
    case = make_perturbed_case(random.Random(5), tax, sample_cv, "p", n_offer=8)
    for e in case.expected:
        assert e.status == truth_status(case.cv_text, tax.get(e.skill_id), e.offer_term)


def test_spearman():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert spearman([1, 2], [1, 2]) is None  # trop peu de points


def test_tfidf_baseline_prefers_the_closer_document():
    docs = ["python docker fastapi mlflow", "cuisine jardinage voyage", "python docker kubernetes"]
    idf = build_idf(docs)
    assert tfidf_cosine(docs[0], docs[2], idf) > tfidf_cosine(docs[0], docs[1], idf)


def test_run_eval_smoke_offline(tmp_path):
    rc = main(["--n", "8", "--provider", "fake", "--base-cv", str(ROOT / "data" / "sample_cv.md"), "--out", str(tmp_path)])
    assert rc == 0
    data = json.loads((tmp_path / "eval_fake_both.json").read_text(encoding="utf-8"))
    m = data["metrics"]
    assert m["n_cases"] == 8 and m["hallucinated_quote_rate"] == 0
    assert m["status_accuracy"] >= 0.95 and m["extraction"]["f1"] >= 0.95
    assert "LLM factice" in (tmp_path / "eval_fake_both.md").read_text(encoding="utf-8")
