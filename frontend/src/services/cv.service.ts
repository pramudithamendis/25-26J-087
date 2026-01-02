import axios from 'axios';
import type { CVSubmitResponse, CVListResponse, CVParsed } from '../types/cv.types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Upload and parse CV
 */
export const uploadCV = async (file: File): Promise<CVSubmitResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('access_token');
    const response = await axios.post<CVSubmitResponse>(
      `${API_BASE_URL}/cv/submit`,
      formData,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    // Store CV ID for easy access
    localStorage.setItem('last_uploaded_cv_id', response.data.cv_id);

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'CV upload failed');
    }
    throw error;
  }
};

/**
 * Get list of user's CVs
 */
export const listCVs = async (): Promise<CVListResponse> => {
  try {
    const token = localStorage.getItem('access_token');
    const response = await axios.get<CVListResponse>(
      `${API_BASE_URL}/cv/list`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch CVs');
    }
    throw error;
  }
};

/**
 * Get specific CV by ID
 */
export const getCVById = async (cvId: string): Promise<CVParsed> => {
  try {
    const token = localStorage.getItem('access_token');
    const response = await axios.get<CVParsed>(
      `${API_BASE_URL}/cv/${cvId}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch CV');
    }
    throw error;
  }
};
