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
          <p>See how changes in candidate profile could affect the assessment</p>
          
        <p>
          These scenarios show how specific improvements in the candidate's profile 
          could change the early attrition risk.
        </p>
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

          </div>
        ))}
      </div>
    </div>
  );
};

export default TurnoverCounterfactuals;
