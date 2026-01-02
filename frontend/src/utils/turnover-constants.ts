export const RISK_LABELS = {
  0: 'High Risk (0-6 months)',
  1: 'Medium Risk (6-12 months)',
  2: 'Low Risk (>1 year)'
} as const;

export const RISK_COLORS = {
  0: '#ef4444', // Red
  1: '#f59e0b', // Orange
  2: '#10b981'  // Green
} as const;

export const RISK_BACKGROUNDS = {
  0: '#fef2f2', // Light red
  1: '#fffbeb', // Light orange
  2: '#f0fdf4'  // Light green
} as const;

export const IMPACT_COLORS = {
  high: '#dc2626',
  medium: '#f59e0b',
  low: '#10b981'
} as const;

export const FEATURE_LABELS: Record<string, string> = {
  skill_match: 'Skill Match',
  title_match: 'Title Match',
  exp_match: 'Experience Match',
  location_match: 'Location Match',
  overall_match: 'Overall Match',
  job_hopping_rate: 'Job Hopping Rate',
  total_jobs: 'Total Jobs',
  total_experience: 'Total Experience (years)',
  avg_tenure_months: 'Average Tenure (months)'
};

export const PREDICTION_STATUS = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error'
} as const;

export const MIN_JOB_DESCRIPTION_LENGTH = 50;
export const MAX_JOB_DESCRIPTION_LENGTH = 5000;
