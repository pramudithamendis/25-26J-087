"""
Extraction Agent for CV evaluation.

Extracts information from CV/LinkedIn/GitHub, decides what to extract based on
job requirements, and validates extracted data quality.
"""

from typing import Dict, List, Optional
import logging
from .base_agent import BaseAgent
from .state import EvaluationState
from .tools.extraction_tools import (
    extract_cv_tool,
    extract_linkedin_tool,
    extract_jd_tool,
    EXTRACT_CV_TOOL_SCHEMA,
    EXTRACT_LINKEDIN_TOOL_SCHEMA,
    EXTRACT_JD_TOOL_SCHEMA
)

logger = logging.getLogger(__name__)


class ExtractionAgent(BaseAgent):
    """
    Extraction agent that extracts data from CV/LinkedIn/GitHub.
    
    Decides what to extract based on job requirements, validates extracted data,
    and requests additional info if needed.
    """
    
    def __init__(self):
        """Initialize extraction agent"""
        system_prompt = """You are an extraction agent for CV evaluation system. Your role is to:
1. Extract structured data from CV, LinkedIn, and GitHub profiles
2. Prioritize extraction based on job requirements
3. Validate extracted data quality
4. Request additional information if needed

Always extract:
- Skills (technical and soft skills)
- Experience (title, company, dates, highlights)
- Education (degree, institution, dates)
- GitHub handle (if mentioned)

For LinkedIn, also extract:
- Certifications
- Endorsements
- Publications
- Projects

Always respond with structured data in JSON format."""
        
        tools = [
            {
                "type": "function",
                "function": EXTRACT_CV_TOOL_SCHEMA
            },
            {
                "type": "function",
                "function": EXTRACT_LINKEDIN_TOOL_SCHEMA
            },
            {
                "type": "function",
                "function": EXTRACT_JD_TOOL_SCHEMA
            }
        ]
        
        super().__init__(
            name="ExtractionAgent",
            system_prompt=system_prompt,
            temperature=0.1,  # Very low temperature for consistent extraction
            tools=tools
        )
        
        # Register tool functions
        self.register_tool("extract_cv", extract_cv_tool, EXTRACT_CV_TOOL_SCHEMA)
        self.register_tool("extract_linkedin", extract_linkedin_tool, EXTRACT_LINKEDIN_TOOL_SCHEMA)
        self.register_tool("extract_jd", extract_jd_tool, EXTRACT_JD_TOOL_SCHEMA)
    
    def extract_candidate_data(
        self,
        cv_path: Optional[str] = None,
        linkedin_path: Optional[str] = None,
        github_handle: Optional[str] = None
    ) -> Dict:
        """
        Extract candidate data from available sources.
        
        Args:
            cv_path: Path to CV PDF
            linkedin_path: Path to LinkedIn PDF
            github_handle: GitHub username
        
        Returns:
            Dictionary with extracted data
        """
        result = {
            "cv_data": None,
            "linkedin_data": None,
            "github_handle": github_handle
        }
        
        # Extract CV if available
        if cv_path:
            try:
                cv_result = extract_cv_tool(cv_path)
                if cv_result.get("status") == "success":
                    result["cv_data"] = cv_result["data"]
                    # Extract GitHub handle from CV if not provided
                    if not github_handle:
                        result["github_handle"] = result["cv_data"].get("github_handle", "")
            except Exception as e:
                logger.error(f"CV extraction failed: {str(e)}")
        
        # Extract LinkedIn if available
        if linkedin_path:
            try:
                linkedin_result = extract_linkedin_tool(linkedin_path)
                if linkedin_result.get("status") == "success":
                    result["linkedin_data"] = linkedin_result["data"]
            except Exception as e:
                logger.error(f"LinkedIn extraction failed: {str(e)}")
        
        return result
    
    def prioritize_extraction(self, job_requirements: Dict) -> List[str]:
        """
        Decide extraction order based on job requirements.
        
        Args:
            job_requirements: Job description with must_have, nice_to_have
        
        Returns:
            Ordered list of extraction priorities
        """
        priorities = []
        
        # Always extract CV first (most important)
        priorities.append("cv")
        
        # If job requires GitHub skills, prioritize GitHub
        must_have = job_requirements.get("must_have", [])
        nice_to_have = job_requirements.get("nice_to_have", [])
        all_skills = must_have + nice_to_have
        
        github_keywords = ["github", "git", "version control", "open source"]
        if any(keyword in " ".join(all_skills).lower() for keyword in github_keywords):
            priorities.append("github")
        
        # LinkedIn is nice to have
        priorities.append("linkedin")
        
        return priorities
    
    def validate_extraction(self, data: Dict) -> bool:
        """
        Validate extracted data quality.
        
        Args:
            data: Extracted data
        
        Returns:
            True if data is valid
        """
        if not data:
            return False
        
        # Check if we have at least some data
        has_skills = len(data.get("skills_raw", [])) > 0
        has_experience = len(data.get("experience", [])) > 0
        has_education = len(data.get("education", [])) > 0
        
        # At least one of these should be present
        return has_skills or has_experience or has_education
    
    def execute(self, state: Dict) -> Dict:
        """
        Execute extraction agent.
        
        Args:
            state: Current evaluation state or extraction request
        
        Returns:
            Extracted data
        """
        if isinstance(state, EvaluationState):
            # Extract from state
            candidate_data = state.candidate_data or {}
            job_data = state.job_data or {}
            
            cv_path = candidate_data.get("cv_file_path")
            linkedin_path = candidate_data.get("linkedin_file_path")
            github_handle = candidate_data.get("github_handle", "")
            
            # Extract candidate data
            extracted = self.extract_candidate_data(cv_path, linkedin_path, github_handle)
            
            # Extract JD if needed
            jd_data = None
            if job_data.get("jd_text") and not state.is_extracted("jd"):
                jd_result = extract_jd_tool(job_data["jd_text"])
                if jd_result.get("status") == "success":
                    jd_data = jd_result["data"]
            
            return {
                "cv_data": extracted.get("cv_data"),
                "linkedin_data": extracted.get("linkedin_data"),
                "github_handle": extracted.get("github_handle"),
                "jd_data": jd_data
            }
        else:
            # Direct extraction request
            cv_path = state.get("cv_path")
            linkedin_path = state.get("linkedin_path")
            github_handle = state.get("github_handle")
            jd_text = state.get("jd_text")
            
            result = self.extract_candidate_data(cv_path, linkedin_path, github_handle)
            
            if jd_text:
                jd_result = extract_jd_tool(jd_text)
                if jd_result.get("status") == "success":
                    result["jd_data"] = jd_result["data"]
            
            return result

