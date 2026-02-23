import { useState } from 'react';
import type {
  TurnoverPredictionRequest,
  TurnoverPredictionResponse
} from '../types/turnover.types';
import { predictTurnover, validateJobDescription } from '../services/turnover-api.service';
import { PREDICTION_STATUS } from '../utils/turnover-constants';

type PredictionStatus = typeof PREDICTION_STATUS[keyof typeof PREDICTION_STATUS];

interface UseTurnoverPredictionReturn {
  prediction: TurnoverPredictionResponse | null;
  loading: boolean;
  error: string | null;
  status: PredictionStatus;
  predict: (data: TurnoverPredictionRequest) => Promise<void>;
  reset: () => void;
}

export const useTurnoverPrediction = (): UseTurnoverPredictionReturn => {
  const [prediction, setPrediction] = useState<TurnoverPredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<PredictionStatus>(PREDICTION_STATUS.IDLE);

  const predict = async (data: TurnoverPredictionRequest) => {
    // Validate job description
    const validation = validateJobDescription(data.job_description);
    if (!validation.valid) {
      setError(validation.error || 'Invalid job description');
      setStatus(PREDICTION_STATUS.ERROR);
      return;
    }

    setLoading(true);
    setError(null);
    setStatus(PREDICTION_STATUS.LOADING);

    try {
      const result = await predictTurnover(data);
      setPrediction(result);
      setStatus(PREDICTION_STATUS.SUCCESS);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to predict turnover risk';
      setError(errorMessage);
      setStatus(PREDICTION_STATUS.ERROR);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setPrediction(null);
    setError(null);
    setStatus(PREDICTION_STATUS.IDLE);
  };

  return {
    prediction,
    loading,
    error,
    status,
    predict,
    reset
  };
};
