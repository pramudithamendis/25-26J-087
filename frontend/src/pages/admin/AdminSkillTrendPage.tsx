import { useState, useEffect } from 'react';
import { Table } from '../../components/shared/Table';
import { Button } from '../../components/Button';
import { Alert } from '../../components/Alert';
import { Search } from 'lucide-react';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { getTopSkillsHistory, getSkillHistory } from '../../services/adminService';
import type { TopSkillTrendScoreListResponse, CVTrendScoreHistory } from '../../types/adminTypes';
import { MiniTrendChart } from '../../components/trends/MiniTrendChart';


export const AdminSkillTrendPage = () => {
  const [trendData, setTrendData] = useState<TopSkillTrendScoreListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Search and filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [scoreFilter, setScoreFilter] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit] = useState(10);
  const [totalCount, setTotalCount] = useState(0);
  
  // Searched skill data
  const [searchedSkill, setSearchedSkill] = useState<{
    skill: string;
    trend_score: number;
    forecast_score: number;
    job_count: number;
    google_interest: number;
    history: CVTrendScoreHistory[];
  } | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  
  // Skill history state (for top skills)
  const [skillHistories, setSkillHistories] = useState<Map<string, CVTrendScoreHistory[]>>(new Map());
  const [loadingHistories, setLoadingHistories] = useState<Set<string>>(new Set());
  const [selectedSkillForModal, setSelectedSkillForModal] = useState<string | null>(null);

  useEffect(() => {
    loadTrendData();
  }, []);

  const loadTrendData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getTopSkillsHistory(10, 16);
      setTrendData(response);
      setTotalCount(response.top_skills.length);
      
      // Use history data from getTopSkillsHistory response
      const historyMap = new Map<string, CVTrendScoreHistory[]>();
      response.history.forEach(record => {
        if (!historyMap.has(record.skill)) {
          historyMap.set(record.skill, []);
        }
        historyMap.get(record.skill)!.push(record);
      });
      setSkillHistories(historyMap);
      
    } catch (err: any) {
      setError(err.detail || 'Failed to load trend data');
    } finally {
      setLoading(false);
    }
  };

  // Search for any skill using the /skill/{skill_name} endpoint
  const searchForSkill = async (skillName: string) => {
    setIsSearching(true);
    setSearchError(null);
    setSearchedSkill(null);
    
    try {
      const response = await getSkillHistory(skillName, 16);
      if (response.success && response.history && response.history.length > 0) {
        // Get the latest history record for current data
        const sortedHistory = [...response.history].sort((a, b) =>
          a.week_id.localeCompare(b.week_id)
        );

        const latestHistory = sortedHistory[sortedHistory.length - 1];
        setSearchedSkill({
          skill: skillName,
          trend_score: latestHistory.trend_score,
          forecast_score: latestHistory.forecast_score,
          job_count: latestHistory.job_count,
          google_interest: latestHistory.google_interest,
          history: sortedHistory
        });
        
        // Also add to skillHistories for modal view
        setSkillHistories(prev => new Map(prev).set(skillName, sortedHistory));
      } else {
        setSearchError(`Skill "${skillName}" not found`);
        setSearchedSkill(null);
      }
    } catch (err: any) {
      console.error('Failed to search skill:', err);
      setSearchError(err.detail || `Skill "${skillName}" not found`);
      setSearchedSkill(null);
    } finally {
      setIsSearching(false);
    }
  };

  // Search when search term changes (debounced)
  useEffect(() => {
    const debounceTimeout = setTimeout(() => {
      if (searchTerm.trim() && searchTerm.length >= 2) {
        searchForSkill(searchTerm.trim());
      } else if (searchTerm.length === 0) {
        setSearchedSkill(null);
        setSearchError(null);
      }
    }, 500);
    
    return () => clearTimeout(debounceTimeout);
  }, [searchTerm]);

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-green-600 font-semibold';      
    if (score >= 0.4) return 'text-yellow-600 font-semibold';     
    if (score >= 0.2) return 'text-orange-600 font-semibold';    
    return 'text-red-600 font-semibold';
  };

  // Determine which data to display (searched skill or top skills)
  const getDisplayData = () => {
    if (searchTerm.trim() && searchTerm.length >= 2) {
      // Show searched skill if found
      if (searchedSkill) {
        // Apply score filter to searched skill
        if (scoreFilter === 'high' && searchedSkill.trend_score < 0.7) return [];
        if (scoreFilter === 'medium' && (searchedSkill.trend_score < 0.4 || searchedSkill.trend_score >= 0.7)) return [];
        if (scoreFilter === 'low' && searchedSkill.trend_score >= 0.4) return [];
        return [searchedSkill];
      }
      return [];
    } else if (trendData) {
      // Show top skills
      let filtered = [...trendData.top_skills];
      
      if (scoreFilter === 'high') {
        filtered = filtered.filter(s => s.trend_score >= 0.7);
      } else if (scoreFilter === 'medium') {
        filtered = filtered.filter(s => s.trend_score >= 0.4 && s.trend_score < 0.7);
      } else if (scoreFilter === 'low') {
        filtered = filtered.filter(s => s.trend_score < 0.4);
      }
      
      filtered.sort((a, b) => b.trend_score - a.trend_score);
      return filtered.slice(skip, skip + limit);
    }
    return [];
  };

  const getTotalCount = () => {
    if (searchTerm.trim() && searchTerm.length >= 2) {
      if (!searchedSkill) return 0;
      if (scoreFilter === 'high' && searchedSkill.trend_score < 0.7) return 0;
      if (scoreFilter === 'medium' && (searchedSkill.trend_score < 0.4 || searchedSkill.trend_score >= 0.7)) return 0;
      if (scoreFilter === 'low' && searchedSkill.trend_score >= 0.4) return 0;
      return 1;
    } else if (trendData) {
      let filtered = [...trendData.top_skills];
      if (scoreFilter === 'high') {
        filtered = filtered.filter(s => s.trend_score >= 0.7);
      } else if (scoreFilter === 'medium') {
        filtered = filtered.filter(s => s.trend_score >= 0.4 && s.trend_score < 0.7);
      } else if (scoreFilter === 'low') {
        filtered = filtered.filter(s => s.trend_score < 0.4);
      }
      return filtered.length;
    }
    return 0;
  };

  // Full history modal with Google Trends style chart
  const FullHistoryModal = ({ skillName, onClose }: { skillName: string; onClose: () => void }) => {
    const history = skillHistories.get(skillName);
    
    if (!history) return null;
    
    const sortedHistory = [...history].sort((a, b) => a.week_id.localeCompare(b.week_id));
    const width = 600;
    const height = 300;
    
    const values = sortedHistory.map(d => d.trend_score);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue || 1;
    
    const xStep = values.length > 1 ? width / (values.length - 1) : width;
    const points = values.map((value, index) => {
      const x = index * xStep;
      const normalizedValue = (value - minValue) / range;
      const y = height - (normalizedValue * (height * 0.85) + height * 0.075);
      return `${x},${y}`;
    }).join(' ');
    
    const areaPoints = points + ` ${width},${height} 0,${height}`;
    
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
        <div className="bg-white rounded-lg p-8 max-w-4xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-2xl font-bold text-gray-900">{skillName}</h3>
              <p className="text-sm text-gray-500 mt-1">Interest over time</p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="relative">
            <svg width={width} height={height} className="mx-auto">
              <polygon points={areaPoints} fill="url(#gradient)" opacity="0.1" />
              <defs>
                <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                </linearGradient>
              </defs>
              <polyline points={points} fill="none" stroke="#3b82f6" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            
            <div className="flex justify-between mt-2 text-xs text-gray-500">
              {sortedHistory.map((record, index) => (
                <div key={index} className="text-center" style={{ width: `${xStep}px` }}>
                  W{record.week_id}
                </div>
              ))}
            </div>
          </div>
          
          <div className="mt-8 grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-sm text-gray-500">Peak</div>
              <div className="text-xl font-bold text-green-600">
                {(Math.max(...values) * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500">Average</div>
              <div className="text-xl font-bold text-blue-600">
                {(values.reduce((a, b) => a + b, 0) / values.length * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500">Latest</div>
              <div className="text-xl font-bold text-purple-600">
                {(values[values.length - 1] * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500">Change</div>
              <div className={`text-xl font-bold ${values[values.length - 1] > values[0] ? 'text-green-600' : 'text-red-600'}`}>
                {((values[values.length - 1] - values[0]) * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const columns = [
    { 
      key: 'skill', 
      header: 'Skill Name',
      render: (item: any) => (
        <span className="font-medium text-gray-900">{item.skill}</span>
      ),
    },
    {
      key: 'trend_score',
      header: 'Trend Score',
      render: (item: any) => {
        const percentage = item.trend_score * 100;
        return (
          <div className="flex items-center gap-2">
            <span className={getScoreColor(item.trend_score)}>
              {percentage.toFixed(1)}%
            </span>
          </div>
        );
      },
    },
    {
      key: 'forecast_score',
      header: 'Forecast',
      render: (item: any) => (
        <span className="text-blue-600 font-medium">
          {(item.forecast_score * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      key: 'history',
      header: 'Trend',
      render: (item: any) => {
        // For searched skill, use its history directly
        let history = skillHistories.get(item.skill);
        const isLoading = loadingHistories.has(item.skill);
        
        if (isLoading) {
          return <LoadingSpinner size="sm" />;
        }
        
        if (!history) {
          return <span className="text-gray-400 text-xs">No data</span>;
        }
        
        return (
          <MiniTrendChart 
            history={history} 
            onClick={() => setSelectedSkillForModal(item.skill)}
          />
        );
      },
    },
  ];

  const displayData = getDisplayData();
  const displayTotalCount = getTotalCount();

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin - Skill Trends</h1>
          <p className="text-gray-600 mt-1">
            Search any skill or browse top trending skills with historical trend analysis
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={loadTrendData}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
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

      {/* Info Banner */}
      {trendData && !searchTerm && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-800">
                <strong>Analysis Week:</strong> {trendData.week_id}
              </p>
              <p className="text-xs text-blue-600 mt-1">
                Showing top {trendData.top_skills.length} skills. Use search to find any skill in the database.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Search Result Banner */}
      {searchTerm && searchTerm.length >= 2 && searchedSkill && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-800">
                <strong>Search Result:</strong> Showing data for "{searchTerm}"
              </p>
              <p className="text-xs text-purple-600 mt-1">
                Click on the trend line to view full historical data
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setSearchTerm('');
                setSearchedSkill(null);
                setSearchError(null);
                setSkip(0);
              }}
            >
              Clear Search
            </Button>
          </div>
        </div>
      )}

      {/* Search Error Banner */}
      {searchError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-red-800">
                <strong>Not Found:</strong> {searchError}
              </p>
              <p className="text-xs text-red-600 mt-1">
                Try checking the spelling or search for a different skill
              </p>
            </div>
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                setSearchTerm('');
                setSearchError(null);
              }}
            >
              Clear
            </Button>
          </div>
        </div>
      )}

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        
        {/* Filters Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Search Bar */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Search Any Skill</label>
          <div className="relative">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setSkip(0);
              }}
              placeholder="Search by skill name (e.g., Python, React, AWS)..."
              className="w-full px-3 py-2 pl-10 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          </div>
          <p className="text-xs text-gray-600 mt-1">Type at least 2 characters to search</p>
        </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Trend Score</label>
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
          
        </div>
      </div>

      {/* Skills Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        {loading || (isSearching && searchTerm.length >= 2) ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={displayData}
              emptyMessage={
                searchTerm ? 
                  `No skill found matching "${searchTerm}"` : 
                  "No skills found matching your filters"
              }
            />
            
            {/* Pagination - only for top skills, not for search results */}
            {!searchTerm && displayTotalCount > limit && (
              <div className="px-6 py-4 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-600">
                    Showing {skip + 1} to {Math.min(skip + limit, displayTotalCount)} of {displayTotalCount} skills
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
                      disabled={skip + limit >= displayTotalCount}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal for full history */}
      {selectedSkillForModal && (
        <FullHistoryModal 
          skillName={selectedSkillForModal}
          onClose={() => setSelectedSkillForModal(null)}
        />
      )}
    </div>
  );
};