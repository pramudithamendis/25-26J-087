import apiClient from '../../config/api'; 
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, TrendingUp, TrendingDown, Minus, Search, Filter, Clock, ArrowLeft } from 'lucide-react';
import './TurnoverHistoryPage.css';
import { Button } from '../Button';

interface PredictionHistoryItem {
  _id: string;
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
  0: '#ef4444', // High Risk - Red
  1: '#f59e0b', // Medium Risk - Orange
  2: '#10b981'  // Low Risk - Green
};

const TurnoverHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [predictions, setPredictions] = useState<PredictionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRisk, setFilterRisk] = useState<number | null>(null);

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
    if (riskLevel === 0) return <TrendingDown size={20} />;
    if (riskLevel === 1) return <Minus size={20} />;
    return <TrendingUp size={20} />;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleViewDetails = (resultId: string) => {
    navigate(`/dashboard/admin/turnover/results?result_id=${resultId}`);
  };

  // Filter predictions
  const filteredPredictions = predictions.filter(pred => {
    const matchesSearch = pred.cv_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterRisk === null || pred.prediction.risk_level === filterRisk;
    return matchesSearch && matchesFilter;
  });

  // Group by risk level for statistics
  const stats = {
    total: predictions.length,
    high_risk: predictions.filter(p => p.prediction.risk_level === 0).length,
    medium_risk: predictions.filter(p => p.prediction.risk_level === 1).length,
    low_risk: predictions.filter(p => p.prediction.risk_level === 2).length
  };

  return (
    <div className="turnover-history-page">
      <div className="history-header">
        <div className="header-content">
          <History className="header-icon" style={{ color: '#2563eb' }}/>
          <div>
            <h1>Turnover Risk Assessment History</h1>
          </div>
        </div>
        <Button variant="primary" onClick={() => navigate('/dashboard/admin/turnover/new')}>
          New Turnover Risk Assessment
      </Button>
      </div>

      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Predictions</div>
          <div className="stat-value">{stats.total}</div>
        </div>
        <div className="stat-card high-risk">
          <div className="stat-label">High Risk</div>
          <div className="stat-value">{stats.high_risk}</div>
        </div>
        <div className="stat-card medium-risk">
          <div className="stat-label">Medium Risk</div>
          <div className="stat-value">{stats.medium_risk}</div>
        </div>
        <div className="stat-card low-risk">
          <div className="stat-label">Low Risk</div>
          <div className="stat-value">{stats.low_risk}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search by candidate name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-buttons">
          <button
            className={`filter-btn ${filterRisk === null ? 'active' : ''}`}
            onClick={() => setFilterRisk(null)}
          >
            All
          </button>
          <button
            className={`filter-btn high-risk ${filterRisk === 0 ? 'active' : ''}`}
            onClick={() => setFilterRisk(0)}
          >
            High Risk
          </button>
          <button
            className={`filter-btn medium-risk ${filterRisk === 1 ? 'active' : ''}`}
            onClick={() => setFilterRisk(1)}
          >
            Medium Risk
          </button>
          <button
            className={`filter-btn low-risk ${filterRisk === 2 ? 'active' : ''}`}
            onClick={() => setFilterRisk(2)}
          >
            Low Risk
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={fetchHistory}>Retry</button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading prediction history...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredPredictions.length === 0 && (
        <div className="empty-state">
          <History size={64} />
          <h3>No predictions found</h3>
          <p>
            {searchQuery || filterRisk !== null
              ? 'Try adjusting your filters'
              : 'Upload a CV and make a prediction to get started'}
          </p>
        </div>
      )}

      {/* Predictions List */}
      {!loading && filteredPredictions.length > 0 && (
        <div className="predictions-list">
          {filteredPredictions.map((pred, index) => (
            <div
              key={index}
              className="prediction-card"
              onClick={() => handleViewDetails(pred._id || pred.cv_id)}
            >
              <div className="card-left">
                <div 
                  className="risk-indicator"
                  style={{ 
                    backgroundColor: RISK_COLORS[pred.prediction.risk_level as keyof typeof RISK_COLORS] 
                  }}
                >
                  {getRiskIcon(pred.prediction.risk_level)}
                </div>
                
                <div className="card-info">
                  <h3>{pred.cv_name}</h3>
                  <div className="card-meta">
                    <Clock size={14} />
                    <span>{formatDate(pred.calculated_at)}</span>
                  </div>
                </div>
              </div>

              <div className="card-right">
                <div className="risk-badge" style={{
                  backgroundColor: `${RISK_COLORS[pred.prediction.risk_level as keyof typeof RISK_COLORS]}15`,
                  color: RISK_COLORS[pred.prediction.risk_level as keyof typeof RISK_COLORS]
                }}>
                  {pred.prediction.risk_label}
                </div>
                {/* <div className="confidence-label">
                  {(pred.prediction.confidence * 100).toFixed(0)}% confidence
                </div> */}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TurnoverHistoryPage;