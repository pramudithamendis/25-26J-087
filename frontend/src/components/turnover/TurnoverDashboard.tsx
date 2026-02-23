import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import TurnoverJobDetailsForm from './TurnoverJobDetailsForm';
import TurnoverPredictionResults from './TurnoverPredictionResults';
import TurnoverSHAPExplanation from './TurnoverSHAPExplanation';
import TurnoverRiskFactors from './TurnoverRiskFactors';
import TurnoverCounterfactuals from './TurnoverCounterfactuals';
import { useTurnoverPrediction } from '../../hooks/useTurnoverPrediction';
import { PREDICTION_STATUS } from '../../utils/turnover-constants';
import './TurnoverDashboard.css';

const TurnoverDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { prediction, loading, error, status, predict, reset } = useTurnoverPrediction();
 
  // Get CV ID from URL params or localStorage
  const [cvId, setCvId] = useState<string>('');

  useEffect(() => {
    // Try to get CV ID from URL params
    const params = new URLSearchParams(window.location.search);
    const urlCvId = params.get('cv_id');
   
    if (urlCvId) {
      setCvId(urlCvId);
    } else {
      // Fallback to localStorage (if CV was just uploaded)
      const storedCvId = localStorage.getItem('last_uploaded_cv_id');
      if (storedCvId) {
        setCvId(storedCvId);
      } else {
        // No CV ID found, redirect to CV upload
        navigate('/cv/upload');
      }
    }
  }, [navigate]);

  const handlePredictionSubmit = (jobDescription: string, jobLocation: string) => {
    predict({
      cv_id: cvId,
      job_description: jobDescription,
      job_location: jobLocation || undefined
    });
  };

  const handleReset = () => {
    reset();
  };

  const handleBackToUpload = () => {
    navigate('/cv/upload');
  };

  const handleViewHistory = () => {
    navigate('/turnover/history');
  };

  return (
    <div className="turnover-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <button
          className="back-button"
          onClick={handleBackToUpload}
        >
          <ArrowLeft size={20} />
          Back to CV Upload
        </button>
        <h1>Turnover Risk Prediction</h1>
        <p className="subtitle">
          Predict early attrition risk using pre-hire data analysis
        </p>
        <button
          className="back-button"
          onClick={handleViewHistory}
          style={{ marginTop: '0.5rem' }}
        >
          <RefreshCw size={20} />
          View History
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={handleReset}>Dismiss</button>
        </div>
      )}

      {/* Main Content */}
      <div className="dashboard-content">
        {status === PREDICTION_STATUS.IDLE && (
          <TurnoverJobDetailsForm
            cvId={cvId}
            onSubmit={handlePredictionSubmit}
            loading={loading}
          />
        )}

        {/* LOADING STATE - Show while calculating */}
        {status === PREDICTION_STATUS.LOADING && (
          <div className="loading-container">
            <div className="loading-card">
              <div className="loading-spinner"></div>
              <h2>Analyzing Candidate Profile...</h2>
              <p>This may take a few moments</p>
              <div className="loading-steps">
                <div className="step">
                  <div className="step-icon">✓</div>
                  <span>Processing CV data</span>
                </div>
                <div className="step">
                  <div className="step-icon">✓</div>
                  <span>Analyzing job requirements</span>
                </div>
                <div className="step active">
                  <div className="step-icon">
                    <div className="mini-spinner"></div>
                  </div>
                  <span>Calculating risk factors with SHAP</span>
                </div>
                <div className="step pending">
                  <div className="step-icon">○</div>
                  <span>Generating recommendations</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {status === PREDICTION_STATUS.SUCCESS && prediction && (
          <>
            <div className="results-actions">
              <button
                className="reset-button"
                onClick={handleReset}
              >
                <RefreshCw size={18} />
                New Prediction
              </button>
            </div>

            {/* 1. Show the prediction result first */}
            <TurnoverPredictionResults prediction={prediction} />
           
            {/* 2. THEN show SHAP explanation (WHY this prediction?) */}
            <TurnoverSHAPExplanation shapExplanation={prediction.shap_explanation} />
           
            {/* 3. Show risk factors (What are the concerns?) */}
            <TurnoverRiskFactors riskFactors={prediction.risk_factors} />
           
            {/* 4. Finally show counterfactuals (How to improve?) */}
            <TurnoverCounterfactuals counterfactuals={prediction.counterfactuals} />
          </>
        )}
      </div>
    </div>
  );
};

export default TurnoverDashboard;