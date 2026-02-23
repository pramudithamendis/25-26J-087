import apiClient from '../../config/api';
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, History } from 'lucide-react';
import TurnoverPredictionResults from './TurnoverPredictionResults';
import TurnoverSHAPExplanation from './TurnoverSHAPExplanation';
import TurnoverRiskFactors from './TurnoverRiskFactors';
import TurnoverCounterfactuals from './TurnoverCounterfactuals';
import type { TurnoverPredictionResponse } from '../../types/turnover.types';
import './TurnoverDashboard.css';
import axios from 'axios'

const TurnoverResultsView: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const cvId = searchParams.get('cv_id');

  const [prediction, setPrediction] = useState<TurnoverPredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!cvId) {
      navigate('/dashboard/admin/turnover/history');
      return;
    }
    fetchStoredPrediction();
  }, [cvId, navigate]);

  const fetchStoredPrediction = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await apiClient.get(`/turnover/result/${cvId}`);
      
      setPrediction(response.data);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setError('No prediction found for this candidate. Please make a new prediction.');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load prediction');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBackToHistory = () => {
    navigate('/dashboard/admin/turnover/history');
  };

  const handleNewPrediction = () => {
    navigate(`/dashboard/admin/turnover?cv_id=${cvId}`);
  };

  if (loading) {
    return (
      <div className="turnover-dashboard">
        <div className="dashboard-content">
          <div className="loading-container">
            <div className="loading-card">
              <div className="loading-spinner"></div>
              <h2>Loading Prediction...</h2>
              <p>Retrieving stored results</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !prediction) {
    return (
      <div className="turnover-dashboard">
        <div className="dashboard-header">
          <button className="back-button" onClick={handleBackToHistory}>
            <ArrowLeft size={20} />
            Back to History
          </button>
          <h1>Turnover Risk Prediction</h1>
        </div>

        <div className="dashboard-content">
          <div className="error-banner">
            <span>{error || 'Failed to load prediction'}</span>
            <button onClick={handleBackToHistory}>Back to History</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="turnover-dashboard">
      <div className="dashboard-header">
        <button className="back-button" onClick={handleBackToHistory}>
          <ArrowLeft size={20} />
          Back to History
        </button>
        <h1>Turnover Risk Prediction</h1>
        
      </div>

      <div className="dashboard-content">
        <div className="results-actions">
          <button className="reset-button" onClick={handleBackToHistory}>
            <History size={18} />
            View All History
          </button>
          <button className="reset-button" onClick={handleNewPrediction} style={{ marginLeft: '0.5rem' }}>
             New Prediction
          </button>
        </div>

        {/* Show all prediction components */}
        <TurnoverPredictionResults prediction={prediction} />
        <TurnoverSHAPExplanation shapExplanation={prediction.shap_explanation} />
        <TurnoverRiskFactors riskFactors={prediction.risk_factors} />
        <TurnoverCounterfactuals counterfactuals={prediction.counterfactuals} />
      </div>
    </div>
  );
};

export default TurnoverResultsView;