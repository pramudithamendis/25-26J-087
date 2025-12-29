"""
Extraction tools for agents.

Wraps existing CV/LinkedIn/JD extractors to provide tool interface.
"""

from typing import Dict, Any, Optional
import logging
from app.services.preprocessing import preprocess_pdf
from app.services.extractors.cv_extractor_openai import extract_from_cv_openai
from app.services.extractors.cv_extractor import extract_from_cv
from app.services.extractors.linkedin_extractor_openai import extract_from_linkedin_openai
from app.services.extractors.linkedin_extractor import extract_from_linkedin
from app.services.extractors.jd_extractor import extract_from_jd
from app.config import settings

logger = logging.getLogger(__name__)


def extract_cv_tool(cv_file_path: str) -> Dict[str, Any]:
    """
    Extract data from CV PDF.
    
    Args:
        cv_file_path: Path to CV PDF file
    
    Returns:
        Dictionary with skills_raw, experience, education, github_handle
    """
    try:
        logger.info(f"Extracting CV from: {cv_file_path}")
        
        # Preprocess PDF
        preprocessed = preprocess_pdf(cv_file_path)
        
        # Use OpenAI extraction if configured, otherwise use regex
        if settings.CV_EXTRACTION_METHOD == "openai" and settings.OPENAI_API_KEY:
            result = extract_from_cv_openai(preprocessed)
        else:
            result = extract_from_cv(preprocessed)
        
        logger.info(f"CV extraction successful: {len(result.get('skills_raw', []))} skills found")
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"CV extraction failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "skills_raw": [],
                "experience": [],
                "education": [],
                "github_handle": ""
            }
        }


def extract_linkedin_tool(linkedin_file_path: str) -> Dict[str, Any]:
    """
    Extract data from LinkedIn PDF.
    
    Args:
        linkedin_file_path: Path to LinkedIn PDF file
    
    Returns:
        Dictionary with skills_raw, experience, education, certifications, etc.
    """
    try:
        logger.info(f"Extracting LinkedIn from: {linkedin_file_path}")
        
        # Preprocess PDF
        preprocessed = preprocess_pdf(linkedin_file_path)
        
        # Use OpenAI extraction if configured, otherwise use regex
        if settings.CV_EXTRACTION_METHOD == "openai" and settings.OPENAI_API_KEY:
            result = extract_from_linkedin_openai(preprocessed)
        else:
            result = extract_from_linkedin(preprocessed)
        
        logger.info(f"LinkedIn extraction successful: {len(result.get('skills_raw', []))} skills found")
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"LinkedIn extraction failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "skills_raw": [],
                "experience": [],
                "education": [],
                "certifications": [],
                "endorsements": []
            }
        }


def extract_jd_tool(jd_text: str, job_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract structured data from job description text.
    
    Args:
        jd_text: Job description text
        job_id: Optional job ID for caching (ensures same job always extracts same skills)
    
    Returns:
        Dictionary with title, must_have, nice_to_have, jd_text, min_years
    """
    try:
        logger.info("Extracting job description")
        result = extract_from_jd(jd_text, job_id=job_id)
        # Ensure jd_text is preserved in the result
        if "jd_text" not in result:
            result["jd_text"] = jd_text
        logger.info(f"JD extraction successful: {len(result.get('must_have', []))} must-have skills")
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"JD extraction failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "title": "",
                "must_have": [],
                "nice_to_have": [],
                "jd_text": jd_text,
                "min_years": 0
            }
        }


# Tool schemas for OpenAI function calling
EXTRACT_CV_TOOL_SCHEMA = {
    "name": "extract_cv",
    "description": "Extract structured data from CV PDF file. Returns skills, experience, education, and GitHub handle.",
    "parameters": {
        "type": "object",
        "properties": {
            "cv_file_path": {
                "type": "string",
                "description": "Path to CV PDF file"
            }
        },
        "required": ["cv_file_path"]
    }
}

EXTRACT_LINKEDIN_TOOL_SCHEMA = {
    "name": "extract_linkedin",
    "description": "Extract structured data from LinkedIn PDF file. Returns skills, experience, education, certifications, and endorsements.",
    "parameters": {
        "type": "object",
        "properties": {
            "linkedin_file_path": {
                "type": "string",
                "description": "Path to LinkedIn PDF file"
            }
        },
        "required": ["linkedin_file_path"]
    }
}

EXTRACT_JD_TOOL_SCHEMA = {
    "name": "extract_jd",
    "description": "Extract structured data from job description text. Returns title, must-have skills, nice-to-have skills, and minimum years.",
    "parameters": {
        "type": "object",
        "properties": {
            "jd_text": {
                "type": "string",
                "description": "Job description text"
            }
        },
        "required": ["jd_text"]
    }
}

