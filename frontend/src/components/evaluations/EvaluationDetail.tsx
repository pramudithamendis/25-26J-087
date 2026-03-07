import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../Button';
import { Alert } from '../Alert';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ScoreBreakdown } from './ScoreBreakdown';
import { RolePredictions } from './RolePredictions';
import { getEvaluation } from '../../services/evaluationService';
import type { EvaluationResponse } from '../../types/evaluationTypes';

interface EvaluationDetailProps {
  evaluationId: string;
}

export const EvaluationDetail = ({ evaluationId }: EvaluationDetailProps) => {
  const navigate = useNavigate();
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEvaluation();
  }, [evaluationId]);

  const loadEvaluation = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getEvaluation(evaluationId);
      setEvaluation(data);
    } catch (err: any) {
      setError(err.detail || 'Failed to load evaluation');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !evaluation) {
    return (
      <div>
        <Alert type="error">{error || 'Evaluation not found'}</Alert>
        <Button
          variant="outline"
          onClick={() => navigate('/dashboard/evaluations')}
          className="mt-4"
        >
          Back to Evaluations
        </Button>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getDecisionColor = (decision: string) => {
    if (decision === 'Proceed') return 'bg-green-100 text-green-800';
    if (decision === 'Review') return 'bg-yellow-100 text-yellow-800';
    if (decision === 'Do Not Proceed') return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div>
      <div className="mb-6">
        <Button
          variant="outline"
          onClick={() => navigate('/dashboard/evaluations')}
        >
          ← Back to Evaluations
        </Button>
      </div>

      <div className="space-y-6">
        {/* Score and Decision Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Evaluation Results
              </h2>
              <p className="text-sm text-gray-600">
                User ID: {evaluation.user_id} • Job ID: {evaluation.job_id}
              </p>
            </div>
            <div className="text-right">
              <div className={`text-4xl font-bold ${getScoreColor(evaluation.total_score)}`}>
                {evaluation.total_score}
              </div>
              <div className="text-sm text-gray-500">Total Score</div>
            </div>
          </div>

          <div className="mb-6">
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getDecisionColor(evaluation.decision)}`}
            >
              {evaluation.decision}
            </span>
          </div>

          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className={`h-4 rounded-full transition-all ${
                evaluation.total_score >= 75
                  ? 'bg-green-600'
                  : evaluation.total_score >= 60
                  ? 'bg-yellow-600'
                  : 'bg-red-600'
              }`}
              style={{ width: `${evaluation.total_score}%` }}
            />
          </div>
        </div>

        {/* Role Predictions */}
        {evaluation.role_predictions.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <RolePredictions predictions={evaluation.role_predictions} />
          </div>
        )}

        {/* Score Breakdown */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <ScoreBreakdown breakdown={evaluation.breakdown} />
        </div>

        {/* Explanations */}
        {evaluation.why.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Evaluation Summary
            </h3>
            <ul className="space-y-2">
              {evaluation.why.map((reason, index) => (
                <li
                  key={index}
                  className="flex items-start gap-3 text-sm text-gray-700"
                >
                  <span className="text-blue-600 mt-0.5">•</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Metadata */}
        {evaluation.created_at && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-500">
              Created: {new Date(evaluation.created_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

