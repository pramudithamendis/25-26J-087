import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Table } from '../../components/shared/Table';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Alert } from '../../components/Alert';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { getJobApplicants } from '../../services/adminService';
import { getJob } from '../../services/jobService';
import type { JobApplicantListItem } from '../../types/adminTypes';
import type { Job } from '../../types/jobTypes';

export const JobApplicantsPage = () => {
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [applicants, setApplicants] = useState<JobApplicantListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [minScore, setMinScore] = useState('');
  const [maxScore, setMaxScore] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [hasEvaluation, setHasEvaluation] = useState<boolean | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (jobId) {
      loadJob();
      loadApplicants();
    }
  }, [jobId, statusFilter, minScore, maxScore, decisionFilter, hasEvaluation, searchQuery]);

  const loadJob = async () => {
    if (!jobId) return;
    try {
      const jobData = await getJob(jobId);
      setJob(jobData);
    } catch (err: any) {
      setError(err.detail || 'Failed to load job details');
    }
  };

  const loadApplicants = async () => {
    if (!jobId) return;
    try {
      setLoading(true);
      setError(null);
      const response = await getJobApplicants(jobId, {
        status: statusFilter || undefined,
        minScore: minScore ? parseFloat(minScore) : undefined,
        maxScore: maxScore ? parseFloat(maxScore) : undefined,
        decision: decisionFilter || undefined,
        hasEvaluation: hasEvaluation,
        search: searchQuery || undefined,
      });
      setApplicants(response.applicants);
    } catch (err: any) {
      setError(err.detail || 'Failed to load applicants');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score?: number) => {
    if (score === undefined) return 'text-gray-500';
    if (score >= 75) return 'text-green-600 font-semibold';
    if (score >= 60) return 'text-yellow-600 font-semibold';
    return 'text-red-600 font-semibold';
  };

  const getDecisionBadge = (decision?: string) => {
    if (!decision) return <span className="text-gray-500">-</span>;
    let colorClass = '';
    switch (decision.toLowerCase()) {
      case 'proceed':
        colorClass = 'bg-green-100 text-green-800';
        break;
      case 'review':
        colorClass = 'bg-yellow-100 text-yellow-800';
        break;
      case 'do not proceed':
        colorClass = 'bg-red-100 text-red-800';
        break;
      default:
        colorClass = 'bg-gray-100 text-gray-800';
    }
    return (
      <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${colorClass}`}>
        {decision}
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    let colorClass = '';
    switch (status.toLowerCase()) {
      case 'approved':
        colorClass = 'bg-green-100 text-green-800';
        break;
      case 'rejected':
        colorClass = 'bg-red-100 text-red-800';
        break;
      case 'evaluated':
        colorClass = 'bg-blue-100 text-blue-800';
        break;
      case 'pending':
        colorClass = 'bg-yellow-100 text-yellow-800';
        break;
      default:
        colorClass = 'bg-gray-100 text-gray-800';
    }
    return (
      <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${colorClass}`}>
        {status}
      </span>
    );
  };

  const columns = [
    { key: 'user_name', header: 'Applicant Name' },
    { key: 'user_email', header: 'Email' },
    {
      key: 'status',
      header: 'Status',
      render: (applicant: JobApplicantListItem) => getStatusBadge(applicant.status),
    },
    {
      key: 'total_score',
      header: 'Score',
      render: (applicant: JobApplicantListItem) => (
        <span className={getScoreColor(applicant.total_score)}>
          {applicant.total_score !== undefined ? applicant.total_score.toFixed(1) : 'N/A'}
        </span>
      ),
    },
    {
      key: 'decision',
      header: 'Decision',
      render: (applicant: JobApplicantListItem) => getDecisionBadge(applicant.decision),
    },
    {
      key: 'created_at',
      header: 'Applied Date',
      render: (applicant: JobApplicantListItem) => new Date(applicant.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (applicant: JobApplicantListItem) => (
        <Button
          size="sm"
          variant="outline"
          onClick={() => navigate(`/dashboard/admin/jobs/${jobId}/applicants/${applicant.application_id}`)}
        >
          View Details
        </Button>
      ),
    },
  ];

  if (loading && !job) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Button variant="outline" onClick={() => navigate('/dashboard/admin/jobs')} className="mb-4">
            ← Back to Jobs
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">
            Applicants for: {job?.title || 'Loading...'}
          </h1>
          <p className="text-gray-600 mt-1">
            Manage and review all applicants for this job posting
          </p>
        </div>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label htmlFor="statusFilter" className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              id="statusFilter"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="evaluated">Evaluated</option>
            </select>
          </div>

          <div>
            <label htmlFor="minScore" className="block text-sm font-medium text-gray-700 mb-1">
              Min Score
            </label>
            <Input
              id="minScore"
              type="number"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
              placeholder="0"
              min="0"
              max="100"
            />
          </div>

          <div>
            <label htmlFor="maxScore" className="block text-sm font-medium text-gray-700 mb-1">
              Max Score
            </label>
            <Input
              id="maxScore"
              type="number"
              value={maxScore}
              onChange={(e) => setMaxScore(e.target.value)}
              placeholder="100"
              min="0"
              max="100"
            />
          </div>

          <div>
            <label htmlFor="decisionFilter" className="block text-sm font-medium text-gray-700 mb-1">
              Decision
            </label>
            <select
              id="decisionFilter"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
            >
              <option value="">All Decisions</option>
              <option value="Proceed">Proceed</option>
              <option value="Review">Review Required</option>
              <option value="Do Not Proceed">Do Not Proceed</option>
            </select>
          </div>

          <div>
            <label htmlFor="hasEvaluation" className="block text-sm font-medium text-gray-700 mb-1">
              Has Evaluation
            </label>
            <select
              id="hasEvaluation"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              value={hasEvaluation === undefined ? '' : hasEvaluation ? 'true' : 'false'}
              onChange={(e) => {
                const value = e.target.value;
                setHasEvaluation(value === '' ? undefined : value === 'true');
              }}
            >
              <option value="">All</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>

          <div>
            <label htmlFor="searchQuery" className="block text-sm font-medium text-gray-700 mb-1">
              Search (Name/Email)
            </label>
            <Input
              id="searchQuery"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search applicants..."
            />
          </div>
        </div>
      </div>

      {/* Applicants Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            <div className="mb-4">
              <p className="text-sm text-gray-600">
                Showing <strong>{applicants.length}</strong> applicant{applicants.length !== 1 ? 's' : ''}
              </p>
            </div>
            <Table
              columns={columns}
              data={applicants}
              emptyMessage="No applicants found matching your criteria."
            />
          </>
        )}
      </div>
    </div>
  );
};

