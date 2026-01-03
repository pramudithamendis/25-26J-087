import apiClient from '../config/api';
import type { EvaluationResponse, ApiError } from '../types/evaluationTypes';

/**
 * Evaluation Service
 * Handles all evaluation-related API calls
 */

export const getEvaluation = async (
  evaluationId: string
): Promise<EvaluationResponse> => {
  try {
    const response = await apiClient.get<EvaluationResponse>(
      `/api/evaluations/${evaluationId}`
    );
    return response.data;
  } catch (error: any) {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'Failed to fetch evaluation.',
      statusCode: error.response?.status,
    };
    throw apiError;
  }
};

