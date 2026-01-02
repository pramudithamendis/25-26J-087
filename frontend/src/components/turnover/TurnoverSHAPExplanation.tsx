import React from 'react';
import { Lightbulb, TrendingUp, TrendingDown } from 'lucide-react';
import './TurnoverSHAPExplanation.css';

interface SHAPFeature {
  feature: string;
  value: number;
  value_display: string;
  shap_value: number;
  abs_shap_value: number;
  impact: 'increases_risk' | 'decreases_risk';
}

interface SHAPExplanation {
  base_value: number;
  prediction_value: number;
  top_features: SHAPFeature[];
  all_features: SHAPFeature[];
  explanation?: string;
}

interface TurnoverSHAPExplanationProps {
  shapExplanation: SHAPExplanation | null;
}

// Human-readable feature names and explanations
const FEATURE_EXPLANATIONS: Record<string, { 
  label: string; 
  increasesRisk: string; 
  decreasesRisk: string;
}> = {
  'job_hopping_rate': {
    label: 'Job Stability',
    increasesRisk: 'Frequent job changes in the past suggest they may leave soon',
    decreasesRisk: 'Stable job history indicates they typically stay long-term'
  },
  'avg_tenure_months': {
    label: 'Average Time per Job',
    increasesRisk: 'Short average tenure suggests difficulty committing long-term',
    decreasesRisk: 'Long average tenure shows they commit to employers'
  },
  'skill_match_score': {
    label: 'Skills Alignment',
    increasesRisk: 'Weak skill match may lead to frustration and job searching',
    decreasesRisk: 'Strong skill match means they can excel and feel fulfilled'
  },
  'title_match_score': {
    label: 'Role Similarity',
    increasesRisk: 'Different role may cause dissatisfaction or mismatch',
    decreasesRisk: 'Similar role to their experience means better fit'
  },
  'exp_match_score': {
    label: 'Experience Level Fit',
    increasesRisk: 'Experience mismatch can lead to boredom or overwhelm',
    decreasesRisk: 'Experience level aligns well with position requirements'
  },
  'location_match_score': {
    label: 'Commute Distance',
    increasesRisk: 'Long commute often leads to burnout and job searching',
    decreasesRisk: 'Convenient commute improves work-life balance'
  },
  'overall_match_score': {
    label: 'Overall Job Fit',
    increasesRisk: 'Poor overall fit increases likelihood of early departure',
    decreasesRisk: 'Excellent fit suggests they will thrive in this role'
  },
  'is_overqualified': {
    label: 'Qualification Level',
    increasesRisk: 'Overqualified candidates often leave for better opportunities',
    decreasesRisk: 'Appropriately qualified for the position'
  },
  'is_underqualified': {
    label: 'Qualification Level',
    increasesRisk: 'Underqualified candidates may struggle and leave',
    decreasesRisk: 'Has the right qualifications for success'
  },
  'current_job_tenure': {
    label: 'Current Job Duration',
    increasesRisk: 'Short current tenure suggests readiness to move',
    decreasesRisk: 'Been in current role for a while, shows stability'
  },
  'total_jobs': {
    label: 'Number of Jobs',
    increasesRisk: 'Many jobs in short time indicates job hopping pattern',
    decreasesRisk: 'Reasonable number of jobs for their experience level'
  },
  'total_exp_years': {
    label: 'Total Experience',
    increasesRisk: 'Experience level may not match position requirements',
    decreasesRisk: 'Experience level is appropriate for this role'
  },
  'short_stints_count': {
    label: 'Short-Term Jobs',
    increasesRisk: 'Multiple short-term jobs suggest instability',
    decreasesRisk: 'Few or no short-term jobs shows commitment'
  }
};

const getFeatureExplanation = (feature: SHAPFeature): { label: string; explanation: string } => {
  const config = FEATURE_EXPLANATIONS[feature.feature];
  
  if (!config) {
    return {
      label: feature.feature.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      explanation: feature.impact === 'increases_risk' 
        ? 'This factor increases the risk'
        : 'This factor decreases the risk'
    };
  }

  return {
    label: config.label,
    explanation: feature.impact === 'increases_risk' 
      ? config.increasesRisk 
      : config.decreasesRisk
  };
};

const TurnoverSHAPExplanation: React.FC<TurnoverSHAPExplanationProps> = ({
  shapExplanation
}) => {
  if (!shapExplanation || !shapExplanation.top_features || shapExplanation.top_features.length === 0) {
    return ( 
    <div className="shap-explanation hr-friendly" style={{ padding: '2rem', textAlign: 'center' }}>
      <Lightbulb size={48} style={{ color: '#f59e0b', marginBottom: '1rem' }} />
      <h3>Explanation Unavailable</h3>
      <p style={{ color: '#6b7280' }}>
        {shapExplanation?.explanation || "SHAP analysis could not be generated. Using rule-based risk factors instead."}
      </p>
    </div>
    );
  }

  const { top_features } = shapExplanation;

  // Separate positive and negative contributors
  const increasesRisk = top_features.filter(f => f.impact === 'increases_risk').slice(0, 5);
  const decreasesRisk = top_features.filter(f => f.impact === 'decreases_risk').slice(0, 5);

  return (
    <div className="shap-explanation hr-friendly">
      <div className="shap-header">
        <Lightbulb className="header-icon" />
        <div>
          <h3>Why This Prediction?</h3>
          <p>Key factors that influenced this assessment</p>
        </div>
      </div>

      {/* Warning Factors */}
      {increasesRisk.length > 0 && (
        <div className="factors-section risk-section">
          <div className="section-header">
            <TrendingUp className="section-icon" />
            <h4>⚠️ Warning Signs (Increases Risk)</h4>
          </div>
          <div className="factors-list">
            {increasesRisk.map((feature, idx) => {
              const { label, explanation } = getFeatureExplanation(feature);
              return (
                <div key={idx} className="factor-card warning">
                  <div className="factor-header">
                    <span className="factor-label">{label}</span>
                    <span className="factor-value">{feature.value_display}</span>
                  </div>
                  <p className="factor-explanation">{explanation}</p>
                  <div className="importance-bar">
                    <div 
                      className="importance-fill warning"
                      style={{
                        width: `${Math.min((feature.abs_shap_value / Math.max(...top_features.map(f => f.abs_shap_value))) * 100, 100)}%`
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Positive Factors */}
      {decreasesRisk.length > 0 && (
        <div className="factors-section positive-section">
          <div className="section-header">
            <TrendingDown className="section-icon" />
            <h4>✅ Positive Indicators (Reduces Risk)</h4>
          </div>
          <div className="factors-list">
            {decreasesRisk.map((feature, idx) => {
              const { label, explanation } = getFeatureExplanation(feature);
              return (
                <div key={idx} className="factor-card positive">
                  <div className="factor-header">
                    <span className="factor-label">{label}</span>
                    <span className="factor-value">{feature.value_display}</span>
                  </div>
                  <p className="factor-explanation">{explanation}</p>
                  <div className="importance-bar">
                    <div 
                      className="importance-fill positive"
                      style={{
                        width: `${Math.min((feature.abs_shap_value / Math.max(...top_features.map(f => f.abs_shap_value))) * 100, 100)}%`
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Simple Explanation Footer */}
      <div className="explanation-footer">
        <p>
          <strong>How to read this:</strong> The bars show which factors had the biggest impact on the prediction. 
          Longer bars = stronger influence. These insights help you understand what to discuss in the interview.
        </p>
      </div>
    </div>
  );
};

export default TurnoverSHAPExplanation;