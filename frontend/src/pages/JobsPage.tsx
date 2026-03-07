import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { JobsList } from '../components/jobs/JobsList';
import { JobForm } from '../components/jobs/JobForm';
import { Modal } from '../components/shared/Modal';
import { Alert } from '../components/Alert';
import { useAuth } from '../contexts/AuthContext';
import { listJobs, createJob } from '../services/jobService';
import type { Job, JobCreate } from '../types/jobTypes';

export const JobsPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listJobs();
      // Ensure all jobs have _id field
      const jobsWithId = response.jobs.map((job) => {
        if (!job._id) {
          console.error('Job missing _id:', job);
        }
        return job;
      });
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
      navigate(`/dashboard/jobs/${newJob._id}`);
    } catch (err: any) {
      setError(err.detail || 'Failed to create job');
      throw err;
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
        <p className="text-gray-600 mt-1">
          Manage your job postings and descriptions
        </p>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      <JobsList
        jobs={filteredJobs}
        loading={loading}
        onSearch={handleSearch}
        onCreateNew={isAdmin ? () => setIsCreateModalOpen(true) : undefined}
        showCreateButton={isAdmin}
      />

      {isAdmin && (
        <Modal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          title="Create New Job"
          size="xl"
        >
          <JobForm
            onSubmit={handleCreate}
            onCancel={() => setIsCreateModalOpen(false)}
            isLoading={isCreating}
          />
        </Modal>
      )}
    </div>
  );
};

