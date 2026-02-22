import React, { useState, useEffect, useRef } from 'react';
import { Briefcase, MapPin, AlertCircle } from 'lucide-react';
import { MIN_JOB_DESCRIPTION_LENGTH, MAX_JOB_DESCRIPTION_LENGTH } from '../../utils/turnover-constants';
import './TurnoverJobDetailsForm.css';

interface TurnoverJobDetailsFormProps {
  cvId: string;
  onSubmit: (jobDescription: string, jobLocation: string) => void;
  loading?: boolean;
}

const TurnoverJobDetailsForm: React.FC<TurnoverJobDetailsFormProps> = ({
  cvId,
  onSubmit,
  loading = false
}) => {
  const [jobDescription, setJobDescription] = useState('');
  const [jobLocation, setJobLocation] = useState('');
  const [error, setError] = useState('');
  
  // Reference to button to ensure it's visible
  const buttonRef = useRef<HTMLButtonElement>(null);

  const characterCount = jobDescription.length;
  const isValid = characterCount >= MIN_JOB_DESCRIPTION_LENGTH &&
                  characterCount <= MAX_JOB_DESCRIPTION_LENGTH;

  // Force button visibility
  useEffect(() => {
    if (buttonRef.current) {
      buttonRef.current.style.display = 'flex';
      buttonRef.current.style.opacity = '1';
      buttonRef.current.style.visibility = 'visible';
    }
  }, [loading, isValid]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!jobDescription.trim()) {
      setError('Job description is required');
      return;
    }

    if (characterCount < MIN_JOB_DESCRIPTION_LENGTH) {
      setError(`Job description must be at least ${MIN_JOB_DESCRIPTION_LENGTH} characters`);
      return;
    }

    if (characterCount > MAX_JOB_DESCRIPTION_LENGTH) {
      setError(`Job description must be less than ${MAX_JOB_DESCRIPTION_LENGTH} characters`);
      return;
    }

    onSubmit(jobDescription, jobLocation);
  };

  return (
    <div className="turnover-job-details-form">
      <div className="form-header">
        <Briefcase className="icon" />
        <div>
          <h2>Job Details</h2>
          <p>Provide job description to predict turnover risk</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Job Description */}
        <div className="form-group">
          <label htmlFor="jobDescription">
            Job Description <span className="required">*</span>
          </label>
          <textarea
            id="jobDescription"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the complete job description here including responsibilities, requirements, and qualifications..."
            rows={12}
            disabled={loading}
            className={!isValid && characterCount > 0 ? 'invalid' : ''}
          />
          <div className="character-count">
            <span className={characterCount < MIN_JOB_DESCRIPTION_LENGTH ? 'text-red' : ''}>
              {characterCount} / {MAX_JOB_DESCRIPTION_LENGTH} characters
            </span>
            {characterCount > 0 && characterCount < MIN_JOB_DESCRIPTION_LENGTH && (
              <span className="text-red">
                (Need {MIN_JOB_DESCRIPTION_LENGTH - characterCount} more)
              </span>
            )}
          </div>
        </div>

        {/* Job Location */}
        <div className="form-group">
          <label htmlFor="jobLocation">
            <MapPin size={16} className="inline" /> Job Location
          </label>
          <input
            type="text"
            id="jobLocation"
            value={jobLocation}
            onChange={(e) => setJobLocation(e.target.value)}
            placeholder="e.g., Colombo, Sri Lanka"
            disabled={loading}
          />
          <small className="help-text">
            Location will be extracted from job description if not provided
          </small>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          ref={buttonRef}
          type="submit"
          className="submit-button"
          disabled={loading || !isValid}
          style={{
            display: 'flex',
            opacity: 1,
            visibility: 'visible',
            background: (loading || !isValid) ? '#9ca3af' : 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
            color: '#ffffff',
            border: 'none',
            width: '100%',
            minHeight: '48px'
          }}
        >
          {loading ? (
            <>
              <div className="spinner"></div>
              Analyzing...
            </>
          ) : (
            'Predict Turnover Risk'
          )}
        </button>

        <div className="info-box">
          <AlertCircle size={16} />
          <p>
            The prediction uses only pre-hire data from the CV and job description.
            No sensitive demographic information is required.
          </p>
        </div>
      </form>
    </div>
  );
};

export default TurnoverJobDetailsForm;