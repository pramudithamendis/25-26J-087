from typing import Dict, List
import logging
import json
from openai import OpenAI
from app.config import settings
from app.services.technology_mismatch_detector import detect_technology_mismatch, build_mismatch_warning

logger = logging.getLogger(__name__)

_openai_client = None

def get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for role classification")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def classify_roles(canonical_skills: List[str], jd_info: Dict) -> List[Dict]:
    """
    Classify candidate into role categories using pure LLM-based approach
    
    Uses LLM to:
    1. Extract roles from JD dynamically
    2. Extract critical skills for each role from JD
    3. Validate candidate has critical skills
    4. Score role relevance
    5. Rank and filter to top N roles
    
    No hardcoded values - fully LLM-driven.
    
    Args:
        canonical_skills: List of normalized skill names
        jd_info: Job description information
    
    Returns:
        List of role predictions with similarity scores
    """
    if not canonical_skills:
        logger.warning("No canonical skills provided for role classification")
        return []
    
    if not jd_info:
        logger.warning("No JD info provided for role classification")
        return []
    
    # Check if OpenAI is available
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, cannot perform LLM-based role classification")
        return []
    
    client = get_openai_client()
    if not client:
        logger.warning("OpenAI client not available, cannot perform LLM-based role classification")
        return []
    
    # Build candidate profile
    candidate_profile = ", ".join(canonical_skills)
    
    # Build JD profile
    jd_title = jd_info.get("title", "")
    jd_text = jd_info.get("jd_text", "")
    jd_must_have = jd_info.get("must_have", [])
    jd_nice_to_have = jd_info.get("nice_to_have", [])
    
    # Combine JD information
    jd_summary_parts = []
    if jd_title:
        jd_summary_parts.append(f"Job Title: {jd_title}")
    if jd_text:
        # Use first 2000 chars of JD text to avoid token limits
        jd_summary_parts.append(f"Job Description: {jd_text[:2000]}")
    if jd_must_have:
        jd_summary_parts.append(f"Required Skills: {', '.join(jd_must_have)}")
    if jd_nice_to_have:
        jd_summary_parts.append(f"Preferred Skills: {', '.join(jd_nice_to_have)}")
    
    jd_summary = "\n".join(jd_summary_parts)
    
    logger.debug(f"LLM role classification: {len(canonical_skills)} candidate skills, JD title='{jd_title}'")
    
    # CRITICAL: Check for technology mismatch BEFORE building prompt using LLM-based detection
    candidate_dict = {"skills_canonical": canonical_skills, "skills_raw": canonical_skills}
    mismatch_result = detect_technology_mismatch(jd_info, candidate_dict)
    
    framework_mismatch_warning = ""
    if mismatch_result.get("mismatch_detected") and mismatch_result.get("severity") == "critical":
        # Use dynamic mismatch warning from LLM result
        framework_mismatch_warning = build_mismatch_warning(mismatch_result)
        # Add role-specific instructions
        required_techs = ", ".join(mismatch_result.get("required_technologies", []))
        framework_mismatch_warning += f"""
YOU MUST:
1. Set has_critical_skills = FALSE for roles requiring {required_techs}
2. Set relevance_score < 0.3 for roles requiring {required_techs}
3. EXCLUDE roles requiring {required_techs} from final_rankings
4. Only include other suitable roles in final_rankings

DO NOT include roles requiring {required_techs} in final_rankings even if candidate has related experience!

"""
    
    # Single LLM call with structured output for all steps
    prompt = f"""{framework_mismatch_warning}Analyze this job description and candidate profile to classify the candidate into suitable roles.

JOB DESCRIPTION:
{jd_summary}

CANDIDATE SKILLS:
{candidate_profile}

Perform the following analysis:

1. **Extract Roles from JD**: Identify the primary role(s) this job is targeting. Consider the job title, responsibilities, and required skills. Return 1-5 potential roles (e.g., "Mobile Developer", "Backend Engineer", "Full-Stack Engineer", etc.). Be specific - if the JD mentions a specific technology/framework, include it in the role name (e.g., "Mobile Developer (Flutter)", "Backend Engineer (Python)").

2. **For Each Extracted Role**:
   a. Extract critical skills: Identify the MUST-HAVE skills for this role from the JD. These are skills without which a candidate cannot perform the role. Distinguish from nice-to-have skills.
   b. Validate candidate skills: Check if the candidate has the critical skills. 
   
   **CRITICAL TECHNOLOGY RULES - BE STRICT:**
   - Incompatible technologies in the same category are DIFFERENT and do NOT match (e.g., different mobile frameworks, different frontend frameworks, different backend languages)
   - If JD requires a specific technology and candidate has a different but incompatible technology in the same category, set has_critical_skills = FALSE and relevance_score < 0.3
   - Only consider semantic equivalence for similar technologies (e.g., "React" matches "React.js")
   - For technology-specific roles, the technology name MUST match exactly or be semantically equivalent
   
   c. Score relevance: Rate how well the candidate fits this role (0.0 to 1.0) considering:
      - Critical skill match (most important) - if missing critical framework, score MUST be < 0.3
      - Overall skill alignment
      - Experience relevance
      - Fit with job requirements
   d. Provide reasoning: Explain why the candidate does/doesn't fit this role. If there's a framework mismatch, explicitly state it.

3. **Identify Other Suitable Roles**: Based on the candidate's skills and experience, identify OTHER roles they might fit (even if not mentioned in the JD). Consider roles like:
   - DevOps Engineer (if candidate has cloud, CI/CD, containerization skills)
   - Backend Engineer (if candidate has server-side, API, database skills)
   - Frontend Engineer (if candidate has UI/UX, frontend framework skills)
   - Full-Stack Engineer (if candidate has both frontend and backend skills)
   - Data Scientist (if candidate has ML, data analysis skills)
   - QA Engineer (if candidate has testing, QA skills)
   - Software Architect (if candidate has architecture, system design skills)
   - Mobile Developer (if candidate has mobile development skills, even if different framework)
   
   For each identified role:
   a. Extract critical skills for that role type
   b. Validate candidate has those skills
   c. Score relevance (0.0 to 1.0)
   d. Provide reasoning

4. **Rank and Filter**: Combine JD roles and other suitable roles. Rank ALL roles by relevance score and keep only the top 2-3 most relevant roles. 
   
   **EXCLUSION RULES:**
   - If JD role requires a specific technology and candidate has a different but incompatible technology in the same category, EXCLUDE that JD role from final_rankings
   - Include roles where:
     * Candidate has the critical skills AND relevance score >= 0.5, OR
     * Relevance score is above 0.6 (even if not perfect match)
   - Exclude roles where:
     * Candidate completely lacks critical technology skills (technology mismatch detected)
     * Relevance score is below 0.4

Return the result as JSON with this exact structure:
{{
  "extracted_roles": [
    {{
      "role": "Role Name",
      "critical_skills": ["skill1", "skill2", ...],
      "has_critical_skills": true/false,
      "relevance_score": 0.0-1.0,
      "reasoning": "Explanation of why candidate fits/doesn't fit this role"
    }}
  ],
  "other_suitable_roles": [
    {{
      "role": "Role Name",
      "critical_skills": ["skill1", "skill2", ...],
      "has_critical_skills": true/false,
      "relevance_score": 0.0-1.0,
      "reasoning": "Explanation"
    }}
  ],
  "final_rankings": [
    {{
      "role": "Role Name",
      "similarity": 0.0-1.0,
      "reason": "Brief reason for inclusion"
    }}
  ]
}}

Important guidelines:
- If candidate doesn't fit JD role, still identify OTHER roles they fit
- Be strict about critical skills for JD role - do not match incompatible technologies
- Be more flexible for other roles (consider semantic equivalence)
- Always return at least 1-2 roles if candidate has relevant skills
- Relevance score should reflect actual fit
- Return maximum 3 roles in final_rankings
"""

    try:
        logger.info("Calling LLM for role classification...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing job descriptions and candidate profiles to match candidates to suitable roles. Be precise, strict, and accurate in your analysis. Always return valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistent results
            response_format={"type": "json_object"},
            max_tokens=2000
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
        
        # Extract final rankings
        final_rankings = result.get("final_rankings", [])
        extracted_roles = result.get("extracted_roles", [])
        other_suitable_roles = result.get("other_suitable_roles", [])
        
        # Log extracted roles for debugging
        if extracted_roles:
            logger.info(f"LLM extracted {len(extracted_roles)} roles from JD")
            for role_info in extracted_roles:
                logger.debug(f"  - {role_info.get('role')}: has_critical_skills={role_info.get('has_critical_skills')}, relevance={role_info.get('relevance_score', 0):.2f}")
        
        if other_suitable_roles:
            logger.info(f"LLM identified {len(other_suitable_roles)} other suitable roles")
            for role_info in other_suitable_roles:
                logger.debug(f"  - {role_info.get('role')}: has_critical_skills={role_info.get('has_critical_skills')}, relevance={role_info.get('relevance_score', 0):.2f}")
        
        # Build role predictions from final rankings
        role_predictions = []
        for ranking in final_rankings:
            role = ranking.get("role", "")
            similarity = ranking.get("similarity", 0.0)
            reason = ranking.get("reason", "Skill match with role requirements")
            
            if role and similarity > 0:
                # Determine reason category
                if similarity >= 0.7:
                    reason_category = "Strong skill match with role requirements"
                elif similarity >= 0.5:
                    reason_category = "Moderate skill match with role requirements"
                elif similarity >= 0.3:
                    reason_category = "Partial skill match"
                else:
                    reason_category = "Weak skill match"
                
                # Use LLM's reason if provided, otherwise use category
                final_reason = reason if reason and len(reason) > 10 else reason_category
                
                role_predictions.append({
                    "role": role,
                    "similarity": round(float(similarity), 2),
                    "reason": final_reason
                })
        
        logger.info(f"LLM role classification result: {len(role_predictions)} roles predicted")
        if role_predictions:
            logger.info(f"Top role: {role_predictions[0]['role']} (similarity: {role_predictions[0]['similarity']:.2f})")
        
        return role_predictions
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
        logger.debug(f"LLM response text: {result_text[:500] if 'result_text' in locals() else 'N/A'}")
        return []
    except Exception as e:
        logger.error(f"LLM role classification error: {str(e)}", exc_info=True)
        return []
