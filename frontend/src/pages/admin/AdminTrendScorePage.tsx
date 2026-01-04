import { useState, useEffect } from 'react';
import { Table } from '../../components/shared/Table';
import { Button } from '../../components/Button';
import { Alert } from '../../components/Alert';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { listAllCVTrendScores } from '../../services/adminService';
import type { CVTrendScore } from '../../types/adminTypes';

export const AdminTrendScorePage = () => {
  const [results, setResults] = useState<CVTrendScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [weekId, setWeekId] = useState<string>('');
  const [expandedSkills, setExpandedSkills] = useState<Record<string, boolean>>({});
  
  // Filters
  const [scoreFilter, setScoreFilter] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit] = useState(5);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    loadEvaluations();
  }, [scoreFilter, skip]);

  const loadEvaluations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listAllCVTrendScores();
      setResults(response.results);
      setTotalCount(response.resumes_processed || response.results.length);
      setWeekId(response.week_id || '');
    } catch (err: any) {
      setError(err.detail || 'Failed to load evaluations');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-green-600 font-semibold';      
    if (score >= 0.4) return 'text-yellow-600 font-semibold';     
    if (score >= 0.2) return 'text-orange-600 font-semibold';    
    return 'text-red-600 font-semibold';                         
  };

  const getSkillScoreColor = (score: number) => {
    if (score >= 0.5) return 'bg-green-100 text-green-800 border border-green-200 hover:bg-green-200';
    if (score >= 0.3) return 'bg-yellow-100 text-yellow-800 border border-yellow-200 hover:bg-yellow-200';
    if (score >= 0.1) return 'bg-blue-100 text-blue-800 border border-blue-200 hover:bg-blue-200';
    return 'bg-gray-100 text-gray-800 border border-gray-200 hover:bg-gray-200';
  };

  // Get paginated results with filtering and sorting
  const getPaginatedResults = () => {
    let filteredResults = results;
    
    // Apply score filter
    if (scoreFilter === 'high') {
      filteredResults = results.filter(r => r.cv_trend_score >= 0.7);
    } else if (scoreFilter === 'medium') {
      filteredResults = results.filter(r => r.cv_trend_score >= 0.4 && r.cv_trend_score < 0.7);
    } else if (scoreFilter === 'low') {
      filteredResults = results.filter(r => r.cv_trend_score < 0.4);
    }
    
    // Sort by score (highest to lowest)
    filteredResults = [...filteredResults].sort((a, b) => b.cv_trend_score - a.cv_trend_score);
    
    return filteredResults.slice(skip, skip + limit);
  };

  const getScoreBadge = (score: number) => {
    if (score >= 0.7) return 'bg-green-100 text-green-800';
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-800';
    if (score >= 0.2) return 'bg-orange-100 text-orange-800';
    return 'bg-red-100 text-red-800';
  };

  const toggleSkills = (cvId: string) => {
    setExpandedSkills(prev => ({
      ...prev,
      [cvId]: !prev[cvId]
    }));
  };

  // Check if skill needs attention (low score)
  const needsAttention = (score: number) => {
    return score < 0.1; // Skills below 10% might need attention
  };

  const columns = [
    { 
      key: 'email', 
      header: 'User Email',
      render: (item: CVTrendScore) => (
        <span className="font-medium text-gray-900">{item.email || 'No email'}</span>
      ),
    },
    {
      key: 'cv_trend_score',
      header: 'Score',
      render: (item: CVTrendScore) => {
        const percentage = item.cv_trend_score * 100;
        return (
          <div className="flex items-center gap-2">
            <span className={getScoreColor(item.cv_trend_score)}>
              {percentage.toFixed(1)}%
            </span>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreBadge(item.cv_trend_score)}`}>
              {item.cv_trend_score >= 0.7 ? 'High' : 
               item.cv_trend_score >= 0.4 ? 'Medium' : 
               item.cv_trend_score >= 0.2 ? 'Low' : 'Minimal'}
            </span>
          </div>
        );
      },
    },
  {
      key: 'skills',
      header: 'Skills',
      render: (item: CVTrendScore) => {
        const skills = item.skills_matched || [];
        const sortedSkills = [...skills].sort((a, b) => b.score - a.score);
        const isExpanded = expandedSkills[item.cv_id || ''] || false;
        const displaySkills = isExpanded ? sortedSkills : sortedSkills.slice(0, 5);
        
        return (
          <div className="max-w-lg">
            <div className="flex flex-wrap gap-1.5">
              {displaySkills.map((skillMatch, index) => (
                <div 
                  key={index}
                  className="inline-flex items-center gap-1 group relative"
                  title={`${skillMatch.skill}: ${(skillMatch.score * 100).toFixed(1)}% match`}
                >
                  <span className={`px-2 py-1 rounded text-xs transition-all duration-200 ${getSkillScoreColor(skillMatch.score)}`}>
                    {skillMatch.skill}
                  </span>
                  <span className="text-xs text-gray-500 font-medium">
                    {(skillMatch.score * 100).toFixed(0)}%
                  </span>
                  {/* Attention indicator for very low scores */}
                  {needsAttention(skillMatch.score) && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full flex items-center justify-center">
                      <span className="text-[8px] text-white font-bold">!</span>
                    </div>
                  )}
                </div>
              ))}
              {skills.length > 5 && !isExpanded && (
                <button
                  onClick={() => toggleSkills(item.cv_id || '')}
                  className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200 transition-colors border border-gray-300"
                  title={`Show all ${skills.length} skills`}
                >
                  +{skills.length - 5} more
                </button>
              )}
              {isExpanded && skills.length > 5 && (
                <button
                  onClick={() => toggleSkills(item.cv_id || '')}
                  className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200 transition-colors border border-gray-300"
                >
                  Show less
                </button>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {skills.length} skills • Avg: {(item.cv_trend_score * 100).toFixed(1)}%
            </div>
            {/* Legend for attention indicators */}
            {skills.some(s => needsAttention(s.score)) && (
              <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-[8px] text-white font-bold">!</span>
                </div>
                <span>Skills below 10% match</span>
              </div>
            )}
          </div>
        );
      },
    },
    {
      key: 'week_id',
      header: 'Week',
      render: (item: CVTrendScore) => (
        <span className="font-mono text-sm">{item.week_id}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Date',
      render: (item: CVTrendScore) => (
        <span>{new Date(item.created_at).toLocaleDateString()}</span>
      ),
    },
  ];

  // const calculateStats = () => {
  //   if (results.length === 0) return null;
    
  //   const scores = results.map(r => r.cv_trend_score);
  //   const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  //   const max = Math.max(...scores);
  //   const min = Math.min(...scores);
    
  //   // Count by score ranges
  //   const excellent = scores.filter(s => s >= 0.7).length;
  //   const good = scores.filter(s => s >= 0.4 && s < 0.7).length;
  //   const fair = scores.filter(s => s >= 0.2 && s < 0.4).length;
  //   const poor = scores.filter(s => s < 0.2).length;
    
  //   return { avg, max, min, excellent, good, fair, poor };
  // };

  //const stats = calculateStats();
  const paginatedResults = getPaginatedResults();
  const filteredTotalCount = scoreFilter ? 
    results.filter(r => {
      if (scoreFilter === 'high') return r.cv_trend_score >= 0.7;
      if (scoreFilter === 'medium') return r.cv_trend_score >= 0.4 && r.cv_trend_score < 0.7;
      if (scoreFilter === 'low') return r.cv_trend_score < 0.4;
      return true;
    }).length : totalCount;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin - CV Trend Scores</h1>
          <p className="text-gray-600 mt-1">View CV trend analysis scores with individual skill matching</p>
        </div>
        <Button 
          variant="outline" 
          onClick={loadEvaluations}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Score</label>
            <select
              value={scoreFilter}
              onChange={(e) => {
                setScoreFilter(e.target.value);
                setSkip(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All Scores</option>
              <option value="high">High (≥70%)</option>
              <option value="medium">Medium (40-70%)</option>
              <option value="low">Low (&lt;40%)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Analysis Week</label>
            <div className="flex items-center px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-gray-700">
              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
              </svg>
              {weekId || 'Loading...'}
            </div>
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
              data={paginatedResults}
              emptyMessage="No CV trend scores found"
            />
            {filteredTotalCount > limit && (
              <>
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-gray-600">
                    Showing {skip + 1} to {Math.min(skip + limit, filteredTotalCount)} of {filteredTotalCount} evaluations
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
                      disabled={skip + limit >= filteredTotalCount}
                    >
                      Next
                    </Button>
                  </div>
                </div>
                
                {/* Page number indicators - ADDED BACK */}
                <div className="mt-4 flex justify-center">
                  <div className="flex gap-1">
                    {Array.from({ length: Math.ceil(filteredTotalCount / limit) }, (_, i) => (
                      <button
                        key={i}
                        className={`px-3 py-1 rounded text-sm ${
                          skip === i * limit
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                        onClick={() => setSkip(i * limit)}
                      >
                        {i + 1}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};