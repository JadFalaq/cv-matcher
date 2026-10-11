import random

from cvmatch.config import ScoringConfig
from cvmatch.schemas import Assessment, Requirement
from cvmatch.scoring import ats_keywords, build_suggestions, compute_score, find_gaps

CFG = ScoringConfig()
ORDER = ["absent", "implicit", "hidden", "visible"]  # du moins au plus couvert


def mk(status, imp="must", sid="x", rewrite_ok=None):
    if rewrite_ok is None:
        rewrite_ok = status in ("hidden", "implicit")
    return Assessment(
        requirement=Requirement(id=sid, name=sid, importance=imp, offer_terms=[sid.upper()]),
        status=status,
        evidence_quote=None if status == "absent" else "preuve",
        suggested_rewrite="réécriture" if rewrite_ok else None,
        rewrite_ok=rewrite_ok,
    )


def test_bounds_and_empty():
    assert compute_score([mk("visible"), mk("visible", sid="y")], CFG).score == 100
    assert compute_score([mk("absent")], CFG).score == 0
    assert compute_score([], CFG).score == 0


def test_weights_must_vs_nice():
    s = compute_score([mk("visible", "must", "a"), mk("absent", "nice", "b")], CFG)
    assert s.score == 75.0 and s.must_coverage == 1.0


def test_credits_actual_vs_potential():
    items = [mk("hidden")]
    assert compute_score(items, CFG, "actual").score == 60.0
    assert compute_score(items, CFG, "potential").score == 100.0
    assert compute_score([mk("implicit")], CFG, "potential").score == 85.0


def test_no_valid_rewrite_means_no_potential_gain():
    items = [mk("hidden", rewrite_ok=False)]
    assert compute_score(items, CFG, "potential").score == compute_score(items, CFG, "actual").score


def test_final_applies_only_approved_rewrites():
    items = [mk("hidden", sid="a"), mk("hidden", sid="b")]
    none = compute_score(items, CFG, "final", set()).score
    one = compute_score(items, CFG, "final", {"sg-a"}).score
    both = compute_score(items, CFG, "final", {"sg-a", "sg-b"}).score
    assert none == 60.0 < one < both == 100.0


def test_score_is_monotonic_when_a_status_improves():
    rng = random.Random(0)
    for _ in range(300):
        items = [mk(rng.choice(ORDER), rng.choice(["must", "nice"]), f"s{i}") for i in range(rng.randint(1, 10))]
        i = rng.randrange(len(items))
        better = ORDER[min(ORDER.index(items[i].status) + 1, 3)]
        upgraded = list(items)
        upgraded[i] = mk(better, items[i].requirement.importance, items[i].requirement.id)
        for mode in ("actual", "potential"):
            assert compute_score(upgraded, CFG, mode).score >= compute_score(items, CFG, mode).score


def test_potential_never_below_actual():
    rng = random.Random(1)
    for _ in range(100):
        items = [mk(rng.choice(ORDER), rng.choice(["must", "nice"]), f"s{i}") for i in range(6)]
        assert compute_score(items, CFG, "potential").score >= compute_score(items, CFG, "actual").score


def test_suggestions_sorted_by_gain_and_gain_adds_up():
    items = [mk("hidden", "must", "a"), mk("hidden", "nice", "b"), mk("visible", "must", "c")]
    sg = build_suggestions(items, CFG)
    assert [s.skill_id for s in sg] == ["a", "b"]
    assert sg[0].gain > sg[1].gain
    delta = compute_score(items, CFG, "potential").score - compute_score(items, CFG, "actual").score
    assert abs(sum(s.gain for s in sg) - delta) < 0.2


def test_ats_keywords_only_for_skills_the_candidate_has():
    items = [mk("hidden", sid="a"), mk("implicit", sid="b"), mk("absent", sid="c"), mk("visible", sid="d")]
    assert ats_keywords(items) == ["A", "B"]


def test_gaps_list_must_first():
    items = [mk("absent", "nice", "n"), mk("absent", "must", "m"), mk("visible", "must", "v")]
    assert [g.skill_id for g in find_gaps(items)] == ["m", "n"]
