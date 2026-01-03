/**
 * TypeScript type definitions for Admin Dashboard
 */

export interface AdminStats {
  total_jobs: number;
  total_applications: number;
  total_users: number;
  total_evaluations: number;
}

export interface UserListItem {
  _id: string;
  email: string;
  role: string;
  first_name?: string;
  last_name?: string;
  city?: string;
  created_at?: string;
}

export interface UserListResponse {
  count: number;
  users: UserListItem[];
}

export interface ApplicationListItem {
  _id: string;
  user_id: string;
  job_id: string;
  status: string;
  created_at: string;
  evaluation_id?: string;
  user_email?: string;
  user_name?: string;
  job_title?: string;
}

export interface ApplicationListResponse {
  count: number;
  applications: ApplicationListItem[];
}

export interface ApplicationDetailResponse {
  _id: string;
  user_id: string;
  job_id: string;
  status: string;
  created_at: string;
  evaluation_id?: string;
  user: {
    email?: string;
    first_name?: string;
    last_name?: string;
    city?: string;
    phone_number?: string;
    github_url?: string;
    linkedin_url?: string;
    cv_file_path?: string;
    linkedin_file_path?: string;
  };
  job: {
    _id?: string;
    title?: string;
    jd_text?: string;
    created_at?: string;
  };
}

export interface EvaluationListItem {
  _id: string;
  user_id: string;
  job_id: string;
  total_score: number;
  decision: string;
  status: string;
  created_at: string;
  user_email?: string;
  user_name?: string;
  job_title?: string;
}

export interface EvaluationListResponse {
  count: number;
  evaluations: EvaluationListItem[];
}

export interface SystemSettings {
  evaluation_threshold_selected: number;
  evaluation_threshold_review: number;
  email_notifications_enabled: boolean;
}

export interface SystemSettingsResponse {
  settings: SystemSettings;
}

export interface JobApplicantListItem {
  application_id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  status: string;
  created_at: string;
  evaluation_id?: string;
  total_score?: number;
  decision?: string;
  has_evaluation: boolean;
}

export interface JobApplicantListResponse {
  count: number;
  applicants: JobApplicantListItem[];
}

export interface ApplicationTimelineEvent {
  event_type: 'application_submitted' | 'evaluation_started' | 'evaluation_completed' | 'status_changed';
  timestamp: string;
  description: string;
  metadata?: {
    score?: number;
    decision?: string;
    status?: string;
  };
}

export interface ApiError {
  detail: string;
  statusCode?: number;
}

