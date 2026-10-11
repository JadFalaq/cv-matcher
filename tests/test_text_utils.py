from cvmatch.text_utils import (
    contains_term,
    find_quote,
    normalize,
    numbers_in,
    original_surface,
    slugify,
    tokenize,
)


def test_normalize_accents_and_ligatures():
    assert normalize("Mise en œuvre d’Éléments") == "mise en oeuvre d'elements"


def test_contains_term_respects_word_boundaries():
    assert contains_term("Développement en C++, Java", "c++")
    assert contains_term("Node.js et CI/CD", "ci/cd")
    assert contains_term("scikit-learn", "scikit learn")
    assert not contains_term("Pages HTML", "ml")  # « ml » dans « html »
    assert not contains_term("javascript", "java")
    assert not contains_term("", "python")


def test_find_quote_is_tolerant_to_punctuation_but_not_to_invention():
    src = "- Python, SQL, Git, Linux\n- Conteneurisation avec Docker."
    assert find_quote("Python, SQL", src)
    assert find_quote("python sql git linux", src)
    assert find_quote("Conteneurisation avec Docker", src)
    assert not find_quote("Expert Python certifié", src)
    assert not find_quote("Python, Rust", src)
    assert not find_quote(None, src)
    assert not find_quote("", src)


def test_original_surface_keeps_offer_casing():
    assert original_surface("Maîtrise du RAG et de l'API REST.", "rag") == "RAG"
    assert original_surface("Maîtrise du RAG et de l'API REST.", "api rest") == "API REST"
    assert original_surface("Un bon Esprit d'équipe", "esprit d'équipe") == "Esprit d'équipe"
    assert original_surface("Python et C++", "c++") == "C++"
    assert original_surface("rien ici", "docker") is None


def test_slugify():
    assert slugify("C++") == "cpp"
    assert slugify("CI/CD") == "ci-cd"
    assert slugify("Deep Learning") == "deep-learning"


def test_numbers_in():
    assert numbers_in("5 000 images, +12,5 % et 3.2") == {"5", "000", "12,5", "3.2"}


def test_tokenize_drops_stopwords_and_plurals():
    assert tokenize("Les modèles de langages") == ["modele", "langage"]


def test_strip_qualifiers_keeps_real_skill_names():
    from cvmatch.text_utils import strip_qualifiers

    assert strip_qualifiers("Excellente maîtrise de Python") == "Python"
    assert strip_qualifiers("Connaissance d'Azure") == "Azure"
    assert strip_qualifiers("Un plus : expérience en Kubernetes") == "Kubernetes"
    for untouched in ("Deep learning", "Python", "API REST", "Data engineering", "Connaissance", "Expertise"):
        assert strip_qualifiers(untouched) == untouched
    assert strip_qualifiers("Connaissances deep learning") == "Connaissances deep learning"  # pas de « de » collé à « deep »
