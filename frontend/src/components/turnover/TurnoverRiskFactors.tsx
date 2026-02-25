import React from 'react';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { RiskFactor } from '../../types/turnover.types';
import { IMPACT_COLORS } from '../../utils/turnover-constants';
import './TurnoverRiskFactors.css';

interface TurnoverRiskFactorsProps {
  riskFactors: RiskFactor[];
}

const TurnoverRiskFactors: React.FC<TurnoverRiskFactorsProps> = ({ riskFactors }) => {
  const getImpactIcon = (impact: string) => {
    if (impact === 'high') return <AlertTriangle size={20} />;
    if (impact === 'medium') return <AlertCircle size={20} />;
    return <Info size={20} />;
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

  return (
    <div className="turnover-risk-factors">
      <div className="factors-header">
        <AlertTriangle className="header-icon" />
        <div>
          <h3>Top Risk Factors</h3>
          <p>Key indicators that may influence turnover likelihood</p>
        </div>
      </div>

      <div className="factors-list">
        {riskFactors.map((factor, index) => (
          <div 
            key={index} 
            className="factor-card"
            style={{ borderLeftColor: IMPACT_COLORS[factor.impact] }}
          >
            <div className="factor-header">
              <div className="factor-icon" style={{ color: IMPACT_COLORS[factor.impact] }}>
                {getImpactIcon(factor.impact)}
              </div>
              <div className="factor-title">
                <h4>{factor.factor}</h4>
                <span 
                  className="impact-badge"
                  style={{ 
                    backgroundColor: `${IMPACT_COLORS[factor.impact]}20`,
                    color: IMPACT_COLORS[factor.impact]
                  }}
                >
                  {getImpactLabel(factor.impact)}
                </span>
              </div>
            </div>
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
