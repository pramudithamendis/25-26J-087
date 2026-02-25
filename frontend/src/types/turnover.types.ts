export interface TurnoverPredictionRequest {
  cv_id: string;
  job_description: string;
  job_location?: string;
}

export interface TurnoverPredictionResponse {
  status: string;
  cv_id: string;
  cv_name: string;
  job_description?: string; 
  job_location?: string;  
  prediction: {
    risk_level: number; // 0 = High, 1 = Medium, 2 = Low
    risk_label: string;
    confidence: number;
    probabilities: {
      high_risk: number;
      medium_risk: number;
      low_risk: number;
    };
  };
  features: {
    skill_match: number;
    title_match: number;
    exp_match: number;
    location_match: number;
    overall_match: number;
    job_hopping_rate: number;
    total_jobs: number;
    total_experience: number;
    avg_tenure_months: number;
  };
  shap_explanation: SHAPExplanation | null; 
  risk_factors: RiskFactor[];
  counterfactuals: Counterfactual[];
}

export interface RiskFactor {
  factor: string;
  value: number | string;
  description: string;
  impact: 'high' | 'medium' | 'low';
}

export interface Counterfactual {
  scenario: string;
  original_risk: string;
  new_risk: string;
  confidence_change: number;
  impact: 'positive' | 'negative';
  feature_changed: string;
  original_value: number;
  new_value: number;
}

export interface TurnoverHealthResponse {
  status: string;
  model_loaded: boolean;
  message: string;
}

export interface SHAPFeature {
  feature: string;
  value: number;
  value_display: string;
  shap_value: number;
  abs_shap_value: number;
  impact: 'increases_risk' | 'decreases_risk';
}

export interface SHAPExplanation {
  base_value: number;
  prediction_value: number;
  top_features: SHAPFeature[];
  all_features: SHAPFeature[];
  explanation?: string;
}