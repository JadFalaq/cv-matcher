"use client";

import { useState } from "react";

import { capitalize, IMPORTANCE_LABEL, STATUS_INFO } from "@/lib/labels";
import type { Suggestion } from "@/lib/types";

export default function Rewrites({
  suggestions,
  termsBySkill,
  approved,
  onToggle,
}: {
  suggestions: Suggestion[];
  termsBySkill: Record<string, string[]>;
  approved: Set<string>;
  onToggle: (id: string) => void;
}) {
  return (
    <section>
      <h2 className="text-xl font-bold text-slate-900">Ce que tu peux améliorer tout de suite</h2>
      <p className="mt-1 text-slate-600">
        Ces lignes viennent de ton CV. On les a reformulées avec les mots de l&apos;offre,{" "}
        <strong>sans ajouter aucun fait</strong> : mêmes expériences, mêmes chiffres. Copie celles qui te
        ressemblent dans ton CV ; décoche les autres pour voir l&apos;effet sur le score.
      </p>
      <ol className="mt-4 space-y-4">
        {suggestions.map((s) => (
          <RewriteCard
            key={s.id}
            s={s}
            terms={termsBySkill[s.skill_id] ?? []}
            kept={approved.has(s.id)}
            onToggle={() => onToggle(s.id)}
          />
        ))}
      </ol>
    </section>
  );
}

function RewriteCard({
  s,
  terms,
  kept,
  onToggle,
}: {
  s: Suggestion;
  terms: string[];
  kept: boolean;
  onToggle: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const info = STATUS_INFO[s.status];

  async function copy() {
    try {
      await navigator.clipboard.writeText(s.rewrite);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* presse-papiers indisponible (http, navigateur ancien) : le texte reste sélectionnable */
    }
  }

  return (
    <li className={`rounded-2xl bg-white p-5 ring-1 ${kept ? "ring-indigo-200" : "ring-slate-200 opacity-75"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold text-slate-900">{capitalize(terms[0] ?? s.skill_name)}</h3>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${info.badge}`}>{info.short}</span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {IMPORTANCE_LABEL[s.importance]}
          </span>
        </div>
        <span className="text-sm font-semibold text-emerald-600">+{s.gain.toLocaleString("fr-FR")} pts</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Aujourd&apos;hui dans ton CV{s.section ? ` (${s.section})` : ""}
          </p>
          <p className="mt-1 text-slate-700">{s.original}</p>
        </div>
        <div className="rounded-xl bg-indigo-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Proposition</p>
          <p className="mt-1 text-slate-900">
            <Highlight text={s.rewrite} terms={terms} />
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={kept} onChange={onToggle} className="size-4 accent-indigo-600" />
          Je garde cette reformulation
        </label>
        <button
          type="button"
          onClick={copy}
          className="rounded-lg px-3 py-1.5 text-sm font-medium text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-50"
        >
          {copied ? "Copié ✓" : "Copier le texte"}
        </button>
      </div>
    </li>
  );
}

/** Met en évidence les mots de l'offre dans la reformulation. */
function Highlight({ text, terms }: { text: string; terms: string[] }) {
  const usable = terms.filter((t) => t.trim().length > 1);
  if (!usable.length) return <>{text}</>;
  const escaped = usable.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="rounded bg-indigo-200/70 px-0.5 font-semibold text-indigo-950">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}
