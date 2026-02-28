/**
 * TypeScript type definitions for Jobs
 */

export interface Job {
  _id: string;
  title: string;
  jd_text: string;
  created_at: string;
  application_count?: number;
  has_applied?: boolean;
}

export interface JobCreate {
  title: string;
  jd_text: string;
}

export interface JobUpdate {
  title?: string;
  jd_text?: string;
}

export interface JobResponse {
  _id: string;
  title: string;
  jd_text: string;
  created_at: string;
}

export interface JobListResponse {
  count: number;
  jobs: JobResponse[];
}

export interface ApiError {
  detail: string;
  statusCode?: number;
}

