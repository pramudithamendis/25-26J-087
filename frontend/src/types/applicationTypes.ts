/**
 * TypeScript type definitions for Job Applications
 */

export interface ApplicationData {
  first_name?: string;
  last_name?: string;
  city?: string;
  phone_number?: string;
  github_url?: string; // Can be empty string to clear
  linkedin_url?: string; // Can be empty string to clear
  resume?: File;
  linkedin_resume?: File;
}

export interface ApplicationResponse {
  message: string;
  evaluation_id: string;
  evaluation: {
    _id: string;
    user_id: string;
    job_id: string;
    total_score: number;
    decision: string;
    role_predictions: Array<{
      role: string;
      similarity: number;
      confidence?: number;
    }>;
    why: string[];
    breakdown: Record<string, any>;
    raw_pipeline: Record<string, any>;
    created_at?: string;
  };
}

export interface ApiError {
  detail: string;
  statusCode?: number;
}

