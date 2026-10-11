import { ArrowRight, Clock, Lock, ShieldCheck, Sparkles } from "lucide-react";

import Gauge from "@/components/Gauge";

const TRUST = [
  { icon: Sparkles, text: "Gratuit, sans inscription" },
  { icon: Clock, text: "Résultat en 30 secondes environ" },
  { icon: ShieldCheck, text: "Rien n'est jamais inventé" },
  { icon: Lock, text: "Ton CV n'est pas conservé" },
];

export default function Hero({ onExample }: { onExample: () => void }) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-indigo-50 via-white to-white">
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:py-20 lg:grid-cols-2">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-medium text-indigo-700 ring-1 ring-indigo-100">
            <span className="size-1.5 rounded-full bg-indigo-500" aria-hidden />
            Assistant de candidature propulsé par l&apos;IA
          </p>
          <h1 className="mt-5 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            Ton CV répond-il vraiment à cette offre ?
          </h1>
          <p className="mt-5 text-lg text-slate-600">
            Colle une offre d&apos;emploi et ton CV. Pour <strong>chaque compétence demandée</strong>, cvmatch cherche
            la preuve dans ton CV, te montre ce qu&apos;un recruteur risque de ne pas voir, et propose des
            reformulations de <strong>tes propres lignes</strong> avec les mots de l&apos;offre.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <a
              href="#analyser"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3.5 font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              Analyser mon CV <ArrowRight className="size-4" aria-hidden />
            </a>
            <button
              type="button"
              onClick={onExample}
              className="inline-flex items-center justify-center rounded-xl bg-white px-6 py-3.5 font-semibold text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-50"
            >
              Essayer avec un exemple
            </button>
          </div>
          <ul className="mt-8 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
            {TRUST.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2">
                <Icon className="size-4 shrink-0 text-indigo-600" aria-hidden />
                {text}
              </li>
            ))}
          </ul>
        </div>

        <ResultPreview />
      </div>
    </section>
  );
}

/** Aperçu illustratif d'un bilan (données fictives). */
function ResultPreview() {
  const rows = [
    { skill: "Python", status: "Bien visible", dot: "bg-emerald-500", tag: "bg-emerald-50 text-emerald-800" },
    { skill: "Deep learning", status: "Autres mots", dot: "bg-amber-400", tag: "bg-amber-50 text-amber-800" },
    { skill: "API REST", status: "Sous-entendue", dot: "bg-orange-500", tag: "bg-orange-50 text-orange-800" },
    { skill: "Azure", status: "Absente", dot: "bg-rose-500", tag: "bg-rose-50 text-rose-800" },
  ];
  return (
    <div aria-label="Aperçu d'un bilan (exemple fictif)" className="relative mx-auto w-full max-w-md">
      <div className="absolute -inset-4 -z-10 rounded-[2rem] bg-indigo-100/60 blur-2xl" aria-hidden />
      <div className="rounded-2xl bg-white p-6 shadow-xl ring-1 ring-slate-200">
        <div className="flex items-center gap-5">
          <Gauge value={58} size="size-24" />
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Exemple de bilan</p>
            <p className="mt-1 text-lg font-bold text-emerald-700">Bon match, à affiner</p>
            <p className="text-sm text-slate-600">
              <span className="font-semibold text-indigo-700">74/100</span> avec les reformulations
            </p>
          </div>
        </div>
        <ul className="mt-5 divide-y divide-slate-100">
          {rows.map((r) => (
            <li key={r.skill} className="flex items-center justify-between py-2.5 text-sm">
              <span className="flex items-center gap-2 font-medium text-slate-800">
                <span className={`size-2.5 rounded-full ${r.dot}`} aria-hidden />
                {r.skill}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${r.tag}`}>{r.status}</span>
            </li>
          ))}
        </ul>
        <div className="mt-4 rounded-xl bg-indigo-50 p-3 text-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Reformulation proposée</p>
          <p className="mt-1 text-slate-500 line-through decoration-slate-300">
            Réseaux de neurones, apprentissage profond sur 5 000 images.
          </p>
          <p className="mt-1 text-slate-900">
            Réseaux de neurones,{" "}
            <mark className="rounded bg-indigo-200/70 px-0.5 font-semibold text-indigo-950">deep learning</mark> sur 5
            000 images.
          </p>
        </div>
      </div>
    </div>
  );
}
