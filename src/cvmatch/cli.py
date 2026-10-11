"""Ligne de commande : `cvmatch --cv mon_cv.pdf --offer offre.txt`."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .config import Settings
from .ingestion import read_document
from .pipeline import analyze


def _interactive_review(suggestions: list[dict]):
    print("\n=== Validation des reformulations ===")
    approved: list[str] = []
    for i, s in enumerate(suggestions, 1):
        print(f"\n[{i}/{len(suggestions)}] {s['skill_name']} (+{s['gain']:g} pts)")
        print(f"  Avant : {s['original']}")
        print(f"  Après : {s['rewrite']}")
        answer = input("  Appliquer ? [o]ui / [N]on / [t]outes les restantes / [a]ucune : ").strip().lower()
        if answer in ("t", "tout", "toutes"):
            approved += [x["id"] for x in suggestions[i - 1 :]]
            break
        if answer in ("a", "aucune"):
            break
        if answer in ("o", "oui", "y", "yes"):
            approved.append(s["id"])
    return approved


def main(argv: list[str] | None = None) -> int:
    try:  # sortie UTF-8 même sur les consoles Windows
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    p = argparse.ArgumentParser(prog="cvmatch", description="Adapter son CV à une offre, compétence par compétence.")
    p.add_argument("--cv", required=True, help="CV (.pdf, .txt ou .md)")
    p.add_argument("--offer", required=True, help="Offre d'emploi (.txt, .md ou .pdf)")
    p.add_argument("--out", help="Fichier Markdown de sortie (sinon : affichage)")
    p.add_argument("--json", dest="json_out", help="Fichier JSON de sortie (résultat complet)")
    p.add_argument("--review", action="store_true", help="Valider les reformulations une par une")
    p.add_argument("--provider", help="Surcharge LLM_PROVIDER (fake, azure, openai, anthropic, ollama)")
    args = p.parse_args(argv)

    settings = Settings.from_env()
    if args.provider:
        settings = replace(settings, llm_provider=args.provider)
    if settings.llm_provider == "fake":
        print(
            "[mode démo] LLM factice à règles : résultats limités aux compétences du référentiel. "
            "Configure LLM_PROVIDER pour un vrai modèle.\n",
            file=sys.stderr,
        )

    result = analyze(
        read_document(args.cv),
        read_document(args.offer),
        settings=settings,
        review=_interactive_review if args.review else None,
    )

    if args.out:
        Path(args.out).write_text(result.report_md, encoding="utf-8")
        print(f"Rapport écrit dans {args.out}")
    else:
        print(result.report_md)
    if args.json_out:
        Path(args.json_out).write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"JSON écrit dans {args.json_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
