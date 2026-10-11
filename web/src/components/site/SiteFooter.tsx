import { Code, Lock } from "lucide-react";

const GITHUB_URL = process.env.NEXT_PUBLIC_GITHUB_URL;

export default function SiteFooter() {
  return (
    <footer className="bg-slate-900 text-slate-300">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 md:grid-cols-3">
        <div>
          <p className="flex items-center gap-2 text-lg font-semibold text-white">
            <span aria-hidden className="grid size-8 place-items-center rounded-lg bg-indigo-500 text-sm">
              cv
            </span>
            cvmatch
          </p>
          <p className="mt-3 text-sm text-slate-400">
            Adapter son CV à une offre, compétence par compétence, sans jamais rien inventer.
          </p>
        </div>

        <div>
          <p className="flex items-center gap-2 font-semibold text-white">
            <Lock className="size-4" aria-hidden /> Confidentialité
          </p>
          <p className="mt-3 text-sm text-slate-400">
            Ton CV est analysé puis oublié : rien n&apos;est conservé. Son texte est transmis à un modèle d&apos;IA
            (Azure OpenAI) uniquement le temps de l&apos;analyse.
          </p>
        </div>

        <div>
          <p className="flex items-center gap-2 font-semibold text-white">
            <Code className="size-4" aria-hidden /> Sous le capot
          </p>
          <p className="mt-3 text-sm text-slate-400">
            Orchestration LangGraph, recherche de preuves (RAG), Azure OpenAI, contrôles anti-hallucination en Python,
            API FastAPI et site Next.js.
          </p>
          {GITHUB_URL && (
            <a href={GITHUB_URL} className="mt-3 inline-block text-sm font-medium text-indigo-300 hover:text-indigo-200">
              Voir le code source →
            </a>
          )}
        </div>
      </div>
      <div className="border-t border-slate-800">
        <p className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500">
          Le score mesure à quel point ton CV montre ce que l&apos;offre demande ; il ne prédit pas une décision de
          recrutement.
        </p>
      </div>
    </footer>
  );
}
