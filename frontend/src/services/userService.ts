import apiClient from '../config/api';
import type { User, ApiError } from '../types/auth';

/**
 * User Profile Service
 * Handles all user profile-related API calls
 */

export interface UserUpdate {
  name?: string;
  github_handle?: string;
  github_url?: string;
  linkedin_url?: string;
}

export interface UploadResponse {
  message: string;
  file_path: string;
}

/**
 * Get current user's full profile
 */
export const getCurrentUserProfile = async (): Promise<User> => {
  try {
    const response = await apiClient.get<User>('/users/me');
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch user profile.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Update user profile (name, github_handle)
 */
export const updateProfile = async (
  update: UserUpdate
): Promise<User> => {
  try {
    const response = await apiClient.put<User>('/users/me', update);
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to update profile.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Upload CV PDF for current user
 */
export const uploadUserCV = async (file: File): Promise<UploadResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<UploadResponse>(
      '/users/me/upload-cv',
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
      detail: error.response?.data?.detail || 'Failed to upload CV.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

/**
 * Upload LinkedIn PDF for current user
 */
export const uploadLinkedIn = async (file: File): Promise<UploadResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<UploadResponse>(
      '/users/me/upload-linkedin',
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
      detail: error.response?.data?.detail || 'Failed to upload LinkedIn PDF.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

