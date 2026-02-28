"""
Unit tests for PlanningAgent.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.agents.planning_agent import PlanningAgent
from app.services.agents.state import EvaluationState, EvaluationStage


class TestPlanningAgent:
    """Test cases for PlanningAgent"""
    
    def test_planning_agent_initialization(self):
        """Test planning agent initialization"""
        agent = PlanningAgent()
        assert agent.name == "PlanningAgent"
        assert agent.temperature == 0.2
    
    def test_get_default_action_extract_cv(self):
        """Test default action when CV not extracted"""
        agent = PlanningAgent()
        state = EvaluationState("cand1", "job1")
        state.candidate_data = {"cv_file_path": "/path/to/cv.pdf"}
        
        action = agent._get_default_action(state)
        assert action["action"] == "extract_cv"
        assert action["agent"] == "extraction"
    
    def test_get_default_action_extract_jd(self):
        """Test default action when JD not extracted"""
        agent = PlanningAgent()
        state = EvaluationState("cand1", "job1")
        state.candidate_data = {}
        state.job_data = {"jd_text": "Job description"}
        state.mark_extracted("cv", {})
        
        action = agent._get_default_action(state)
        assert action["action"] == "extract_jd"
    
    def test_get_default_action_complete(self):
        """Test default action when evaluation complete"""
        agent = PlanningAgent()
        state = EvaluationState("cand1", "job1")
        state.mark_extracted("cv", {})
        state.mark_extracted("jd", {})
        state.semantic_features = {}
        state.judge_scores = []
        state.critic_scores = []
        state.aggregated_score = {"total_score": 75}
        
        action = agent._get_default_action(state)
        assert action["action"] == "complete"
    
    def test_select_agent(self):
        """Test agent selection"""
        agent = PlanningAgent()
        assert agent.select_agent("extract CV") == "extraction"
        assert agent.select_agent("verify GitHub") == "verification"
        assert agent.select_agent("score candidate") == "judge"
        assert agent.select_agent("review scores") == "critic"
        assert agent.select_agent("aggregate scores") == "aggregator"
    
    def test_should_continue(self):
        """Test should continue logic"""
        agent = PlanningAgent()
        state = EvaluationState("cand1", "job1")
        
        # Should continue if not complete
        assert agent.should_continue(state) == True
        
        # Should not continue if complete
        state.set_stage(EvaluationStage.COMPLETED)
        assert agent.should_continue(state) == False
        
        # Should not continue if too many errors
        state.set_stage(EvaluationStage.INITIALIZED)
        state.add_error("Error 1")
        state.add_error("Error 2")
        state.add_error("Error 3")
        state.add_error("Error 4")
        assert agent.should_continue(state) == False
    
    def test_handle_failure(self):
        """Test failure handling"""
        agent = PlanningAgent()
        state = EvaluationState("cand1", "job1")
        
        # API error - should retry
        error = Exception("OpenAI API error")
        recovery = agent.handle_failure(error, state)
        assert recovery["action"] == "retry"
        
        # Extraction error - should try fallback
        error = Exception("Extraction failed")
        recovery = agent.handle_failure(error, state)
        assert recovery["action"] == "extract_fallback"
        
        # Unknown error - should skip
        error = Exception("Unknown error")
        recovery = agent.handle_failure(error, state)
        assert recovery["action"] == "skip"

