import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/Button';
import { JobApplicationForm } from '../components/jobs/JobApplicationForm';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { getJob } from '../services/jobService';
import { useState, useEffect } from 'react';
import type { Job } from '../types/jobTypes';

export const JobApplicationPage = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setError('Invalid job ID');
      setLoading(false);
      return;
    }

    const loadJob = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getJob(jobId);
        setJob(data);
      } catch (err: any) {
        setError(err.detail || 'Failed to load job');
      } finally {
        setLoading(false);
      }
    };

    loadJob();
  }, [jobId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div>
        <Alert type="error">{error || 'Job not found'}</Alert>
        <Button
          variant="outline"
          onClick={() => navigate('/dashboard/jobs')}
          className="mt-4"
        >
          Back to Jobs
        </Button>
      </div>
    );
  }

  if (!jobId) {
    return (
      <div>
        <Alert type="error">Invalid job ID</Alert>
        <Button
          variant="outline"
          onClick={() => navigate('/dashboard/jobs')}
          className="mt-4"
        >
          Back to Jobs
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <Button variant="outline" onClick={() => navigate(`/dashboard/jobs/${jobId}`)}>
          ← Back to Job Details
        </Button>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Apply for: {job.title}
          </h1>
          <p className="text-sm text-gray-600">
            Please fill out the form below to apply for this position.
          </p>
        </div>

        <JobApplicationForm
          jobId={jobId}
          onSubmit={(applicationId) => {
            navigate(`/dashboard/jobs/${jobId}/apply/confirmation`);
          }}
          onCancel={() => navigate(`/dashboard/jobs/${jobId}`)}
        />
      </div>
    </div>
  );
};

