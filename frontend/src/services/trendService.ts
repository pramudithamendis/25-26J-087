import apiClient from '../config/api';

export interface TrendScoreResult {
    success: boolean;
    week_id: string;
    cv_trend_score: number;
    skills_matched: Array<{ skill: string; score: number }>;
}

/**
 * Calculate trend score for a single CV
 */
export const calculateCVTrendScore = async (cvId: string): Promise<TrendScoreResult> => {
    try {
        const response = await apiClient.post<TrendScoreResult>(`/api/trends/cv/${cvId}/calculate`);
        return response.data;
    } catch (error: any) {
        throw new Error(error.response?.data?.detail || 'Failed to calculate trend score');
    }
};
