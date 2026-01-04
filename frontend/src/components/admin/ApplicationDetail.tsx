import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../Button';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { Alert } from '../Alert';
import { getApplicationDetails, downloadResume, downloadLinkedInResume } from '../../services/adminService';
import type { ApplicationDetailResponse } from '../../types/adminTypes';

interface ApplicationDetailProps {
  applicationId: string;
  onClose: () => void;
  onApprove: () => void;
  onReject: () => void;
}

export const ApplicationDetail = ({ applicationId, onClose, onApprove, onReject }: ApplicationDetailProps) => {
  const navigate = useNavigate();
  const [application, setApplication] = useState<ApplicationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadApplication();
  }, [applicationId]);

  const loadApplication = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getApplicationDetails(applicationId);
      setApplication(data);
    } catch (err: any) {
      setError(err.detail || 'Failed to load application details');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadResume = async () => {
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

  const handleDownloadLinkedInResume = async () => {
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

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !application) {
    return (
      <div>
        <Alert type="error">{error || 'Application not found'}</Alert>
        <Button variant="outline" onClick={onClose} className="mt-4">
          Close
        </Button>
      </div>
    );
  }

  const user = application.user;
  const job = application.job;

  return (
    <div className="space-y-6">
      {/* User Information */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">User Information</h3>
        <div className="bg-gray-50 rounded-lg p-4 space-y-2">
          <div>
            <span className="text-sm font-medium text-gray-500">Email:</span>
            <span className="ml-2 text-gray-900">{user.email || 'N/A'}</span>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-500">Name:</span>
            <span className="ml-2 text-gray-900">
              {user.first_name || ''} {user.last_name || ''}
            </span>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-500">City:</span>
            <span className="ml-2 text-gray-900">{user.city || 'N/A'}</span>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-500">Phone:</span>
            <span className="ml-2 text-gray-900">{user.phone_number || 'N/A'}</span>
          </div>
          {user.github_url && (
            <div>
              <span className="text-sm font-medium text-gray-500">GitHub:</span>
              <a href={user.github_url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600 hover:underline">
                {user.github_url}
              </a>
            </div>
          )}
          {user.linkedin_url && (
            <div>
              <span className="text-sm font-medium text-gray-500">LinkedIn:</span>
              <a href={user.linkedin_url} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-600 hover:underline">
                {user.linkedin_url}
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Job Information */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Job Information</h3>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="font-medium text-gray-900 mb-2">{job.title || 'N/A'}</div>
          <p className="text-sm text-gray-600">{job.jd_text || 'No description available'}</p>
        </div>
      </div>

      {/* Application Status */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Application Status</h3>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="mb-2">
            <span className="text-sm font-medium text-gray-500">Status:</span>
            <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${
              application.status === 'approved' ? 'bg-green-100 text-green-800' :
              application.status === 'rejected' ? 'bg-red-100 text-red-800' :
              application.status === 'evaluated' ? 'bg-blue-100 text-blue-800' :
              'bg-yellow-100 text-yellow-800'
            }`}>
              {application.status}
            </span>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-500">Created At:</span>
            <span className="ml-2 text-gray-900">
              {new Date(application.created_at).toLocaleString()}
            </span>
          </div>
          {application.evaluation_id && (
            <div className="mt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onClose();
                  navigate(`/dashboard/evaluations/${application.evaluation_id}`);
                }}
              >
                View Multi-Source-Evaluations
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Files */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Files</h3>
        <div className="flex gap-4">
          {user.cv_file_path && (
            <Button variant="outline" onClick={handleDownloadResume}>
              Download Resume
            </Button>
          )}
          {user.linkedin_file_path && (
            <Button variant="outline" onClick={handleDownloadLinkedInResume}>
              Download LinkedIn Resume
            </Button>
          )}
          {!user.cv_file_path && !user.linkedin_file_path && (
            <p className="text-sm text-gray-500">No files available</p>
          )}
        </div>
      </div>

      {/* Actions */}
      {application.status === 'pending' && (
        <div className="flex gap-4 pt-4 border-t border-gray-200">
          <Button variant="primary" onClick={onApprove}>
            Approve Application
          </Button>
          <Button variant="outline" onClick={onReject} className="text-red-600">
            Reject Application
          </Button>
        </div>
      )}
    </div>
  );
};

