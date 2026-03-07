import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../Button';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { Alert } from '../Alert';
import { ScoreBreakdown } from '../evaluations/ScoreBreakdown';
import { getApplicationDetails, downloadResume, downloadLinkedInResume } from '../../services/adminService';
import { getEvaluation } from '../../services/evaluationService';
import type { ApplicationDetailResponse, ApplicationTimelineEvent } from '../../types/adminTypes';
import type { EvaluationResponse } from '../../types/evaluationTypes';
import TurnoverRiskTabSafe from '../turnover/TurnoverRiskTab';

interface JobApplicantDetailProps {
  applicationId: string;
  jobId: string;
}

type TabType = 'user-info' | 'evaluation-result' | 'overview' | 'turnover-risk';

export const JobApplicantDetail = ({ applicationId, jobId }: JobApplicantDetailProps) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('user-info');
  const [application, setApplication] = useState<ApplicationDetailResponse | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [applicationId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const appData = await getApplicationDetails(applicationId);
      setApplication(appData);

      if (appData.evaluation_id) {
        try {
          const evalData = await getEvaluation(appData.evaluation_id);
          setEvaluation(evalData);
        } catch (err) {
          console.warn('Failed to load evaluation:', err);
        }
      }
    } catch (err: any) {
      setError(err.detail || 'Failed to load applicant details');
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

  const buildTimeline = (): ApplicationTimelineEvent[] => {
    if (!application) return [];
    const timeline: ApplicationTimelineEvent[] = [];

    timeline.push({
      event_type: 'application_submitted',
      timestamp: application.created_at,
      description: 'Application submitted',
    });

    if (application.status === 'approved') {
      timeline.push({
        event_type: 'status_changed',
        timestamp: application.created_at,
        description: 'Application approved',
        metadata: { status: 'approved' },
      });
    } else if (application.status === 'rejected') {
      timeline.push({
        event_type: 'status_changed',
        timestamp: application.created_at,
        description: 'Application rejected',
        metadata: { status: 'rejected' },
      });
    }

    if (evaluation) {
      timeline.push({
        event_type: 'evaluation_started',
        timestamp: evaluation.created_at || application.created_at,
        description: 'Evaluation process started',
      });
      timeline.push({
        event_type: 'evaluation_completed',
        timestamp: evaluation.created_at || application.created_at,
        description: `Evaluation completed with score: ${evaluation.total_score}`,
        metadata: { score: evaluation.total_score, decision: evaluation.decision },
      });
    }

    return timeline.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
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
        <Button
          variant="outline"
          onClick={() => navigate(`/dashboard/admin/jobs/${jobId}/applicants`)}
          className="mt-4"
        >
          Back to Applicants
        </Button>
      </div>
    );
  }

  const user = application.user;
  const timeline = buildTimeline();

  const tabs = [
    { id: 'user-info' as TabType, label: 'User Info' },
    { id: 'evaluation-result' as TabType, label: 'Evaluation Result' },
    { id: 'overview' as TabType, label: 'Overview' },
    // { id: 'turnover-risk' as TabType, label: 'Early Attrition Risk' },
  ];

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">

        {/* ── User Info (unchanged) ── */}
        {activeTab === 'user-info' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">User Information</h3>
              <div className="bg-gray-50 rounded-lg p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm font-medium text-gray-500">Email:</span>
                    <p className="text-gray-900 mt-1">{user.email || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">Name:</span>
                    <p className="text-gray-900 mt-1">
                      {user.first_name || ''} {user.last_name || ''}
                    </p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">City:</span>
                    <p className="text-gray-900 mt-1">{user.city || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-500">Phone:</span>
                    <p className="text-gray-900 mt-1">{user.phone_number || 'N/A'}</p>
                  </div>
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
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Documents</h3>
              <div className="flex gap-4">
                {user.cv_file_path && (
                  <Button variant="outline" onClick={handleDownloadResume}>Download Resume</Button>
                )}
                {user.linkedin_file_path && (
                  <Button variant="outline" onClick={handleDownloadLinkedInResume}>Download LinkedIn Resume</Button>
                )}
                {!user.cv_file_path && !user.linkedin_file_path && (
                  <p className="text-sm text-gray-500">No files available</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Evaluation Result ── */}
        {activeTab === 'evaluation-result' && (
          <div className="space-y-6">
            {/* Evaluation Status Card */}
            {application && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Evaluation Status</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Status</p>
                    <p className="text-base font-medium">
                      {application.evaluation_status === 'pending' && (
                        <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800">
                          Pending
                        </span>
                      )}
                      {application.evaluation_status === 'processing' && (
                        <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800">
                          Processing
                        </span>
                      )}
                      {application.evaluation_status === 'evaluated' && (
                        <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium bg-green-100 text-green-800">
                          Evaluated
                        </span>
                      )}
                      {application.evaluation_status === 'failed' && (
                        <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium bg-red-100 text-red-800">
                          Failed
                        </span>
                      )}
                      {!application.evaluation_status && (
                        <span className="text-gray-500">Not started</span>
                      )}
                    </p>
                  </div>
                  {application.processing_started_at && (
                    <div>
                      <p className="text-sm text-gray-500">Processing Started</p>
                      <p className="text-base font-medium text-gray-900">
                        {new Date(application.processing_started_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {application.processing_completed_at && (
                    <div>
                      <p className="text-sm text-gray-500">Processing Completed</p>
                      <p className="text-base font-medium text-gray-900">
                        {new Date(application.processing_completed_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {application.processing_started_at && application.processing_completed_at && (
                    <div>
                      <p className="text-sm text-gray-500">Processing Time</p>
                      <p className="text-base font-medium text-gray-900">
                        {Math.round(
                          (new Date(application.processing_completed_at).getTime() -
                            new Date(application.processing_started_at).getTime()) /
                            1000
                        )}{' '}
                        seconds
                      </p>
                    </div>
                  )}
                  {application.error_message && (
                    <div className="md:col-span-2">
                      <p className="text-sm text-gray-500">Error Message</p>
                      <p className="text-base font-medium text-red-600 bg-red-50 p-2 rounded">
                        {application.error_message}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {evaluation ? (
              <>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900 mb-2">Evaluation Results</h3>
                      <p className="text-sm text-gray-600">Evaluation ID: {evaluation._id}</p>
                    </div>
                    <div className="text-right">
                      <div className={`text-4xl font-bold ${
                        evaluation.total_score >= 75 ? 'text-green-600'
                        : evaluation.total_score >= 60 ? 'text-yellow-600'
                        : 'text-red-600'
                      }`}>
                        {evaluation.total_score}
                      </div>
                      <div
                        className={`mt-2 inline-flex items-center rounded-md px-3 py-1 text-sm font-medium ${
                          evaluation.decision === 'Proceed'
                            ? 'bg-green-100 text-green-800'
                            : evaluation.decision === 'Review'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {evaluation.decision}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <ScoreBreakdown breakdown={evaluation.breakdown || {}} />
                </div>
                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      const evalId = application?.evaluation_id || evaluation?._id;
                      if (evalId) navigate(`/dashboard/evaluations/${evalId}`);
                      else setError('Evaluation ID not available');
                    }}
                  >
                    View Full Evaluation Details
                  </Button>
                </div>
              </>
            ) : (
              <div className="bg-gray-50 rounded-lg p-6 text-center">
                <p className="text-gray-600">No evaluation available for this application yet.</p>
                <p className="text-sm text-gray-500 mt-2">The evaluation process may still be in progress.</p>
              </div>
            )}
          </div>
        )}

        {/* ── Overview ── */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Application Timeline</h3>
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                {timeline.length > 0 ? (
                  <div className="relative">
                    {timeline.map((event, index) => (
                      <div key={index} className="flex items-start mb-6 last:mb-0">
                        <div className="flex-shrink-0">
                          <div className={`w-3 h-3 rounded-full ${
                            event.event_type === 'application_submitted' ? 'bg-blue-500'
                            : event.event_type === 'evaluation_completed' ? 'bg-green-500'
                            : event.event_type === 'status_changed'
                              ? event.metadata?.status === 'approved' ? 'bg-green-500' : 'bg-red-500'
                            : 'bg-yellow-500'
                          }`} />
                          {index < timeline.length - 1 && (
                            <div className="w-0.5 h-12 bg-gray-300 ml-1.5" />
                          )}
                        </div>
                        <div className="ml-4 flex-1">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium text-gray-900">{event.description}</p>
                            <p className="text-xs text-gray-500">{new Date(event.timestamp).toLocaleString()}</p>
                          </div>
                          {event.metadata && (
                            <div className="mt-2 space-y-1">
                              {event.metadata.score !== undefined && (
                                <p className="text-xs text-gray-600">Score: <span className="font-medium">{event.metadata.score}</span></p>
                              )}
                              {event.metadata.decision && (
                                <p className="text-xs text-gray-600">
                                  Decision: <span className="font-medium">{event.metadata.decision}</span>
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No timeline events available</p>
                )}
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Application Summary</h3>
              <div className="bg-gray-50 rounded-lg p-6 space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-gray-500">Status:</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    application.status === 'approved' ? 'bg-green-100 text-green-800'
                    : application.status === 'rejected' ? 'bg-red-100 text-red-800'
                    : application.status === 'evaluated' ? 'bg-blue-100 text-blue-800'
                    : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {application.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-gray-500">Applied Date:</span>
                  <span className="text-sm text-gray-900">{new Date(application.created_at).toLocaleString()}</span>
                </div>
                {application.evaluation_id && (
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-500">Evaluation ID:</span>
                    <span className="text-sm text-gray-900">{application.evaluation_id}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Turnover Risk ── */}
        {/* {activeTab === 'turnover-risk' && (
          <TurnoverRiskTabSafe
            userEmail={user.email ?? ""}
            jobId={application.job._id ?? ""}
            jobDescription={application.job.jd_text ?? ""}
            jobTitle={application.job.title ?? ""}
            jobLocation={application.job.location ?? ""}
            evaluationDecision={evaluation?.decision}
          />
        )} */}

      </div>
    </div>
  );
};