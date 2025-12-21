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
            logger.info("OpenAI client initialized for JD extraction")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def extract_from_jd_openai(jd_text: str) -> Dict:
    """
    Extract structured data from job description using OpenAI
    
    Uses OpenAI to intelligently parse JD text and extract structured information
    without relying on hardcoded keyword lists.
    
    Args:
        jd_text: Full job description text
    
    Returns:
        Dictionary with title, must_have, nice_to_have, min_years, jd_text
    """
    if not jd_text or not jd_text.strip():
        logger.warning("No text found in JD")
        return {
            "title": "",
            "must_have": [],
            "nice_to_have": [],
            "min_years": 0,
            "jd_text": jd_text
        }
    
    # Fix common data issues
    jd_text = jd_text.strip()
    # Fix "ob Description" -> "Job Description"
    if jd_text.startswith("ob Description"):
        jd_text = "Job Description" + jd_text[14:]
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, falling back to regex extraction")
        from .jd_extractor import extract_from_jd
        return extract_from_jd(jd_text)
    
    try:
        client = get_openai_client()
        if not client:
            from .jd_extractor import extract_from_jd
            return extract_from_jd(jd_text)
        
        # Truncate if too long (keep first 12000 chars for context)
        jd_text_truncated = jd_text[:12000] if len(jd_text) > 12000 else jd_text
        
        prompt = f"""Extract structured information from this job description. Parse it carefully and extract all relevant information.

JOB DESCRIPTION TEXT:
{jd_text_truncated}

Extract the following information and return ONLY valid JSON:

1. TITLE: Extract the job title/position. Look for patterns like:
   - "We are looking for a [Title]"
   - "Seeking a [Title]"
   - "Position: [Title]"
   - "Role: [Title]"
   - Job title at the beginning of the description
   Include any qualifiers like "Entry-Level", "Senior", "Junior" if mentioned.
   Return the full title as a string (e.g., "Entry-Level Mobile Application Developer (Flutter)").

2. MUST_HAVE: Extract ALL required/mandatory skills and qualifications. Look for sections like:
   - "Required Skills"
   - "Must have"
   - "Essential"
   - "Prerequisites"
   - "Requirements"
   Extract ALL technologies, tools, frameworks, programming languages, and technical skills mentioned as required.
   Return as a list of individual skill strings (e.g., ["Flutter", "Dart", "Firebase", "REST API", "Git"]).
   Include both specific technologies and general concepts (e.g., "mobile UI/UX", "state management").

3. NICE_TO_HAVE: Extract all preferred/bonus skills. Look for sections like:
   - "Nice to have"
   - "Preferred"
   - "Bonus"
   - "Optional"
   - "Plus"
   Return as a list of individual skill strings.

4. MIN_YEARS: Extract minimum years of experience required. Look for patterns like:
   - "X+ years of experience"
   - "Minimum X years"
   - "At least X years"
   Return as an integer (0 if not specified or entry-level).

Return the response in this EXACT JSON format (no markdown, no code blocks):
{{
  "title": "Job Title",
  "must_have": ["skill1", "skill2", ...],
  "nice_to_have": ["skill1", "skill2", ...],
  "min_years": 0
}}

Important:
- Extract ALL skills mentioned in required sections, don't miss any technologies
- Extract the exact job title as written (including qualifiers and parentheses)
- For skills, extract both specific technologies (e.g., "Flutter", "Dart") and general concepts (e.g., "mobile app development", "RESTful APIs")
- If a field is not found, use empty string "" or empty array [] or 0
- Be comprehensive - extract all relevant skills and requirements
- Don't rely on predefined keyword lists - extract what's actually mentioned in the JD
"""

        logger.info("Calling OpenAI for JD extraction...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at parsing job descriptions. Always extract accurate, structured information and return ONLY valid JSON, no markdown formatting. Extract ALL skills and requirements mentioned, don't miss any technologies or tools."
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
        title = result.get("title", "").strip()
        must_have = result.get("must_have", [])
        nice_to_have = result.get("nice_to_have", [])
        min_years = result.get("min_years", 0)
        
        # Clean skills: remove empty strings, deduplicate, normalize
        must_have = [s.strip() for s in must_have if s and s.strip()]
        must_have = list(dict.fromkeys(must_have))  # Remove duplicates while preserving order
        
        nice_to_have = [s.strip() for s in nice_to_have if s and s.strip()]
        nice_to_have = list(dict.fromkeys(nice_to_have))  # Remove duplicates
        
        # Validate min_years
        try:
            min_years = int(min_years) if min_years else 0
            min_years = max(0, min_years)  # Ensure non-negative
        except (ValueError, TypeError):
            min_years = 0
        
        logger.info(f"OpenAI JD extraction successful: title='{title}', {len(must_have)} must-have skills, {len(nice_to_have)} nice-to-have skills, min_years={min_years}")
        
        return {
            "title": title,
            "must_have": must_have,
            "nice_to_have": nice_to_have,
            "min_years": min_years,
            "jd_text": jd_text  # Preserve original JD text for semantic analysis
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
        # Fallback to regex extraction
        from .jd_extractor import extract_from_jd
        return extract_from_jd(jd_text)
    except Exception as e:
        logger.error(f"OpenAI JD extraction error: {str(e)}, falling back to regex")
        # Fallback to regex extraction
        from .jd_extractor import extract_from_jd
        return extract_from_jd(jd_text)

