from typing import Dict, List, Optional
from app.config import settings
import logging
import json

logger = logging.getLogger(__name__)

_openai_client = None

def get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for technology mismatch detection")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def detect_technology_mismatch(job_desc: Dict, candidate: Dict) -> Dict:
    """
    Use LLM to dynamically detect technology/framework mismatches between job requirements and candidate skills.
    
    This function analyzes the job description and candidate profile to identify incompatible technology pairs
    without any hardcoded technology names. The LLM understands technology relationships and incompatibilities.
    
    Args:
        job_desc: Dictionary with job description data (title, must_have, nice_to_have, jd_text)
        candidate: Dictionary with candidate data (skills_canonical, skills_raw, experience, etc.)
    
    Returns:
        Dictionary with:
        {
            "mismatch_detected": bool,
            "mismatch_type": str,  # e.g., "framework_mismatch", "language_mismatch", "platform_mismatch"
            "required_technologies": List[str],  # Technologies required by JD
            "candidate_technologies": List[str],  # Technologies candidate has
            "incompatible_technologies": List[str],  # Technologies candidate has that are incompatible
            "mismatch_details": str,  # Human-readable explanation
            "severity": str  # "critical", "moderate", "minor"
        }
    """
    client = get_openai_client()
    
    if not client:
        logger.warning("OpenAI client not available, returning no mismatch")
        return {
            "mismatch_detected": False,
            "mismatch_type": None,
            "required_technologies": [],
            "candidate_technologies": [],
            "incompatible_technologies": [],
            "mismatch_details": "",
            "severity": None
        }
    
    # Extract relevant information
    jd_title = job_desc.get("title", "")
    jd_must_have = job_desc.get("must_have", [])
    jd_nice_to_have = job_desc.get("nice_to_have", [])
    jd_text = job_desc.get("jd_text", "")
    
    candidate_skills = candidate.get("skills_canonical", candidate.get("skills_raw", []))
    candidate_experience = candidate.get("experience", [])
    
    # Build candidate skills summary
    candidate_skills_text = ", ".join(candidate_skills[:50])  # Limit to avoid token issues
    
    # Build experience summary
    experience_summary = ""
    if candidate_experience:
        for exp in candidate_experience[:3]:  # Last 3 experiences
            title = exp.get("title", "")
            company = exp.get("company", "")
            highlights = exp.get("highlights", [])
            exp_text = f"{title} at {company}: {', '.join(highlights[:2])}"
            experience_summary += exp_text + "\n"
    
    # Build prompt for LLM
    prompt = f"""Analyze this job description and candidate profile to detect technology/framework mismatches.

JOB DESCRIPTION:
Title: {jd_title}
Must-Have Skills: {', '.join(jd_must_have[:20])}
Nice-to-Have Skills: {', '.join(jd_nice_to_have[:15])}
Description: {jd_text[:1000]}

CANDIDATE PROFILE:
Skills: {candidate_skills_text}
Recent Experience:
{experience_summary}

Your task is to:
1. Extract the PRIMARY/CORE technologies/frameworks required by the job (e.g., Flutter, React Native, Python, Java, React, Vue, Angular, Swift, Kotlin, etc.)
2. Extract the PRIMARY/CORE technologies/frameworks the candidate has
3. Determine if there's a mismatch where:
   - The job requires a specific technology/framework (e.g., Flutter)
   - The candidate has a DIFFERENT but similar technology/framework in the same category (e.g., React Native)
   - These technologies are INCOMPATIBLE (cannot substitute one for the other)

IMPORTANT RULES:
- Only flag CRITICAL mismatches where technologies are in the same category but incompatible
- Examples of CRITICAL mismatches:
  * Mobile frameworks: Flutter vs React Native (both mobile but different)
  * Frontend frameworks: React vs Vue vs Angular (all frontend but different)
  * Backend languages: Python vs Java vs Node.js (all backend but different)
  * Mobile platforms: iOS/Swift vs Android/Kotlin (both mobile but different platforms)
- Do NOT flag if:
  * Candidate has the required technology (even if they also have alternatives)
  * Technologies are complementary (e.g., React + Node.js is fine if job requires both)
  * Candidate has related but acceptable technologies (e.g., TypeScript if job requires JavaScript)
  * The mismatch is minor or can be learned quickly

Return your analysis as JSON with this exact structure:
{{
  "mismatch_detected": true/false,
  "mismatch_type": "framework_mismatch" | "language_mismatch" | "platform_mismatch" | null,
  "required_technologies": ["list", "of", "required", "technologies"],
  "candidate_technologies": ["list", "of", "candidate", "technologies"],
  "incompatible_technologies": ["list", "of", "incompatible", "technologies", "candidate", "has"],
  "mismatch_details": "Detailed explanation of the mismatch",
  "severity": "critical" | "moderate" | "minor" | null
}}

Severity guidelines:
- "critical": Technologies are fundamentally incompatible and cannot be substituted (e.g., Flutter vs React Native)
- "moderate": Technologies are different but some skills may transfer (e.g., React vs Vue)
- "minor": Technologies are related but different versions/variants (e.g., React vs React.js)

If no mismatch is detected, set mismatch_detected to false and return null for other fields.
"""
    
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert technical recruiter who understands technology relationships and incompatibilities. Analyze job requirements and candidate skills to detect critical technology mismatches."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        logger.info(f"Technology mismatch detection result: mismatch_detected={result.get('mismatch_detected', False)}, severity={result.get('severity')}")
        
        if result.get("mismatch_detected"):
            logger.warning(f"🚨 Technology mismatch detected: {result.get('mismatch_details', '')}")
            logger.info(f"   Required: {result.get('required_technologies', [])}")
            logger.info(f"   Candidate has: {result.get('candidate_technologies', [])}")
            logger.info(f"   Incompatible: {result.get('incompatible_technologies', [])}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in LLM-based technology mismatch detection: {str(e)}")
        logger.warning("Falling back to no mismatch detection")
        return {
            "mismatch_detected": False,
            "mismatch_type": None,
            "required_technologies": [],
            "candidate_technologies": [],
            "incompatible_technologies": [],
            "mismatch_details": "",
            "severity": None
        }

def build_mismatch_warning(mismatch_result: Dict) -> str:
    """
    Convert LLM mismatch detection result into formatted warning text for prompts.
    
    Args:
        mismatch_result: Result from detect_technology_mismatch()
    
    Returns:
        Formatted warning string for inclusion in prompts
    """
    if not mismatch_result.get("mismatch_detected"):
        return ""
    
    required = ", ".join(mismatch_result.get("required_technologies", []))
    incompatible = ", ".join(mismatch_result.get("incompatible_technologies", []))
    details = mismatch_result.get("mismatch_details", "")
    severity = mismatch_result.get("severity", "moderate")
    
    warning = f"""
⚠️⚠️⚠️ CRITICAL TECHNOLOGY MISMATCH DETECTED ⚠️⚠️⚠️
JOB REQUIRES: {required}
CANDIDATE HAS: {incompatible}
SEVERITY: {severity.upper()}

{details}

THESE ARE DIFFERENT TECHNOLOGIES - THEY DO NOT MATCH!

YOU MUST:
1. Set has_critical_skills = FALSE for roles requiring {required}
2. Set relevance_score < 0.3 for roles requiring {required}
3. EXCLUDE roles requiring {required} from final_rankings if severity is "critical"
4. Only include other suitable roles in final_rankings

DO NOT include roles requiring {required} in final_rankings even if candidate has related experience!

"""
    
    return warning

