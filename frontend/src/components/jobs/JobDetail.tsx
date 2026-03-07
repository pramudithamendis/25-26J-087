import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../Button';
import { JobForm } from './JobForm';
import { Alert } from '../Alert';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { useAuth } from '../../contexts/AuthContext';
import { getJob, updateJob } from '../../services/jobService';
import { checkApplicationStatus } from '../../services/applicationService';
import type { Job, JobUpdate } from '../../types/jobTypes';

interface JobDetailProps {
  jobId: string;
}

export const JobDetail = ({ jobId }: JobDetailProps) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [hasApplied, setHasApplied] = useState<boolean | null>(null);

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

  useEffect(() => {
    loadJob();
    loadApplicationStatus();
  }, [jobId]);

  const loadApplicationStatus = async () => {
    if (isAdmin) {
      return; // Admins don't need to check application status
    }
    try {
      const status = await checkApplicationStatus(jobId);
      setHasApplied(status.has_applied);
    } catch (err) {
      console.error('Failed to check application status:', err);
      setHasApplied(false);
    }
  };

  const handleUpdate = async (data: JobUpdate) => {
    try {
      setIsUpdating(true);
      await updateJob(jobId, data);
      await loadJob(); 
      setIsEditing(false);
    } catch (err: any) {
      setError(err.detail || 'Failed to update job');
      throw err;
    } finally {
      setIsUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error && !job) {
    return (
      <div>
        <Alert type="error">{error}</Alert>
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

  if (!job) return null;

  return (
    <div>
      <div className="mb-6">
        <Button variant="outline" onClick={() => navigate('/dashboard/jobs')}>
          ← Back to Jobs
        </Button>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">{job.title}</h2>
          <div className="flex gap-3">
            {isAdmin ? (
              <>
                <Button
                  variant="primary"
                  onClick={() => navigate(`/dashboard/admin/jobs/${jobId}/applicants`)}
                >
                  View Applicants
                </Button>
                <Button
                  variant={isEditing ? 'outline' : 'primary'}
                  onClick={() => setIsEditing(!isEditing)}
                >
                  {isEditing ? 'Cancel Edit' : 'Edit Job'}
                </Button>
              </>
            ) : hasApplied ? (
              <Button
                type="button"
                variant="outline"
                disabled={true}
              >
                Already Applied
              </Button>
            ) : (
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="primary"
                  onClick={() => navigate(`/dashboard/jobs/${jobId}/apply`)}
                >
                  Apply for this Job
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  onClick={() => navigate(`/dashboard/evaluate/${jobId}`)}
                >
                  Evaluate CV
                </Button>
              </div>
            )}
          </div>
        </div>

        {isEditing ? (
          <JobForm
            job={job}
            onSubmit={handleUpdate}
            onCancel={() => setIsEditing(false)}
            isLoading={isUpdating}
          />
        ) : (
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Job Description
              </h3>
              <div className="prose max-w-none">
                <p className="text-gray-900 whitespace-pre-wrap">
                  {job.jd_text}
                </p>
              </div>
            </div>
            {job.location && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">
                    Location
                  </h3>
                  <p className="text-gray-900">{job.location}</p>
                </div>
              )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">
                  Created At
                </h3>
                <p className="text-gray-900">
                  {new Date(job.created_at).toLocaleDateString()}
                </p>
              </div>
              
              {job.application_count !== undefined && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">
                    Applications
                  </h3>
                  <p className="text-gray-900 font-semibold">
                    {job.application_count === 0
                      ? 'No applications yet'
                      : `${job.application_count} ${job.application_count === 1 ? 'candidate has' : 'candidates have'} applied for this position`}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

