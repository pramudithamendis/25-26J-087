from typing import Dict, List, Optional
from app.config import settings
import logging
import json
import re
from openai import OpenAI

logger = logging.getLogger(__name__)

_openai_client = None
_jd_cache = {}  # Cache: {job_id: extracted_data} - ensures same job always extracts same skills

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

def extract_from_jd_openai(jd_text: str, job_id: Optional[str] = None) -> Dict:
    """
    Extract structured data from job description using OpenAI
    
    Uses OpenAI to intelligently parse JD text and extract structured information
    without relying on hardcoded keyword lists.
    
    Args:
        jd_text: Full job description text
        job_id: Optional job ID for caching (ensures same job always extracts same skills)
    
    Returns:
        Dictionary with title, must_have, nice_to_have, min_years, jd_text
    """
    # Check cache first if job_id provided
    if job_id and job_id in _jd_cache:
        logger.info(f"✅ Using cached JD extraction for job {job_id} (ensures consistency)")
        cached_result = _jd_cache[job_id]
        logger.info(f"   Cached must-have skills: {len(cached_result.get('must_have', []))} - {cached_result.get('must_have', [])}")
        return cached_result.copy()  # Return copy to prevent mutation
    
    if not jd_text or not jd_text.strip():
        logger.warning("No text found in JD")
        result = {
            "title": "",
            "must_have": [],
            "nice_to_have": [],
            "min_years": 0,
            "jd_text": jd_text
        }
        # Cache even empty results
        if job_id:
            _jd_cache[job_id] = result.copy()
        return result
    
    # Fix common data issues
    jd_text = jd_text.strip()
    # Fix "ob Description" -> "Job Description"
    if jd_text.startswith("ob Description"):
        jd_text = "Job Description" + jd_text[14:]
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, falling back to regex extraction")
        from .jd_extractor import extract_from_jd
        return extract_from_jd(jd_text)
    
    def _regex_fallback(jd_text: str) -> Dict:
        """Call regex-based extraction with the fallback flag set to prevent recursion."""
        from .jd_extractor import _fallback_active
        import app.services.extractors.jd_extractor as jd_mod
        jd_mod._fallback_active = True
        try:
            from .jd_extractor import extract_from_jd
            return extract_from_jd(jd_text)
        finally:
            jd_mod._fallback_active = False

    try:
        client = get_openai_client()
        if not client:
            return _regex_fallback(jd_text)
        
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

2. MUST_HAVE: Extract ONLY TECHNICAL SKILLS that are required/mandatory. Look for sections like:
   - "Required Skills"
   - "Must have"
   - "Essential"
   - "Prerequisites"
   - "Requirements"
   
   CRITICAL: Only include TECHNICAL SKILLS in MUST_HAVE:
   - Programming languages (SQL, Python, Java, JavaScript, etc.)
   - Frameworks and tools (Power BI, React, Flutter, AWS, Docker, etc.)
   - Technical concepts (REST APIs, databases, microservices, etc.)
   
   DO NOT include in MUST_HAVE:
   - Soft skills (communication skills, teamwork, leadership) → Move to NICE_TO_HAVE
   - Work arrangements (remote work, on-site, hybrid) → Move to NICE_TO_HAVE
   - General concepts without technical specificity (data insights, business acumen) → Move to NICE_TO_HAVE
   
   Return as a list of individual technical skill strings (e.g., ["SQL", "Power BI", "Python", "REST API", "Git"]).

3. NICE_TO_HAVE: Extract all preferred/bonus skills, soft skills, work arrangements, and general concepts. Look for sections like:
   - "Nice to have"
   - "Preferred"
   - "Bonus"
   - "Optional"
   - "Plus"
   
   Include in NICE_TO_HAVE:
   - Additional technical skills that are preferred but not required
   - Soft skills (communication skills, teamwork, problem-solving)
   - Work arrangements (remote work, on-site, hybrid)
   - General concepts (data insights, business acumen, agile methodology)
   
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
- For MUST_HAVE: ONLY include TECHNICAL SKILLS (programming languages, tools, frameworks). Exclude soft skills, work arrangements, and vague concepts.
- Extract the exact job title as written (including qualifiers and parentheses)
- For technical skills, extract specific technologies (e.g., "SQL", "Power BI", "Python", "REST API")
- Soft skills, work arrangements, and general concepts should go in NICE_TO_HAVE, not MUST_HAVE
- If a field is not found, use empty string "" or empty array [] or 0
- Be comprehensive but precise - distinguish between technical requirements and soft skills/work arrangements
- Don't rely on predefined keyword lists - extract what's actually mentioned in the JD
"""
        
        # Retry loop with max attempts (for transient errors like 5xx)
        max_retries = 3
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Calling OpenAI for JD extraction... (attempt {attempt}/{max_retries})")
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
                    temperature=0.0,  # Zero temperature for maximum determinism (with caching ensures perfect consistency)
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
                
                # Successfully parsed — break out of retry loop
                break
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from OpenAI response (attempt {attempt}): {str(e)}")
                last_error = e
                if attempt == max_retries:
                    logger.error(f"All {max_retries} attempts failed with JSON decode errors, falling back to regex")
                    return _regex_fallback(jd_text)
                continue
                
            except Exception as e:
                error_str = str(e)
                last_error = e
                # For auth errors (401) or invalid API key, don't retry — it will never succeed
                if "401" in error_str or "invalid_api_key" in error_str or "Unauthorized" in error_str:
                    logger.error(f"OpenAI authentication failed (attempt {attempt}): {error_str}. Not retrying — falling back to regex.")
                    return _regex_fallback(jd_text)
                
                logger.warning(f"OpenAI call failed (attempt {attempt}/{max_retries}): {error_str}")
                if attempt == max_retries:
                    logger.error(f"All {max_retries} OpenAI attempts failed, falling back to regex")
                    return _regex_fallback(jd_text)
                continue
        
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
        
        # Post-processing: Filter non-technical skills from must_have
        from app.services.skill_categorizer import categorize_skills_batch
        
        # Categorize must_have skills
        must_have_categorized = categorize_skills_batch(must_have)
        must_have_technical = must_have_categorized["technical"]
        must_have_non_technical = (
            must_have_categorized["soft"] + 
            must_have_categorized["work_arrangement"] + 
            must_have_categorized["concept"]
        )
        
        # Move non-technical skills from must_have to nice_to_have
        if must_have_non_technical:
            logger.info(f"Moving {len(must_have_non_technical)} non-technical skills from must_have to nice_to_have: {must_have_non_technical}")
            nice_to_have.extend(must_have_non_technical)
            nice_to_have = list(dict.fromkeys(nice_to_have))  # Remove duplicates
            must_have = must_have_technical  # Keep only technical skills in must_have
        
        # Validate min_years
        try:
            min_years = int(min_years) if min_years else 0
            min_years = max(0, min_years)  # Ensure non-negative
        except (ValueError, TypeError):
            min_years = 0
        
        logger.info(f"OpenAI JD extraction successful: title='{title}', {len(must_have)} must-have skills, {len(nice_to_have)} nice-to-have skills, min_years={min_years}")
        
        result = {
            "title": title,
            "must_have": must_have,
            "nice_to_have": nice_to_have,
            "min_years": min_years,
            "jd_text": jd_text  # Preserve original JD text for semantic analysis
        }
        
        # Cache result if job_id provided
        if job_id:
            _jd_cache[job_id] = result.copy()
            logger.info(f"✅ Cached JD extraction for job {job_id}: {len(must_have)} must-have skills - {must_have}")
        
        return result
    
    except Exception as e:
        logger.error(f"Unexpected error in OpenAI JD extraction: {str(e)}, falling back to regex")
        return _regex_fallback(jd_text)

