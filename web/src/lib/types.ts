// Miroir des schémas Pydantic de l'API (src/cvmatch/schemas.py).

export type Status = "visible" | "hidden" | "implicit" | "absent";
export type Importance = "must" | "nice";

export interface Requirement {
  id: string;
  name: string;
  category: string;
  importance: Importance;
  offer_terms: string[];
  offer_quote: string | null;
}

export interface Assessment {
  requirement: Requirement;
  status: Status;
  evidence_quote: string | null;
  chunk_id: string | null;
  section: string | null;
  reasoning: string;
  suggested_rewrite: string | null;
  rewrite_ok: boolean;
  verified: boolean;
  needs_review: boolean;
  attempts: number; // 0 = aucun verdict obtenu (erreur du fournisseur LLM)
  notes: string[];
}

export interface Suggestion {
  id: string;
  skill_id: string;
  skill_name: string;
  status: Status;
  importance: Importance;
  section: string | null;
  original: string;
  rewrite: string;
  gain: number;
}

export interface ScoreResult {
  score: number;
  points: number;
  max_points: number;
  must_coverage: number;
  counts: Record<Status, number>;
}

export interface Gap {
  skill_id: string;
  skill_name: string;
  importance: Importance;
  offer_quote: string | null;
}

export interface Summary {
  headline: string;
  strengths: string[];
  priorities: string[];
}

export interface AnalysisResult {
  requirements: Requirement[];
  assessments: Assessment[];
  score_actual: ScoreResult;
  score_potential: ScoreResult;
  score_final: ScoreResult;
  suggestions: Suggestion[];
  approved_ids: string[];
  ats_keywords: string[];
  gaps: Gap[];
  summary: Summary | null;
  report_md: string;
}

export interface Progress {
  step: string;
  label: string;
  done: number;
  total: number;
}
