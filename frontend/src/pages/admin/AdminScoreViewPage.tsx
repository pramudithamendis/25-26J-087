import { useState, useEffect } from 'react';
import { listAllCVTrendScores, listAllEvaluations, sendApplicationEmail } from '../../services/adminService';
import type { CVTrendScore } from '../../types/adminTypes';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { Alert } from '../../components/Alert';
import { useNavigate } from 'react-router-dom';
import { listJobs } from '../../services/jobService';
import type { EvaluationListItem } from '../../types/adminTypes';
import type { Job } from '../../types/jobTypes';
// import { getDecisionDisplayValue } from '../../utils/decisionMapper';
import apiClient from '../../config/api';
import type { TurnoverPredictionResponse } from '../../types/turnover.types';
import { TrendingUp, Briefcase, Users, Mail, Calendar, MapPin, FileText, AlertCircle, LayoutGrid, List, CheckCircle, XCircle, ArrowRight, Search } from 'lucide-react';
import { Modal } from '../../components/shared/Modal';
import { Table } from '../../components/shared/Table';


const MiniPDFViewer = ({ cvId, email }: { cvId?: string; email: string }) => {
  const [showFullscreen, setShowFullscreen] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cvId || !showFullscreen || pdfBlobUrl) return;

    const loadPdf = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await apiClient.get(`/cv/${cvId}/pdf`, {
          responseType: "blob",
        });

        const blob = new Blob([response.data], { type: "application/pdf" });
        const url = URL.createObjectURL(blob);

        setPdfBlobUrl(url);
      } catch (error) {
        console.error("Failed to load CV PDF:", error);
        setError("Failed to load PDF");
      } finally {
        setLoading(false);
      }
    };

    loadPdf();

    return () => {
      // We don't necessarily want to revoke immediately if we want to cache it while the component is mounted,
      // but if the user closes and reopens, we might want to keep it.
      // However, for memory management, revoking on unmount is good.
    };
  }, [cvId, showFullscreen, pdfBlobUrl]);

  useEffect(() => {
    return () => {
      if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl);
    };
  }, [pdfBlobUrl]);

  return (
    <>
      <div
        onClick={cvId ? () => setShowFullscreen(true) : undefined}
        className={`h-full bg-gray-50 rounded-lg border border-gray-200 transition-all duration-200 flex flex-col items-center justify-center ${cvId
          ? 'cursor-pointer hover:bg-white hover:border-blue-400 hover:shadow-sm'
          : 'cursor-not-allowed opacity-50'
          }`}
        title={cvId ? "Click to view PDF" : "No PDF available"}
      >
        {loading && showFullscreen ? (
          <LoadingSpinner size="sm" />
        ) : cvId ? (
          <>
            <div className="p-3 bg-blue-50 rounded-full mb-2 group-hover:bg-blue-100 transition-colors">
              <FileText size={24} className="text-blue-600" />
            </div>
            <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">View CV</span>
          </>
        ) : (
          <>
            <FileText size={24} className="text-gray-300 mb-2" />
            <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">No PDF</span>
          </>
        )}
      </div>

      <Modal
        isOpen={showFullscreen}
        onClose={() => setShowFullscreen(false)}
        title={`CV View: ${email}`}
        size="xl"
      >
        <div className="w-full bg-gray-100 rounded-lg overflow-hidden border border-gray-200" style={{ height: '75vh' }}>
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <LoadingSpinner size="lg" />
                <p className="mt-4 text-gray-500 font-medium">Loading PDF document...</p>
              </div>
            </div>
          ) : pdfBlobUrl ? (
            <iframe
              src={pdfBlobUrl}
              className="w-full h-full border-0"
              title={`CV for ${email}`}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <AlertCircle size={48} className="text-gray-300 mb-4" />
              <p className="font-medium">{error || "No PDF available for display"}</p>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
};

export const AdminScoreViewPage = () => {
  const navigate = useNavigate();
  const [results, setResults] = useState<CVTrendScore[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationListItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [turnoverPredictions, setTurnoverPredictions] = useState<Record<string, TurnoverPredictionResponse>>({});
  const [loading, setLoading] = useState(true);
  const [loadingTurnover, setLoadingTurnover] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [selectedPdfCv, setSelectedPdfCv] = useState<CVTrendScore | null>(null);
  const [sendingEmail, setSendingEmail] = useState<string | null>(null); // tracks cv_id being emailed

  // Filters
  const [scoreFilter, setScoreFilter] = useState('');
  const [jobFilter, setJobFilter] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [attritionFilter, setAttritionFilter] = useState('');
  const [emailFilter, setEmailFilter] = useState('');

  useEffect(() => {
    loadJobs();
    loadEvaluations();
    loadTrendScores();
  }, []);

  useEffect(() => {
    if (results.length > 0) {
      loadTurnoverPredictions();
    }
  }, [results]);

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
      const response = await listAllEvaluations({});
      setEvaluations(response.evaluations);
    } catch (err) {
      console.error('Failed to load evaluations:', err);
    }
  };

  const loadTrendScores = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listAllCVTrendScores();
      setResults(response.results);
    } catch (err: any) {
      setError(err.detail || 'Failed to load evaluations');
    } finally {
      setLoading(false);
    }
  };

  const loadTurnoverPredictions = async () => {
    setLoadingTurnover(true);
    try {
      const cvIds = results.map(cv => cv.cv_id).filter(Boolean).join(',');
      if (!cvIds) return;

      const response = await apiClient.get(`/turnover/latest-results/batch?cv_ids=${cvIds}`);
      const batchResults: TurnoverPredictionResponse[] = response.data.results || [];

      const predictions: Record<string, TurnoverPredictionResponse> = {};
      for (const result of batchResults) {
        if (result.cv_id) {
          predictions[result.cv_id] = result;
        }
      }
      setTurnoverPredictions(predictions);
    } catch (err) {
      console.error('Failed to load turnover predictions:', err);
    } finally {
      setLoadingTurnover(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getTrendScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-green-600';
    if (score >= 0.4) return 'text-yellow-600';
    if (score >= 0.2) return 'text-orange-600';
    return 'text-red-600';
  };

  const getTurnoverRiskColor = (riskLevel: number) => {
    if (riskLevel === 2) return 'text-green-600';
    if (riskLevel === 1) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getTurnoverRiskBg = (riskLevel: number) => {
    if (riskLevel === 2) return 'bg-green-100';
    if (riskLevel === 1) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const getTurnoverRiskText = (riskLevel: number) => {
    if (riskLevel === 2) return 'Low';
    if (riskLevel === 1) return 'Medium';
    return 'High';
  };

  const getSkillScoreColor = (score: number) => {
    if (score >= 0.5) return 'bg-green-100 text-green-800';
    if (score >= 0.3) return 'bg-yellow-100 text-yellow-800';
    if (score >= 0.1) return 'bg-blue-100 text-blue-800';
    return 'bg-gray-100 text-gray-800';
  };

  const getDecisionBadge = (decision: string) => {
    const colors: Record<string, string> = {
      Proceed: 'bg-green-100 text-green-800',
      Review: 'bg-yellow-100 text-yellow-800',
      'Do Not Proceed': 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[decision] || 'bg-gray-100 text-gray-800'}`}>
        {decision}
      </span>
    );
  };

  const getEvaluationForCv = (email: string) => {
    return evaluations.find(e => e.user_email === email);
  };

  const getFilteredResults = () => {
    return results.filter(cv => {
      // Email search filter
      if (emailFilter && !cv.email.toLowerCase().includes(emailFilter.toLowerCase())) return false;

      // Score filter
      if (scoreFilter === 'high' && cv.cv_trend_score < 0.7) return false;
      if (scoreFilter === 'medium' && (cv.cv_trend_score < 0.4 || cv.cv_trend_score >= 0.7)) return false;
      if (scoreFilter === 'low' && cv.cv_trend_score >= 0.4) return false;

      // Get evaluation for this CV
      const evaluation = getEvaluationForCv(cv.email);

      // Job filter
      if (jobFilter && evaluation?.job_id !== jobFilter) return false;

      // Decision filter
      if (decisionFilter && evaluation?.decision !== decisionFilter) return false;

      // Attrition risk filter
      if (attritionFilter !== '') {
        const turnover = cv.cv_id ? turnoverPredictions[cv.cv_id] : null;
        if (!turnover || turnover.prediction.risk_level !== parseInt(attritionFilter)) return false;
      }

      // Hide rejected CVs
      if (cv.email_status === 'rejected') return false;

      return true;
    });
  };

  const handleAccept = async (cv: CVTrendScore) => {
    if (sendingEmail) return;
    setSendingEmail(cv.cv_id || cv.email);
    try {
      const evaluation = getEvaluationForCv(cv.email);
      const job = jobs.find(j => j._id === evaluation?.job_id);
      await sendApplicationEmail({
        email: cv.email,
        type: 'accepted',
        applicant_name: cv.email.split('@')[0],
        job_title: job?.title || 'the position',
      });
      setSuccess(`Acceptance email sent to ${cv.email}`);
      await loadTrendScores(); // Refresh from backend to get updated email_status
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Failed to send acceptance email');
    } finally {
      setSendingEmail(null);
      setTimeout(() => setSuccess(null), 3000);
    }
  };

  const handleReject = async (cv: CVTrendScore) => {
    if (sendingEmail) return;
    setSendingEmail(cv.cv_id || cv.email);
    try {
      const evaluation = getEvaluationForCv(cv.email);
      const job = jobs.find(j => j._id === evaluation?.job_id);
      await sendApplicationEmail({
        email: cv.email,
        type: 'rejected',
        applicant_name: cv.email.split('@')[0],
        job_title: job?.title || 'the position',
      });
      setSuccess(`Rejection email sent to ${cv.email}`);
      await loadTrendScores(); // Refresh from backend to hide the rejected CV
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Failed to send rejection email');
    } finally {
      setSendingEmail(null);
      setTimeout(() => setSuccess(null), 3000);
    }
  };

  const filteredResults = getFilteredResults();

  const tableColumns = [
    {
      key: 'email',
      header: 'Applicant',
      render: (cv: CVTrendScore) => (
        <div className="flex flex-col">
          <span className="font-medium text-gray-900">{cv.email}</span>
          <button
            onClick={() => setSelectedPdfCv(cv)}
            className="text-[10px] text-blue-600 hover:underline text-left mt-0.5"
          >
            View CV
          </button>
        </div>
      )
    },
    {
      key: 'job',
      header: 'Job Title',
      render: (cv: CVTrendScore) => {
        const evaluation = getEvaluationForCv(cv.email);
        const job = jobs.find(j => j._id === evaluation?.job_id);
        return <span className="text-sm text-gray-600">{job?.title || 'N/A'}</span>;
      }
    },
    {
      key: 'cv_trend_score',
      header: 'Trend',
      render: (cv: CVTrendScore) => (
        <div className="flex items-center gap-2">
          <span className={`font-semibold ${getTrendScoreColor(cv.cv_trend_score)}`}>
            {(cv.cv_trend_score * 100).toFixed(1)}%
          </span>
          <div className="w-16 bg-gray-200 rounded-full h-1.5 hidden md:block">
            <div
              className={`h-1.5 rounded-full ${cv.cv_trend_score >= 0.7 ? 'bg-green-600' :
                cv.cv_trend_score >= 0.4 ? 'bg-yellow-600' :
                  cv.cv_trend_score >= 0.2 ? 'bg-orange-600' : 'bg-red-600'
                }`}
              style={{ width: `${cv.cv_trend_score * 100}%` }}
            />
          </div>
        </div>
      )
    },
    {
      key: 'attrition',
      header: 'Attrition Risk',
      render: (cv: CVTrendScore) => {
        const turnover = cv.cv_id ? turnoverPredictions[cv.cv_id] : null;
        if (loadingTurnover) return <LoadingSpinner size="sm" />;
        return turnover ? (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTurnoverRiskBg(turnover.prediction.risk_level)} ${getTurnoverRiskColor(turnover.prediction.risk_level)}`}>
            {getTurnoverRiskText(turnover.prediction.risk_level)}
          </span>
        ) : <span className="text-xs text-gray-400">N/A</span>;
      }
    },
    {
      key: 'evaluation',
      header: 'Evaluation',
      render: (cv: CVTrendScore) => {
        const evaluation = getEvaluationForCv(cv.email);
        return evaluation ? (
          <span className={`font-medium ${getScoreColor(evaluation.total_score)}`}>
            {evaluation.total_score.toFixed(1)}
          </span>
        ) : <span className="text-xs text-gray-400">-</span>;
      }
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (cv: CVTrendScore) => (
        <div className="flex gap-2">
          {cv.email_status === 'accepted' ? (
            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800">
              <CheckCircle size={14} className="mr-1" />
              Accepted
            </span>
          ) : (
            <>
              <button
                onClick={() => handleAccept(cv)}
                disabled={sendingEmail === (cv.cv_id || cv.email)}
                className="p-1 text-green-600 hover:bg-green-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Accept"
              >
                {sendingEmail === (cv.cv_id || cv.email) ? <LoadingSpinner size="sm" /> : <CheckCircle size={16} />}
              </button>
              <button
                onClick={() => handleReject(cv)}
                disabled={sendingEmail === (cv.cv_id || cv.email)}
                className="p-1 text-red-600 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Reject"
              >
                <XCircle size={16} />
              </button>
            </>
          )}
          {cv.cv_id && turnoverPredictions[cv.cv_id] && (
            <button
              onClick={() => navigate(`/dashboard/admin/turnover/result?cv_id=${cv.cv_id}`)}
              className="p-1 text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
              title="Details"
            >
              <ArrowRight size={16} />
            </button>
          )}
        </div>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 top-0 z-10 py-6 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col gap-6">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Admin Score View</h1>
              <p className="text-slate-500 mt-2 text-lg">
                Review CV trend scores, evaluations, and early attrition risk
              </p>
            </div>

            {/* Filters */}
            <div className="flex  justify-between items-center">
              <div className="flex gap-4 items-center">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search size={14} className="text-gray-400" />
                  </div>
                  <input
                    type="text"
                    placeholder="Search by email..."
                    value={emailFilter}
                    onChange={(e) => setEmailFilter(e.target.value)}
                    className="pl-9 pr-3 py-2 border border-gray-300 rounded-md bg-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 min-w-[200px]"
                  />
                </div>

                <select
                  value={jobFilter}
                  onChange={(e) => setJobFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md bg-white text-sm min-w-[150px]"
                >
                  <option value="">All Jobs</option>
                  {jobs.map((job) => (
                    <option key={job._id} value={job._id}>
                      {job.title}
                    </option>
                  ))}
                </select>

                <select
                  value={decisionFilter}
                  onChange={(e) => setDecisionFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md bg-white text-sm min-w-[150px]"
                >
                  <option value="">All Decisions</option>
                  <option value="Selected">Proceed</option>
                  <option value="Review">Review Required</option>
                  <option value="Not Selected">Do Not Proceed</option>
                </select>

                <select
                  value={scoreFilter}
                  onChange={(e) => setScoreFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md bg-white text-sm min-w-[150px]"
                >
                  <option value="">All Trend Scores</option>
                  <option value="high">High Trend (≥70%)</option>
                  <option value="medium">Medium Trend (40-70%)</option>
                  <option value="low">Low Trend (&lt;40%)</option>
                </select>

                <select
                  value={attritionFilter}
                  onChange={(e) => setAttritionFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md bg-white text-sm min-w-[150px]"
                >
                  <option value="">All Early Attrition Risks</option>
                  <option value="2">Low Early Attrition Risk</option>
                  <option value="1">Moderate Early Attrition Risk</option>
                  <option value="0">High Early Attrition Risk</option>
                </select>
              </div>

              <div className="flex bg-gray-100 p-1 rounded-md border border-gray-200 w-18">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-1.5 rounded-md transition-all ${viewMode === 'grid'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                    }`}
                  title="Grid View"
                >
                  <LayoutGrid size={18} />
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`p-1.5 rounded-md transition-all ${viewMode === 'table'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                    }`}
                  title="Table View"
                >
                  <List size={18} />
                </button>
              </div>
            </div>


          </div>
        </div>
      </div>

      {/* Alerts */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        {error && (
          <Alert type="error" onClose={() => setError(null)} className="mb-4">
            {error}
          </Alert>
        )}
        {success && (
          <Alert type="success" onClose={() => setSuccess(null)} className="mb-4">
            {success}
          </Alert>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : filteredResults.length === 0 ? (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center text-gray-500">
            No CVs found matching the selected criteria
          </div>
        </div>
      ) : (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Results count */}
          <div className="mb-4 text-sm text-gray-600">
            Showing {filteredResults?.length} CVs
          </div>

          {viewMode === 'grid' ? (
            /* Grid of CV Cards */
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {filteredResults?.map((cv) => {
                const evaluation = getEvaluationForCv(cv.email);
                const turnover = cv.cv_id ? turnoverPredictions[cv.cv_id] : null;

                return (
                  <div
                    key={cv.cv_id || cv.email}
                    className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
                  >
                    {/* Header */}
                    <div className="border-b border-gray-200 bg-gray-50 px-4 py-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <Mail size={14} className="text-gray-400 flex-shrink-0" />
                          <span className="text-sm font-medium text-gray-900 truncate" title={cv.email}>
                            {cv.email}
                          </span>
                        </div>

                      </div>
                    </div>

                    {/* Main Content */}
                    <div className="flex h-48">
                      {/* Left side - PDF Thumbnail */}
                      <div className="w-1/3 p-2">
                        <MiniPDFViewer cvId={cv.cv_id} email={cv.email} />
                      </div>

                      {/* Right side - Scores */}
                      <div className="w-2/3 p-3 space-y-2">
                        {/* Trend Score */}
                        <div>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <div className="flex items-center gap-1">
                              <TrendingUp size={12} className="text-gray-400" />
                              <span className="text-gray-500">Trend</span>
                            </div>
                            <span className={`font-medium ${getTrendScoreColor(cv.cv_trend_score)}`}>
                              {(cv.cv_trend_score * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${cv.cv_trend_score >= 0.7 ? 'bg-green-600' :
                                cv.cv_trend_score >= 0.4 ? 'bg-yellow-600' :
                                  cv.cv_trend_score >= 0.2 ? 'bg-orange-600' : 'bg-red-600'
                                }`}
                              style={{ width: `${cv.cv_trend_score * 100}%` }}
                            />
                          </div>
                        </div>

                        {/* Attrition Risk */}
                        <div>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <div className="flex items-center gap-1">
                              <Users size={12} className="text-gray-400" />
                              <span className="text-gray-500">Attrition Risk</span>
                            </div>
                            {loadingTurnover ? (
                              <LoadingSpinner size="sm" />
                            ) : turnover ? (
                              <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${getTurnoverRiskBg(turnover.prediction.risk_level)} ${getTurnoverRiskColor(turnover.prediction.risk_level)}`}>
                                {getTurnoverRiskText(turnover.prediction.risk_level)}
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">N/A</span>
                            )}
                          </div>
                        </div>

                        {/* Evaluation Score */}
                        {evaluation && (
                          <div>
                            <div className="flex items-center justify-between text-xs mb-1">
                              <div className="flex items-center gap-1">
                                <Briefcase size={12} className="text-gray-400" />
                                <span className="text-gray-500">Evaluation</span>
                              </div>
                              <span className={`font-medium ${getScoreColor(evaluation.total_score)}`}>
                                {evaluation.total_score.toFixed(1)}
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-1.5">
                              <div
                                className={`h-1.5 rounded-full ${evaluation.total_score >= 75 ? 'bg-green-600' :
                                  evaluation.total_score >= 60 ? 'bg-yellow-600' : 'bg-red-600'
                                  }`}
                                style={{ width: `${evaluation.total_score}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {evaluation && (
                          <div className="flex-shrink-0">
                            {getDecisionBadge(evaluation.decision)}
                          </div>
                        )}

                        {/* Skills Preview */}
                        {cv.skills_matched && cv.skills_matched.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {cv.skills_matched.slice(0, 2).map((skill, idx) => (
                              <span
                                key={idx}
                                className={`text-[10px] px-1 py-0.5 rounded ${getSkillScoreColor(skill.score)}`}
                              >
                                {skill.skill}
                              </span>
                            ))}
                            {cv.skills_matched.length > 2 && (
                              <span className="text-[10px] text-gray-400">
                                +{cv.skills_matched.length - 2}
                              </span>
                            )}
                          </div>
                        )}

                        {/* Location and Date */}
                        <div className="flex items-center justify-between text-[10px] text-gray-400 pt-1">
                          {turnover?.job_location && (
                            <div className="flex items-center gap-1">
                              <MapPin size={10} />
                              <span className="truncate max-w-[80px]">{turnover.job_location}</span>
                            </div>
                          )}
                          <div className="flex items-center gap-1">
                            <Calendar size={10} />
                            <span>{new Date(cv.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="border-t border-gray-200 bg-gray-50 px-4 py-2">
                      <div className="flex items-center justify-between">
                        <div className="flex gap-2">
                          {cv.email_status === 'accepted' ? (
                            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                              <CheckCircle size={14} className="mr-1.5" />
                              Accepted
                            </span>
                          ) : (
                            <>
                              <button
                                onClick={() => handleAccept(cv)}
                                disabled={sendingEmail === (cv.cv_id || cv.email)}
                                className="flex items-center gap-1.5 text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-md transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                              >
                                {sendingEmail === (cv.cv_id || cv.email) ? (
                                  <>
                                    <LoadingSpinner size="sm" />
                                    <span>Sending...</span>
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle size={14} />
                                    <span>Accept</span>
                                  </>
                                )}
                              </button>
                              <button
                                onClick={() => handleReject(cv)}
                                disabled={sendingEmail === (cv.cv_id || cv.email)}
                                className="flex items-center gap-1.5 text-xs bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-md transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                              >
                                <XCircle size={14} />
                                <span>Reject</span>
                              </button>
                            </>
                          )}
                        </div>
                        {turnover && (
                          <button
                            onClick={() => navigate(`/dashboard/admin/turnover/result?cv_id=${cv.cv_id}`)}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                          >
                            Details →
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Table View */
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <Table
                columns={tableColumns}
                data={filteredResults}
                emptyMessage="No CVs found matching the selected criteria"
              />
            </div>
          )}

          {/* Modal for PDF View from Table */}
          {selectedPdfCv && (
            <Modal
              isOpen={!!selectedPdfCv}
              onClose={() => setSelectedPdfCv(null)}
              title={`CV View: ${selectedPdfCv.email}`}
              size="xl"
            >
              <div className="w-full bg-gray-100 rounded-lg overflow-hidden border border-gray-200" style={{ height: '75vh' }}>
                <LazyPDFViewer cvId={selectedPdfCv.cv_id} email={selectedPdfCv.email} />
              </div>
            </Modal>
          )}

          {/* Loading indicator */}
          {loadingTurnover && filteredResults.length > 0 && (
            <div className="mt-6 flex justify-center">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 px-4 py-2 flex items-center gap-2">
                <LoadingSpinner size="sm" />
                <span className="text-sm text-gray-600">Loading attrition data...</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Simplified PDF Viewer component for the Table Modal or shared use
const LazyPDFViewer = ({ cvId, email }: { cvId?: string; email: string }) => {
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cvId || pdfBlobUrl) return;

    const loadPdf = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.get(`/cv/${cvId}/pdf`, { responseType: "blob" });
        const blob = new Blob([response.data], { type: "application/pdf" });
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
      } catch (error) {
        console.error("Failed to load CV PDF:", error);
        setError("Failed to load PDF");
      } finally {
        setLoading(false);
      }
    };

    loadPdf();

    return () => {
      if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl);
    };
  }, [cvId, pdfBlobUrl]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-500 font-medium">Loading PDF document...</p>
        </div>
      </div>
    );
  }

  if (pdfBlobUrl) {
    return <iframe src={pdfBlobUrl} className="w-full h-full border-0" title={`CV for ${email}`} />;
  }

  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-500">
      <AlertCircle size={48} className="text-gray-300 mb-4" />
      <p className="font-medium">{error || "No PDF available for display"}</p>
    </div>
  );
};
