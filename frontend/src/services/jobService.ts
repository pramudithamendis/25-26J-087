import apiClient from '../config/api';
import type {
  JobCreate,
  JobResponse,
  JobUpdate,
  JobListResponse,
  ApiError,
} from '../types/jobTypes';

/**
 * Job Service
 * Handles all job-related API calls
 */

export const createJob = async (job: JobCreate): Promise<JobResponse> => {
  try {
    const response = await apiClient.post<JobResponse>('/api/jobs', job);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to create job.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

export const listJobs = async (): Promise<JobListResponse> => {
  try {
    const response = await apiClient.get<JobListResponse>('/api/jobs');
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch jobs.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

export const getJob = async (jobId: string): Promise<JobResponse> => {
  try {
    const response = await apiClient.get<JobResponse>(`/api/jobs/${jobId}`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch job.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

export const updateJob = async (
  jobId: string,
  job: JobUpdate
): Promise<JobResponse> => {
  try {
    const response = await apiClient.put<JobResponse>(`/api/jobs/${jobId}`, job);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to update job.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

export interface ApplyToJobResponse {
  message: string;
  application_id: string;
  status: string;
}

/**
 * Apply to a job with CV file and optional LinkedIn PDF
 */
export const applyToJob = async (
  jobId: string,
  resumeFile?: File,
  linkedinFile?: File
): Promise<ApplyToJobResponse> => {
  try {
    const formData = new FormData();
    if (resumeFile) {
      formData.append('resume', resumeFile);
    }
    if (linkedinFile) {
      formData.append('linkedin_resume', linkedinFile);
    }

    const response = await apiClient.post<ApplyToJobResponse>(
      `/api/jobs/${jobId}/apply`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to apply to job.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

export interface UserApplicationStatus {
  application_id: string;
  job_id: string;
  status: 'submitted' | 'under_review' | 'reviewed';
  created_at: string;
  job_title?: string;
}

export const getMyApplicationStatus = async (jobId: string): Promise<UserApplicationStatus> => {
  try {
    const response = await apiClient.get<UserApplicationStatus>(`/api/jobs/${jobId}/my-application-status`);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch application status.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};
