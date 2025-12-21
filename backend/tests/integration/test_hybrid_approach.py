"""
Integration tests for hybrid approach (agentic + rule-based).
"""

import pytest
from unittest.mock import Mock, patch
from app.services.agents.aggregator_agent import AggregatorAgent


class TestHybridApproach:
    """Test cases for hybrid aggregation"""
    
    def test_hybrid_aggregation(self):
        """Test hybrid aggregation combines rule-based and agentic"""
        agent = AggregatorAgent()
        
        semantic_features = {"sim_profile_to_jd": 0.8}
        judge_scores = {
            "judge_scores": [
                {"criterion": "APIs", "score": 4},
                {"criterion": "Databases", "score": 3}
            ]
        }
        github_info = {"commits_last_12m": 50}
        experience_info = []
        merged_json = {"candidate": {}, "job_description": {}}
        
        with patch('app.services.agents.aggregator_agent.aggregate_scores') as mock_aggregate:
            mock_aggregate.return_value = {
                "total_score": 70,
                "breakdown": {"semantic_fit": 25, "role_competency": 30}
            }
            
            with patch.object(agent, '_agentic_adjustment') as mock_adjustment:
                mock_adjustment.return_value = {
                    "total_score": 75,
                    "breakdown": {"semantic_fit": 25, "role_competency": 30},
                    "reasoning": "Test"
                }
                
                result = agent.aggregate_hybrid(
                    semantic_features,
                    judge_scores,
                    github_info,
                    experience_info,
                    merged_json
                )
                
                # Should combine: 0.3 * 70 + 0.7 * 75 = 21 + 52.5 = 73.5
                assert result["total_score"] == 74  # Rounded
                assert result["baseline_score"] == 70
                assert result["agentic_score"] == 75

