from typing import Dict, List, Optional
from app.config import settings
import logging
import json
import re

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
    # CRITICAL: Ensure we're using the latest JD data (should come from state.jd_data)
    jd_title = job_desc.get("title", "")
    jd_must_have = job_desc.get("must_have", [])
    jd_nice_to_have = job_desc.get("nice_to_have", [])
    jd_text = job_desc.get("jd_text", "")
    
    # Log JD data being used for debugging
    logger.debug(f"Technology mismatch detection using JD: title={jd_title}, must_have count={len(jd_must_have)}, jd_text length={len(jd_text)}")
    
    candidate_skills = candidate.get("skills_canonical", candidate.get("skills_raw", []))
    candidate_experience = candidate.get("experience", [])
    
    # CRITICAL: Validate candidate has required skills FIRST
    # Use same logic as has_required_skills() to ensure consistency
    # This prevents judge from seeing incorrect mismatch warnings
    if jd_must_have:
        from app.services.aggregator import has_required_skills
        from app.services.skill_categorizer import filter_technical_skills
        
        # Filter to technical skills only
        must_have_technical = filter_technical_skills(jd_must_have)
        
        if must_have_technical:
            # Check if candidate has all required skills FIRST
            candidate_has_required_skills, skill_match_details = has_required_skills(
                candidate_skills, must_have_technical, use_semantic_matching=True
            )
            
            if candidate_has_required_skills:
                logger.info(f"✅ Pre-validation: Candidate has all required technical skills - no mismatch")
                logger.info(f"   Match details: {skill_match_details.get('found_skills', [])}")
                logger.info(f"   This prevents judge from seeing incorrect mismatch warnings")
                # Return immediately - no mismatch, no need to call LLM
                return {
                    "mismatch_detected": False,
                    "mismatch_type": None,
                    "required_technologies": [],
                    "candidate_technologies": [],
                    "incompatible_technologies": [],
                    "mismatch_details": "All required technologies found in candidate skills",
                    "severity": None
                }
            else:
                logger.info(f"❌ Pre-validation: Candidate missing some required technical skills")
                logger.info(f"   Missing: {skill_match_details.get('missing_skills', [])}")
                logger.info(f"   Found: {skill_match_details.get('found_skills', [])}")
                logger.info(f"   Proceeding with LLM mismatch detection for detailed analysis")
    
    # Only proceed with LLM mismatch detection if candidate is missing required skills
    
    # CRITICAL: Build explicit candidate technologies list for validation
    # Include ALL required technologies, even if not in first 30 skills
    # This prevents false "missing" reports (e.g., "R" not found because it's skill #31)
    all_candidate_skills = list(set(candidate_skills))  # Deduplicate
    required_techs_lower = [tech.lower() for tech in jd_must_have]
    
    # Prioritize required technologies in the list
    prioritized_skills = []
    other_skills = []
    
    for skill in all_candidate_skills:
        skill_lower = skill.lower()
        # Check if this skill matches any required technology (exact or substring)
        matches_required = any(
            req_tech.lower() in skill_lower or skill_lower in req_tech.lower()
            for req_tech in jd_must_have
        )
        if matches_required:
            prioritized_skills.append(skill)
        else:
            other_skills.append(skill)
    
    # Build list: required matches first, then others (limit to 50 total for token efficiency)
    # CRITICAL: This ensures ALL required technologies are visible to LLM, even if not in first 30
    candidate_technologies = prioritized_skills + other_skills[:max(0, 50 - len(prioritized_skills))]
    candidate_tech_list = "\n".join([f"{i+1}. {tech}" for i, tech in enumerate(candidate_technologies)])
    
    logger.info(f"Technology mismatch validation list: {len(prioritized_skills)} prioritized (required matches), {len(candidate_technologies)} total")
    if prioritized_skills:
        logger.debug(f"  Prioritized skills (required matches): {prioritized_skills[:10]}")
    
    # Build candidate skills summary
    candidate_skills_text = ", ".join(all_candidate_skills[:50])  # Limit to avoid token issues
    
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
Skills Summary: {candidate_skills_text}

CANDIDATE TECHNOLOGIES LIST (VERIFY EACH REQUIRED SKILL AGAINST THIS LIST):
{candidate_tech_list}

Recent Experience:
{experience_summary}

CRITICAL VALIDATION STEP - VERIFY EACH REQUIRED SKILL AGAINST CANDIDATE TECHNOLOGIES LIST:
Before analyzing mismatches, you MUST verify each required technology exists in the "CANDIDATE TECHNOLOGIES LIST" above.

For EACH required technology from Must-Have Skills, you MUST:
1. Search the "CANDIDATE TECHNOLOGIES LIST" above (items 1-{len(candidate_technologies)})
2. Check for exact match (case-insensitive)
3. Check for substring match (e.g., "Power BI" matches "Microsoft Power BI", "SQL" matches "SQLite")
4. Document your check: "Required: [TECH] → Found in list: YES/NO → Match type: [EXACT/SUBSTRING/NONE]"

Example validation:
- Required: "SQL" → Check list items 1-{len(candidate_technologies)} → If "SQL" or "sql" appears → FOUND → Match: EXACT or SUBSTRING
- Required: "Power BI" → Check list items 1-{len(candidate_technologies)} → If "Power BI", "power bi", or "powerbi" appears → FOUND → Match: EXACT or SUBSTRING

ONLY proceed to mismatch analysis if a required technology is NOT FOUND in the list.
If ALL required technologies are FOUND → SET mismatch_detected = false (NO MISMATCH, return immediately)

ONLY flag a mismatch if:
- The candidate is MISSING one or more required PRIMARY/CORE technologies
- AND the candidate has DIFFERENT but similar technologies in the same category that are INCOMPATIBLE
- Example: Job requires Flutter, candidate has React Native but NO Flutter → MISMATCH
- Example: Job requires SQL and Power BI, candidate has SQL but NO Power BI (has Tableau instead) → MISMATCH

Your task is to:
1. Extract the PRIMARY/CORE technologies/frameworks required by the job from Must-Have Skills (e.g., Flutter, React Native, Python, Java, React, Vue, Angular, Swift, Kotlin, SQL, Power BI, etc.)
2. For EACH required technology, perform the VALIDATION STEP above using the "CANDIDATE TECHNOLOGIES LIST"
3. If ALL required technologies are FOUND in the list → mismatch_detected = false (NO MISMATCH, return immediately)
4. If ANY required technology is NOT FOUND in the list, then determine if there's a mismatch where:
   - The job requires a specific technology/framework (e.g., Flutter)
   - The candidate has a DIFFERENT but similar technology/framework in the same category (e.g., React Native)
   - These technologies are INCOMPATIBLE (cannot substitute one for the other)

IMPORTANT RULES:
- BEFORE flagging any mismatch, you MUST verify each required technology against the candidate_technologies list
- If a required technology appears in candidate_technologies (exact or substring match), the candidate HAS that technology
- ONLY flag CRITICAL mismatches where candidate is MISSING required technologies AND has incompatible alternatives
- Examples of CRITICAL mismatches (candidate MISSING required tech):
  * Job requires Flutter, candidate_technologies=['React Native', 'Dart'] → Flutter NOT FOUND → CRITICAL MISMATCH
  * Job requires React, candidate_technologies=['Vue', 'Angular'] → React NOT FOUND → CRITICAL MISMATCH
  * Job requires Python, candidate_technologies=['Java', 'C++'] → Python NOT FOUND → CRITICAL MISMATCH
- Do NOT flag if:
  * Candidate has ALL required technologies in candidate_technologies list → NO MISMATCH (even with additional skills)
  * Example: Job requires SQL and Power BI, candidate_technologies=['SQL', 'Power BI', 'Python', 'AWS'] → SQL FOUND, Power BI FOUND → NO MISMATCH
  * Candidate has required technology + complementary technologies → NO MISMATCH
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
                {"role": "system", "content": "You are an expert technical recruiter who understands technology relationships and incompatibilities. CRITICAL RULES: 1) Before flagging any mismatch, you MUST explicitly verify each required technology exists in the candidate_technologies list by checking it item by item. 2) If a required technology appears in candidate_technologies (exact or substring match), the candidate HAS that technology. 3) Only flag technology mismatches if the candidate is MISSING required technologies. 4) If the candidate HAS all required technologies (even with additional skills), there is NO MISMATCH. Always validate required technologies against candidate_technologies FIRST before flagging any mismatch."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Post-processing validation: Check LLM response against actual candidate skills
        # Use has_required_skills() directly for consistency (same logic everywhere)
        # This catches LLM hallucination where it reports technologies as missing when they're actually present
        if result.get("mismatch_detected"):
            required_techs = result.get("required_technologies", [])
            
            # Use has_required_skills() for validation (same logic everywhere)
            from app.services.aggregator import has_required_skills
            from app.services.skill_categorizer import filter_technical_skills
            
            all_candidate_skills = candidate.get("skills_canonical", candidate.get("skills_raw", []))
            required_technical = filter_technical_skills(required_techs)
            
            if required_technical:
                candidate_has_required_skills, skill_match_details = has_required_skills(
                    all_candidate_skills, required_technical, use_semantic_matching=True
                )
                
                if candidate_has_required_skills:
                    # Override LLM result
                    logger.warning(f"LLM hallucination detected: Reported mismatch but all required technologies found")
                    logger.warning(f"  Required technologies: {required_techs}")
                    logger.warning(f"  Found skills: {skill_match_details.get('found_skills', [])}")
                    logger.warning(f"  Overriding LLM result: mismatch_detected=False")
                    result["mismatch_detected"] = False
                    result["severity"] = None
                    result["mismatch_details"] = "All required technologies found in candidate skills"
                    result["incompatible_technologies"] = []
                else:
                    # LLM was correct - candidate is missing some technologies
                    missing_skills = skill_match_details.get("missing_skills", [])
                    logger.info(f"Validated mismatch: Actually missing {len(missing_skills)} technologies: {missing_skills}")
                    logger.info(f"  Found skills: {skill_match_details.get('found_skills', [])}")
                    # Update required_technologies to only include actually missing ones
                    result["required_technologies"] = missing_skills
        
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

