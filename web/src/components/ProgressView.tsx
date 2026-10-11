"use client";

import type { Progress } from "@/lib/types";

// Étapes affichées : chaque étape est terminée quand l'un de ses nœuds de fin est apparu.
const STAGES = [
  {
    title: "Lecture de ton CV et de l'offre",
    help: "Ton CV est découpé en blocs (une expérience, un projet…) pour pouvoir y chercher des preuves.",
    doneWhen: ["normalize_requirements"],
  },
  {
    title: "Repérage des compétences demandées",
    help: "L'offre est relue une seconde fois pour s'assurer qu'aucune compétence n'a été oubliée.",
    doneWhen: ["dispatch"],
  },
  {
    title: "Recherche des preuves dans ton CV",
    help: "Pour chaque compétence, l'IA cherche une ligne de ton CV qui la prouve, puis un programme vérifie que cette ligne existe vraiment.",
    doneWhen: ["aggregate"],
  },
  {
    title: "Calcul du score et rédaction du bilan",
    help: "Le score est calculé par un programme, à partir des preuves vérifiées.",
    doneWhen: ["finalize"],
  },
];

export default function ProgressView({ events }: { events: Progress[] }) {
  const seen = new Set(events.map((e) => e.step));
  const current = STAGES.findIndex((s) => !s.doneWhen.some((n) => seen.has(n)));
  const last = events.at(-1);
  const skills = events.filter((e) => e.step === "assess_skill");
  const total = last?.total ?? 0;
  const done = last?.done ?? 0;

  return (
    <section aria-live="polite" className="mx-auto max-w-xl">
      <h1 className="text-center text-2xl font-bold text-slate-900">Analyse en cours…</h1>
      <p className="mt-2 text-center text-slate-600">Cela prend en général 20 à 60 secondes. Garde cette page ouverte.</p>

      <ol className="mt-8 space-y-3">
        {STAGES.map((stage, i) => {
          const state = current === -1 || i < current ? "done" : i === current ? "active" : "todo";
          return (
            <li
              key={stage.title}
              className={`rounded-xl bg-white p-4 ring-1 ${state === "active" ? "ring-indigo-300" : "ring-slate-200"}`}
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden
                  className={`grid size-7 shrink-0 place-items-center rounded-full text-sm font-semibold ${
                    state === "done"
                      ? "bg-emerald-100 text-emerald-700"
                      : state === "active"
                        ? "bg-indigo-100 text-indigo-700"
                        : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {state === "done" ? "✓" : state === "active" ? <Spinner /> : i + 1}
                </span>
                <span className={`font-medium ${state === "todo" ? "text-slate-400" : "text-slate-900"}`}>
                  {stage.title}
                  {i === 2 && total > 0 && (
                    <span className="ml-2 font-normal text-slate-500">
                      {done}/{total}
                    </span>
                  )}
                </span>
              </div>
              {state === "active" && <p className="mt-2 pl-10 text-sm text-slate-600">{stage.help}</p>}
              {i === 2 && state === "active" && total > 0 && (
                <div className="mt-3 pl-10">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                      style={{ width: `${Math.round((100 * done) / total)}%` }}
                    />
                  </div>
                  {skills.length > 0 && (
                    <p className="mt-2 truncate text-sm text-slate-500">{skills.at(-1)?.label}</p>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function Spinner() {
  return <span className="size-3.5 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-700" />;
}
