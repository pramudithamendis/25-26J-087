/**
 * TypeScript type definitions for Evaluations
 */

export interface RolePrediction {
  role: string;
  similarity: number;
  confidence?: number;
}

export interface ScoreBreakdown {
  semantic_fit?: number;
  role_competency?: number;
  github_evidence?: number;
  experience_match?: number;
  [key: string]: number | undefined;
}

export interface Evaluation {
  _id: string;
  user_id: string;
  job_id: string;
  total_score: number;
  decision: string;
  role_predictions: RolePrediction[];
  why: string[];
  breakdown: ScoreBreakdown;
  raw_pipeline: Record<string, any>;
  created_at?: string;
}

export interface EvaluationResponse {
  _id: string;
  user_id: string;
  job_id: string;
  total_score: number;
  decision: string;
  role_predictions: RolePrediction[];
  why: string[];
  breakdown: ScoreBreakdown;
  raw_pipeline: Record<string, any>;
  created_at?: string;
}

export interface ApiError {
  detail: string;
  statusCode?: number;
}

