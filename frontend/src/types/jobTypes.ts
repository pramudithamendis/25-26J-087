/**
 * TypeScript type definitions for Jobs
 */

export const PROJECT_TYPES = ['r_and_d', 'production', 'support', 'general'] as const;
export type ProjectType = (typeof PROJECT_TYPES)[number];

export interface Job {
  _id: string;
  title: string;
  jd_text: string;
  location?: string;
  created_at: string;
  application_count?: number;
  has_applied?: boolean;
  project_type?: string | null;
}

export interface JobCreate {
  title: string;
  jd_text: string;
  location?: string;
  project_type?: string;
}

export interface JobUpdate {
  title?: string;
  jd_text?: string;
  location?: string;
  project_type?: string;
}

export interface JobResponse {
  _id: string;
  title: string;
  jd_text: string;
  location?: string;
  created_at: string;
  project_type?: string | null;
}

export interface JobListResponse {
  count: number;
  jobs: JobResponse[];
}

export interface ApiError {
  detail: string;
  statusCode?: number;
}

