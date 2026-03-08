import apiClient from '../config/api';

export interface TrendScoreResult {
    success: boolean;
    week_id: string;
    cv_trend_score: number;
    skills_matched: Array<{
        skill: string;
        trend_score: number;
        forecast_score: number;
        combined_score: number;
    }>;
}

export interface JobEvaluationResult {
    week_id: string;
    job_id: string;
    average_score: number;        // Average trend score of applicants
    applicant_count: number;      // Number of applicants for this job
    scores: Array<{
        cv_id: string;
        cv_trend_score: number;
    }>;
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

/**
 * Get job evaluation: average score & applicants for a specific job
 */
export const getJobEvaluation = async (jobId: string): Promise<JobEvaluationResult> => {
    try {
        const response = await apiClient.get<JobEvaluationResult>(`/api/trends/${jobId}/evaluation`);
        return response.data;
    } catch (error: any) {
        throw new Error(error.response?.data?.detail || 'Failed to fetch job evaluation');
    }
};
