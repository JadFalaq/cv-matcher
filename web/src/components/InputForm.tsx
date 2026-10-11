"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, getExample, type AnalyzeInput } from "@/lib/api";

const ACCEPTED = ".pdf,.md,.txt";
const MAX_FILE_MB = 5;
const MAX_CV_CHARS = 15_000; // mêmes valeurs par défaut que l'API (src/cvmatch/limits.py)
const MAX_OFFER_CHARS = 8_000;

export default function InputForm({
  onSubmit,
  exampleSignal = 0,
}: {
  onSubmit: (input: AnalyzeInput) => void;
  /** Incrémenté par la page (« Essayer avec un exemple ») pour charger l'exemple. */
  exampleSignal?: number;
}) {
  const [mode, setMode] = useState<"file" | "text">("file");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [cvText, setCvText] = useState("");
  const [offerText, setOfferText] = useState("");
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [loadingExample, setLoadingExample] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function pickFile(file: File | undefined) {
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "md", "txt"].includes(ext ?? "")) {
      setNotice("Formats acceptés : PDF, .md ou .txt. Pour un fichier Word, enregistre-le en PDF ou colle son texte.");
      return;
    }
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      setNotice(`Ce fichier dépasse ${MAX_FILE_MB} Mo.`);
      return;
    }
    setNotice(null);
    setCvFile(file);
  }

  async function loadExample() {
    setLoadingExample(true);
    try {
      const ex = await getExample();
      setMode("text");
      setCvFile(null);
      setCvText(ex.cv_text);
      setOfferText(ex.offer_text);
      setNotice(null);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Exemple indisponible.");
    } finally {
      setLoadingExample(false);
    }
  }

  useEffect(() => {
    if (exampleSignal > 0) loadExample();
  }, [exampleSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  const hasCv = mode === "file" ? cvFile !== null : cvText.trim().length >= 20;
  const hasOffer = offerText.trim().length >= 20;
  const cvTooLong = mode === "text" && cvText.length > MAX_CV_CHARS;
  const offerTooLong = offerText.length > MAX_OFFER_CHARS;
  const ready = hasCv && hasOffer && !cvTooLong && !offerTooLong;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready) return;
    onSubmit({ cvFile: mode === "file" ? cvFile : null, cvText, offerText });
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
        <span>Première visite ? Essaie avec un CV et une offre fictifs.</span>
        <button
          type="button"
          onClick={loadExample}
          disabled={loadingExample}
          className="rounded-lg bg-white px-3 py-1.5 font-medium text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-100 disabled:opacity-60"
        >
          {loadingExample ? "Chargement…" : "Charger l'exemple"}
        </button>
      </div>

      {notice && (
        <p role="alert" className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200">
          {notice}
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* ---------------------------------------------------------------- CV */}
        <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-slate-900">1. Ton CV</h2>
            <div className="flex rounded-lg bg-slate-100 p-0.5 text-sm" role="tablist">
              {(["file", "text"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => setMode(m)}
                  className={`rounded-md px-2.5 py-1 font-medium ${
                    mode === m ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {m === "file" ? "Fichier" : "Texte"}
                </button>
              ))}
            </div>
          </div>

          {mode === "file" ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                pickFile(e.dataTransfer.files[0]);
              }}
              className={`mt-4 flex min-h-56 flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition ${
                dragging ? "border-indigo-400 bg-indigo-50" : "border-slate-200"
              }`}
            >
              <input
                ref={fileInput}
                type="file"
                accept={ACCEPTED}
                className="sr-only"
                onChange={(e) => pickFile(e.target.files?.[0])}
              />
              {cvFile ? (
                <>
                  <p className="text-3xl" aria-hidden>
                    📄
                  </p>
                  <p className="mt-2 max-w-full truncate font-medium text-slate-900">{cvFile.name}</p>
                  <p className="text-sm text-slate-500">{Math.round(cvFile.size / 1024)} Ko</p>
                  <div className="mt-3 flex gap-2 text-sm">
                    <button
                      type="button"
                      onClick={() => fileInput.current?.click()}
                      className="rounded-lg px-3 py-1.5 font-medium text-indigo-700 hover:bg-indigo-50"
                    >
                      Changer
                    </button>
                    <button
                      type="button"
                      onClick={() => setCvFile(null)}
                      className="rounded-lg px-3 py-1.5 font-medium text-slate-600 hover:bg-slate-100"
                    >
                      Retirer
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-3xl" aria-hidden>
                    ⬆️
                  </p>
                  <p className="mt-2 font-medium text-slate-900">Glisse ton CV ici</p>
                  <p className="text-sm text-slate-500">PDF, .md ou .txt, {MAX_FILE_MB} Mo maximum</p>
                  <button
                    type="button"
                    onClick={() => fileInput.current?.click()}
                    className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
                  >
                    Choisir un fichier
                  </button>
                </>
              )}
            </div>
          ) : (
            <>
              <label htmlFor="cv-text" className="sr-only">
                Texte du CV
              </label>
              <textarea
                id="cv-text"
                value={cvText}
                onChange={(e) => setCvText(e.target.value)}
                placeholder="Colle ici le texte de ton CV…"
                className="mt-4 h-56 w-full resize-y rounded-xl border border-slate-200 p-3 text-sm focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 focus:outline-none"
              />
              {cvTooLong && (
                <p className="mt-1 text-sm text-rose-700">
                  Texte trop long ({cvText.length.toLocaleString("fr-FR")} caractères, maximum{" "}
                  {MAX_CV_CHARS.toLocaleString("fr-FR")}).
                </p>
              )}
            </>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Astuce : un CV sur une seule colonne donne de meilleurs résultats qu&apos;une mise en page à deux colonnes.
          </p>
        </section>

        {/* ------------------------------------------------------------- Offre */}
        <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            <label htmlFor="offer-text">2. L&apos;offre d&apos;emploi</label>
          </h2>
          <textarea
            id="offer-text"
            value={offerText}
            onChange={(e) => setOfferText(e.target.value)}
            placeholder="Colle ici le texte complet de l'annonce (missions, profil recherché…)"
            className="mt-4 h-56 w-full resize-y rounded-xl border border-slate-200 p-3 text-sm focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 focus:outline-none"
          />
          {offerTooLong && (
            <p className="mt-1 text-sm text-rose-700">
              Texte trop long ({offerText.length.toLocaleString("fr-FR")} caractères, maximum{" "}
              {MAX_OFFER_CHARS.toLocaleString("fr-FR")}).
            </p>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Inclus surtout la partie « profil recherché » : c&apos;est là que sont les compétences attendues.
          </p>
        </section>
      </div>

      <div className="flex flex-col items-center gap-2">
        <button
          type="submit"
          disabled={!ready}
          className="w-full rounded-xl bg-indigo-600 px-8 py-3.5 text-base font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300 sm:w-auto"
        >
          3. Analyser mon CV
        </button>
        <p className="text-sm text-slate-500">
          {!hasCv
            ? "Ajoute d'abord ton CV."
            : !hasOffer
              ? "Colle maintenant le texte de l'offre."
              : "Environ 20 à 60 secondes."}
        </p>
      </div>
    </form>
  );
}
