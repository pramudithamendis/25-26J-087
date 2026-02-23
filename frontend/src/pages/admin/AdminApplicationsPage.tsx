import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table } from '../../components/shared/Table';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Alert } from '../../components/Alert';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { Modal } from '../../components/shared/Modal';
import { ApplicationDetail } from '../../components/admin/ApplicationDetail';
import { listAllApplications, approveApplication, rejectApplication, downloadResume, downloadLinkedInResume, exportApplications } from '../../services/adminService';
import { listJobs } from '../../services/jobService';
import type { ApplicationListItem } from '../../types/adminTypes';
import type { Job } from '../../types/jobTypes';

export const AdminApplicationsPage = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<ApplicationListItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<string | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  
  // Filters
  const [jobFilter, setJobFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    loadJobs();
    loadApplications();
  }, [jobFilter, statusFilter, skip]);

  const loadJobs = async () => {
    try {
      const response = await listJobs();
      setJobs(response.jobs);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  };

  const loadApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listAllApplications({
        job_id: jobFilter || undefined,
        status: statusFilter || undefined,
        skip,
        limit,
      });
      setApplications(response.applications);
      setTotalCount(response.count);
    } catch (err: any) {
      setError(err.detail || 'Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (applicationId: string) => {
    try {
      await approveApplication(applicationId);
      setSuccess('Application approved successfully');
      setTimeout(() => setSuccess(null), 3000);
      loadApplications();
    } catch (err: any) {
      setError(err.detail || 'Failed to approve application');
    }
  };

  const handleReject = async (applicationId: string) => {
    if (!window.confirm('Are you sure you want to reject this application?')) {
      return;
    }
    try {
      await rejectApplication(applicationId);
      setSuccess('Application rejected successfully');
      setTimeout(() => setSuccess(null), 3000);
      loadApplications();
    } catch (err: any) {
      setError(err.detail || 'Failed to reject application');
    }
  };

  const handleDownloadResume = async (applicationId: string) => {
    try {
      const blob = await downloadResume(applicationId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume-${applicationId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.detail || 'Failed to download resume');
    }
  };

  const handleDownloadLinkedInResume = async (applicationId: string) => {
    try {
      const blob = await downloadLinkedInResume(applicationId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `linkedin-resume-${applicationId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.detail || 'Failed to download LinkedIn resume');
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportApplications({
        job_id: jobFilter || undefined,
        status: statusFilter || undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'applications.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setSuccess('Applications exported successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.detail || 'Failed to export applications');
    }
  };

  const handleViewDetails = (applicationId: string) => {
    setSelectedApplication(applicationId);
    setIsDetailModalOpen(true);
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      evaluated: 'bg-blue-100 text-blue-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  const columns = [
    { key: 'user_email', header: 'User Email' },
    { key: 'user_name', header: 'User Name' },
    { key: 'job_title', header: 'Job Title' },
    {
      key: 'status',
      header: 'Status',
      render: (app: ApplicationListItem) => getStatusBadge(app.status),
    },
    { key: 'created_at', header: 'Created At' },
    {
      key: 'actions',
      header: 'Actions',
      render: (app: ApplicationListItem) => (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => handleViewDetails(app._id)}>
            View
          </Button>
          {app.status === 'pending' && (
            <>
              <Button size="sm" variant="primary" onClick={() => handleApprove(app._id)}>
                Approve
              </Button>
              <Button size="sm" variant="outline" onClick={() => handleReject(app._id)} className="text-red-600">
                Reject
              </Button>
            </>
          )}
          <Button size="sm" variant="outline" onClick={() => handleDownloadResume(app._id)}>
            Resume
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleDownloadLinkedInResume(app._id)}>
            LinkedIn
          </Button>
          {app.evaluation_id && (
            <Button size="sm" variant="outline" onClick={() => navigate(`/dashboard/evaluations/${app.evaluation_id}`)}>
              Evaluation
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin - Applications Management</h1>
          <p className="text-gray-600 mt-1">View and manage all job applications</p>
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Status</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setSkip(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="evaluated">Evaluated</option>
            </select>
          </div>
        </div>
      </div>

      {/* Applications Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={applications}
              emptyMessage="No applications found"
            />
            {totalCount > limit && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Showing {skip + 1} to {Math.min(skip + limit, totalCount)} of {totalCount} applications
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

      {/* Application Detail Modal */}
      {selectedApplication && (
        <Modal
          isOpen={isDetailModalOpen}
          onClose={() => {
            setIsDetailModalOpen(false);
            setSelectedApplication(null);
          }}
          title="Application Details"
          size="xl"
        >
          <ApplicationDetail
            applicationId={selectedApplication}
            onClose={() => {
              setIsDetailModalOpen(false);
              setSelectedApplication(null);
            }}
            onApprove={() => {
              handleApprove(selectedApplication);
              setIsDetailModalOpen(false);
              setSelectedApplication(null);
            }}
            onReject={() => {
              handleReject(selectedApplication);
              setIsDetailModalOpen(false);
              setSelectedApplication(null);
            }}
          />
        </Modal>
      )}
    </div>
  );
};

