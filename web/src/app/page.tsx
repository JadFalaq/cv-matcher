"use client";

import { useState } from "react";

import InputForm from "@/components/InputForm";
import ProgressView from "@/components/ProgressView";
import Results from "@/components/Results";
import Faq from "@/components/site/Faq";
import Hero from "@/components/site/Hero";
import { Example, ForWho, Guarantees, HowItWorks, Problem, Statuses } from "@/components/site/LandingSections";
import Section from "@/components/site/Section";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";
import { analyzeStream, ApiError, type AnalyzeInput } from "@/lib/api";
import type { AnalysisResult, Progress } from "@/lib/types";

type Phase = "input" | "running" | "done";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("input");
  const [progress, setProgress] = useState<Progress[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exampleSignal, setExampleSignal] = useState(0);

  async function run(input: AnalyzeInput) {
    setError(null);
    setProgress([]);
    setPhase("running");
    window.scrollTo({ top: 0 });
    try {
      const res = await analyzeStream(input, (p) => setProgress((prev) => [...prev, p]));
      setResult(res);
      setPhase("done");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Une erreur inattendue est survenue. Réessaie.");
      setPhase("input");
      requestAnimationFrame(() => document.getElementById("analyser")?.scrollIntoView());
    }
  }

  function home() {
    setResult(null);
    setPhase("input");
    window.scrollTo({ top: 0 });
  }

  /** Remplit le formulaire avec l'exemple fictif et y descend. */
  function showExample() {
    setExampleSignal((n) => n + 1);
    document.getElementById("analyser")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader landing={phase === "input"} onHome={home} />

      {/* Toujours monté (seulement masqué) : le CV et l'offre saisis survivent à une erreur ou à une nouvelle analyse */}
      <main hidden={phase !== "input"} className="flex-1">
        <Hero onExample={showExample} />
        <Problem />
        <HowItWorks />
        <Section
          id="analyser"
          eyebrow="À toi de jouer"
          title="Analyse ton CV"
          intro="Ajoute ton CV, colle l'offre qui t'intéresse, et obtiens ton bilan compétence par compétence."
          tone="accent"
        >
          <div className="mx-auto max-w-5xl">
            {error && (
              <div role="alert" className="mb-6 rounded-xl bg-rose-50 p-4 text-rose-800 ring-1 ring-rose-200">
                {error}
              </div>
            )}
            <InputForm onSubmit={run} exampleSignal={exampleSignal} />
          </div>
        </Section>
        <Statuses />
        <Example onExample={showExample} />
        <Guarantees />
        <ForWho />
        <Section id="faq" eyebrow="FAQ" title="Questions fréquentes">
          <Faq />
        </Section>
      </main>

      {phase !== "input" && (
        <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:py-12">
          {phase === "running" && <ProgressView events={progress} />}
          {phase === "done" && result && <Results result={result} onRestart={home} />}
        </main>
      )}

      <SiteFooter />
    </div>
  );
}
