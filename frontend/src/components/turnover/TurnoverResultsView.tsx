import apiClient from '../../config/api';
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, MapPin, ChevronDown, ChevronUp } from 'lucide-react';
import TurnoverPredictionResults from './TurnoverPredictionResults';
import TurnoverSHAPExplanation from './TurnoverSHAPExplanation';
import TurnoverRiskFactors from './TurnoverRiskFactors';
import TurnoverCounterfactuals from './TurnoverCounterfactuals';
import type { TurnoverPredictionResponse } from '../../types/turnover.types';
import './TurnoverDashboard.css';
import { Button } from '../Button';
import axios from 'axios';

const TurnoverResultsView: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const cvId = searchParams.get('cv_id');
  const resultId = searchParams.get('result_id');
  const [prediction, setPrediction] = useState<TurnoverPredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showJD, setShowJD] = useState(false);

  useEffect(() => {
    if (!cvId && !resultId) {
      navigate('/dashboard/admin/turnover/history');
      return;
    }
    fetchStoredPrediction();
  }, [cvId, resultId, navigate]);

  const fetchStoredPrediction = async () => {
    setLoading(true);
    setError('');

    try {
      const endpoint = resultId
        ? `/turnover/result-by-id/${resultId}`
        : `/turnover/result/${cvId}`;
      const response = await apiClient.get(endpoint);
      setPrediction(response.data);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setError('No turnover assessment found for this candidate. Please make a new assessment.');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load turnover assessment');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBackToHistory = () => {
    navigate('/dashboard/admin/turnover/history');
  };

  const handleNewPrediction = () => {
    navigate('/dashboard/admin/turnover/new');
  };

  if (loading) {
    return (
      <div className="turnover-dashboard">
        <div className="dashboard-content">
          <div className="loading-container">
            <div className="loading-card">
              <div className="loading-spinner"></div>
              <h2>Loading turnover assessment...</h2>
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
          <Button variant="outline" onClick={handleBackToHistory}>
            <ArrowLeft size={16} />
            Back to History
          </Button>
          <h1>Early Attrition Risk Assessment</h1>
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
      <Button variant="outline" onClick={handleBackToHistory}>
        <ArrowLeft size={16} />
        Back to History
      </Button>
      
      <Button variant="primary" onClick={handleNewPrediction}>
        New Early Attrition Risk Assessment
      </Button>
      
    </div>

      <div className="dashboard-content">
      <h1>Early Attrition Risk Assessment</h1>
        {/* Job Details Section */}
        {(prediction.job_description || prediction.job_location) && (
          <div className="shap-explanation-card" style={{ marginBottom: '1rem' }}>
            <div
              className="section-header"
              onClick={() => setShowJD(!showJD)}
              style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <h3>Job Details</h3>
              {showJD ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </div>
            {showJD && (
              <div style={{ marginTop: '1rem' }}>
                {prediction.job_location && (
                  <div style={{
                    marginBottom: '0.75rem',
                    padding: '0.5rem 1rem',
                    background: '#eff6ff',
                    borderRadius: '8px',
                    color: '#1d4ed8',
                    fontWeight: '500',
                    fontSize: '0.9rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem'
                  }}>
                    <MapPin size={14} />
                    {prediction.job_location}
                  </div>
                )}
                {prediction.job_description && (
                  <div style={{
                    padding: '1rem',
                    background: '#f9fafb',
                    borderRadius: '8px',
                    whiteSpace: 'pre-wrap',
                    fontSize: '0.9rem',
                    color: '#374151',
                    lineHeight: '1.6'
                  }}>
                    {prediction.job_description}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <TurnoverPredictionResults prediction={prediction} />
        <TurnoverSHAPExplanation shapExplanation={prediction.shap_explanation} />
        <TurnoverRiskFactors riskFactors={prediction.risk_factors} />
        <TurnoverCounterfactuals counterfactuals={prediction.counterfactuals} />

      </div>
    </div>
  );
};

export default TurnoverResultsView;