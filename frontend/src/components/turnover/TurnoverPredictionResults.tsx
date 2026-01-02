import React from 'react';
import { AlertCircle, User } from 'lucide-react';
import type { TurnoverPredictionResponse } from '../../types/turnover.types';
import { RISK_LABELS, RISK_COLORS, RISK_BACKGROUNDS } from '../../utils/turnover-constants';
import './TurnoverPredictionResults.css';

interface TurnoverPredictionResultsProps {
  prediction: TurnoverPredictionResponse;
}

const getRecommendation = (riskLevel: number): { title: string; description: string; emoji: string } => {
  if (riskLevel === 2) {
    return {
      title: "Strong Candidate - Recommend to Hire",
      description: "This candidate shows excellent stability indicators and strong fit for the role. They are likely to stay long-term and contribute effectively.",
      emoji: "✅"
    };
  } else if (riskLevel === 1) {
    return {
      title: "Proceed with Caution",
      description: "This candidate has some concerns but could be a good fit. Consider discussing career goals, work environment expectations, and long-term plans during interview.",
      emoji: "⚠️"
    };
  } else {
    return {
      title: "High Risk - Careful Evaluation Needed",
      description: "This candidate shows warning signs for early departure. If proceeding, have frank discussions about expectations, provide strong onboarding support, and ensure competitive compensation.",
      emoji: "🚨"
    };
  }
};

const getModelCertainty = (confidence: number): string => {
  if (confidence >= 0.85) return 'Very High Certainty';
  if (confidence >= 0.70) return 'High Certainty';
  if (confidence >= 0.55) return 'Moderate Certainty';
  if (confidence >= 0.40) return 'Low Certainty';
  return 'Very Low Certainty';
};

// Likelihood labels
const getLikelihoodLabel = (probability: number): { text: string; color: string } => {
  if (probability >= 0.7) return { text: 'Very Likely', color: '#ef4444' };
  if (probability >= 0.5) return { text: 'Likely', color: '#f59e0b' };
  if (probability >= 0.3) return { text: 'Possible', color: '#eab308' };
  if (probability >= 0.1) return { text: 'Unlikely', color: '#94a3b8' };
  return { text: 'Very Unlikely', color: '#cbd5e1' };
};

const TurnoverPredictionResults: React.FC<TurnoverPredictionResultsProps> = ({ prediction }) => {
  const { prediction: pred, cv_name, features } = prediction;
 
  const riskColor = RISK_COLORS[pred.risk_level as keyof typeof RISK_COLORS];
  const riskBg = RISK_BACKGROUNDS[pred.risk_level as keyof typeof RISK_BACKGROUNDS];
  const recommendation = getRecommendation(pred.risk_level);
  
  const getRiskIcon = () => {
    if (pred.risk_level === 0) return <span style={{ fontSize: '2rem' }}>⚠️</span>;
    if (pred.risk_level === 1) return <span style={{ fontSize: '2rem' }}>⚡</span>;
    return <span style={{ fontSize: '2rem' }}>✅</span>;
  };

  return (
    <div className="turnover-prediction-results">
      {/* Header */}
      <div className="results-header">
        <div className="candidate-info">
          <div className="user-icon">👤</div>
          <div>
            <h3>Assessment for {cv_name}</h3>
            <p className="candidate-name">Turnover Risk Analysis</p>
          </div>
        </div>
      </div>

      {/* Main Recommendation Card */}
      <div
        className="risk-card"
        style={{
          backgroundColor: riskBg,
          borderColor: riskColor
        }}
      >
        <div className="risk-header">
          {getRiskIcon()}
          <div>
            <h2 style={{ color: riskColor }}>
              {RISK_LABELS[pred.risk_level as keyof typeof RISK_LABELS]}
            </h2>
            <p className="confidence">
              Model Certainty: <strong>{getModelCertainty(pred.confidence)}</strong>
            </p>
          </div>
        </div>

        {/* HR Recommendation */}
        <div className="hr-recommendation">
          <div className="recommendation-emoji">{recommendation.emoji}</div>
          <div className="recommendation-content">
            <h3>{recommendation.title}</h3>
            <p>{recommendation.description}</p>
          </div>
        </div>

        {/* Likelihood Breakdown */}
        <div className="likelihood-section">
          <h4>How Long Will They Stay?</h4>
          <div className="probability-grid">
            {/* High Risk */}
            <div className="prob-item">
              <div className="prob-header">
                <span className="prob-label">Leaves within 6 months</span>
                <span 
                  className="prob-confidence-label" 
                  style={{ color: getLikelihoodLabel(pred.probabilities.high_risk).color }}
                >
                  {getLikelihoodLabel(pred.probabilities.high_risk).text}
                </span>
              </div>
              <div className="prob-bar-container">
                <div
                  className="prob-bar"
                  style={{
                    width: `${pred.probabilities.high_risk * 100}%`,
                    backgroundColor: RISK_COLORS[0]
                  }}
                />
              </div>
            </div>

            {/* Medium Risk */}
            <div className="prob-item">
              <div className="prob-header">
                <span className="prob-label">Leaves within 6-12 months</span>
                <span 
                  className="prob-confidence-label"
                  style={{ color: getLikelihoodLabel(pred.probabilities.medium_risk).color }}
                >
                  {getLikelihoodLabel(pred.probabilities.medium_risk).text}
                </span>
              </div>
              <div className="prob-bar-container">
                <div
                  className="prob-bar"
                  style={{
                    width: `${pred.probabilities.medium_risk * 100}%`,
                    backgroundColor: RISK_COLORS[1]
                  }}
                />
              </div>
            </div>

            {/* Low Risk */}
            <div className="prob-item">
              <div className="prob-header">
                <span className="prob-label">Stays more than 1 year</span>
                <span 
                  className="prob-confidence-label"
                  style={{ color: getLikelihoodLabel(pred.probabilities.low_risk).color }}
                >
                  {getLikelihoodLabel(pred.probabilities.low_risk).text}
                </span>
              </div>
              <div className="prob-bar-container">
                <div
                  className="prob-bar"
                  style={{
                    width: `${pred.probabilities.low_risk * 100}%`,
                    backgroundColor: RISK_COLORS[2]
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Candidate Strengths & Concerns */}
      <div className="strengths-concerns-grid">
        {/* Strengths */}
        <div className="strengths-card">
          <div className="card-header">
            <span className="card-emoji">👍</span>
            <h3>Strengths</h3>
          </div>
          <ul className="points-list">
            {features.skill_match >= 0.7 && (
              <li className="point-item success">
                <span className="point-emoji">✓</span>
                <span>Strong skill alignment with job requirements ({(features.skill_match * 100).toFixed(0)}% match)</span>
              </li>
            )}
            {features.exp_match >= 0.7 && (
              <li className="point-item success">
                <span className="point-emoji">✓</span>
                <span>Experience level fits well with position requirements</span>
              </li>
            )}
            {features.location_match >= 0.7 && (
              <li className="point-item success">
                <span className="point-emoji">✓</span>
                <span>Convenient commute distance - less likely to leave due to travel</span>
              </li>
            )}
            {features.avg_tenure_months >= 24 && (
              <li className="point-item success">
                <span className="point-emoji">✓</span>
                <span>Stays an average of {(features.avg_tenure_months / 12).toFixed(1)} years per job - shows commitment</span>
              </li>
            )}
            {features.job_hopping_rate < 0.3 && (
              <li className="point-item success">
                <span className="point-emoji">✓</span>
                <span>Stable work history with minimal job hopping</span>
              </li>
            )}
            {features.overall_match >= 0.7 && (
              <li className="point-item success">
                <span className="point-emoji">✓</span>
                <span>Overall excellent fit for this position ({(features.overall_match * 100).toFixed(0)}% match)</span>
              </li>
            )}
          </ul>
        </div>

        {/* Concerns */}
        <div className="concerns-card">
          <div className="card-header">
            <span className="card-emoji">👎</span>
            <h3>Concerns</h3>
          </div>
          <ul className="points-list">
            {features.skill_match < 0.5 && (
              <li className="point-item warning">
                <span className="point-emoji">⚠</span>
                <span>Limited skill overlap with job requirements (only {(features.skill_match * 100).toFixed(0)}% match)</span>
              </li>
            )}
            {features.job_hopping_rate >= 0.5 && (
              <li className="point-item warning">
                <span className="point-emoji">⚠</span>
                <span>Frequent job changes - {(features.job_hopping_rate * 100).toFixed(0)}% of jobs were short-term</span>
              </li>
            )}
            {features.avg_tenure_months < 12 && (
              <li className="point-item warning">
                <span className="point-emoji">⚠</span>
                <span>Short average tenure of {features.avg_tenure_months.toFixed(0)} months per job</span>
              </li>
            )}
            {features.location_match < 0.5 && (
              <li className="point-item warning">
                <span className="point-emoji">⚠</span>
                <span>Long commute distance may lead to dissatisfaction</span>
              </li>
            )}
            {features.total_experience < 2 && (
              <li className="point-item warning">
                <span className="point-emoji">⚠</span>
                <span>Limited overall work experience ({features.total_experience.toFixed(1)} years)</span>
              </li>
            )}
            {features.exp_match < 0.5 && (
              <li className="point-item warning">
                <span className="point-emoji">⚠</span>
                <span>Experience level doesn't align well with position</span>
              </li>
            )}
          </ul>
        </div>
      </div>

      {/* Career Profile Summary */}
      <div className="profile-summary-card">
        <h3>Career Profile at a Glance</h3>
        <div className="profile-stats">
          <div className="stat-box">
            <span className="stat-label">Total Experience</span>
            <span className="stat-value">{features.total_experience.toFixed(1)} years</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Number of Jobs</span>
            <span className="stat-value">{features.total_jobs}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Average Time per Job</span>
            <span className="stat-value">{(features.avg_tenure_months / 12).toFixed(1)} years</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Skill Match</span>
            <span className="stat-value">{(features.skill_match * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Interview Discussion Points */}
      <div className="interview-tips-card">
        <h3>💡 Recommended Interview Discussion Points</h3>
        <ul className="tips-list">
          {pred.risk_level <= 1 ? (
            <>
              <li>Ask about long-term career goals and how this role fits into their plans</li>
              <li>Discuss what motivates them and keeps them engaged in their work</li>
              <li>Explore their expectations for growth and development opportunities</li>
            </>
          ) : (
            <>
              <li><strong>Critical:</strong> Understand their reasons for frequent job changes</li>
              <li><strong>Critical:</strong> Ask what would make them stay long-term at a company</li>
              <li>Discuss work-life balance expectations and commute concerns</li>
              <li>Explore if there are skill gaps and their willingness to learn</li>
              <li>Clarify role expectations to ensure alignment</li>
            </>
          )}
        </ul>
      </div>

      {/* Disclaimer */}
      <div className="info-note">
        <AlertCircle size={16} />
        <p>
          This assessment is based on historical patterns and should be used as <strong>one input</strong> in your hiring decision.
          Always combine with interview performance, cultural fit assessment, reference checks, and your professional judgment.
        </p>
      </div>
    </div>
  );
};

export default TurnoverPredictionResults;