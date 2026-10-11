import { IMPORTANCE_LABEL, skillName, STATUS_INFO, STATUS_ORDER } from "@/lib/labels";
import type { Assessment } from "@/lib/types";

export default function SkillList({ assessments }: { assessments: Assessment[] }) {
  return (
    <section>
      <h2 className="text-xl font-bold text-slate-900">Compétence par compétence</h2>
      <p className="mt-1 text-slate-600">
        Toutes les compétences demandées par l&apos;offre, regroupées selon ce qu&apos;on a trouvé dans ton CV. Clique
        sur une compétence pour voir la preuve et quoi faire.
      </p>
      <div className="mt-4 space-y-6">
        {STATUS_ORDER.map((status) => {
          // indispensables d'abord
          const items = assessments
            .filter((a) => a.status === status)
            .sort((a, b) => Number(a.requirement.importance === "nice") - Number(b.requirement.importance === "nice"));
          if (!items.length) return null;
          const info = STATUS_INFO[status];
          return (
            <div key={status} className={`rounded-2xl border-l-4 bg-white p-5 ring-1 ring-slate-200 ${info.card}`}>
              <h3 className="flex items-center gap-2 font-semibold text-slate-900">
                <span className={`size-3 rounded-full ${info.dot}`} aria-hidden />
                {info.title}
                <span className="font-normal text-slate-500">({items.length})</span>
              </h3>
              <p className="mt-1 text-sm text-slate-600">{info.explain}</p>
              <ul className="mt-3 divide-y divide-slate-100">
                {items.map((a) => (
                  <SkillRow key={a.requirement.id} a={a} />
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function SkillRow({ a }: { a: Assessment }) {
  const info = STATUS_INFO[a.status];
  const notAssessed = a.attempts === 0;
  return (
    <li>
      <details className="group py-2.5">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2">
            <span className="text-slate-400 transition group-open:rotate-90" aria-hidden>
              ›
            </span>
            <span className="truncate font-medium text-slate-900">{skillName(a)}</span>
            {a.needs_review && (
              <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                à vérifier
              </span>
            )}
          </span>
          <span
            className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
              a.requirement.importance === "must" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {IMPORTANCE_LABEL[a.requirement.importance]}
          </span>
        </summary>

        <dl className="mt-3 space-y-3 pl-6 text-sm">
          {a.requirement.offer_quote && (
            <div>
              <dt className="font-medium text-slate-500">Ce que demande l&apos;offre</dt>
              <dd className="mt-0.5 text-slate-700">« {a.requirement.offer_quote} »</dd>
            </div>
          )}
          <div>
            <dt className="font-medium text-slate-500">Preuve trouvée dans ton CV</dt>
            <dd className="mt-0.5 text-slate-700">
              {a.evidence_quote ? (
                <>
                  « {a.evidence_quote} »
                  {a.section && <span className="text-slate-400"> (section {a.section})</span>}
                </>
              ) : notAssessed ? (
                "Non évaluée : le service d'IA n'a pas répondu à temps. Relance l'analyse pour la vérifier."
              ) : (
                "Aucune."
              )}
            </dd>
          </div>
          {a.reasoning && (
            <div>
              <dt className="font-medium text-slate-500">Pourquoi</dt>
              <dd className="mt-0.5 text-slate-700">{a.reasoning}</dd>
            </div>
          )}
          <div>
            <dt className="font-medium text-slate-500">Que faire</dt>
            <dd className="mt-0.5 text-slate-900">{info.action}</dd>
          </div>
          {a.needs_review && a.notes.length > 0 && (
            <div className="rounded-lg bg-amber-50 p-2.5 text-amber-900">
              <span className="font-medium">À vérifier : </span>
              {a.notes.join(" ")}
            </div>
          )}
        </dl>
      </details>
    </li>
  );
}
