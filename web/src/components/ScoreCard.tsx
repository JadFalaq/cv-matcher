import Gauge from "@/components/Gauge";
import { scoreVerdict, STATUS_INFO, STATUS_ORDER, statusCount } from "@/lib/labels";
import type { AnalysisResult, ScoreResult } from "@/lib/types";

export default function ScoreCard({
  result,
  finalScore,
  hasSuggestions,
}: {
  result: AnalysisResult;
  finalScore: ScoreResult;
  hasSuggestions: boolean;
}) {
  const actual = result.score_actual;
  const verdict = scoreVerdict(actual.score);
  const musts = result.assessments.filter((a) => a.requirement.importance === "must");
  const mustFound = musts.filter((a) => a.status !== "absent").length;
  const total = result.assessments.length;

  return (
    <section className="rounded-2xl bg-white p-6 ring-1 ring-slate-200 sm:p-8">
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <Gauge value={actual.score} />
        <div className="flex-1 text-center sm:text-left">
          <p className="text-sm font-medium uppercase tracking-wide text-slate-500">Ton CV face à cette offre</p>
          <h2 className={`mt-1 text-2xl font-bold ${verdict.tone}`}>{verdict.label}</h2>
          <p className="mt-2 text-slate-600">{verdict.text}</p>
          {musts.length > 0 && (
            <p className="mt-3 text-slate-800">
              <strong>
                {mustFound} compétence{mustFound > 1 ? "s" : ""} indispensable{mustFound > 1 ? "s" : ""} sur{" "}
                {musts.length}
              </strong>{" "}
              {mustFound > 1 ? "sont prouvées" : "est prouvée"} dans ton CV.
            </p>
          )}
        </div>
      </div>

      {/* Répartition des compétences */}
      <div className="mt-6">
        <div className="flex h-3 overflow-hidden rounded-full bg-slate-100" aria-hidden>
          {STATUS_ORDER.map((s) =>
            actual.counts[s] ? (
              <div key={s} className={STATUS_INFO[s].dot} style={{ width: `${(100 * actual.counts[s]) / total}%` }} />
            ) : null,
          )}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600">
          {STATUS_ORDER.map((s) => (
            <li key={s} className="flex items-center gap-1.5">
              <span className={`size-2.5 rounded-full ${STATUS_INFO[s].dot}`} aria-hidden />
              {statusCount(s, actual.counts[s] ?? 0)}
            </li>
          ))}
        </ul>
      </div>

      {hasSuggestions && (
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl bg-indigo-50 p-4">
            <p className="text-sm text-indigo-900">Avec les reformulations que tu gardes</p>
            <p className="mt-1 text-2xl font-bold text-indigo-700">
              {fmt(finalScore.score)}
              <span className="text-base font-medium text-indigo-500">/100</span>
              <span className="ml-2 text-base font-semibold text-emerald-600">
                {finalScore.score > actual.score ? `+${fmt(finalScore.score - actual.score)}` : ""}
              </span>
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-sm text-slate-600">Maximum atteignable sans rien inventer</p>
            <p className="mt-1 text-2xl font-bold text-slate-800">
              {fmt(result.score_potential.score)}
              <span className="text-base font-medium text-slate-400">/100</span>
            </p>
          </div>
        </div>
      )}

      <details className="group mt-6 text-sm">
        <summary className="cursor-pointer list-none font-medium text-indigo-700 hover:underline">
          <span className="inline-block transition group-open:rotate-90">›</span> Comment ce score est-il calculé ?
        </summary>
        <div className="mt-2 space-y-2 text-slate-600">
          <p>
            Chaque compétence de l&apos;offre rapporte des points selon ce qu&apos;on trouve dans ton CV : 100 % si elle
            est <strong>bien visible</strong>, 60 % si elle est écrite <strong>avec d&apos;autres mots</strong>, 30 % si
            elle est seulement <strong>sous-entendue</strong>, 0 si elle est <strong>absente</strong>.
          </p>
          <p>
            Une compétence <strong>indispensable</strong> compte trois fois plus qu&apos;une compétence présentée comme
            « un plus ». Le total est ramené sur 100.
          </p>
          <p>
            Ce score mesure à quel point ton CV <em>montre</em> ce que l&apos;offre demande, pas ta valeur : un CV
            qui décrit bien tes compétences avec les mots de l&apos;offre se lit plus vite.
          </p>
        </div>
      </details>
    </section>
  );
}

function fmt(n: number) {
  return n.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}
