import React from 'react';
import {
  AlertCircle, User, Lightbulb, ThumbsUp, ThumbsDown,
  Zap, CircleCheckBig, TriangleAlert, CheckCircle2, AlertTriangle, MessageSquare
} from 'lucide-react';
import type { TurnoverPredictionResponse } from '../../types/turnover.types';
import { RISK_LABELS } from '../../utils/turnover-constants';
import './TurnoverPredictionResults.css';

interface TurnoverPredictionResultsProps {
  prediction: TurnoverPredictionResponse;
}

const RISK_LEVEL_CONFIG = {
  0: {
    label: 'Early Exit Risk (0-6 months)',
    badgeClass: 'risk-badge-high',
    cardClass: 'risk-card-high',
    icon: <TriangleAlert size={20} />,
  },
  1: {
    label: 'First-Year Exit Risk (6-12 months)',
    badgeClass: 'risk-badge-medium',
    cardClass: 'risk-card-medium',
    icon: <Zap size={20} />,
  },
  2: {
    label: 'First-Year Retention Likely (>12 months)',
    badgeClass: 'risk-badge-low',
    cardClass: 'risk-card-low',
    icon: <CircleCheckBig size={20} />,
  },
};

const getRecommendation = (riskLevel: number) => {
  if (riskLevel === 2) return {
    title: "Strong Candidate - Recommend to Hire",
    description: "This candidate shows excellent stability indicators and strong fit for the role. They are likely to stay long-term and contribute effectively.",
  };
  if (riskLevel === 1) return {
    title: "Proceed with Caution",
    description: "This candidate has some concerns but could be a good fit. Consider discussing career goals, work environment expectations, and long-term plans during interview.",
  };
  return {
    title: "High Risk - Careful Evaluation Needed",
    description: "This candidate shows warning signs for early departure. If proceeding, have frank discussions about expectations, provide strong onboarding support, and ensure competitive compensation.",
  };
};

const getModelCertainty = (confidence: number): string => {
  if (confidence >= 0.85) return 'Very High Certainty';
  if (confidence >= 0.70) return 'High Certainty';
  if (confidence >= 0.55) return 'Moderate Certainty';
  if (confidence >= 0.40) return 'Low Certainty';
  return 'Very Low Certainty';
};

const getLikelihoodLabel = (probability: number): string => {
  if (probability >= 0.7) return 'Very Likely';
  if (probability >= 0.5) return 'Likely';
  if (probability >= 0.3) return 'Possible';
  if (probability >= 0.1) return 'Unlikely';
  return 'Very Unlikely';
};

const TurnoverPredictionResults: React.FC<TurnoverPredictionResultsProps> = ({ prediction }) => {
  const { prediction: pred, cv_name, features } = prediction;
  const riskConfig = RISK_LEVEL_CONFIG[pred.risk_level as keyof typeof RISK_LEVEL_CONFIG];
  const recommendation = getRecommendation(pred.risk_level);

  return (
    <div className="turnover-prediction-results">

      {/* Header */}
      <div className="results-header">
        <div className="candidate-info">
          <div className="user-icon"><User size={22} /></div>
          <div className="candidate-details"> 
            <h3>Assessment for {cv_name}</h3>
            <p className="candidate-name">Turnover Risk Analysis</p>
          </div>
          <div className={`risk-badge ${riskConfig.badgeClass}`}>
            {riskConfig.icon}
            {RISK_LABELS[pred.risk_level as keyof typeof RISK_LABELS]}
          </div>
        </div>
      </div>

      {/* Risk Card */}
      <div className={`risk-card ${riskConfig.cardClass}`}>

        {/* Certainty */}
        <p className="confidence">
          Assessment Confidence: <strong>{getModelCertainty(pred.confidence)}</strong>
        </p>

        {/* Recommendation */}
        <div className="hr-recommendation">
          <div className="recommendation-icon">
            <MessageSquare size={18} />
          </div>
          <div className="recommendation-content">
            <h3>{recommendation.title}</h3>
            <p>{recommendation.description}</p>
          </div>
        </div>

        {/* Probability Breakdown */}
        
      </div>

      {/* Strengths & Concerns */}
      <div className="strengths-concerns-grid">

        <div className="strengths-card">
          <div className="card-header">
            <ThumbsUp size={18} className="card-icon" />
            <h3>Strengths</h3>
          </div>
          <ul className="points-list">
            {features.skill_match >= 0.7 && (
              <li className="point-item success">
                <CheckCircle2 size={15} className="point-icon" />
                <span>Strong skill alignment with job requirements</span>
              </li>
            )}
            {features.exp_match >= 0.7 && (
              <li className="point-item success">
                <CheckCircle2 size={15} className="point-icon" />
                <span>Experience level fits well with position requirements</span>
              </li>
            )}
            {features.location_match >= 0.7 && (
              <li className="point-item success">
                <CheckCircle2 size={15} className="point-icon" />
                <span>Convenient commute distance. Less likely to leave due to travel</span>
              </li>
            )}
            {features.avg_tenure_months >= 24 && (
              <li className="point-item success">
                <CheckCircle2 size={15} className="point-icon" />
                <span>Stays an average of {(features.avg_tenure_months / 12).toFixed(1)} years per job. Shows commitment</span>
              </li>
            )}
            {features.job_hopping_rate < 0.3 && (
              <li className="point-item success">
                <CheckCircle2 size={15} className="point-icon" />
                <span>Stable work history with minimal job hopping</span>
              </li>
            )}
            {features.overall_match >= 0.7 && (
              <li className="point-item success">
                <CheckCircle2 size={15} className="point-icon" />
                <span>Overall excellent fit for this position ({(features.overall_match * 100).toFixed(0)}% match)</span>
              </li>
            )}
          </ul>
        </div>

        <div className="concerns-card">
          <div className="card-header">
            <ThumbsDown size={18} className="card-icon" />
            <h3>Concerns</h3>
          </div>
          <ul className="points-list">
            {features.skill_match < 0.5 && (
              <li className="point-item warning">
                <AlertTriangle size={15} className="point-icon" />
                <span>Limited skill overlap with job requirements (only {(features.skill_match * 100).toFixed(0)}% match)</span>
              </li>
            )}
            {features.job_hopping_rate >= 0.5 && (
              <li className="point-item warning">
                <AlertTriangle size={15} className="point-icon" />
                <span>Frequent job changes.  {(features.job_hopping_rate * 100).toFixed(0)}% of jobs were short-term</span>
              </li>
            )}
            {features.avg_tenure_months < 12 && (
              <li className="point-item warning">
                <AlertTriangle size={15} className="point-icon" />
                <span>Short average tenure of {features.avg_tenure_months.toFixed(0)} months per job</span>
              </li>
            )}
            {features.location_match < 0.5 && (
              <li className="point-item warning">
                <AlertTriangle size={15} className="point-icon" />
                <span>Long commute distance may lead to dissatisfaction</span>
              </li>
            )}
            {features.total_experience < 2 && (
              <li className="point-item warning">
                <AlertTriangle size={15} className="point-icon" />
                <span>Limited overall work experience ({features.total_experience.toFixed(1)} years)</span>
              </li>
            )}
            {features.exp_match < 0.5 && (
              <li className="point-item warning">
                <AlertTriangle size={15} className="point-icon" />
                <span>Experience level doesn't align well with position</span>
              </li>
            )}
          </ul>
        </div>
      </div>

      {/* Career Profile */}
      <div className="profile-summary-card">
        <h3>Career Profile at a Glance</h3>
        <div className="profile-stats">
          <div className="stat-box">
            <span className="stat-label">Total Experience</span>
            <span className="stat-value1">{features.total_experience.toFixed(1)} years</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Number of Jobs</span>
            <span className="stat-value1">{features.total_jobs}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Average Time per Job</span>
            <span className="stat-value1">{(features.avg_tenure_months / 12).toFixed(1)} years</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Skill Overlap</span>
            <span className="stat-value-label">
              {features.skill_match >= 0.6
                ? 'Good Overlap'
                : features.skill_match >= 0.35
                ? 'Partial Overlap'
                : 'Limited Overlap'}
            </span>
          </div>
        </div>
      </div>

      {/* Interview Tips */}
      <div className="interview-tips-card">
        <div className="interview-tips-header">
          <Lightbulb size={18} />
          <h3>Recommended Interview Discussion Points</h3>
        </div>
        <ul className="tips-list">
          {pred.risk_level === 2 ? (
            <>
              <li>
                <MessageSquare size={14} />
                <span>Ask about long-term career goals and how this role fits into their plans</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Discuss what motivates them and keeps them engaged in their work</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Explore their expectations for growth and development opportunities</span>
              </li>
            </>
          ) : pred.risk_level === 1 ? (
            <>
              <li>
                <MessageSquare size={14} />
                <span>Ask about long-term career goals and what would make them stay</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Discuss work-life balance expectations and commute concerns</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Explore their expectations for growth and development opportunities</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Clarify role expectations to ensure alignment</span>
              </li>
            </>
          ) : (
            <>
              {pred.risk_level === 0 && features.total_jobs > 1 && (
                <li>
                  <AlertTriangle size={14} />
                  <span><strong>Critical:</strong> Understand their reasons for frequent job changes</span>
                </li>
              )}
              <li>
                <AlertTriangle size={14} />
                <span><strong>Critical:</strong> Ask what would make them stay long-term at a company</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Discuss work-life balance expectations and commute concerns</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Explore if there are skill gaps and their willingness to learn</span>
              </li>
              <li>
                <MessageSquare size={14} />
                <span>Clarify role expectations to ensure alignment</span>
              </li>
            </>
          )}
        </ul>
      </div>

      {/* Disclaimer */}
      <div className="info-note">
        <AlertCircle size={15} />
        <p>
          This assessment is based on historical patterns and should be used as <strong>one input</strong> in your hiring decision.
          Always combine with interview performance, cultural fit assessment, reference checks, and your professional judgment.
        </p>
      </div>

    </div>
  );
};

export default TurnoverPredictionResults;