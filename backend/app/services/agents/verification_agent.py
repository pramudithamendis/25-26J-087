"""
Verification Agent for CV evaluation.

Verifies GitHub handles, checks skill evidence, and detects contradictions
between CV and LinkedIn data.
"""

from typing import Dict, List, Optional
import logging
from .base_agent import BaseAgent
from .state import EvaluationState
from .tools.verification_tools import (
    verify_github_handle_tool,
    check_skill_evidence_tool,
    verify_experience_consistency_tool,
    VERIFY_GITHUB_HANDLE_TOOL_SCHEMA,
    CHECK_SKILL_EVIDENCE_TOOL_SCHEMA,
    VERIFY_EXPERIENCE_CONSISTENCY_TOOL_SCHEMA
)

logger = logging.getLogger(__name__)


class VerificationAgent(BaseAgent):
    """
    Verification agent that verifies claims and checks consistency.
    
    Verifies GitHub handles, checks if skills are mentioned in CV text,
    and detects contradictions between CV and LinkedIn.
    """
    
    def __init__(self):
        """Initialize verification agent"""
        system_prompt = """You are a verification agent for CV evaluation system. Your role is to:
1. Verify GitHub handles exist and are valid
2. Check if skills mentioned in CV actually appear in the text
3. Validate experience dates consistency
4. Flag contradictions between CV and LinkedIn data

Always be thorough and check evidence carefully. Report any inconsistencies found."""
        
        tools = [
            {
                "type": "function",
                "function": VERIFY_GITHUB_HANDLE_TOOL_SCHEMA
            },
            {
                "type": "function",
                "function": CHECK_SKILL_EVIDENCE_TOOL_SCHEMA
            },
            {
                "type": "function",
                "function": VERIFY_EXPERIENCE_CONSISTENCY_TOOL_SCHEMA
            }
        ]
        
        super().__init__(
            name="VerificationAgent",
            system_prompt=system_prompt,
            temperature=0.2,
            tools=tools
        )
        
        # Register tool functions
        self.register_tool("verify_github_handle", verify_github_handle_tool, VERIFY_GITHUB_HANDLE_TOOL_SCHEMA)
        self.register_tool("check_skill_evidence", check_skill_evidence_tool, CHECK_SKILL_EVIDENCE_TOOL_SCHEMA)
        self.register_tool("verify_experience_consistency", verify_experience_consistency_tool, VERIFY_EXPERIENCE_CONSISTENCY_TOOL_SCHEMA)
    
    def verify_github_profile(self, handle: str) -> Dict:
        """
        Verify GitHub handle exists and is valid.
        
        Args:
            handle: GitHub username
        
        Returns:
            Verification result with GitHub data
        """
        if not handle or not handle.strip():
            return {
                "verified": False,
                "error": "Empty GitHub handle",
                "data": None
            }
        
        try:
            result = verify_github_handle_tool(handle.strip())
            return {
                "verified": result.get("verified", False),
                "data": result.get("data"),
                "error": result.get("error")
            }
        except Exception as e:
            logger.error(f"GitHub verification failed: {str(e)}")
            return {
                "verified": False,
                "error": str(e),
                "data": None
            }
    
    def verify_skill_evidence(self, skill: str, cv_text: str) -> bool:
        """
        Check if skill is mentioned in CV text.
        
        Args:
            skill: Skill name
            cv_text: CV text content
        
        Returns:
            True if skill found in CV
        """
        if not skill or not cv_text:
            return False
        
        try:
            result = check_skill_evidence_tool(skill, cv_text)
            return result.get("found", False)
        except Exception as e:
            logger.error(f"Skill evidence check failed: {str(e)}")
            return False
    
    def check_consistency(self, cv_data: Dict, linkedin_data: Dict) -> List[str]:
        """
        Check for consistency between CV and LinkedIn data.
        
        Args:
            cv_data: CV extracted data
            linkedin_data: LinkedIn extracted data
        
        Returns:
            List of inconsistencies found
        """
        if not cv_data and not linkedin_data:
            return []
        
        try:
            result = verify_experience_consistency_tool(cv_data, linkedin_data)
            return result.get("contradictions", [])
        except Exception as e:
            logger.error(f"Consistency check failed: {str(e)}")
            return []
    
    def execute(self, state: Dict) -> Dict:
        """
        Execute verification agent.
        
        Args:
            state: Current evaluation state or verification request
        
        Returns:
            Verification results
        """
        result = {
            "github_verified": False,
            "skill_evidence_verified": False,
            "consistency_verified": False,
            "contradictions": [],
            "github_data": None
        }
        
        if isinstance(state, EvaluationState):
            # Verify GitHub if handle exists
            github_handle = None
            if state.cv_data:
                github_handle = state.cv_data.get("github_handle", "")
            if not github_handle and state.candidate_data:
                github_handle = state.candidate_data.get("github_handle", "")
            
            if github_handle:
                github_result = self.verify_github_profile(github_handle)
                result["github_verified"] = github_result.get("verified", False)
                result["github_data"] = github_result.get("data")
            
            # Check consistency if both CV and LinkedIn exist
            if state.cv_data and state.linkedin_data:
                contradictions = self.check_consistency(state.cv_data, state.linkedin_data)
                result["contradictions"] = contradictions
                result["consistency_verified"] = len(contradictions) == 0
        else:
            # Direct verification request
            github_handle = state.get("github_handle")
            if github_handle:
                github_result = self.verify_github_profile(github_handle)
                result["github_verified"] = github_result.get("verified", False)
                result["github_data"] = github_result.get("data")
            
            cv_data = state.get("cv_data")
            linkedin_data = state.get("linkedin_data")
            if cv_data and linkedin_data:
                contradictions = self.check_consistency(cv_data, linkedin_data)
                result["contradictions"] = contradictions
                result["consistency_verified"] = len(contradictions) == 0
            
            # Check skill evidence if requested
            skill = state.get("skill")
            cv_text = state.get("cv_text")
            if skill and cv_text:
                result["skill_evidence_verified"] = self.verify_skill_evidence(skill, cv_text)
        
        return result

