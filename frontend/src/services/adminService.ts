import apiClient from '../config/api';
import type {
  AdminStats,
  UserListResponse,
  ApplicationListResponse,
  ApplicationDetailResponse,
  EvaluationListResponse,
  SystemSettings,
  SystemSettingsResponse,
  ApiError,
  JobApplicantListItem,
  JobApplicantListResponse,
  CVTrendScoreListResponse
} from '../types/adminTypes';

/**
 * Admin Service
 * Handles all admin-related API calls
 */

export interface ListFilters {
  skip?: number;
  limit?: number;
  role?: string;
  search?: string;
  job_id?: string;
  user_id?: string;
  status?: string;
  min_score?: number;
  max_score?: number;
  decision?: string;
  has_evaluation?: boolean;
}

/**
 * Get admin dashboard statistics
 */
export const getAdminStats = async (): Promise<AdminStats> => {
  try {
    const response = await apiClient.get<AdminStats>('/api/admin/stats');
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch admin statistics.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * List all users (admin only)
 */
export const listAllUsers = async (filters: ListFilters = {}): Promise<UserListResponse> => {
  try {
    const params = new URLSearchParams();
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
    if (filters.role) params.append('role', filters.role);
    if (filters.search) params.append('search', filters.search);

    const response = await apiClient.get<UserListResponse>(`/users?${params.toString()}`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch users.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * List all applications (admin only)
 */
export const listAllApplications = async (filters: ListFilters = {}): Promise<ApplicationListResponse> => {
  try {
    const params = new URLSearchParams();
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
    if (filters.job_id) params.append('job_id', filters.job_id);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.status) params.append('status_filter', filters.status);
    if (filters.has_evaluation !== undefined) params.append('has_evaluation', filters.has_evaluation.toString());

    const response = await apiClient.get<ApplicationListResponse>(`/api/admin/applications?${params.toString()}`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch applications.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Get job applicants with evaluation scores (admin only)
 * Merges application and evaluation data for a specific job
 */
export const getJobApplicants = async (
  jobId: string,
  filters: {
    status?: string;
    minScore?: number;
    maxScore?: number;
    decision?: string;
    hasEvaluation?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  } = {}
): Promise<JobApplicantListResponse> => {
  try {
    // Fetch applications for this job
    const applicationFilters: ListFilters = {
      job_id: jobId,
      status: filters.status,
      skip: filters.skip,
      limit: filters.limit,
    };

    const applicationsResponse = await listAllApplications(applicationFilters);
    const applications = applicationsResponse.applications;

    // Fetch evaluations for this job
    const evaluationFilters: ListFilters = {
      job_id: jobId,
      min_score: filters.minScore,
      max_score: filters.maxScore,
      decision: filters.decision,
    };

    const evaluationsResponse = await listAllEvaluations(evaluationFilters);
    const evaluations = evaluationsResponse.evaluations;

    // Create a map of evaluation_id -> evaluation for quick lookup
    const evaluationMap = new Map<string, typeof evaluations[0]>();
    evaluations.forEach((evaluation) => {
      if (evaluation._id) {
        evaluationMap.set(evaluation._id, evaluation);
      }
    });

    // Merge applications with evaluations
    let applicants: JobApplicantListItem[] = applications.map((app) => {
      const evaluation = app.evaluation_id ? evaluationMap.get(app.evaluation_id) : null;
      
      return {
        application_id: app._id,
        user_id: app.user_id,
        user_email: app.user_email || '',
        user_name: app.user_name || '',
        status: app.status,
        created_at: app.created_at,
        evaluation_id: app.evaluation_id,
        evaluation_status: app.evaluation_status as 'pending' | 'processing' | 'evaluated' | 'failed' | undefined,
        processing_started_at: app.processing_started_at,
        processing_completed_at: app.processing_completed_at,
        error_message: app.error_message,
        total_score: evaluation?.total_score,
        decision: evaluation?.decision,
        has_evaluation: !!app.evaluation_id,
      };
    });

    // Apply has_evaluation filter
    if (filters.hasEvaluation !== undefined) {
      applicants = applicants.filter((app) => app.has_evaluation === filters.hasEvaluation);
    }

    // Apply search filter (name/email)
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      applicants = applicants.filter(
        (app) =>
          app.user_email.toLowerCase().includes(searchLower) ||
          app.user_name.toLowerCase().includes(searchLower)
      );
    }

    // Apply score range filter (if not already filtered by backend)
    if (filters.minScore !== undefined || filters.maxScore !== undefined) {
      applicants = applicants.filter((app) => {
        if (!app.has_evaluation || app.total_score === undefined) return false;
        if (filters.minScore !== undefined && app.total_score < filters.minScore) return false;
        if (filters.maxScore !== undefined && app.total_score > filters.maxScore) return false;
        return true;
      });
    }

    // Apply decision filter (if not already filtered by backend)
    if (filters.decision) {
      applicants = applicants.filter((app) => app.decision === filters.decision);
    }

    return {
      count: applicants.length,
      applicants,
    };
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch job applicants.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Get application details (admin only)
 */
export const getApplicationDetails = async (applicationId: string): Promise<ApplicationDetailResponse> => {
  try {
    const response = await apiClient.get<ApplicationDetailResponse>(`/api/admin/applications/${applicationId}`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch application details.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Get application status (admin only)
 */
export const getApplicationStatus = async (applicationId: string): Promise<{
  application_id: string;
  status: string;
  evaluation_status: string;
  processing_started_at?: string;
  processing_completed_at?: string;
  error_message?: string;
  evaluation_id?: string;
}> => {
  try {
    const response = await apiClient.get(`/api/admin/applications/${applicationId}/status`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch application status.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Get application evaluation details (admin only)
 */
export const getApplicationEvaluation = async (applicationId: string): Promise<any> => {
  try {
    const response = await apiClient.get(`/api/admin/applications/${applicationId}/evaluation`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch evaluation details.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Approve an application (admin only)
 */
export const approveApplication = async (applicationId: string): Promise<{ message: string; application_id: string }> => {
  try {
    const response = await apiClient.post<{ message: string; application_id: string }>(
      `/api/admin/applications/${applicationId}/approve`
    );
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to approve application.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Reject an application (admin only)
 */
export const rejectApplication = async (applicationId: string): Promise<{ message: string; application_id: string }> => {
  try {
    const response = await apiClient.post<{ message: string; application_id: string }>(
      `/api/admin/applications/${applicationId}/reject`
    );
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to reject application.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Download resume file (admin only)
 */
export const downloadResume = async (applicationId: string): Promise<Blob> => {
  try {
    const response = await apiClient.get(`/api/admin/applications/${applicationId}/resume`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to download resume.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Download LinkedIn resume file (admin only)
 */
export const downloadLinkedInResume = async (applicationId: string): Promise<Blob> => {
  try {
    const response = await apiClient.get(`/api/admin/applications/${applicationId}/linkedin-resume`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to download LinkedIn resume.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * List all evaluations (admin only)
 */
export const listAllEvaluations = async (filters: ListFilters = {}): Promise<EvaluationListResponse> => {
  try {
    const params = new URLSearchParams();
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
    if (filters.job_id) params.append('job_id', filters.job_id);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.min_score !== undefined) params.append('min_score', filters.min_score.toString());
    if (filters.max_score !== undefined) params.append('max_score', filters.max_score.toString());
    if (filters.decision) params.append('decision', filters.decision);

    const response = await apiClient.get<EvaluationListResponse>(`/api/admin/evaluations?${params.toString()}`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch evaluations.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Delete a job (admin only)
 */
export const deleteJob = async (jobId: string): Promise<{ message: string; job_id: string }> => {
  try {
    const response = await apiClient.delete<{ message: string; job_id: string }>(`/api/jobs/${jobId}`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to delete job.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Export applications to CSV (admin only)
 */
export const exportApplications = async (filters: ListFilters = {}): Promise<Blob> => {
  try {
    const params = new URLSearchParams();
    if (filters.job_id) params.append('job_id', filters.job_id);
    if (filters.user_id) params.append('user_id', filters.user_id);
    if (filters.status) params.append('status_filter', filters.status);

    const response = await apiClient.get(`/api/admin/export/applications?${params.toString()}`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to export applications.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Export users to CSV (admin only)
 */
export const exportUsers = async (): Promise<Blob> => {
  try {
    const response = await apiClient.get('/api/admin/export/users', {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to export users.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Export evaluations to CSV (admin only)
 */
export const exportEvaluations = async (filters: ListFilters = {}): Promise<Blob> => {
  try {
    const params = new URLSearchParams();
    if (filters.job_id) params.append('job_id', filters.job_id);
    if (filters.user_id) params.append('user_id', filters.user_id);

    const response = await apiClient.get(`/api/admin/export/evaluations?${params.toString()}`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to export evaluations.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Get system settings (admin only)
 */
export const getSettings = async (): Promise<SystemSettingsResponse> => {
  try {
    const response = await apiClient.get<SystemSettingsResponse>('/api/admin/settings');
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch settings.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Update system settings (admin only)
 */
export const updateSettings = async (settings: SystemSettings): Promise<SystemSettingsResponse> => {
  try {
    const response = await apiClient.put<SystemSettingsResponse>('/api/admin/settings', settings);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to update settings.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * List all CV trend scores (admin only)
 */
export const listAllCVTrendScores = async (weekId?: string): Promise<CVTrendScoreListResponse> => {
  try {
    const params = new URLSearchParams();
    if (weekId) params.append('week_id', weekId);

    const response = await apiClient.get<CVTrendScoreListResponse>(`/api/trends/cv/calculate?${params.toString()}`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch CV trend scores.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

