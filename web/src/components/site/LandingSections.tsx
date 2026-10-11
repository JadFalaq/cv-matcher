import {
  BadgeCheck,
  Ban,
  Briefcase,
  Calculator,
  Eye,
  FileSearch,
  GraduationCap,
  Languages,
  Lock,
  ScanSearch,
  Search,
  Target,
} from "lucide-react";

import { STATUS_INFO, STATUS_ORDER } from "@/lib/labels";
import type { Status } from "@/lib/types";

import Section from "./Section";

/* ------------------------------------------------------------ le problème */
const PROBLEMS = [
  {
    icon: Search,
    title: "Le tri automatique",
    text: "Beaucoup d'entreprises filtrent les candidatures avec un logiciel (ATS) qui cherche les mots exacts de l'offre. Une compétence décrite autrement peut ne jamais être vue.",
  },
  {
    icon: Eye,
    title: "La lecture en diagonale",
    text: "Un recruteur parcourt un CV en quelques secondes. Si la compétence n'est pas écrite clairement, il ne fera pas le lien avec ton projet ou ton outil.",
  },
  {
    icon: Languages,
    title: "Les mêmes compétences, d'autres mots",
    text: "« Apprentissage profond » ou « deep learning », « tenue comptable » ou « comptabilité générale » : tu as la compétence, mais ton CV ne parle pas la même langue que l'offre.",
  },
];

export function Problem() {
  return (
    <Section
      id="pourquoi"
      eyebrow="Pourquoi"
      title="Un bon profil peut passer inaperçu"
      intro="Souvent, ce n'est pas l'expérience qui manque, mais la façon dont elle est écrite."
    >
      <div className="grid gap-6 md:grid-cols-3">
        {PROBLEMS.map(({ icon: Icon, title, text }) => (
          <div key={title} className="rounded-2xl bg-slate-50 p-6 ring-1 ring-slate-200">
            <span className="grid size-11 place-items-center rounded-xl bg-white text-indigo-600 ring-1 ring-slate-200">
              <Icon className="size-5" aria-hidden />
            </span>
            <h3 className="mt-4 text-lg font-semibold text-slate-900">{title}</h3>
            <p className="mt-2 text-slate-600">{text}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* --------------------------------------------------------- fonctionnement */
const STEPS = [
  {
    icon: FileSearch,
    title: "Lecture de l'offre",
    text: "L'IA relève chaque compétence demandée et note si elle est indispensable ou « un plus ». Elle relit ensuite l'offre pour vérifier qu'aucune n'a été oubliée.",
  },
  {
    icon: ScanSearch,
    title: "Recherche des preuves",
    text: "Ton CV est découpé en blocs (une expérience, un projet…). Pour chaque compétence, on retrouve les passages les plus pertinents, par les mots et par le sens.",
  },
  {
    icon: BadgeCheck,
    title: "Vérification",
    text: "L'IA propose un verdict et cite la ligne qui le prouve. Un programme vérifie que cette ligne existe mot pour mot ; sinon, l'IA doit corriger sa réponse.",
  },
  {
    icon: Calculator,
    title: "Score et conseils",
    text: "Le score est calculé par un programme à partir des preuves vérifiées. Tu reçois des reformulations contrôlées et la liste honnête de ce qui manque.",
  },
];

export function HowItWorks() {
  return (
    <Section
      id="fonctionnement"
      eyebrow="Comment ça marche"
      title="L'IA propose, le code vérifie"
      intro="Une IA seule peut se tromper ou inventer. Ici, chacune de ses réponses est contrôlée avant d'arriver dans ton bilan."
      tone="muted"
    >
      <ol className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {STEPS.map(({ icon: Icon, title, text }, i) => (
          <li key={title} className="relative rounded-2xl bg-white p-6 ring-1 ring-slate-200">
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-xl bg-indigo-600 text-white">
                <Icon className="size-5" aria-hidden />
              </span>
              <span className="text-sm font-semibold text-indigo-600">Étape {i + 1}</span>
            </div>
            <h3 className="mt-4 text-lg font-semibold text-slate-900">{title}</h3>
            <p className="mt-2 text-slate-600">{text}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

/* ----------------------------------------------------- les 4 situations */
const STATUS_EXAMPLES: Record<Status, { offer: string; cv: string | null; credit: string }> = {
  visible: { offer: "Python", cv: "Python, SQL, Git, Linux", credit: "100 % des points" },
  hidden: { offer: "deep learning", cv: "Réseaux de neurones, apprentissage profond…", credit: "60 % des points" },
  implicit: { offer: "API REST", cv: "Exposition du modèle via FastAPI", credit: "30 % des points" },
  absent: { offer: "Azure", cv: null, credit: "0 point" },
};

export function Statuses() {
  return (
    <Section
      id="situations"
      eyebrow="Lire ton bilan"
      title="Chaque compétence tombe dans l'une de ces 4 situations"
      intro="C'est le cœur du bilan : savoir non seulement si tu as la compétence, mais si ton CV le montre."
    >
      <div className="grid gap-6 md:grid-cols-2">
        {STATUS_ORDER.map((s) => {
          const info = STATUS_INFO[s];
          const ex = STATUS_EXAMPLES[s];
          return (
            <div key={s} className={`rounded-2xl border-l-4 bg-white p-6 ring-1 ring-slate-200 ${info.card}`}>
              <div className="flex items-center justify-between gap-3">
                <h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <span className={`size-3 rounded-full ${info.dot}`} aria-hidden />
                  {info.title}
                </h3>
                <span className="shrink-0 text-sm text-slate-500">{ex.credit}</span>
              </div>
              <p className="mt-2 text-slate-600">{info.explain}</p>
              <dl className="mt-4 grid gap-2 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium text-slate-500">L&apos;offre demande</dt>
                  <dd className="mt-0.5 font-semibold text-slate-900">« {ex.offer} »</dd>
                </div>
                <div>
                  <dt className="font-medium text-slate-500">Ton CV dit</dt>
                  <dd className="mt-0.5 text-slate-900">{ex.cv ? `« ${ex.cv} »` : "Rien à ce sujet"}</dd>
                </div>
              </dl>
              <p className="mt-4 text-sm">
                <span className="font-semibold text-slate-900">Que faire : </span>
                <span className="text-slate-700">{info.action}</span>
              </p>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------- l'exemple */
const REWRITES = [
  {
    skill: "MLOps",
    before: "Mise en place du suivi des expériences et du registre de modèles avec MLflow.",
    after: ["Mise en place du suivi des expériences et du registre de modèles avec MLflow (", "MLOps", ")."],
  },
  {
    skill: "RAG",
    before: "Chatbot documentaire interrogeant des PDF avec FAISS et recherche sémantique.",
    after: ["Chatbot documentaire (", "RAG", ") interrogeant des PDF avec FAISS et recherche sémantique."],
  },
  {
    skill: "Comptabilité générale",
    before: "Tenue de la comptabilité de 40 PME, déclarations de TVA mensuelles.",
    after: ["Tenue de la ", "comptabilité générale", " de 40 PME, déclarations de TVA mensuelles."],
  },
];

export function Example({ onExample }: { onExample: () => void }) {
  return (
    <Section
      id="exemple"
      eyebrow="Exemple"
      title="Les mêmes faits, avec les mots de l'offre"
      intro="Une reformulation reprend une vraie ligne de ton CV. Elle ne change que les mots : mêmes missions, mêmes chiffres, mêmes outils."
      tone="muted"
    >
      <div className="grid gap-6 lg:grid-cols-3">
        {REWRITES.map((r) => (
          <figure key={r.skill} className="flex flex-col rounded-2xl bg-white p-6 ring-1 ring-slate-200">
            <figcaption className="text-sm font-semibold text-indigo-700">L&apos;offre demande « {r.skill} »</figcaption>
            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Avant</p>
            <p className="mt-1 text-slate-600">{r.before}</p>
            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-indigo-700">Après</p>
            <p className="mt-1 text-slate-900">
              {r.after[0]}
              <mark className="rounded bg-indigo-200/70 px-0.5 font-semibold text-indigo-950">{r.after[1]}</mark>
              {r.after[2]}
            </p>
          </figure>
        ))}
      </div>
      <div className="mt-10 text-center">
        <button
          type="button"
          onClick={onExample}
          className="rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white hover:bg-indigo-500"
        >
          Voir un bilan complet sur un exemple
        </button>
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------ garanties */
const GUARANTEES = [
  {
    icon: Ban,
    title: "Aucune expérience inventée",
    text: "Une reformulation qui ajoute un chiffre, un outil ou une compétence absents de ta ligne d'origine est automatiquement rejetée.",
  },
  {
    icon: BadgeCheck,
    title: "Des preuves vérifiables",
    text: "Chaque citation affichée a été retrouvée mot pour mot dans ton CV. En cas de doute, la compétence est marquée « à vérifier ».",
  },
  {
    icon: Calculator,
    title: "Un score calculé, pas deviné",
    text: "Le chiffre vient d'une formule fixe et transparente, appliquée par un programme : même CV et même offre donnent le même score.",
  },
  {
    icon: Target,
    title: "Des lacunes honnêtes",
    text: "Ce qui manque reste listé comme manquant. On te suggère un projet ou une formation, jamais de l'ajouter sans l'avoir.",
  },
  {
    icon: Lock,
    title: "Ton CV reste à toi",
    text: "Pas de compte, pas de base de données : ton CV est analysé puis oublié. Il ne sert à rien d'autre.",
  },
  {
    icon: Eye,
    title: "Tu gardes la main",
    text: "Tu choisis les reformulations que tu gardes, et tu vois tout de suite leur effet sur le score.",
  },
];

export function Guarantees() {
  return (
    <Section
      id="garanties"
      eyebrow="Nos garanties"
      title="Un outil pour mieux te présenter, pas pour embellir"
      intro="Un CV qui exagère se voit en entretien. cvmatch t'aide uniquement à mettre en valeur ce que tu as vraiment fait."
    >
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {GUARANTEES.map(({ icon: Icon, title, text }) => (
          <div key={title} className="flex gap-4">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
              <Icon className="size-5" aria-hidden />
            </span>
            <div>
              <h3 className="font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 text-slate-600">{text}</p>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ------------------------------------------------------------- pour qui */
const AUDIENCES = [
  {
    icon: GraduationCap,
    title: "Étudiants et jeunes diplômés",
    text: "Pour un stage ou un premier emploi : tes projets d'école prouvent souvent plus de compétences que ton CV ne le dit.",
  },
  {
    icon: Briefcase,
    title: "Personnes en poste ou en reconversion",
    text: "Ton expérience est réelle mais décrite avec le vocabulaire de ton ancien métier : traduis-la dans celui de l'offre.",
  },
  {
    icon: Target,
    title: "Toutes les candidatures ciblées",
    text: "Une offre qui te plaît vraiment mérite un CV adapté. En quelques minutes, tu sais quoi changer et pourquoi.",
  },
];

export function ForWho() {
  return (
    <Section
      id="pour-qui"
      eyebrow="Pour qui"
      title="Pour tous les métiers"
      intro="L'analyse fonctionne pour n'importe quelle offre, en français comme en anglais. Elle est encore plus fine pour la data et l'IA, dont l'outil connaît en plus les synonymes et les outils courants."
      tone="muted"
    >
      <div className="grid gap-6 md:grid-cols-3">
        {AUDIENCES.map(({ icon: Icon, title, text }) => (
          <div key={title} className="rounded-2xl bg-white p-6 ring-1 ring-slate-200">
            <Icon className="size-6 text-indigo-600" aria-hidden />
            <h3 className="mt-4 text-lg font-semibold text-slate-900">{title}</h3>
            <p className="mt-2 text-slate-600">{text}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}
