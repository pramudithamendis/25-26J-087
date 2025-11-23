from typing import Dict, List
from app.config import settings
import logging
import json
import re
from openai import OpenAI

logger = logging.getLogger(__name__)

_openai_client = None

def get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for CV extraction")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def extract_from_cv_openai(preprocessed_cv: Dict) -> Dict:
    """
    Extract structured data from CV using OpenAI
    
    Uses OpenAI to intelligently parse CV text and extract structured information
    
    Args:
        preprocessed_cv: Dictionary with full_text and sections
    
    Returns:
        Dictionary with skills_raw, experience, education, github_handle
    """
    full_text = preprocessed_cv.get("full_text", "")
    
    if not full_text:
        logger.warning("No text found in CV")
        return {
            "skills_raw": [],
            "experience": [],
            "education": [],
            "github_handle": ""
        }
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, falling back to regex extraction")
        from .cv_extractor import extract_from_cv
        return extract_from_cv(preprocessed_cv)
    
    try:
        client = get_openai_client()
        if not client:
            from .cv_extractor import extract_from_cv
            return extract_from_cv(preprocessed_cv)
        
        # Truncate if too long (keep first 12000 chars for context)
        cv_text = full_text[:12000] if len(full_text) > 12000 else full_text
        
        prompt = f"""Extract structured information from this CV/resume text. Parse it carefully and extract all relevant information.

CV TEXT:
{cv_text}

Extract the following information and return ONLY valid JSON:

1. SKILLS: Extract all technical skills, programming languages, tools, frameworks, technologies mentioned. Return as a list of individual skill strings (e.g., ["Java", "Spring Boot", "AWS", "Docker"]). Include both hard skills (programming languages, frameworks) and soft skills if mentioned.

2. EXPERIENCE: Extract all work experience entries. For each entry, provide:
   - title: Job title/position
   - company: Company name
   - start: Start date in YYYY-MM format (e.g., "2024-01")
   - end: End date in YYYY-MM format or "Present" if current job
   - location: Location (city, country) if mentioned
   - highlights: List of key achievements/responsibilities (bullet points)

3. EDUCATION: Extract all education entries. For each entry, provide:
   - institution: School/University name
   - degree: Degree name (e.g., "BSc Information Technology")
   - field: Field of study/specialization if mentioned
   - start: Start date in YYYY-MM format
   - end: End date in YYYY-MM format or "Present" if ongoing
   - location: Location if mentioned

4. GITHUB_HANDLE: Extract GitHub username/handle if mentioned anywhere in the CV. Look for patterns like:
   - "github.com/username" or "github.com/username/"
   - "@username" (if context suggests GitHub)
   - "GitHub: username" or "GitHub username"
   - Any mention of GitHub profile URL
   Return the username only (without github.com/ or @), or empty string "" if not found.

Return the response in this EXACT JSON format (no markdown, no code blocks):
{{
  "skills_raw": ["skill1", "skill2", ...],
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "start": "2024-01",
      "end": "2024-12",
      "location": "City, Country",
      "highlights": ["Achievement 1", "Achievement 2"]
    }}
  ],
  "education": [
    {{
      "institution": "University Name",
      "degree": "Degree Name",
      "field": "Field of Study",
      "start": "2021-02",
      "end": "2024-11",
      "location": "City, Country"
    }}
  ],
  "github_handle": "username" or ""
}}

Important:
- Extract ALL skills mentioned anywhere in the CV
- Extract ALL work experience entries with proper dates
- Extract ALL education entries
- Extract GitHub handle if mentioned (look for github.com URLs, @ mentions, or explicit GitHub references)
- If a field is not found, use empty string "" or empty array []
- Dates should be in YYYY-MM format
- Be precise and accurate with the extraction
"""

        logger.info("Calling OpenAI for CV extraction...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at parsing CVs and resumes. Always extract accurate, structured information and return ONLY valid JSON, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistent extraction
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        # Validate and clean the result
        skills_raw = result.get("skills_raw", [])
        experience = result.get("experience", [])
        education = result.get("education", [])
        github_handle = result.get("github_handle", "").strip()
        
        # Clean GitHub handle - remove common prefixes/suffixes
        if github_handle:
            # Remove github.com/ prefix if present
            github_handle = re.sub(r'^https?://(www\.)?github\.com/', '', github_handle, flags=re.IGNORECASE)
            github_handle = re.sub(r'^github\.com/', '', github_handle, flags=re.IGNORECASE)
            # Remove @ prefix if present
            github_handle = github_handle.lstrip('@')
            # Remove trailing slash
            github_handle = github_handle.rstrip('/')
            github_handle = github_handle.strip()
        
        # Clean skills: remove empty strings, deduplicate
        skills_raw = [s.strip() for s in skills_raw if s and s.strip()]
        skills_raw = list(dict.fromkeys(skills_raw))  # Remove duplicates while preserving order
        
        # Validate experience entries
        validated_experience = []
        for exp in experience:
            if isinstance(exp, dict) and exp.get("title") and exp.get("company"):
                validated_experience.append({
                    "title": exp.get("title", ""),
                    "company": exp.get("company", ""),
                    "start": exp.get("start", ""),
                    "end": exp.get("end", ""),
                    "location": exp.get("location", ""),
                    "highlights": exp.get("highlights", []) if isinstance(exp.get("highlights"), list) else []
                })
        
        # Validate education entries - convert to string format for compatibility
        validated_education = []
        for edu in education:
            if isinstance(edu, dict) and edu.get("institution"):
                # Build education string
                parts = []
                if edu.get("degree"):
                    parts.append(edu["degree"])
                if edu.get("field"):
                    parts.append(edu["field"])
                if edu.get("institution"):
                    parts.append(edu["institution"])
                
                edu_str = ", ".join(parts)
                
                # Add dates if available
                if edu.get("start") or edu.get("end"):
                    start = edu.get("start", "")
                    end = edu.get("end", "Present")
                    edu_str += f" ({start} - {end})"
                
                validated_education.append(edu_str)
        
        logger.info(f"OpenAI extraction successful: {len(skills_raw)} skills, {len(validated_experience)} experiences, {len(validated_education)} education entries, github_handle: {github_handle or 'not found'}")
        
        return {
            "skills_raw": skills_raw,
            "experience": validated_experience,
            "education": validated_education,
            "github_handle": github_handle
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
        # Fallback to regex extraction
        from .cv_extractor import extract_from_cv
        return extract_from_cv(preprocessed_cv)
    except Exception as e:
        logger.error(f"OpenAI extraction error: {str(e)}, falling back to regex")
        # Fallback to regex extraction
        from .cv_extractor import extract_from_cv
        return extract_from_cv(preprocessed_cv)

