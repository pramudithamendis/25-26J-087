import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table } from '../../components/shared/Table';
import { Button } from '../../components/Button';
import { Alert } from '../../components/Alert';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { listAllEvaluations, exportEvaluations } from '../../services/adminService';
import { listJobs } from '../../services/jobService';
import type { EvaluationListItem } from '../../types/adminTypes';
import type { Job } from '../../types/jobTypes';

export const AdminEvaluationsPage = () => {
  const navigate = useNavigate();
  const [evaluations, setEvaluations] = useState<EvaluationListItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Filters
  const [jobFilter, setJobFilter] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [minScore, setMinScore] = useState('');
  const [maxScore, setMaxScore] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    loadJobs();
    loadEvaluations();
  }, [jobFilter, decisionFilter, minScore, maxScore, skip]);

  const loadJobs = async () => {
    try {
      const response = await listJobs();
      setJobs(response.jobs);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  };

  const loadEvaluations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listAllEvaluations({
        job_id: jobFilter || undefined,
        decision: decisionFilter || undefined,
        min_score: minScore ? parseFloat(minScore) : undefined,
        max_score: maxScore ? parseFloat(maxScore) : undefined,
        skip,
        limit,
      });
      setEvaluations(response.evaluations);
      setTotalCount(response.count);
    } catch (err: any) {
      setError(err.detail || 'Failed to load evaluations');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportEvaluations({
        job_id: jobFilter || undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'evaluations.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setSuccess('Evaluations exported successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.detail || 'Failed to export evaluations');
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600 font-semibold';
    if (score >= 60) return 'text-yellow-600 font-semibold';
    return 'text-red-600 font-semibold';
  };

  const getDecisionBadge = (decision: string) => {
    const colors: Record<string, string> = {
      Selected: 'bg-green-100 text-green-800',
      Review: 'bg-yellow-100 text-yellow-800',
      'Not Selected': 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[decision] || 'bg-gray-100 text-gray-800'}`}>
        {decision}
      </span>
    );
  };

  const columns = [
    { key: 'user_email', header: 'User Email' },
    { key: 'user_name', header: 'User Name' },
    { key: 'job_title', header: 'Job Title' },
    {
      key: 'total_score',
      header: 'Score',
      render: (evaluation: EvaluationListItem) => (
        <span className={getScoreColor(evaluation.total_score)}>
          {evaluation.total_score.toFixed(1)}
        </span>
      ),
    },
    {
      key: 'decision',
      header: 'Decision',
      render: (evaluation: EvaluationListItem) => getDecisionBadge(evaluation.decision),
    },
    {
      key: 'created_at',
      header: 'Date',
      render: (evaluation: EvaluationListItem) => (
        <span>{new Date(evaluation.created_at).toLocaleDateString()}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (evaluation: EvaluationListItem) => (
        <Button
          size="sm"
          variant="outline"
          onClick={() => navigate(`/dashboard/evaluations/${evaluation._id}`)}
        >
          View Details
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin - Evaluations Management</h1>
          <p className="text-gray-600 mt-1">View all candidate evaluations</p>
        </div>
        <Button variant="primary" onClick={handleExport}>
          Export CSV
        </Button>
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

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Job</label>
            <select
              value={jobFilter}
              onChange={(e) => {
                setJobFilter(e.target.value);
                setSkip(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All Jobs</option>
              {jobs.map((job) => (
                <option key={job._id} value={job._id}>
                  {job.title}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Decision</label>
            <select
              value={decisionFilter}
              onChange={(e) => {
                setDecisionFilter(e.target.value);
                setSkip(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All Decisions</option>
              <option value="Selected">Selected</option>
              <option value="Review">Review</option>
              <option value="Not Selected">Not Selected</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Min Score</label>
            <input
              type="number"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => {
                setMinScore(e.target.value);
                setSkip(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Max Score</label>
            <input
              type="number"
              min="0"
              max="100"
              value={maxScore}
              onChange={(e) => {
                setMaxScore(e.target.value);
                setSkip(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="100"
            />
          </div>
        </div>
      </div>

      {/* Evaluations Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={evaluations}
              emptyMessage="No evaluations found"
            />
            {totalCount > limit && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Showing {skip + 1} to {Math.min(skip + limit, totalCount)} of {totalCount} evaluations
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSkip(Math.max(0, skip - limit))}
                    disabled={skip === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSkip(skip + limit)}
                    disabled={skip + limit >= totalCount}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

