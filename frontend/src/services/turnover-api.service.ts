import axios from 'axios';
import type {
  TurnoverPredictionRequest,
  TurnoverPredictionResponse,
  TurnoverHealthResponse
} from '../types/turnover.types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with auth token
const createAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  };
};

// ============================================================
// TURNOVER PREDICTION ENDPOINTS
// ============================================================

/**
 * Predict turnover risk for a candidate
 */
export const predictTurnover = async (
  data: TurnoverPredictionRequest
): Promise<TurnoverPredictionResponse> => {
  try {
    const formData = new FormData();
    formData.append('cv_id', data.cv_id);
    formData.append('job_description', data.job_description);
    if (data.job_location) {
      formData.append('job_location', data.job_location);
    }

    const response = await axios.post<TurnoverPredictionResponse>(
      `${API_BASE_URL}/turnover/predict`,
      formData,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      }
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail || 
        'Failed to predict turnover risk'
      );
    }
    throw error;
  }
};

/**
 * Check if turnover prediction model is loaded
 */
export const checkTurnoverHealth = async (): Promise<TurnoverHealthResponse> => {
  try {
    const response = await axios.get<TurnoverHealthResponse>(
      `${API_BASE_URL}/turnover/health`
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail || 
        'Failed to check model health'
      );
    }
    throw error;
  }
};

// ============================================================
// HELPER FUNCTIONS
// ============================================================

/**
 * Format prediction confidence as percentage
 */
export const formatConfidence = (confidence: number): string => {
  return `${(confidence * 100).toFixed(1)}%`;
};

/**
 * Get risk level text from numeric value
 */
export const getRiskLevelText = (riskLevel: number): string => {
  const labels = {
    0: 'High Risk',
    1: 'Medium Risk',
    2: 'Low Risk'
  };
  return labels[riskLevel as keyof typeof labels] || 'Unknown';
};

/**
 * Validate job description length
 */
export const validateJobDescription = (description: string): { 
  valid: boolean; 
  error?: string 
} => {
  if (!description || description.trim().length < 50) {
    return {
      valid: false,
      error: 'Job description must be at least 50 characters'
    };
  }
  if (description.length > 5000) {
    return {
      valid: false,
      error: 'Job description must be less than 5000 characters'
    };
  }
  return { valid: true };
};
