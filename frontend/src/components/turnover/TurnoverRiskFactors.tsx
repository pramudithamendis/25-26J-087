import React from 'react';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { RiskFactor } from '../../types/turnover.types';
import './TurnoverRiskFactors.css';

interface TurnoverRiskFactorsProps {
  riskFactors: RiskFactor[];
}

const IMPACT_ORDER = { critical: 4, high: 3, medium: 2, low: 1 };

const TurnoverRiskFactors: React.FC<TurnoverRiskFactorsProps> = ({ riskFactors }) => {
  const getImpactIcon = (impact: string) => {
    if (impact === 'critical' || impact === 'high') return <AlertTriangle size={18} />;
    if (impact === 'medium') return <AlertCircle size={18} />;
    return <Info size={18} />;
  };

  const getImpactLabel = (impact: string) => {
    return impact.charAt(0).toUpperCase() + impact.slice(1) + ' Impact';
  };

  if (!riskFactors || riskFactors.length === 0) {
    return (
      <div className="turnover-risk-factors empty">
        <div className="empty-state">
          <Info size={48} />
          <h3>No Significant Risk Factors</h3>
          <p>This candidate shows a stable career profile with no major red flags.</p>
        </div>
      </div>
    );
  }

  const sortedFactors = [...riskFactors].sort(
    (a, b) =>
      (IMPACT_ORDER[b.impact as keyof typeof IMPACT_ORDER] || 0) -
      (IMPACT_ORDER[a.impact as keyof typeof IMPACT_ORDER] || 0)
  );

  return (
    <div className="turnover-risk-factors">
      <div className="factors-header">
        <AlertTriangle className="header-icon" />
        <div>
          <h3>Key Influencing Factors</h3>
          <p>Top indicators that may influence turnover likelihood</p>
        </div>
      </div>

      <div className="factors-list">
        {sortedFactors.map((factor, index) => (
          <div
            key={index}
            className={`factor-card impact-${factor.impact}`}
          >
            <div className="factor-header">
              <div className={`factor-icon factor-icon-${factor.impact}`}>
                {getImpactIcon(factor.impact)}
              </div>
              <div className="factor-title">
                <h4>{factor.factor}</h4>
                <span className={`impact-badge impact-badge-${factor.impact}`}>
                  {getImpactLabel(factor.impact)}
                </span>
              </div>
            </div>

            {factor.description && (
              <div className="factor-content">
                <p className="factor-description">{factor.description}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="factors-footer">
        <Info size={16} />
        <p>
          These factors are identified based on historical attrition patterns.
          Consider discussing these areas during the interview process.
        </p>
      </div>
    </div>
  );
};

export default TurnoverRiskFactors;