import type { AnalysisResult, Assessment, Progress, ScoreResult } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {}

const UNREACHABLE = "Impossible de joindre le serveur d'analyse. Vérifie ta connexion et réessaie.";

async function request(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(UNREACHABLE);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `Erreur inattendue (${res.status}).`;
    throw new ApiError(detail);
  }
  return res;
}

export async function getExample(): Promise<{ cv_text: string; offer_text: string }> {
  return (await request("/example")).json();
}

export interface AnalyzeInput {
  cvFile: File | null;
  cvText: string;
  offerText: string;
}

/** Lance l'analyse et relaie l'avancement (Server-Sent Events sur une requête POST). */
export async function analyzeStream(
  input: AnalyzeInput,
  onProgress: (p: Progress) => void,
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("offer_text", input.offerText);
  if (input.cvFile) form.append("cv_file", input.cvFile);
  else form.append("cv_text", input.cvText);

  const res = await request("/analyze/stream", { method: "POST", body: form });
  if (!res.body) throw new ApiError(UNREACHABLE);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let end: number;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) continue; // ping de maintien de connexion
      const payload = JSON.parse(data);
      if (event === "progress") onProgress(payload as Progress);
      else if (event === "result") return payload as AnalysisResult;
      else if (event === "error") throw new ApiError(payload.detail);
    }
  }
  throw new ApiError("La connexion a été interrompue avant la fin de l'analyse. Réessaie.");
}

export async function getScore(assessments: Assessment[], approvedIds: string[]): Promise<ScoreResult> {
  const res = await request("/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assessments, approved_ids: approvedIds }),
  });
  return res.json();
}

export async function getReport(result: AnalysisResult, approvedIds: string[]): Promise<string> {
  const res = await request("/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result, approved_ids: approvedIds }),
  });
  return res.text();
}
