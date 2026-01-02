import React from 'react';
import { Lightbulb, ArrowRight, TrendingUp, TrendingDown } from 'lucide-react';
import type { Counterfactual } from '../../types/turnover.types';
import './TurnoverCounterfactuals.css';

interface TurnoverCounterfactualsProps {
  counterfactuals: Counterfactual[];
}

const TurnoverCounterfactuals: React.FC<TurnoverCounterfactualsProps> = ({ 
  counterfactuals 
}) => {
  if (!counterfactuals || counterfactuals.length === 0) {
    return null;
  }

  return (
    <div className="turnover-counterfactuals">
      <div className="counterfactuals-header">
        <Lightbulb className="header-icon" />
        <div>
          <h3>"What-If" Scenarios</h3>
          <p>See how changes in candidate profile could affect the prediction</p>
        </div>
      </div>

      <div className="counterfactuals-list">
        {counterfactuals.map((cf, index) => (
          <div 
            key={index}
            className={`counterfactual-card ${cf.impact}`}
          >
            <div className="cf-scenario">
              <div className="cf-icon">
                {cf.impact === 'positive' ? (
                  <TrendingUp className="positive-icon" />
                ) : (
                  <TrendingDown className="negative-icon" />
                )}
              </div>
              <p className="cf-text">{cf.scenario}</p>
            </div>

            <div className="cf-transition">
              <div className="cf-risk-box original">
                <span className="risk-label">Current</span>
                <span className="risk-value">{cf.original_risk}</span>
              </div>
              
              <ArrowRight className="arrow-icon" />
              
              <div className="cf-risk-box new">
                <span className="risk-label">Predicted</span>
                <span className="risk-value">{cf.new_risk}</span>
              </div>
            </div>

            <div className="cf-details">
              <div className="cf-change">
                <span className="change-label">Confidence Change:</span>
                <span className={`change-value ${cf.confidence_change > 0 ? 'positive' : 'negative'}`}>
                  {cf.confidence_change > 0 ? '+' : ''}
                  {(cf.confidence_change * 100).toFixed(1)}%
                </span>
              </div>
              
              <div className="cf-feature-change">
                <span className="feature-label">Feature:</span>
                <span className="feature-name">{cf.feature_changed}</span>
                <div className="feature-values">
                  <span className="from-value">{cf.original_value.toFixed(2)}</span>
                  <ArrowRight size={14} />
                  <span className="to-value">{cf.new_value.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="counterfactuals-footer">
        <Lightbulb size={16} />
        <p>
          These scenarios show how specific improvements in the candidate's profile 
          could change the turnover risk prediction. Use these insights to identify 
          areas for discussion or development planning.
        </p>
      </div>
    </div>
  );
};

export default TurnoverCounterfactuals;
