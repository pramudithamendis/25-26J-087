from typing import Dict, List, Tuple, Optional
from app.config import settings
from app.services.technology_mismatch_detector import detect_technology_mismatch, build_mismatch_warning
from app.services.role_criteria_generator import generate_role_criteria
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
            logger.info("OpenAI client initialized for Judge")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def build_judge_prompt(candidate: Dict, job_desc: Dict, role_criteria: Optional[Dict] = None) -> Tuple[str, bool, str, Dict]:
    """Build prompt for LLM judge
    
    Args:
        candidate: Candidate data dictionary
        job_desc: Job description dictionary
        role_criteria: Optional pre-generated role criteria (if None, will generate)
    
    Returns:
        tuple: (prompt, framework_mismatch_detected, mismatch_details, role_criteria_dict)
    """
    
    skills = candidate.get("skills_canonical", candidate.get("skills_raw", []))
    experience = candidate.get("experience", [])
    github = candidate.get("github", {})
    education = candidate.get("education", [])
    
    must_have = job_desc.get("must_have", [])
    nice_to_have = job_desc.get("nice_to_have", [])
    jd_text = job_desc.get("jd_text", "")
    jd_title = job_desc.get("title", "")
    
    # Generate role-specific criteria if not provided
    if role_criteria is None:
        role_criteria = generate_role_criteria(job_desc, candidate)
    
    role_category = role_criteria.get("role_category", "IT Professional")
    criteria_list = role_criteria.get("criteria", [])
    
    logger.info(f"Using role-specific criteria for {role_category}: {len(criteria_list)} criteria")
    logger.debug(f"Criteria: {[c.get('criterion') for c in criteria_list]}")
    
    # Log JD data being used for mismatch detection
    logger.debug(f"Using JD data for mismatch detection: title={jd_title}, must_have count={len(must_have)}, jd_text length={len(jd_text)}")
    
    # Use LLM-based dynamic technology mismatch detection
    # CRITICAL: Ensure job_desc contains the latest extracted JD data
    mismatch_result = detect_technology_mismatch(job_desc, candidate)
    framework_mismatch_detected = mismatch_result.get("mismatch_detected", False) and mismatch_result.get("severity") == "critical"
    mismatch_details = mismatch_result.get("mismatch_details", "")
    
    # Build framework requirements list from LLM-detected required technologies
    framework_requirements = []
    required_techs = mismatch_result.get("required_technologies", [])
    if required_techs:
        for tech in required_techs:
            framework_requirements.append(f"{tech} (CRITICAL - cannot substitute with incompatible alternatives)")
    
    # Build the base prompt with role-specific context
    base_prompt = f"""You are an expert technical recruiter evaluating a candidate for a {role_category} position.

JOB POSITION: {jd_title}

JOB DESCRIPTION:
{jd_text[:2000]}

REQUIRED SKILLS: {', '.join(must_have[:20])}
NICE-TO-HAVE SKILLS: {', '.join(nice_to_have[:20])}
"""
    
    # If framework mismatch detected, put warning at the VERY START
    if framework_mismatch_detected:
        logger.warning(f"🚨 TECHNOLOGY MISMATCH DETECTED IN JUDGE: {mismatch_details}")
        # Use dynamic mismatch warning from LLM result
        mismatch_warning = build_mismatch_warning(mismatch_result)
        # Add mandatory scoring instructions with dynamic criteria count
        criteria_count = len(criteria_list)
        criteria_names = [c.get("criterion", "") for c in criteria_list]
        criteria_examples = "\n".join([
            f"- {name}: Score 1 or 2 (NOT 3, 4, or 5) - has related experience but WRONG TECHNOLOGY"
            for name in criteria_names[:6]  # Limit examples to first 6
        ])
        
        mismatch_warning += f"""🚨🚨🚨 MANDATORY LOW SCORING - TECHNOLOGY MISMATCH 🚨🚨🚨

YOU ARE REQUIRED TO SCORE ALL {criteria_count} CRITERIA BETWEEN 0-2 (NOT 3-5).

This is NOT optional. The candidate does NOT have the required technology/framework.
Even if they have related skills, they CANNOT do this job without the specific technology.

MANDATORY SCORING EXAMPLES:
{criteria_examples}

IF YOU GIVE SCORES OF 3-5, YOU ARE WRONG. THIS IS A TECHNOLOGY MISMATCH.

CRITICAL: The maximum score you can give for ANY criterion is 2. Do NOT exceed 2 for any criterion.

"""
        prompt = mismatch_warning + base_prompt
    else:
        prompt = base_prompt
    
    if framework_requirements:
        prompt += "\n⚠️ CRITICAL TECHNOLOGY REQUIREMENTS - READ CAREFULLY:\n"
        for req in framework_requirements:
            prompt += f"- {req}\n"
        
        if not framework_mismatch_detected:
            prompt += """
⚠️ CRITICAL SCORING RULES:
1. Technology/framework mismatches are CRITICAL - do NOT give credit for "general experience"
2. Even if candidate has related skills - if they lack the REQUIRED technology, score LOW
3. Only score 3-5 if candidate has the EXACT technology required OR a very close equivalent
4. If job requires a specific technology and candidate has a different but similar technology in the same category, score LOW (0-2)

DO NOT give scores of 3-5 for technology mismatches!
"""
    
    prompt += f"""
CANDIDATE PROFILE:
Skills: {', '.join(skills[:30])}

Experience:
"""
    
    for i, exp in enumerate(experience[:5], 1):  # Top 5 experiences
        prompt += f"\n{i}. {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('start', '')} - {exp.get('end', 'Present')})\n"
        for highlight in exp.get("highlights", [])[:3]:
            prompt += f"   • {highlight}\n"
    
    if education:
        prompt += f"\nEducation: {', '.join(education[:3])}\n"
    
    if github.get("repos"):
        repos = github.get("repos", [])
        prompt += f"\nGitHub Activity:\n"
        prompt += f"- {len(repos)} repositories\n"
        prompt += f"- {github.get('commits_last_12m', 0)} commits in last 12 months\n"
        prompt += f"- {github.get('external_prs_merged', 0)} external PRs merged\n"
        if repos:
            prompt += f"\nTop Repositories:\n"
            for repo in repos[:3]:
                prompt += f"- {repo.get('name', '')}: {repo.get('primary_language', 'N/A')}\n"
    
    # Build criteria section dynamically from role_criteria
    criteria_text = ""
    for i, crit in enumerate(criteria_list, 1):
        criterion_name = crit.get("criterion", "")
        criterion_desc = crit.get("description", "")
        criteria_text += f"{i}. {criterion_name}: {criterion_desc}\n"
    
    prompt += f"""
Evaluate the candidate on these {len(criteria_list)} criteria (0-5 scale, where 0=No evidence, 5=Excellent evidence):

{criteria_text}
For each criterion:
- Give a score (0-5 integer)
- Provide specific evidence (quote from experience, skill, or GitHub activity)
- Be STRICT: If job requires specific technology (e.g., Flutter) and candidate doesn't have it, score LOW (0-2)
- Be specific and cite actual examples from the profile
- Consider framework mismatches as critical - don't give high scores for wrong technology
- For {role_category} role, evaluate based on role-specific requirements, not generic software engineering criteria

Respond ONLY with valid JSON in this exact format (no markdown, no code blocks):
{{
  "judge_scores": [
    {{
      "criterion": "{criteria_list[0].get('criterion', 'Criterion 1') if criteria_list else 'Criterion'}",
      "score": 4,
      "evidence": "Specific evidence from candidate profile"
    }}
  ]
}}

IMPORTANT: You must score ALL {len(criteria_list)} criteria listed above. Include all criteria in your response.
"""
    
    return prompt, framework_mismatch_detected, mismatch_details, role_criteria

def judge_with_openai(prompt: str, candidate: Dict = None, job_desc: Dict = None, framework_mismatch: bool = False, role_criteria: Optional[Dict] = None) -> Dict:
    """Judge using OpenAI API"""
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, using heuristic fallback")
        return None
    
    try:
        client = get_openai_client()
        if not client:
            logger.warning("OpenAI client not available, using heuristic fallback")
            return None
        
        logger.info("Calling OpenAI API for candidate judgment...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert technical recruiter. Always respond with valid JSON only, no markdown formatting, no code blocks."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent scoring
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
        
        # Validate structure
        if "judge_scores" not in result:
            logger.error("Invalid response structure from OpenAI")
            return None
        
        scores = result.get('judge_scores', [])
        logger.info(f"Successfully received judge scores from OpenAI: {len(scores)} criteria")
        
        # Log individual scores for debugging
        if scores:
            score_values = [s.get('score', 0) for s in scores]
            avg_score = sum(score_values) / len(score_values) if score_values else 0
            # Build score strings separately to avoid f-string backslash issue
            score_strings = [f"{s.get('criterion', 'N/A')}: {s.get('score', 0)}" for s in scores]
            logger.info(f"Judge scores: {score_strings}")
            logger.info(f"Average judge score: {avg_score:.2f} (role_competency will be {avg_score/5.0*30:.1f})")
            
            # Post-process: If framework mismatch was detected, cap all scores to 2
            if framework_mismatch and any(s.get('score', 0) > 2 for s in scores):
                logger.warning(f"⚠️ FRAMEWORK MISMATCH: Judge gave scores > 2. Capping all scores to maximum 2")
                # Post-process: Cap all scores to 2
                for score_item in scores:
                    if score_item.get('score', 0) > 2:
                        score_item['score'] = 2
                        logger.info(f"   Capped {score_item.get('criterion', 'N/A')} score to 2")
                # Recalculate average after capping
                score_values = [s.get('score', 0) for s in scores]
                avg_score = sum(score_values) / len(score_values) if score_values else 0
                logger.info(f"   After capping: Average judge score: {avg_score:.2f} (role_competency will be {avg_score/5.0*30:.1f})")
            elif candidate and job_desc and any(s.get('score', 0) > 2 for s in scores):
                # Fallback check: use LLM-based mismatch detection if framework_mismatch flag wasn't set
                if not framework_mismatch:
                    mismatch_result = detect_technology_mismatch(job_desc, candidate)
                    if mismatch_result.get("mismatch_detected") and mismatch_result.get("severity") == "critical":
                        logger.warning(f"⚠️ WARNING: Judge gave scores > 2 despite technology mismatch! Scores: {score_values}")
                        logger.warning(f"   Mismatch: {mismatch_result.get('mismatch_details', '')}")
                        logger.warning(f"   Capping all scores to maximum 2 due to technology mismatch")
                        # Post-process: Cap all scores to 2
                        for score_item in scores:
                            if score_item.get('score', 0) > 2:
                                score_item['score'] = 2
                                logger.info(f"   Capped {score_item.get('criterion', 'N/A')} score to 2")
                        # Recalculate average after capping
                        score_values = [s.get('score', 0) for s in scores]
                        avg_score = sum(score_values) / len(score_values) if score_values else 0
                        logger.info(f"   After capping: Average judge score: {avg_score:.2f} (role_competency will be {avg_score/5.0*30:.1f})")
        
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return None

def _calculate_heuristic_score(criterion: str, merged_json: Dict, role_criteria: Dict) -> Tuple[int, str]:
    """
    Calculate heuristic score for a specific criterion based on role.
    
    Returns:
        Tuple of (score, evidence_string)
    """
    role_category = role_criteria.get("role_category", "").lower()
    candidate = merged_json.get("candidate", {})
    skills = candidate.get("skills_raw", [])
    experience = candidate.get("experience", [])
    criterion_lower = criterion.lower()
    
    # Impact is universal - check for metrics/achievements
    if "impact" in criterion_lower:
        impact_score = 2
        evidence_parts = []
        for exp in experience:
            highlights = exp.get("highlights", [])
            for highlight in highlights:
                if any(term in highlight.lower() for term in ['reduced', 'improved', 'increased', 'decreased', '%', 'by', 'achieved', 'delivered']):
                    impact_score = min(5, impact_score + 1)
                    evidence_parts.append(highlight[:50])
                    break
        evidence = "Found metrics/impact statements in experience" if impact_score > 2 else "Limited impact metrics"
        if evidence_parts:
            evidence = f"Found impact metrics: {', '.join(evidence_parts[:2])}"
        return (impact_score, evidence)
    
    # Role-specific heuristics
    if "data analyst" in role_category or "data scientist" in role_category:
        if "data analysis" in criterion_lower or "analytics" in criterion_lower:
            analysis_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['data analysis', 'analytics', 'statistical', 'insights', 'reporting'])]
            score = min(5, len(analysis_skills) + 2) if analysis_skills else 2
            evidence = f"Found {len(analysis_skills)} data analysis skills" if analysis_skills else "Limited data analysis experience"
            return (score, evidence)
        
        if "visualization" in criterion_lower or "bi" in criterion_lower:
            viz_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['power bi', 'tableau', 'visualization', 'dashboard', 'chart', 'plot'])]
            score = min(5, len(viz_skills) + 2) if viz_skills else 2
            evidence = f"Found {len(viz_skills)} visualization/BI skills" if viz_skills else "Limited visualization experience"
            return (score, evidence)
        
        if "sql" in criterion_lower or "database" in criterion_lower:
            db_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['sql', 'database', 'mysql', 'postgres', 'sqlite', 'oracle'])]
            score = min(5, len(db_skills) + 2) if db_skills else 2
            evidence = f"Found {len(db_skills)} SQL/database skills" if db_skills else "Limited SQL experience"
            return (score, evidence)
        
        if "etl" in criterion_lower or "pipeline" in criterion_lower:
            etl_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['etl', 'pipeline', 'data engineering', 'data transformation', 'data integration'])]
            score = min(5, len(etl_skills) + 2) if etl_skills else 1
            evidence = f"Found {len(etl_skills)} ETL/pipeline skills" if etl_skills else "Limited ETL experience"
            return (score, evidence)
        
        if "statistical" in criterion_lower or "statistics" in criterion_lower:
            stats_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['statistics', 'statistical', 'r ', 'python', 'pandas', 'numpy'])]
            score = min(5, len(stats_skills) + 2) if stats_skills else 2
            evidence = f"Found {len(stats_skills)} statistical analysis skills" if stats_skills else "Limited statistical experience"
            return (score, evidence)
    
    elif "ui/ux" in role_category or "designer" in role_category:
        if "design" in criterion_lower:
            design_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['figma', 'sketch', 'adobe', 'design', 'ui', 'ux', 'wireframe', 'prototype'])]
            score = min(5, len(design_skills) + 2) if design_skills else 2
            evidence = f"Found {len(design_skills)} design tool skills" if design_skills else "Limited design experience"
            return (score, evidence)
        
        if "research" in criterion_lower or "user" in criterion_lower:
            research_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['user research', 'usability', 'user testing', 'interview', 'survey'])]
            score = min(5, len(research_skills) + 2) if research_skills else 1
            evidence = f"Found {len(research_skills)} user research skills" if research_skills else "Limited user research experience"
            return (score, evidence)
    
    elif "software engineer" in role_category or "developer" in role_category:
        if "api" in criterion_lower:
            api_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['api', 'rest', 'http', 'endpoint', 'graphql'])]
            score = min(5, len(api_skills) + 2) if api_skills else 2
            evidence = f"Found {len(api_skills)} API-related skills" if api_skills else "Limited API experience"
            return (score, evidence)
        
        if "database" in criterion_lower:
            db_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['sql', 'database', 'mysql', 'postgres', 'mongodb', 'nosql'])]
            score = min(5, len(db_skills) + 2) if db_skills else 2
            evidence = f"Found {len(db_skills)} database skills" if db_skills else "Limited database experience"
            return (score, evidence)
        
        if "microservice" in criterion_lower:
            microservices_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['microservice', 'docker', 'kubernetes', 'container'])]
            score = min(5, len(microservices_skills) + 2) if microservices_skills else 1
            evidence = f"Found {len(microservices_skills)} microservices skills" if microservices_skills else "Limited microservices experience"
            return (score, evidence)
        
        if "testing" in criterion_lower or "ci" in criterion_lower:
            testing_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['test', 'ci/cd', 'jenkins', 'github actions', 'testing', 'qa'])]
            score = min(5, len(testing_skills) + 2) if testing_skills else 1
            evidence = f"Found {len(testing_skills)} testing/CI skills" if testing_skills else "Limited testing/CI experience"
            return (score, evidence)
        
        if "cloud" in criterion_lower or "devops" in criterion_lower:
            cloud_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['aws', 'azure', 'cloud', 'devops', 'terraform', 'gcp'])]
            score = min(5, len(cloud_skills) + 2) if cloud_skills else 1
            evidence = f"Found {len(cloud_skills)} cloud/DevOps skills" if cloud_skills else "Limited cloud/DevOps experience"
            return (score, evidence)
    
    # Generic fallback: check if criterion name appears in skills
    matching_skills = [s.lower() for s in skills if criterion_lower in s.lower() or s.lower() in criterion_lower]
    if matching_skills:
        score = min(5, len(matching_skills) + 2)
        evidence = f"Found {len(matching_skills)} skills matching '{criterion}'"
    else:
        score = 2
        evidence = f"Limited evidence for '{criterion}'"
    
    return (score, evidence)

def judge_candidate_heuristic(merged_json: Dict, role_criteria: Optional[Dict] = None) -> Dict:
    """Fallback heuristic-based judging with role-aware criteria"""
    candidate = merged_json.get("candidate", {})
    job_desc = merged_json.get("job_description", {})
    
    # Get role-specific criteria
    if role_criteria is None:
        role_criteria = generate_role_criteria(job_desc, candidate)
    
    criteria_list = role_criteria.get("criteria", [])
    role_category = role_criteria.get("role_category", "IT Professional")
    
    logger.info(f"Using heuristic scoring for {role_category} role with {len(criteria_list)} criteria")
    
    # Apply heuristics for each criterion based on role
    judge_scores = []
    for crit in criteria_list:
        criterion_name = crit.get("criterion", "")
        score, evidence = _calculate_heuristic_score(criterion_name, merged_json, role_criteria)
        judge_scores.append({
            "criterion": criterion_name,
            "score": score,
            "evidence": evidence
        })
    
    return {
        "judge_scores": judge_scores
    }

def judge_candidate(merged_json: Dict, role_criteria: Optional[Dict] = None) -> Dict:
    """
    Judge candidate using LLM API (OpenAI) with heuristic fallback
    
    Args:
        merged_json: Merged JSON with candidate and job_description data
        role_criteria: Optional pre-generated role criteria (if None, will generate)
    
    Returns:
        Dictionary with judge_scores list
    """
    candidate = merged_json.get("candidate", {})
    job_desc = merged_json.get("job_description", {})
    
    # Generate role criteria if not provided
    if role_criteria is None:
        role_criteria = generate_role_criteria(job_desc, candidate)
    
    # Try OpenAI LLM first if configured
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        prompt, framework_mismatch_detected, mismatch_details, role_criteria = build_judge_prompt(candidate, job_desc, role_criteria)
        result = judge_with_openai(prompt, candidate, job_desc, framework_mismatch_detected, role_criteria)
        
        if result:
            logger.info(f"Using OpenAI LLM for candidate judgment ({role_criteria.get('role_category', 'IT Professional')} role)")
            return result
        else:
            logger.warning("OpenAI LLM failed, falling back to heuristic scoring")
    
    # Fallback to heuristic-based scoring
    logger.info(f"Using heuristic-based scoring for candidate judgment ({role_criteria.get('role_category', 'IT Professional')} role)")
    return judge_candidate_heuristic(merged_json, role_criteria)

