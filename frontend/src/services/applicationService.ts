import apiClient from '../config/api';
import type { ApplicationData, ApplicationResponse, ApiError } from '../types/applicationTypes';

/**
 * Application Service
 * Handles job application submissions
 */

export interface ApplicationStatusResponse {
  has_applied: boolean;
  application_id?: string;
}

export interface ApplicationCountResponse {
  count: number;
}

/**
 * Apply to a job posting
 * Updates user profile and returns immediate confirmation
 */
export const applyToJob = async (
  jobId: string,
  applicationData: ApplicationData
): Promise<{ message: string; application_id: string; status: string }> => {
  try {
    const formData = new FormData();

    // Add text fields
    if (applicationData.first_name) {
      formData.append('first_name', applicationData.first_name);
    }
    if (applicationData.last_name) {
      formData.append('last_name', applicationData.last_name);
    }
    if (applicationData.city) {
      formData.append('city', applicationData.city);
    }
    if (applicationData.phone_number) {
      formData.append('phone_number', applicationData.phone_number);
    }
    // Always send URLs (even if empty string) to ensure they're saved/updated in profile
    // This allows URLs to persist across multiple applications
    formData.append('github_url', applicationData.github_url || '');
    formData.append('linkedin_url', applicationData.linkedin_url || '');

    // Add file uploads
    if (applicationData.resume) {
      formData.append('resume', applicationData.resume);
    }
    if (applicationData.linkedin_resume) {
      formData.append('linkedin_resume', applicationData.linkedin_resume);
    }

    const response = await apiClient.post<{ message: string; application_id: string; status: string }>(
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
      detail: error.response?.data?.detail || 'Failed to submit application.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Check if current user has applied to a job
 */
export const checkApplicationStatus = async (
  jobId: string
): Promise<ApplicationStatusResponse> => {
  try {
    const response = await apiClient.get<ApplicationStatusResponse>(
      `/api/jobs/${jobId}/application-status`
    );
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to check application status.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Get application count for a job
 */
export const getApplicationCount = async (
  jobId: string
): Promise<ApplicationCountResponse> => {
  try {
    const response = await apiClient.get<ApplicationCountResponse>(
      `/api/jobs/${jobId}/applications/count`
    );
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to get application count.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

