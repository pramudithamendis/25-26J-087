import React, { useState, useEffect } from 'react';
import { AlertTriangle, MapPin, Loader2, ShieldAlert, Clock, CheckCircle2, ChevronDown } from 'lucide-react';
import { Button } from '../Button';
import apiClient from '../../config/api';
import type { TurnoverPredictionResponse } from '../../types/turnover.types';
import TurnoverPredictionResults from './TurnoverPredictionResults';
import TurnoverSHAPExplanation from './TurnoverSHAPExplanation';
import TurnoverRiskFactors from './TurnoverRiskFactors';
import TurnoverCounterfactuals from './TurnoverCounterfactuals';
import './TurnoverRiskTab.css';

interface TurnoverRiskTabProps {
  userEmail: string;
  jobId: string;
  jobDescription: string;
  jobTitle: string;
  jobLocation?: string;
  evaluationDecision?: string;
}

type TabState =
  | 'loading'
  | 'not_proceeded'
  | 'cv_not_found'
  | 'no_prediction'
  | 'has_prediction'
  | 'predicting'
  | 'error';

const DISQUALIFIED_DECISIONS = ['Not Selected', 'Do Not Proceed'];

const isRemoteJob = (title: string) => title.toLowerCase().includes('remote');

const TurnoverRiskTab: React.FC<TurnoverRiskTabProps> = ({
  userEmail,
  jobId,
  jobDescription,
  jobTitle,
  jobLocation,
  evaluationDecision,
}) => {
  const [tabState, setTabState] = useState<TabState>('loading');
  const [cvId, setCvId] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<TurnoverPredictionResponse | null>(null);
  const [selectedLocation, setSelectedLocation] = useState(jobLocation || '');
  const [locations, setLocations] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const remote = isRemoteJob(jobTitle);

  useEffect(() => {
    if (remote) setSelectedLocation('Remote');
    else if (jobLocation) setSelectedLocation(jobLocation);
    else setSelectedLocation('');
  }, [jobTitle, jobLocation]);

  useEffect(() => {
    fetchLocations();
    initTab();
  }, [userEmail, jobId]);

  const fetchLocations = async () => {
    try {
      const res = await apiClient.get('/locations');
      setLocations((res.data.locations || []).map((l: any) => l.name));
    } catch {
      // fallback - works with no dropdown options
    }
  };

  const initTab = async () => {
    try {
      setTabState('loading');
      setError(null);

      if (DISQUALIFIED_DECISIONS.includes(evaluationDecision ?? '')) {
        setTabState('not_proceeded');
        return;
      }

      const cvRes = await apiClient.get(
        `/turnover/cv-by-email?email=${encodeURIComponent(userEmail)}`
      );
      if (cvRes.data.status === 'not_found' || !cvRes.data.cv_id) {
        setTabState('cv_not_found');
        return;
      }

      const foundCvId = cvRes.data.cv_id;
      setCvId(foundCvId);

      const resultRes = await apiClient.get(
        `/turnover/result-by-job?cv_id=${foundCvId}&job_id=${jobId}`
      );
      if (resultRes.data.status === 'found' && resultRes.data.result) {
        setPrediction(resultRes.data.result);
        setTabState('has_prediction');
      } else {
        setTabState('no_prediction');
      }
    } catch (err: any) {
      console.error('TurnoverRiskTab error:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load data');
      setTabState('error');
    }
  };

  const handlePredict = async () => {
    if (!cvId || !selectedLocation.trim()) return;

    try {
      setTabState('predicting');
      setError(null);

      const formData = new FormData();
      formData.append('cv_id', cvId);
      formData.append('job_description', jobDescription);
      formData.append('job_id', jobId);
      formData.append('job_location', selectedLocation.trim());
      formData.append('job_title', jobTitle);

      const res = await apiClient.post('/turnover/predict-with-job', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setPrediction(res.data);
      setTabState('has_prediction');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((d: any) => d.msg).join(', ')
          : typeof detail === 'string'
          ? detail
          : 'Assessment failed. Please try again.'
      );
      setTabState('no_prediction');
    }
  };

  if (tabState === 'loading') {
    return (
      <div className="trt-center">
        <Loader2 size={32} className="trt-spin" />
        <p>Loading candidate data...</p>
      </div>
    );
  }

  if (tabState === 'not_proceeded') {
    return (
      <div className="trt-state-card">
        <ShieldAlert size={40} className="trt-state-icon trt-icon-gray" />
        <h3>Assessment Not Available</h3>
        <p>This candidate did not proceed to the next stage. Early attrition risk assessment is only available for candidates who have been selected or are under review.</p>
      </div>
    );
  }

  if (tabState === 'cv_not_found') {
    return (
      <div className="trt-state-card">
        <Clock size={40} className="trt-state-icon trt-icon-blue" />
        <h3>Profile Not Yet Available</h3>
        <p>This candidate's profile information is not yet available. Please check back shortly.</p>
        <button className="trt-retry-btn" onClick={initTab}>Check Again</button>
      </div>
    );
  }

  if (tabState === 'error') {
    return (
      <div className="trt-state-card">
        <AlertTriangle size={40} className="trt-state-icon trt-icon-gray" />
        <h3>Something went wrong</h3>
        <p>{error || 'Failed to load retention risk data.'}</p>
        <button className="trt-retry-btn" onClick={initTab}>Try Again</button>
      </div>
    );
  }

  if (tabState === 'no_prediction' || tabState === 'predicting') {
    return (
      <div className="trt-predict-card">
        <div className="trt-predict-header">
          <CheckCircle2 size={20} className="trt-icon-blue" />
          <div>
            <h3>Ready to Assess</h3>
            <p>
              {remote
                ? 'This is a remote position.'
                : 'Select the job office location to begin the early attrition risk assessment.'}
            </p>
          </div>
        </div>

        <div className="trt-job-info">
          <span className="trt-job-label">Job</span>
          <span className="trt-job-title">{jobTitle}</span>
        </div>

        <div className="trt-location-row">
          <label className="trt-location-label">
            <MapPin size={14} />
            Job Location
            {remote && <span className="trt-remote-tag">Auto-filled</span>}
            {!remote && jobLocation && <span className="trt-remote-tag">From job</span>}
          </label>

          {remote ? (
            <input
              className="trt-location-input trt-input-readonly"
              type="text"
              value="Remote"
              readOnly
            />
          ) : (
            <div className="trt-select-wrapper">
              <select
                className="trt-location-select"
                value={selectedLocation}
                onChange={e => setSelectedLocation(e.target.value)}
                disabled={tabState === 'predicting'}
              >
                <option value="">Select office location...</option>
                {locations.filter(l => l !== 'Remote').map(loc => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
              <ChevronDown size={14} className="trt-select-arrow" />
            </div>
          )}
        </div>

        {error && <p className="trt-error">{error}</p>}

        <Button
          variant="primary"
          onClick={handlePredict}
          disabled={tabState === 'predicting'}
        >
          {tabState === 'predicting' ? (
            <span className="trt-btn-loading">
              <Loader2 size={16} className="trt-spin" />
              Analysing...
            </span>
          ) : (
            'Assess Retention Risk'
          )}
        </Button>

        {tabState === 'predicting' && (
          <p className="trt-predicting-note">
            This may take a while on first-time setup.
          </p>
        )}
      </div>
    );
  }

  if (tabState === 'has_prediction' && prediction) {
    return (
      <div className="trt-results">
        <TurnoverPredictionResults prediction={prediction} />
        {(prediction?.shap_explanation?.top_features?.length ?? 0) > 0 && (
          <TurnoverSHAPExplanation shapExplanation={prediction.shap_explanation} />
        )}
        {prediction.risk_factors?.length > 0 && (
          <TurnoverRiskFactors riskFactors={prediction.risk_factors} />
        )}
        {prediction.counterfactuals?.length > 0 && (
          <TurnoverCounterfactuals counterfactuals={prediction.counterfactuals} />
        )}
        <div className="trt-rerun">
          <button className="trt-retry-btn" onClick={() => { setPrediction(null); setTabState('no_prediction'); }}>
            Run New Assessment
          </button>
        </div>
      </div>
    );
  }

  return null;
};

class TurnoverRiskTabErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; errorMsg: string }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, errorMsg: '' };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, errorMsg: error?.message || 'Unknown error' };
  }

  componentDidCatch(error: any, info: any) {
    console.error('TurnoverRiskTab crashed:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="trt-state-card">
          <AlertTriangle size={40} className="trt-state-icon trt-icon-gray" />
          <h3>This section encountered an error</h3>
          <p>Other tabs are not affected. Please refresh or try again later.</p>
          <p className="trt-error-detail">{this.state.errorMsg}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export const TurnoverRiskTabSafe: React.FC<TurnoverRiskTabProps> = (props) => (
  <TurnoverRiskTabErrorBoundary>
    <TurnoverRiskTab {...props} />
  </TurnoverRiskTabErrorBoundary>
);

export default TurnoverRiskTabSafe;