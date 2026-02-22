"""
Seniority Detection Service

Uses LLM to classify role titles into seniority levels and extract base role names.
"""

from typing import Dict, Optional
import logging
import json
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

_openai_client = None

def get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for seniority detection")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client


def detect_seniority(role_title: str) -> Dict:
    """
    Detect seniority level and extract base role name from a role title.
    
    Args:
        role_title: Job title or role name (e.g., "Senior Data Scientist", "Data Science Intern")
    
    Returns:
        Dictionary with:
        - level: int (0=intern, 1=junior, 2=mid, 3=senior, 4=executive)
        - base_role: str (role name without seniority keywords)
        - confidence: float (0.0-1.0)
    """
    if not role_title or not role_title.strip():
        logger.warning("Empty role title provided")
        return {
            "level": 2,  # Default to mid-level
            "base_role": role_title or "",
            "confidence": 0.0
        }
    
    # Check if OpenAI is available
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, using fallback seniority detection")
        return _fallback_seniority_detection(role_title)
    
    client = get_openai_client()
    if not client:
        logger.warning("OpenAI client not available, using fallback seniority detection")
        return _fallback_seniority_detection(role_title)
    
    try:
        prompt = f"""Analyze this job title and extract:
1. Seniority level (0-4):
   - 0 = intern: Intern, Trainee, Entry-level (no experience required)
   - 1 = junior: Junior, Associate, Entry-level (with some experience)
   - 2 = mid: Mid-level, Regular (no prefix), Specialist, Individual Contributor
   - 3 = senior: Senior, Lead, Principal, Staff, Tech Lead
   - 4 = executive: Director, VP, C-level, Head of, Chief

2. Base role name (remove all seniority keywords)

Job Title: "{role_title}"

Return JSON with this exact structure:
{{
  "level": 0-4,
  "base_role": "base role name without seniority",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Examples:
- "Data Science Intern" → {{"level": 0, "base_role": "Data Scientist", "confidence": 0.95}}
- "Senior Software Engineer" → {{"level": 3, "base_role": "Software Engineer", "confidence": 0.95}}
- "Software Engineer" → {{"level": 2, "base_role": "Software Engineer", "confidence": 0.9}}
- "Junior Backend Developer" → {{"level": 1, "base_role": "Backend Developer", "confidence": 0.9}}
- "VP of Engineering" → {{"level": 4, "base_role": "Engineering", "confidence": 0.95}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert at analyzing job titles and extracting seniority levels. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Validate and normalize result
        level = int(result.get("level", 2))
        level = max(0, min(4, level))  # Clamp to 0-4
        
        base_role = result.get("base_role", role_title).strip()
        if not base_role:
            base_role = role_title
        
        confidence = float(result.get("confidence", 0.8))
        confidence = max(0.0, min(1.0, confidence))
        
        logger.info(f"Seniority detected for '{role_title}': level={level}, base_role='{base_role}', confidence={confidence:.2f}")
        
        return {
            "level": level,
            "base_role": base_role,
            "confidence": confidence
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse seniority detection JSON: {str(e)}")
        return _fallback_seniority_detection(role_title)
    except Exception as e:
        logger.error(f"Error in seniority detection: {str(e)}")
        return _fallback_seniority_detection(role_title)


def _fallback_seniority_detection(role_title: str) -> Dict:
    """
    Fallback keyword-based seniority detection when LLM is unavailable.
    
    Args:
        role_title: Job title or role name
    
    Returns:
        Dictionary with level, base_role, and confidence
    """
    if not role_title:
        return {
            "level": 2,
            "base_role": "",
            "confidence": 0.0
        }
    
    title_lower = role_title.lower()
    base_role = role_title
    
    # Detect seniority keywords
    if any(keyword in title_lower for keyword in ["intern", "trainee", "entry-level"]):
        level = 0
        # Remove intern keywords
        for keyword in ["intern", "trainee", "entry-level", "entry level"]:
            base_role = base_role.replace(keyword, "").replace(keyword.title(), "").replace(keyword.upper(), "").strip()
    elif any(keyword in title_lower for keyword in ["junior", "associate", "assoc"]):
        level = 1
        for keyword in ["junior", "associate", "assoc"]:
            base_role = base_role.replace(keyword, "").replace(keyword.title(), "").replace(keyword.upper(), "").strip()
    elif any(keyword in title_lower for keyword in ["senior", "lead", "principal", "staff", "tech lead"]):
        level = 3
        for keyword in ["senior", "lead", "principal", "staff", "tech lead"]:
            base_role = base_role.replace(keyword, "").replace(keyword.title(), "").replace(keyword.upper(), "").strip()
    elif any(keyword in title_lower for keyword in ["director", "vp", "vice president", "head of", "chief", "c-level", "ceo", "cto", "cfo"]):
        level = 4
        for keyword in ["director", "vp", "vice president", "head of", "chief", "c-level", "ceo", "cto", "cfo"]:
            base_role = base_role.replace(keyword, "").replace(keyword.title(), "").replace(keyword.upper(), "").strip()
    else:
        level = 2  # Default to mid-level
    
    base_role = base_role.strip()
    if not base_role:
        base_role = role_title
    
    # Clean up extra spaces
    base_role = " ".join(base_role.split())
    
    return {
        "level": level,
        "base_role": base_role,
        "confidence": 0.6  # Lower confidence for fallback
    }





