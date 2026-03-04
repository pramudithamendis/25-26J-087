import apiClient from '../config/api';

import type { CVSubmitResponse, CVListResponse, CVParsed } from '../types/cv.types';

/**
 * Upload and parse CV
 */
export const uploadCV = async (file: File): Promise<CVSubmitResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<CVSubmitResponse>(
      '/cv/submit',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    // Store CV ID for easy access
    localStorage.setItem('last_uploaded_cv_id', response.data.data.cv_id);

    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'CV upload failed');
  }
};

/**
 * Get list of user's CVs
 */
export const listCVs = async (): Promise<CVListResponse> => {
  try {
    const response = await apiClient.get<CVListResponse>('/cv/list');
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch CVs');
  }
};

/**
 * Get specific CV by ID
 */
export const getCVById = async (cvId: string): Promise<CVParsed> => {
  try {
    const response = await apiClient.get<CVParsed>(`/cv/${cvId}`);
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch CV');
  }
};

/**
 * Update CV data
 */
export const updateCV = async (cvId: string, data: Partial<CVParsed>): Promise<CVParsed> => {
  try {
    const response = await apiClient.put<CVParsed>(`/cv/${cvId}`, data);
    return response.data;
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Failed to update CV');
  }
};