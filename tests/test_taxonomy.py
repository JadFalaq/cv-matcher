import json

from cvmatch.config import Settings
from cvmatch.fake_llm import RuleBasedLLM
from cvmatch.pipeline import analyze
from cvmatch.taxonomy import Taxonomy


def names(tax, text):
    return [e.name for e, _ in tax.find_in_text(text)]


def test_synonyms_resolve_to_one_canonical_skill(taxonomy):
    for term in ("ML", "apprentissage automatique", "Machine Learning"):
        assert taxonomy.resolve(term).name == "machine learning"
    assert taxonomy.resolve("apprentissage profond").id == "deep-learning"
    assert taxonomy.resolve_id("COBOL") == "cobol"  # inconnue : slug


def test_longest_mention_wins_across_skills(taxonomy):
    # « machine learning operations » est un alias de MLOps : il ne doit PAS compter comme « machine learning »
    assert names(taxonomy, "Un plus : machine learning operations") == ["mlops"]
    assert names(taxonomy, "Déploiement d'API REST") == ["rest api"]


def test_two_separate_mentions_are_both_kept(taxonomy):
    assert names(taxonomy, "machine learning et MLOps") == ["machine learning", "mlops"]
    assert names(taxonomy, "machine learning operations puis du machine learning") == ["machine learning", "mlops"]


def test_terms_in_text_drops_included_and_duplicate_variants(taxonomy):
    docker = taxonomy.resolve("docker")
    assert taxonomy.terms_in_text(docker, "Docker, Docker Compose") == ["docker compose"]
    rag = taxonomy.resolve("rag")
    assert taxonomy.terms_in_text(rag, "retrieval-augmented generation") == ["retrieval augmented generation"]


def test_regression_offer_with_long_alias_yields_a_single_requirement():
    offer = "Profil recherché (indispensable)\n- Connaissance de machine learning operations\n"
    r = analyze("## Projets\n- Suivi des modèles avec MLflow.\n", offer, llm=RuleBasedLLM(), settings=Settings())
    assert [x.id for x in r.requirements] == ["mlops"]


def test_custom_taxonomy_from_json(tmp_path):
    f = tmp_path / "tax.json"
    f.write_text(
        json.dumps([{"name": "Terraform", "category": "tool", "aliases": ["IaC"], "implied_by": ["tfstate"]}]),
        encoding="utf-8",
    )
    tax = Taxonomy.from_json(f)
    assert tax.resolve("iac").name == "Terraform" and names(tax, "Infra as code avec IaC") == ["Terraform"]
