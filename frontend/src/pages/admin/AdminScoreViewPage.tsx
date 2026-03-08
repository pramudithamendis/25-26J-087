import { useState, useEffect } from 'react';
import { listAllCVTrendScores } from '../../services/adminService';
import type { CVTrendScore } from '../../types/adminTypes';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { Alert } from '../../components/Alert';
import { useNavigate } from 'react-router-dom';
import { listJobs } from '../../services/jobService';
import { listAllEvaluations } from '../../services/adminService';
import type { EvaluationListItem } from '../../types/adminTypes';
import type { Job } from '../../types/jobTypes';
// import { getDecisionDisplayValue } from '../../utils/decisionMapper';
import apiClient from '../../config/api';
import type { TurnoverPredictionResponse } from '../../types/turnover.types';
import { TrendingUp, Briefcase, Users, Mail, Calendar, MapPin, FileText } from 'lucide-react';

const MiniPDFViewer = ({ cvId, email }: { cvId?: string; email: string }) => {
  const [showFullscreen, setShowFullscreen] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cvId) return;

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
      if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl);
    };
  }, [cvId]);

  if (showFullscreen) {
    return (
      <div className="fixed inset-4 z-50 bg-white rounded-lg shadow-xl border flex flex-col">
        <div className="border-b px-4 py-3 flex justify-between items-center">
          <h3 className="font-semibold">CV: {email}</h3>
          <button
            onClick={() => setShowFullscreen(false)}
            className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded"
          >
            Close
          </button>
        </div>

        <div className="flex-1 bg-gray-100 p-2">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <LoadingSpinner size="lg" />
            </div>
          ) : pdfBlobUrl ? (
            <iframe src={pdfBlobUrl} className="w-full h-full border-0" title={`CV for ${email}`} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              {error || "No PDF available"}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div 
      onClick={() => setShowFullscreen(true)}
      className="h-full bg-gray-100 rounded-lg cursor-pointer hover:bg-gray-200 transition-colors flex flex-col items-center justify-center border-2 border-transparent hover:border-blue-300"
      title="Click to view PDF"
    >
      {loading ? (
        <LoadingSpinner size="sm" />
      ) : pdfBlobUrl ? (
        <>
          <FileText size={32} className="text-gray-400 mb-2" />
          <span className="text-xs text-gray-500">Click to view PDF</span>
        </>
      ) : (
        <>
          <FileText size={32} className="text-gray-300 mb-2" />
          <span className="text-xs text-gray-400">{error || "No PDF"}</span>
        </>
      )}
    </div>
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
  
  // Filters
  const [scoreFilter, setScoreFilter] = useState('');
  const [jobFilter, setJobFilter] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [attritionFilter, setAttritionFilter] = useState('');

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
      Selected: 'bg-green-100 text-green-800',
      Review: 'bg-yellow-100 text-yellow-800',
      'Not Selected': 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[decision] || 'bg-gray-100 text-gray-800'}`}>
        {/* {getDecisionDisplayValue(decision)} */}
      </span>
    );
  };

  const getEvaluationForCv = (email: string) => {
    return evaluations.find(e => e.user_email === email);
  };

  const getFilteredResults = () => {
    return results.filter(cv => {
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

      return true;
    });
  };

  const handleAccept = (cvId?: string) => {
    console.log('Accepted CV:', cvId);
    setSuccess('CV accepted successfully');
    setTimeout(() => setSuccess(null), 3000);
  };

  const handleReject = (cvId?: string) => {
    console.log('Rejected CV:', cvId);
    setSuccess('CV rejected successfully');
    setTimeout(() => setSuccess(null), 3000);
  };

  const filteredResults = getFilteredResults();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Admin Score View</h1>
              <p className="text-gray-600 mt-1">
                Review CV trend scores, evaluations, and early attrition risk
              </p>
            </div>
            
            {/* Filters */}
            <div className="flex flex-wrap gap-3">
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
                <option value="">All Attrition Risks</option>
                <option value="2">Low Risk</option>
                <option value="1">Medium Risk</option>
                <option value="0">High Risk</option>
              </select>
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
            Showing {filteredResults.length} CVs
          </div>

          {/* Grid of CV Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredResults.map((cv) => {
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
                      {evaluation && (
                        <div className="flex-shrink-0">
                          {getDecisionBadge(evaluation.decision)}
                        </div>
                      )}
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
                            className={`h-1.5 rounded-full ${
                              cv.cv_trend_score >= 0.7 ? 'bg-green-600' :
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
                              className={`h-1.5 rounded-full ${
                                evaluation.total_score >= 75 ? 'bg-green-600' :
                                evaluation.total_score >= 60 ? 'bg-yellow-600' : 'bg-red-600'
                              }`}
                              style={{ width: `${evaluation.total_score}%` }}
                            />
                          </div>
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
                        <button
                          onClick={() => {
                            handleAccept(cv.cv_id);
                            localStorage.setItem("currentEmail", cv.email);
                            }}
                          className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded-md transition-colors"
                        >
                          Accept
                        </button>
                        <button
                          onClick={() => handleReject(cv.cv_id)}
                          className="text-xs bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded-md transition-colors"
                        >
                          Reject
                        </button>
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