import pytest

from cvmatch.schemas import CVChunk, JudgeVerdict, Requirement
from cvmatch.text_utils import slugify
from cvmatch.verification import build_assessment, normalize_requirements, verify_verdict

CHUNKS = [
    CVChunk(id="c01", section="Compétences", text="Python, SQL, Git, Linux"),
    CVChunk(
        id="c02",
        section="Projets",
        text="- Réseaux de neurones convolutionnels, apprentissage profond sur 5 000 images.\n- Exposition via FastAPI.",
    ),
]
DL_QUOTE = "Réseaux de neurones convolutionnels, apprentissage profond sur 5 000 images"


def req(name, terms=None, importance="must"):
    return Requirement(id=slugify(name), name=name, importance=importance, offer_terms=terms if terms is not None else [name])


def kinds(v):
    return [p.kind for p in v.problems]


# ----------------------------------------------------------------- citations ---
def test_fabricated_quote_is_rejected(taxonomy):
    v = verify_verdict(req("python"), JudgeVerdict(status="visible", evidence_quote="Expert Python certifié AWS"), CHUNKS, taxonomy)
    assert kinds(v) == ["quote"]


def test_real_quote_accepted(taxonomy):
    v = verify_verdict(req("python", ["Python"]), JudgeVerdict(status="visible", evidence_quote="Python, SQL, Git, Linux"), CHUNKS, taxonomy)
    assert not v.problems and v.status == "visible" and v.chunk.id == "c01"


# ----------------------------------------------- arbitrage visible / hidden ---
def test_visible_is_downgraded_when_offer_term_is_not_in_the_evidence(taxonomy):
    v = verify_verdict(req("deep learning"), JudgeVerdict(status="visible", evidence_quote=DL_QUOTE), CHUNKS, taxonomy)
    assert v.status == "hidden"
    assert kinds(v) == ["rewrite"]  # une reformulation devient nécessaire


def test_hidden_is_upgraded_when_offer_term_is_in_the_evidence(taxonomy):
    v = verify_verdict(req("python", ["Python"]), JudgeVerdict(status="hidden", evidence_quote="Python, SQL, Git, Linux"), CHUNKS, taxonomy)
    assert v.status == "visible" and not v.problems


# ------------------------------------------------------------------- absent ---
def test_absent_is_rejected_when_the_term_is_in_the_excerpts(taxonomy):
    v = verify_verdict(req("git"), JudgeVerdict(status="absent"), CHUNKS, taxonomy)
    assert kinds(v) == ["absent"] and v.lexical[0] == "visible"


def test_absent_is_fine_when_nothing_matches(taxonomy):
    v = verify_verdict(req("docker"), JudgeVerdict(status="absent"), CHUNKS, taxonomy)
    assert not v.problems and v.status == "absent"


# ------------------------------------------------------------ reformulations ---
def hidden(rewrite):
    return JudgeVerdict(status="hidden", evidence_quote=DL_QUOTE, suggested_rewrite=rewrite)


def test_rewrite_must_not_invent_numbers(taxonomy):
    v = verify_verdict(req("deep learning"), hidden("Deep learning sur 5 000 images avec un gain de 40 % de précision"), CHUNKS, taxonomy)
    assert "rewrite" in kinds(v) and "40" in v.problems[0].message


def test_rewrite_must_not_add_tools_missing_from_the_evidence(taxonomy):
    v = verify_verdict(req("deep learning"), hidden("Deep learning avec Kubernetes sur 5 000 images"), CHUNKS, taxonomy)
    assert any("kubernetes" in p.message.lower() for p in v.problems)


def test_rewrite_must_use_the_offer_vocabulary(taxonomy):
    v = verify_verdict(req("deep learning"), hidden("Réseaux de neurones convolutionnels sur 5 000 images"), CHUNKS, taxonomy)
    assert any("terme exact de l'offre" in p.message for p in v.problems)


def test_rewrite_must_differ_and_stay_short(taxonomy):
    same = verify_verdict(req("deep learning"), hidden(DL_QUOTE), CHUNKS, taxonomy)
    assert any("identique" in p.message for p in same.problems)
    long = verify_verdict(req("deep learning"), hidden("Deep learning " + DL_QUOTE + " " + "blabla " * 40), CHUNKS, taxonomy)
    assert any("plus longue" in p.message for p in long.problems)


def test_good_rewrite_is_accepted(taxonomy):
    v = verify_verdict(
        req("deep learning"), hidden("Réseaux de neurones convolutionnels, deep learning sur 5 000 images"), CHUNKS, taxonomy
    )
    assert not v.problems and v.rewrite_ok


# --------------------------------------------------------- repli en dernier recours ---
def test_final_fallback_never_keeps_a_fabricated_quote(taxonomy):
    a, fb = build_assessment(
        req("python"), JudgeVerdict(status="visible", evidence_quote="Expert Python certifié"), CHUNKS, taxonomy, attempts=3, final=True
    )
    assert fb == "" and a.status == "absent" and a.evidence_quote is None
    assert a.needs_review and not a.verified


def test_final_fallback_uses_lexical_evidence_when_llm_says_absent_wrongly(taxonomy):
    a, _ = build_assessment(req("git"), JudgeVerdict(status="absent"), CHUNKS, taxonomy, attempts=3, final=True)
    assert a.status == "visible" and a.needs_review and "Git" in a.evidence_quote


def test_not_final_returns_feedback_for_the_judge(taxonomy):
    a, feedback = build_assessment(
        req("python"), JudgeVerdict(status="visible", evidence_quote="inventé"), CHUNKS, taxonomy, attempts=1, final=False
    )
    assert a is None and "MOT POUR MOT" in feedback


# ------------------------------------------------------------ normalisation ---
def test_normalize_merges_duplicates_and_grounds_quotes(taxonomy):
    offer = "Profil\n- Notions de ML\n- machine learning requis\n"
    drafts = [
        {"name": "ML", "importance": "nice", "offer_terms": ["ML"], "offer_quote": "Notions de ML"},
        {"name": "machine learning", "importance": "must", "offer_terms": ["machine learning"], "offer_quote": "phrase inventée"},
    ]
    [r] = normalize_requirements(drafts, offer, taxonomy)
    assert r.id == "machine-learning" and r.importance == "must"
    assert set(r.offer_terms) == {"ML", "machine learning"}
    assert r.offer_quote == "Notions de ML"  # la citation inventée est écartée


def test_normalize_must_wins_whatever_the_order(taxonomy):
    offer = "Profil\n- machine learning requis\n- Notions de ML\n"
    must_first = [
        {"name": "machine learning", "importance": "must", "offer_terms": ["machine learning"]},
        {"name": "ML", "importance": "nice", "offer_terms": ["ML"]},
    ]
    [r] = normalize_requirements(must_first, offer, taxonomy)
    assert r.importance == "must"
    [r] = normalize_requirements(list(reversed(must_first)), offer, taxonomy)
    assert r.importance == "must"
    nice_only = [dict(d, importance="nice") for d in must_first]
    [r] = normalize_requirements(nice_only, offer, taxonomy)
    assert r.importance == "nice"


def test_normalize_drops_terms_absent_from_the_offer(taxonomy):
    offer = "Maîtrise de Python"
    [r] = normalize_requirements(
        [{"name": "python", "offer_terms": ["Python avancé", "Python"], "offer_quote": None}], offer, taxonomy
    )
    assert r.offer_terms == ["Python"]


def test_normalize_unknown_skill_gets_a_slug_id(taxonomy):
    offer = "Connaissance de COBOL"
    [r] = normalize_requirements([{"name": "COBOL", "offer_terms": ["COBOL"]}], offer, taxonomy)
    assert r.id == "cobol" and r.offer_terms == ["COBOL"]


@pytest.mark.parametrize(
    "offer_line, llm_term, expected",
    [  # termes réellement renvoyés par gpt-4.1-mini sur l'offre d'exemple
        ("- Excellente maîtrise de Python", "Excellente maîtrise de Python", "Python"),
        ("- Connaissance de SQL", "Connaissance de SQL", "SQL"),
        ("- Bonnes bases en MLOps", "Bonnes bases en MLOps", "MLOps"),
        ("- Expérience avec LangGraph ou LangChain", "Expérience avec LangGraph", "LangGraph"),
        ("- Connaissances en LLM et en deep learning", "Connaissances en LLM", "LLM"),
        ("- Strong experience with Kubernetes", "Strong experience with Kubernetes", "Kubernetes"),
        ("- Expérience avec COBOL", "Expérience avec COBOL", "COBOL"),  # hors référentiel aussi
    ],
)
def test_normalize_strips_qualifiers_from_offer_terms(taxonomy, offer_line, llm_term, expected):
    offer = f"Profil recherché\n{offer_line}\n"
    name = expected.lower()
    [r] = normalize_requirements([{"name": name, "offer_terms": [llm_term]}], offer, taxonomy)
    assert r.offer_terms == [expected]


def test_qualified_term_no_longer_downgrades_a_visible_skill(taxonomy):
    offer = "Profil recherché\n- Excellente maîtrise de Python\n"
    [req] = normalize_requirements([{"name": "python", "offer_terms": ["Excellente maîtrise de Python"]}], offer, taxonomy)
    chunk = CVChunk(id="c01", section="Compétences", text="Python, SQL, Git, Linux")
    verdict = JudgeVerdict(status="visible", evidence_quote="Python, SQL, Git, Linux")
    a, _ = build_assessment(req, verdict, [chunk], taxonomy, attempts=1, final=False)
    assert a.status == "visible"
