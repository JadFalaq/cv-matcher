"""Évaluation automatique par perturbation contrôlée.

    python -m evaluation.run_eval --n 30 --mode both --base-cv data/sample_cv.md
    python -m evaluation.run_eval --n 50 --provider azure      # vrai LLM : les chiffres qui comptent

Sorties : tableau dans le terminal + JSON et Markdown dans evaluation/results/.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from cvmatch.config import Settings
from cvmatch.llm import get_llm
from cvmatch.pipeline import analyze
from cvmatch.schemas import AnalysisResult, Assessment, Requirement
from cvmatch.scoring import compute_score
from cvmatch.text_utils import find_quote

from .baselines import build_idf, direct_llm, tfidf_cosine
from .synthetic import SyntheticCase, generate_cases

STATUSES = ["visible", "hidden", "implicit", "absent"]


# ------------------------------------------------------------------ utilitaires ---
def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def truth_score(case: SyntheticCase, settings: Settings) -> float:
    items = [
        Assessment(
            requirement=Requirement(id=e.skill_id, name=e.skill_id, importance=e.importance, offer_terms=[e.offer_term]),  # type: ignore[arg-type]
            status=e.status,  # type: ignore[arg-type]
            rewrite_ok=e.status in ("hidden", "implicit"),
        )
        for e in case.expected
    ]
    return compute_score(items, settings.scoring, "actual").score


# ------------------------------------------------------------------ par cas ---
def evaluate_case(case: SyntheticCase, result: AnalysisResult, settings: Settings) -> dict:
    pred = {a.requirement.id: a for a in result.assessments}
    exp = {e.skill_id: e for e in case.expected}
    rows = []
    for sid, e in exp.items():
        p = pred.get(sid)
        rows.append(
            {
                "skill": sid,
                "expected": e.status,
                "predicted": p.status if p else "missing",
                "importance_ok": bool(p and p.requirement.importance == e.importance),
            }
        )
    non_absent = [a for a in result.assessments if a.status != "absent"]
    return {
        "case_id": case.case_id,
        "mode": case.mode,
        "tp": len(set(pred) & set(exp)),
        "fp": len(set(pred) - set(exp)),
        "fn": len(set(exp) - set(pred)),
        "rows": rows,
        "quotes_checked": len(non_absent),
        "quotes_bad": sum(1 for a in non_absent if not find_quote(a.evidence_quote, case.cv_text)),
        "needs_review": sum(1 for a in result.assessments if a.needs_review),
        "retried": sum(1 for a in result.assessments if a.attempts > 1),
        "n_assessed": len(result.assessments),
        "truth_score": truth_score(case, settings),
        "pred_score": result.score_actual.score,
    }


# ----------------------------------------------------------------- agrégation ---
def aggregate(per_case: list[dict], baseline_scores: list[float], direct_acc: float | None) -> dict:
    tp = sum(c["tp"] for c in per_case)
    fp = sum(c["fp"] for c in per_case)
    fn = sum(c["fn"] for c in per_case)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    rows = [r for c in per_case for r in c["rows"]]
    confusion: dict[str, Counter] = {s: Counter() for s in STATUSES}
    for r in rows:
        confusion[r["expected"]][r["predicted"]] += 1
    acc = sum(1 for r in rows if r["expected"] == r["predicted"]) / len(rows) if rows else 0.0
    per_status = {
        s: (confusion[s][s] / sum(confusion[s].values()) if sum(confusion[s].values()) else None) for s in STATUSES
    }
    quotes = sum(c["quotes_checked"] for c in per_case)
    n_assessed = sum(c["n_assessed"] for c in per_case) or 1
    truth = [c["truth_score"] for c in per_case]
    pred = [c["pred_score"] for c in per_case]
    return {
        "n_cases": len(per_case),
        "n_skills_expected": len(rows),
        "extraction": {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)},
        "status_accuracy": round(acc, 3),
        "recall_per_status": {k: (round(v, 3) if v is not None else None) for k, v in per_status.items()},
        "importance_accuracy": round(sum(r["importance_ok"] for r in rows) / len(rows), 3) if rows else 0.0,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "hallucinated_quote_rate": round(sum(c["quotes_bad"] for c in per_case) / quotes, 4) if quotes else 0.0,
        "needs_review_rate": round(sum(c["needs_review"] for c in per_case) / n_assessed, 4),
        "retry_rate": round(sum(c["retried"] for c in per_case) / n_assessed, 4),
        "score_mae": round(sum(abs(a - b) for a, b in zip(pred, truth)) / len(truth), 2) if truth else None,
        "score_spearman_pipeline": spearman(pred, truth),
        "score_spearman_tfidf_baseline": spearman(baseline_scores, truth),
        "direct_llm_status_accuracy": direct_acc,
    }


def to_markdown(metrics: dict, provider: str, mode: str) -> str:
    m = metrics
    lines = [f"# Évaluation ({provider}, mode {mode})", ""]
    if provider == "fake":
        lines += [
            "> ⚠ LLM factice à règles : ces chiffres valident la plomberie (RAG, boucles, garde-fous, score),",
            "> pas la qualité d'un vrai LLM. Relance avec un vrai fournisseur pour mesurer le modèle.",
            "",
        ]
    lines += [
        f"{m['n_cases']} cas, {m['n_skills_expected']} compétences attendues.",
        "",
        "| Métrique | Valeur |",
        "|---|---|",
        f"| Extraction : précision / rappel / F1 | {m['extraction']['precision']} / {m['extraction']['recall']} / {m['extraction']['f1']} |",
        f"| Exactitude du statut (4 classes) | {m['status_accuracy']} |",
        f"| Exactitude de l'importance (must/nice) | {m['importance_accuracy']} |",
        f"| Citations introuvables dans le CV (hallucinations) | {m['hallucinated_quote_rate']:.2%} |",
        f"| Verdicts marqués « à vérifier » | {m['needs_review_rate']:.2%} |",
        f"| Verdicts ayant nécessité un 2e essai (boucle) | {m['retry_rate']:.2%} |",
        f"| Erreur absolue moyenne du score (points /100) | {m['score_mae']} |",
        f"| Spearman score pipeline vs vérité | {m['score_spearman_pipeline']} |",
        f"| Spearman baseline TF-IDF vs vérité | {m['score_spearman_tfidf_baseline']} |",
        f"| Exactitude baseline « 1 prompt LLM » | {m['direct_llm_status_accuracy'] if m['direct_llm_status_accuracy'] is not None else 'non exécutée'} |",
        "",
        "## Rappel par statut",
        "",
        "| Statut attendu | Rappel |",
        "|---|---|",
    ]
    lines += [f"| {s} | {v if v is not None else '—'} |" for s, v in m["recall_per_status"].items()]
    lines += ["", "## Matrice de confusion (lignes = attendu, colonnes = prédit)", "", "| attendu \\ prédit | " + " | ".join(STATUSES + ["missing"]) + " |", "|---|" + "---|" * 5]
    for s in STATUSES:
        lines.append(f"| {s} | " + " | ".join(str(m["confusion"][s].get(p, 0)) for p in STATUSES + ["missing"]) + " |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------ main ---
def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="evaluation.run_eval")
    p.add_argument("--n", type=int, default=30, help="nombre de cas")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mode", choices=["templated", "perturb", "both"], default="both")
    p.add_argument("--base-cv", default="data/sample_cv.md", help="CV réel anonymisé pour le mode perturb")
    p.add_argument("--provider", help="surcharge LLM_PROVIDER")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--direct-baseline", action="store_true", help="baseline « 1 prompt LLM » (vrai LLM requis)")
    p.add_argument("--out", default="evaluation/results")
    args = p.parse_args(argv)

    settings = Settings.from_env()
    if args.provider:
        settings = replace(settings, llm_provider=args.provider)
    llm = get_llm(settings)

    base_cv = Path(args.base_cv).read_text(encoding="utf-8") if args.mode in ("perturb", "both") else None
    cases = generate_cases(args.n, args.seed, args.mode, base_cv)

    def run(case: SyntheticCase) -> dict:
        return evaluate_case(case, analyze(case.cv_text, case.offer_text, llm=llm, settings=settings), settings)

    if args.workers > 1:
        with ThreadPoolExecutor(args.workers) as pool:
            per_case = list(pool.map(run, cases))
    else:
        per_case = [run(c) for c in cases]

    idf = build_idf([c.cv_text for c in cases] + [c.offer_text for c in cases])
    baseline = [tfidf_cosine(c.cv_text, c.offer_text, idf) for c in cases]

    direct_acc = None
    if args.direct_baseline:
        if settings.llm_provider == "fake":
            print("Baseline « 1 prompt LLM » ignorée : nécessite un vrai LLM.", file=sys.stderr)
        else:
            ok = total = 0
            for c in cases:
                answers = direct_llm(llm, c.cv_text, [e.offer_term for e in c.expected])
                for e in c.expected:
                    total += 1
                    ok += answers.get(e.offer_term.strip().lower()) == e.status
            direct_acc = round(ok / total, 3) if total else None

    metrics = aggregate(per_case, baseline, direct_acc)
    md = to_markdown(metrics, settings.llm_provider, args.mode)
    print(md)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"eval_{settings.llm_provider}_{args.mode}"
    (out / f"{stem}.json").write_text(json.dumps({"metrics": metrics, "cases": per_case}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / f"{stem}.md").write_text(md, encoding="utf-8")
    print(f"Résultats écrits dans {out}/{stem}.(json|md)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
