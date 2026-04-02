import apiClient from '../config/api';

import type {
  TurnoverPredictionRequest,
  TurnoverPredictionResponse,
  TurnoverHealthResponse
} from '../types/turnover.types';

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
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return response.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.detail ||
      'Failed to predict early attrition risk'
    );
  }
};

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

export const formatConfidence = (confidence: number): string => {
  return `${(confidence * 100).toFixed(1)}%`;
};

export const getRiskLevelText = (riskLevel: number): string => {
  const labels = {
    0: 'High Early Attrition Risk',
    1: 'Moderate Early Attrition Risk',
    2: 'Low Early Attrition Risk'
  };
  return labels[riskLevel as keyof typeof labels] || 'Unknown';
};

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