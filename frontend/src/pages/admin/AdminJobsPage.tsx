import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { JobsList } from '../../components/jobs/JobsList';
import { JobForm } from '../../components/jobs/JobForm';
import { Modal } from '../../components/shared/Modal';
import { Alert } from '../../components/Alert';
import { Button } from '../../components/Button';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { listJobs, createJob } from '../../services/jobService';
import { deleteJob } from '../../services/adminService';
import type { Job, JobCreate } from '../../types/jobTypes';

export const AdminJobsPage = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listJobs();
      const jobsWithId = response.jobs.filter((job) => job._id);
      setJobs(jobsWithId);
      setFilteredJobs(jobsWithId);
    } catch (err: any) {
      setError(err.detail || 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (query: string) => {
    if (!query.trim()) {
      setFilteredJobs(jobs);
      return;
    }
    const lowerQuery = query.toLowerCase();
    const filtered = jobs.filter(
      (j) =>
        j.title.toLowerCase().includes(lowerQuery) ||
        j.jd_text.toLowerCase().includes(lowerQuery)
    );
    setFilteredJobs(filtered);
  };

  const handleCreate = async (data: JobCreate) => {
    try {
      setIsCreating(true);
      setError(null);
      const newJob = await createJob(data);
      setJobs([...jobs, newJob]);
      setFilteredJobs([...filteredJobs, newJob]);
      setIsCreateModalOpen(false);
      setSuccess('Job created successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.detail || 'Failed to create job');
      throw err;
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (jobId: string) => {
    if (!window.confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
      return;
    }

    try {
      setDeletingJobId(jobId);
      setError(null);
      await deleteJob(jobId);
      setJobs(jobs.filter((j) => j._id !== jobId));
      setFilteredJobs(filteredJobs.filter((j) => j._id !== jobId));
      setSuccess('Job deleted successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.detail || 'Failed to delete job');
    } finally {
      setDeletingJobId(null);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin - Jobs Management</h1>
        <p className="text-gray-600 mt-1">Create, edit, and delete job postings</p>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      {success && (
        <Alert type="success" onClose={() => setSuccess(null)} className="mb-6">
          {success}
        </Alert>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <JobsList
          jobs={filteredJobs}
          loading={loading}
          onSearch={handleSearch}
          onCreateNew={() => setIsCreateModalOpen(true)}
          showCreateButton={true}
        />
      </div>

      {/* Enhanced job list with delete buttons */}
      {!loading && filteredJobs.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">All Jobs</h2>
          <div className="space-y-4">
            {filteredJobs.map((job) => (
              <div
                key={job._id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                onClick={() => navigate(`/dashboard/admin/jobs/${job._id}/applicants`)}
              >
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{job.title}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {job.application_count !== undefined && `${job.application_count} applications`}
                  </p>
                </div>
                <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => navigate(`/dashboard/admin/jobs/${job._id}/applicants`)}
                  >
                    View Applicants
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/dashboard/jobs/${job._id}`)}
                  >
                    View Job
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(job._id!)}
                    disabled={deletingJobId === job._id}
                    className="text-red-600 hover:text-red-700"
                  >
                    {deletingJobId === job._id ? 'Deleting...' : 'Delete'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Job"
        size="lg"
      >
        <JobForm
          onSubmit={handleCreate}
          onCancel={() => setIsCreateModalOpen(false)}
          isLoading={isCreating}
        />
      </Modal>
    </div>
  );
};

