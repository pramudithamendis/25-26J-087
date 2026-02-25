import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Briefcase, Search, MapPin, CheckCircle2, ChevronRight, ArrowLeft, Zap, Loader2, History, FileText, UserCheck } from 'lucide-react';
import apiClient from '../../config/api';
import './TurnoverNewPrediction.css';
import { Button } from '../Button';

interface Candidate {
  _id: string;
  name: string;
  email: string;
  uploaded_at: string;
}

interface Job {
  _id: string;
  title: string;
  jd_text: string;
  created_at: string;
}

const TurnoverNewPrediction: React.FC = () => {
  const navigate = useNavigate();

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobLocation, setJobLocation] = useState('');
  const [candidateSearch, setCandidateSearch] = useState('');
  const [jobSearch, setJobSearch] = useState('');
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchCandidates();
    fetchJobs();
  }, []);

  const fetchCandidates = async () => {
    try {
      const res = await apiClient.get('/turnover/candidates');
      setCandidates(res.data.candidates || []);
    } catch (e) {
      setError('Failed to load candidates');
    } finally {
      setLoadingCandidates(false);
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await apiClient.get('/turnover/jobs');
      setJobs(res.data.jobs || []);
    } catch (e) {
      setError('Failed to load jobs');
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleSelectCandidate = (candidate: Candidate) => {
    setSelectedCandidate(candidate);
    setStep(2);
  };

  const handleSelectJob = (job: Job) => {
    setSelectedJob(job);
    setStep(3);
  };

  const handlePredict = async () => {
    if (!selectedCandidate || !selectedJob || !jobLocation.trim()) {
      setError('Please fill in all fields');
      return;
    }

    setPredicting(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('cv_id', selectedCandidate._id);
      formData.append('job_description', selectedJob.jd_text);
      formData.append('job_location', jobLocation.trim());

      const res = await apiClient.post('/turnover/predict', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      console.log('Prediction response:', res.data); 
      if (res.data.result_id) {
        navigate(`/dashboard/admin/turnover?result_id=${res.data.result_id}`);
      } else if (res.data.cv_id) {
        navigate(`/dashboard/admin/turnover?cv_id=${res.data.cv_id}`);
      }
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      // detail might be an array of validation errors
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join(', '));
      } else {
        setError(typeof detail === 'string' ? detail : 'Prediction failed. Please try again.');
      }
    } finally {
      setPredicting(false);
    }
  };

  const filteredCandidates = candidates.filter(c =>
    c.name.toLowerCase().includes(candidateSearch.toLowerCase()) ||
    c.email.toLowerCase().includes(candidateSearch.toLowerCase())
  );

  const filteredJobs = jobs.filter(j =>
    j.title.toLowerCase().includes(jobSearch.toLowerCase())
  );

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: 'numeric', month: 'short', year: 'numeric'
      });
    } catch { return ''; }
  };

  return (
    <div className="tnp-container">

      {/* Header */}
      <div className="tnp-header">
        <Button
          variant="outline"
          onClick={() => navigate('/dashboard/admin/turnover/history')}
        >
          <History size={16} />
          Back to History
        </Button>
        <div className="tnp-header-text">
          <h1>New Turnover Prediction</h1>
          <p>Select a candidate and job to predict turnover risk</p>
        </div>
      </div>

      {/* Stepper */}
      <div className="tnp-stepper">
        <div className={`tnp-step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'done' : ''}`}>
          <div className="tnp-step-circle">
            {step > 1 ? <CheckCircle2 size={16} /> : '1'}
          </div>
          <span>Select Candidate</span>
        </div>
        <div className="tnp-step-line" />
        <div className={`tnp-step ${step >= 2 ? 'active' : ''} ${step > 2 ? 'done' : ''}`}>
          <div className="tnp-step-circle">
            {step > 2 ? <CheckCircle2 size={16} /> : '2'}
          </div>
          <span>Select Job</span>
        </div>
        <div className="tnp-step-line" />
        <div className={`tnp-step ${step >= 3 ? 'active' : ''}`}>
          <div className="tnp-step-circle">3</div>
          <span>Confirm & Predict</span>
        </div>
      </div>

      {error && <div className="tnp-error">{error}</div>}

      {/* Step 1 — Select Candidate */}
      {step === 1 && (
        <div className="tnp-card">
          <div className="tnp-card-title">
            <User size={20} className="tnp-card-icon" />
            <h2>Select a Candidate</h2>
          </div>
          <p className="tnp-subtitle">Choose from candidates who have submitted their CVs</p>

          <div className="tnp-search-wrapper">
            <Search size={16} className="tnp-search-icon" />
            <input
              className="tnp-search"
              placeholder="Search by name or email..."
              value={candidateSearch}
              onChange={e => setCandidateSearch(e.target.value)}
            />
          </div>

          {loadingCandidates ? (
            <div className="tnp-loading">
              <Loader2 size={20} className="tnp-spin" />
              Loading candidates...
            </div>
          ) : filteredCandidates.length === 0 ? (
            <div className="tnp-empty">No candidates found</div>
          ) : (
            <div className="tnp-list">
              {filteredCandidates.map(candidate => (
                <div
                  key={candidate._id}
                  className="tnp-list-item"
                  onClick={() => handleSelectCandidate(candidate)}
                >
                  <div className="tnp-item-avatar">
                    <User size={18} />
                  </div>
                  <div className="tnp-item-info">
                    <span className="tnp-item-name">{candidate.name}</span>
                    <span className="tnp-item-sub">{candidate.email}</span>
                  </div>
                  <div className="tnp-item-meta">
                    <span className="tnp-item-date">{formatDate(candidate.uploaded_at)}</span>
                    <ChevronRight size={16} className="tnp-item-arrow" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 2 — Select Job */}
      {step === 2 && (
        <div className="tnp-card">
          <div className="tnp-card-nav">
            <button className="tnp-nav-back" onClick={() => setStep(1)}>
              <ArrowLeft size={16} /> Back
            </button>
            <div className="tnp-selected-badge">
              <UserCheck size={14} /> {selectedCandidate?.name}
            </div>
          </div>

          <div className="tnp-card-title">
            <Briefcase size={20} className="tnp-card-icon" />
            <h2>Select a Job</h2>
          </div>
          <p className="tnp-subtitle">Choose the job position for this prediction</p>

          <div className="tnp-search-wrapper">
            <Search size={16} className="tnp-search-icon" />
            <input
              className="tnp-search"
              placeholder="Search jobs..."
              value={jobSearch}
              onChange={e => setJobSearch(e.target.value)}
            />
          </div>

          {loadingJobs ? (
            <div className="tnp-loading">
              <Loader2 size={20} className="tnp-spin" />
              Loading jobs...
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="tnp-empty">No jobs found</div>
          ) : (
            <div className="tnp-list">
              {filteredJobs.map(job => (
                <div
                  key={job._id}
                  className="tnp-list-item"
                  onClick={() => handleSelectJob(job)}
                >
                  <div className="tnp-item-avatar tnp-item-avatar-job">
                    <FileText size={18} />
                  </div>
                  <div className="tnp-item-info">
                    <span className="tnp-item-name">{job.title}</span>
                    <span className="tnp-item-sub">{job.jd_text.substring(0, 80)}...</span>
                  </div>
                  <div className="tnp-item-meta">
                    <span className="tnp-item-date">{formatDate(job.created_at)}</span>
                    <ChevronRight size={16} className="tnp-item-arrow" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 3 — Confirm & Predict */}
      {step === 3 && (
        <div className="tnp-card">
          <div className="tnp-card-nav">
            <button className="tnp-nav-back" onClick={() => setStep(2)}>
              <ArrowLeft size={16} /> Back
            </button>
          </div>

          <div className="tnp-card-title">
            <CheckCircle2 size={20} className="tnp-card-icon tnp-card-icon-green" />
            <h2>Confirm & Predict</h2>
          </div>
          <p className="tnp-subtitle">Review your selections and enter the job location</p>

          <div className="tnp-summary">
            <div className="tnp-summary-item">
              <span className="tnp-summary-label">Candidate</span>
              <div className="tnp-summary-value">
                <div className="tnp-summary-row">
                  <User size={15} />
                  <span>{selectedCandidate?.name}</span>
                </div>
                <small>{selectedCandidate?.email}</small>
              </div>
            </div>
            <div className="tnp-summary-item">
              <span className="tnp-summary-label">Job</span>
              <div className="tnp-summary-value">
                <div className="tnp-summary-row">
                  <Briefcase size={15} />
                  <span>{selectedJob?.title}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="tnp-location-group">
            <label>
              <MapPin size={15} className="tnp-label-icon" />
              Job Location
            </label>
            <input
              className="tnp-location-input"
              placeholder="e.g. Colombo, Sri Lanka"
              value={jobLocation}
              onChange={e => setJobLocation(e.target.value)}
            />
            <small>Enter the work location for this position</small>
          </div>

          <button
            className="tnp-predict-btn"
            onClick={handlePredict}
            disabled={predicting || !jobLocation.trim()}
          >
            {predicting ? (
              <>
                <Loader2 size={18} className="tnp-spin" />
                Analyzing... This may take up to 30 seconds
              </>
            ) : (
              <>
                <Zap size={18} />
                Predict Turnover Risk
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default TurnoverNewPrediction;