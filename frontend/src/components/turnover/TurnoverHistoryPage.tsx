import apiClient from '../../config/api'; 
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, TrendingUp, TrendingDown, Minus, Search, Clock } from 'lucide-react';
import './TurnoverHistoryPage.css';
import { Button } from '../Button';

interface PredictionHistoryItem {
  _id: string;
  result_id?: string;
  cv_id: string;
  cv_name: string;
  prediction: {
    risk_level: number;
    risk_label: string;
    confidence: number;
  };
  calculated_at: string;
}

const RISK_COLORS = {
  0: '#ef4444',
  1: '#f59e0b',
  2: '#10b981'
};

const RISK_LABELS_SHORT = {
  0: 'High Early Attrition Risk',
  1: 'Moderate Early Attrition Risk',
  2: 'Low Early Attrition Risk'
};

const TurnoverHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [predictions, setPredictions] = useState<PredictionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRisk, setFilterRisk] = useState<string>('all');

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await apiClient.get('/turnover/history?limit=50');
      if (response.data.status === 'success') {
        setPredictions(response.data.predictions);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
    } finally {
      setLoading(false);
    }
  };

  const getRiskIcon = (riskLevel: number) => {
    if (riskLevel === 0) return <TrendingDown size={16} />;
    if (riskLevel === 1) return <Minus size={16} />;
    return <TrendingUp size={16} />;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    try {
      const normalized = dateStr.endsWith('Z') || dateStr.includes('+')
        ? dateStr
        : dateStr + 'Z';
      return new Date(normalized).toLocaleDateString('en-GB', {
        day: 'numeric', month: 'short', year: 'numeric',
        timeZone: 'Asia/Colombo'
      });
    } catch { return ''; }
  };

  const handleViewDetails = (item: PredictionHistoryItem) => {
    navigate(`/dashboard/admin/turnover/results?result_id=${item._id}`);
  };

  const filteredPredictions = predictions.filter(pred => {
    const matchesSearch = pred.cv_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterRisk === 'all' || pred.prediction.risk_level === parseInt(filterRisk);
    return matchesSearch && matchesFilter;
  });

  const stats = {
    total: predictions.length,
    high_risk: predictions.filter(p => p.prediction.risk_level === 0).length,
    medium_risk: predictions.filter(p => p.prediction.risk_level === 1).length,
    low_risk: predictions.filter(p => p.prediction.risk_level === 2).length
  };

  return (
    <div className="th-page">

      {/* Header */}
      <div className="th-header">
        <div>
          <h1>Early Attrition Risk History</h1>
          <p>View all candidate early attrition risk assessments</p>
        </div>
        <Button variant="primary" onClick={() => navigate('/dashboard/admin/turnover/new')}>
          New Assessment
        </Button>
      </div>

      {/* Stats */}
      <div className="th-stats-grid">
        <div className="th-stat-card">
          <div className="th-stat-label">Total Assessments</div>
          <div className="th-stat-value">{stats.total}</div>
        </div>
        <div className="th-stat-card high-risk">
          <div className="th-stat-label">High Risk</div>
          <div className="th-stat-value">{stats.high_risk}</div>
        </div>
        <div className="th-stat-card medium-risk">
          <div className="th-stat-label">Medium Risk</div>
          <div className="th-stat-value">{stats.medium_risk}</div>
        </div>
        <div className="th-stat-card low-risk">
          <div className="th-stat-label">Low Risk</div>
          <div className="th-stat-value">{stats.low_risk}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="th-table-card">
        <div className="th-filters">
          <div className="th-filter-group">
            <label>Filter by Risk</label>
            <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)}>
              <option value="all">All Risk Levels</option>
              <option value="0">High Risk</option>
              <option value="1">Medium Risk</option>
              <option value="2">Low Risk</option>
            </select>
          </div>
          <div className="th-filter-group">
            <label>Search Candidate</label>
            <div className="th-search-box">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search by name..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="th-error-banner">
            <span>{error}</span>
            <button onClick={fetchHistory}>Retry</button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="th-loading">
            <div className="th-spinner" />
            <p>Loading assessment history...</p>
          </div>
        )}

        {/* Table */}
        {!loading && filteredPredictions.length > 0 && (
          <table className="th-table">
            <thead>
              <tr>
                <th>CANDIDATE NAME</th>
                <th>RISK LEVEL</th>
                <th>DATE</th>
              </tr>
            </thead>
            <tbody>
              {filteredPredictions.map((pred, index) => (
                <tr key={index} onClick={() => handleViewDetails(pred)} className="th-row">
                  <td className="th-name-cell">
                    <div className="th-risk-dot" style={{ backgroundColor: RISK_COLORS[pred.prediction.risk_level as keyof typeof RISK_COLORS] }} />
                    {pred.cv_name}
                  </td>
                  <td>
                    <span
                      className="th-risk-badge"
                      style={{
                        color: RISK_COLORS[pred.prediction.risk_level as keyof typeof RISK_COLORS],
                        backgroundColor: `${RISK_COLORS[pred.prediction.risk_level as keyof typeof RISK_COLORS]}15`
                      }}
                    >
                      {getRiskIcon(pred.prediction.risk_level)}
                      {RISK_LABELS_SHORT[pred.prediction.risk_level as keyof typeof RISK_LABELS_SHORT]}
                    </span>
                  </td>
                  <td className="th-date-cell">
                    <Clock size={13} />
                    {formatDate(pred.calculated_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Empty */}
        {!loading && filteredPredictions.length === 0 && (
          <div className="th-empty">
            <History size={48} />
            <h3>No assessments found</h3>
            <p>{searchQuery || filterRisk !== 'all' ? 'Try adjusting your filters' : 'No assessments have been run yet'}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TurnoverHistoryPage;