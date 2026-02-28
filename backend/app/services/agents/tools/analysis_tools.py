"""
Analysis tools for agents.

Tools for semantic similarity, skill normalization, and role classification.
"""

from typing import Dict, Any, List
import logging
from app.services.semantic import build_semantic_features
from app.services.normalization import normalize_skills
from app.services.role_classifier import classify_roles

logger = logging.getLogger(__name__)


def calculate_semantic_similarity_tool(
    candidate_block: str,
    jd_block: str,
    github_summary: str = ""
) -> Dict[str, Any]:
    """
    Calculate semantic similarity between candidate profile and job description.
    
    Args:
        candidate_block: Combined text from CV + LinkedIn
        jd_block: Job description text
        github_summary: Summary of GitHub activity (optional)
    
    Returns:
        Dictionary with similarity scores
    """
    try:
        logger.info("Calculating semantic similarity")
        result = build_semantic_features(candidate_block, jd_block, github_summary)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Semantic similarity calculation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "sim_profile_to_jd": 0.0,
                "sim_github_to_jd": 0.0
            }
        }


def normalize_skills_tool(skills_raw: List[str]) -> Dict[str, Any]:
    """
    Normalize skill names to canonical forms.
    
    Args:
        skills_raw: List of raw skill strings
    
    Returns:
        Dictionary with normalized skills
    """
    try:
        logger.info(f"Normalizing {len(skills_raw)} skills")
        normalized = normalize_skills(skills_raw)
        return {
            "status": "success",
            "data": {
                "skills_canonical": normalized,
                "original_count": len(skills_raw),
                "normalized_count": len(normalized)
            }
        }
    except Exception as e:
        logger.error(f"Skill normalization failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "skills_canonical": skills_raw,
                "original_count": len(skills_raw),
                "normalized_count": len(skills_raw)
            }
        }


def classify_role_tool(canonical_skills: List[str], jd_info: Dict) -> Dict[str, Any]:
    """
    Classify candidate into suitable roles based on skills and job description.
    
    Args:
        canonical_skills: Normalized skill list
        jd_info: Job description information
    
    Returns:
        Dictionary with role predictions
    """
    try:
        logger.info("Classifying roles")
        predictions = classify_roles(canonical_skills, jd_info)
        return {
            "status": "success",
            "data": {
                "role_predictions": predictions
            }
        }
    except Exception as e:
        logger.error(f"Role classification failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "role_predictions": []
            }
        }


# Tool schemas for OpenAI function calling
CALCULATE_SEMANTIC_SIMILARITY_TOOL_SCHEMA = {
    "name": "calculate_semantic_similarity",
    "description": "Calculate semantic similarity between candidate profile and job description using embeddings. Returns similarity scores.",
    "parameters": {
        "type": "object",
        "properties": {
            "candidate_block": {
                "type": "string",
                "description": "Combined text from CV and LinkedIn profile"
            },
            "jd_block": {
                "type": "string",
                "description": "Job description text"
            },
            "github_summary": {
                "type": "string",
                "description": "Summary of GitHub activity (optional)"
            }
        },
        "required": ["candidate_block", "jd_block"]
    }
}

NORMALIZE_SKILLS_TOOL_SCHEMA = {
    "name": "normalize_skills",
    "description": "Normalize skill names to canonical forms. Maps variations (e.g., 'Java EE', 'Java SE') to standard names (e.g., 'Java').",
    "parameters": {
        "type": "object",
        "properties": {
            "skills_raw": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of raw skill strings from CV/LinkedIn"
            }
        },
        "required": ["skills_raw"]
    }
}

CLASSIFY_ROLE_TOOL_SCHEMA = {
    "name": "classify_role",
    "description": "Classify candidate into suitable roles based on skills and job description. Returns role predictions with similarity scores.",
    "parameters": {
        "type": "object",
        "properties": {
            "canonical_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Normalized skill list"
            },
            "jd_info": {
                "type": "object",
                "description": "Job description information"
            }
        },
        "required": ["canonical_skills", "jd_info"]
    }
}

