"use client";

import { useEffect, useMemo, useState } from "react";

import { getReport, getScore } from "@/lib/api";
import { skillName } from "@/lib/labels";
import type { AnalysisResult, ScoreResult } from "@/lib/types";

import Rewrites from "./Rewrites";
import Faq from "./site/Faq";
import ScoreCard from "./ScoreCard";
import SkillList from "./SkillList";

export default function Results({ result, onRestart }: { result: AnalysisResult; onRestart: () => void }) {
  const [approved, setApproved] = useState<Set<string>>(() => new Set(result.approved_ids));
  const [finalScore, setFinalScore] = useState<ScoreResult>(result.score_final);
  const [downloading, setDownloading] = useState(false);

  // Le score « avec tes choix » est recalculé par l'API (même formule que le reste de l'analyse).
  useEffect(() => {
    const ids = [...approved];
    const timer = setTimeout(() => {
      getScore(result.assessments, ids)
        .then(setFinalScore)
        .catch(() => {}); // on garde la dernière valeur connue
    }, 200);
    return () => clearTimeout(timer);
  }, [approved, result.assessments]);

  const termsBySkill = useMemo(
    () => Object.fromEntries(result.assessments.map((a) => [a.requirement.id, a.requirement.offer_terms])),
    [result.assessments],
  );
  const notAssessed = result.assessments.filter((a) => a.attempts === 0).map(skillName);

  function toggle(id: string) {
    setApproved((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function download() {
    setDownloading(true);
    try {
      const md = await getReport(result, [...approved]);
      const url = URL.createObjectURL(new Blob([md], { type: "text/markdown;charset=utf-8" }));
      const link = Object.assign(document.createElement("a"), { href: url, download: "cvmatch-bilan.md" });
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-10">
      <ScoreCard result={result} finalScore={finalScore} hasSuggestions={result.suggestions.length > 0} />

      {notAssessed.length > 0 && (
        <div role="alert" className="rounded-xl bg-amber-50 p-4 text-amber-900 ring-1 ring-amber-200">
          <strong>
            {notAssessed.length} compétence{notAssessed.length > 1 ? "s n'ont" : " n'a"} pas pu être vérifiée
            {notAssessed.length > 1 ? "s" : ""}
          </strong>{" "}
          ({notAssessed.join(", ")}) : le service d&apos;IA était saturé. Elles sont comptées comme absentes ; relance
          l&apos;analyse dans une minute.
        </div>
      )}

      {result.summary && (
        <section className="rounded-2xl bg-white p-6 ring-1 ring-slate-200">
          <h2 className="text-xl font-bold text-slate-900">En bref</h2>
          <p className="mt-2 text-slate-700">{result.summary.headline}</p>
          <div className="mt-4 grid gap-6 md:grid-cols-2">
            {result.summary.strengths.length > 0 && (
              <div>
                <h3 className="font-semibold text-emerald-700">Tes points forts</h3>
                <ul className="mt-2 space-y-1.5">
                  {result.summary.strengths.map((s) => (
                    <li key={s} className="flex gap-2 text-slate-700">
                      <span className="text-emerald-600" aria-hidden>
                        ✓
                      </span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.summary.priorities.length > 0 && (
              <div>
                <h3 className="font-semibold text-indigo-700">Par quoi commencer</h3>
                <ol className="mt-2 space-y-1.5">
                  {result.summary.priorities.map((s, i) => (
                    <li key={s} className="flex gap-2 text-slate-700">
                      <span className="font-semibold text-indigo-600">{i + 1}.</span>
                      {s}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </section>
      )}

      {result.suggestions.length > 0 && (
        <Rewrites
          suggestions={result.suggestions}
          termsBySkill={termsBySkill}
          approved={approved}
          onToggle={toggle}
        />
      )}

      {result.ats_keywords.length > 0 && (
        <section className="rounded-2xl bg-white p-6 ring-1 ring-slate-200">
          <h2 className="text-xl font-bold text-slate-900">Les mots de l&apos;offre à reprendre</h2>
          <p className="mt-1 text-slate-600">
            Tu as déjà ces compétences, mais ton CV ne les nomme pas comme l&apos;offre. Glisse ces mots exacts dans
            tes lignes d&apos;expérience (les reformulations ci-dessus le font pour toi).
          </p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {result.ats_keywords.map((k) => (
              <li key={k} className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-800">
                {k}
              </li>
            ))}
          </ul>
        </section>
      )}

      <SkillList assessments={result.assessments} />

      <section>
        <h2 className="text-xl font-bold text-slate-900">Comment lire ces résultats ?</h2>
        <div className="mt-3">
          <Faq />
        </div>
      </section>

      <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
        <button
          onClick={download}
          disabled={downloading}
          className="w-full rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white hover:bg-indigo-500 disabled:opacity-60 sm:w-auto"
        >
          {downloading ? "Préparation…" : "Télécharger mon bilan"}
        </button>
        <button
          onClick={onRestart}
          className="w-full rounded-xl px-6 py-3 font-semibold text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-50 sm:w-auto"
        >
          Analyser une autre offre
        </button>
      </div>
    </div>
  );
}
