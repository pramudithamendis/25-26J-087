import apiClient from '../config/api';

import type {
  TurnoverPredictionRequest,
  TurnoverPredictionResponse,
  TurnoverHealthResponse
} from '../types/turnover.types';

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

    const response = await apiClient.post<TurnoverPredictionResponse>(
      '/turnover/predict',
      formData
    );

    return response.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.detail ||
      'Failed to predict turnover risk'
    );
  }
};

/**
 * Check if turnover prediction model is loaded
 */
export const checkTurnoverHealth = async (): Promise<TurnoverHealthResponse> => {
  try {
    const response = await apiClient.get<TurnoverHealthResponse>('/turnover/health');
    return response.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.detail ||
      'Failed to check model health'
    );
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