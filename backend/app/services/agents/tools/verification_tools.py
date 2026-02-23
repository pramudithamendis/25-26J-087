"""
Verification tools for agents.

Tools to verify GitHub handles, check skill evidence, and detect contradictions.
"""

from typing import Dict, Any, List
import logging
from app.services.extractors.github_analyzer import analyze_github

logger = logging.getLogger(__name__)


def verify_github_handle_tool(github_handle: str) -> Dict[str, Any]:
    """
    Verify GitHub handle exists and analyze profile.
    
    Args:
        github_handle: GitHub username
    
    Returns:
        Dictionary with verification result and GitHub data
    """
    try:
        if not github_handle or not github_handle.strip():
            return {
                "status": "error",
                "verified": False,
                "error": "Empty GitHub handle",
                "data": {
                    "repos": [],
                    "commits_last_12m": 0,
                    "external_prs_merged": 0
                }
            }
        
        logger.info(f"Verifying GitHub handle: {github_handle}")
        github_data = analyze_github(github_handle.strip())
        
        # Consider verified if we got any data
        verified = len(github_data.get("repos", [])) > 0 or github_data.get("commits_last_12m", 0) > 0
        
        return {
            "status": "success",
            "verified": verified,
            "data": github_data
        }
    except Exception as e:
        logger.error(f"GitHub verification failed: {str(e)}")
        return {
            "status": "error",
            "verified": False,
            "error": str(e),
            "data": {
                "repos": [],
                "commits_last_12m": 0,
                "external_prs_merged": 0
            }
        }


def check_skill_evidence_tool(skill: str, cv_text: str) -> Dict[str, Any]:
    """
    Check if a skill is mentioned in CV text.
    
    Args:
        skill: Skill name to check
        cv_text: CV text content
    
    Returns:
        Dictionary with evidence check result
    """
    try:
        if not skill or not cv_text:
            return {
                "status": "error",
                "found": False,
                "error": "Missing skill or CV text"
            }
        
        # Case-insensitive search
        skill_lower = skill.lower()
        cv_text_lower = cv_text.lower()
        
        found = skill_lower in cv_text_lower
        
        # Find context (surrounding text)
        context = None
        if found:
            index = cv_text_lower.find(skill_lower)
            start = max(0, index - 50)
            end = min(len(cv_text), index + len(skill) + 50)
            context = cv_text[start:end].strip()
        
        return {
            "status": "success",
            "found": found,
            "skill": skill,
            "context": context
        }
    except Exception as e:
        logger.error(f"Skill evidence check failed: {str(e)}")
        return {
            "status": "error",
            "found": False,
            "error": str(e)
        }


def verify_experience_consistency_tool(cv_data: Dict, linkedin_data: Dict) -> Dict[str, Any]:
    """
    Check for consistency between CV and LinkedIn experience data.
    
    Args:
        cv_data: CV extracted data
        linkedin_data: LinkedIn extracted data
    
    Returns:
        Dictionary with consistency check results and any contradictions
    """
    try:
        cv_experience = cv_data.get("experience", [])
        linkedin_experience = linkedin_data.get("experience", [])
        
        if not cv_experience and not linkedin_experience:
            return {
                "status": "success",
                "consistent": True,
                "contradictions": [],
                "message": "No experience data to compare"
            }
        
        contradictions = []
        
        # Check for major contradictions
        # 1. Check if companies match
        cv_companies = {exp.get("company", "").lower() for exp in cv_experience if exp.get("company")}
        linkedin_companies = {exp.get("company", "").lower() for exp in linkedin_experience if exp.get("company")}
        
        if cv_companies and linkedin_companies:
            # Check if there's overlap
            overlap = cv_companies.intersection(linkedin_companies)
            if not overlap and len(cv_companies) > 0 and len(linkedin_companies) > 0:
                contradictions.append("No overlapping companies between CV and LinkedIn")
        
        # 2. Check date ranges (simplified)
        cv_dates = []
        for exp in cv_experience:
            start = exp.get("start", "")
            end = exp.get("end", "")
            if start:
                cv_dates.append((start, end))
        
        linkedin_dates = []
        for exp in linkedin_experience:
            start = exp.get("start", "")
            end = exp.get("end", "")
            if start:
                linkedin_dates.append((start, end))
        
        # If both have dates but no overlap, flag as potential contradiction
        if cv_dates and linkedin_dates:
            # Simple check: if date ranges don't overlap at all
            cv_years = set()
            for start, end in cv_dates:
                if start:
                    year = start.split("-")[0] if "-" in start else start[:4]
                    try:
                        cv_years.add(int(year))
                    except:
                        pass
            
            linkedin_years = set()
            for start, end in linkedin_dates:
                if start:
                    year = start.split("-")[0] if "-" in start else start[:4]
                    try:
                        linkedin_years.add(int(year))
                    except:
                        pass
            
            if cv_years and linkedin_years:
                overlap = cv_years.intersection(linkedin_years)
                if not overlap:
                    contradictions.append("No overlapping years between CV and LinkedIn experience")
        
        consistent = len(contradictions) == 0
        
        return {
            "status": "success",
            "consistent": consistent,
            "contradictions": contradictions,
            "cv_experience_count": len(cv_experience),
            "linkedin_experience_count": len(linkedin_experience)
        }
    except Exception as e:
        logger.error(f"Experience consistency check failed: {str(e)}")
        return {
            "status": "error",
            "consistent": False,
            "error": str(e),
            "contradictions": []
        }


# Tool schemas for OpenAI function calling
VERIFY_GITHUB_HANDLE_TOOL_SCHEMA = {
    "name": "verify_github_handle",
    "description": "Verify GitHub handle exists and analyze profile. Returns repository data, commit counts, and PR information.",
    "parameters": {
        "type": "object",
        "properties": {
            "github_handle": {
                "type": "string",
                "description": "GitHub username to verify"
            }
        },
        "required": ["github_handle"]
    }
}

CHECK_SKILL_EVIDENCE_TOOL_SCHEMA = {
    "name": "check_skill_evidence",
    "description": "Check if a skill is mentioned in CV text. Returns whether skill was found and surrounding context.",
    "parameters": {
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "Skill name to check"
            },
            "cv_text": {
                "type": "string",
                "description": "CV text content to search"
            }
        },
        "required": ["skill", "cv_text"]
    }
}

VERIFY_EXPERIENCE_CONSISTENCY_TOOL_SCHEMA = {
    "name": "verify_experience_consistency",
    "description": "Check for consistency between CV and LinkedIn experience data. Returns contradictions if any.",
    "parameters": {
        "type": "object",
        "properties": {
            "cv_data": {
                "type": "object",
                "description": "CV extracted data with experience field"
            },
            "linkedin_data": {
                "type": "object",
                "description": "LinkedIn extracted data with experience field"
            }
        },
        "required": ["cv_data", "linkedin_data"]
    }
}

