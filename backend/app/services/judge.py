from typing import Dict, List
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
            logger.info("OpenAI client initialized for Judge")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def build_judge_prompt(candidate: Dict, job_desc: Dict) -> str:
    """Build prompt for LLM judge"""
    
    skills = candidate.get("skills_canonical", candidate.get("skills_raw", []))
    experience = candidate.get("experience", [])
    github = candidate.get("github", {})
    education = candidate.get("education", [])
    
    must_have = job_desc.get("must_have", [])
    nice_to_have = job_desc.get("nice_to_have", [])
    jd_text = job_desc.get("jd_text", "")
    jd_title = job_desc.get("title", "")
    
    prompt = f"""You are an expert technical recruiter evaluating a candidate for a software engineering position.

JOB POSITION: {jd_title}

JOB DESCRIPTION:
{jd_text[:2000]}

REQUIRED SKILLS: {', '.join(must_have[:20])}
NICE-TO-HAVE SKILLS: {', '.join(nice_to_have[:20])}

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
    
    prompt += """
Evaluate the candidate on these criteria (0-5 scale, where 0=No evidence, 5=Excellent evidence):

1. APIs: REST API design, HTTP endpoints, API architecture, API security
2. Databases: SQL/NoSQL knowledge, database design, query optimization, data modeling
3. Microservices: Containerization (Docker), orchestration (Kubernetes), service architecture, distributed systems
4. Testing/CI: Unit testing, integration testing, CI/CD pipelines, test automation, quality assurance
5. Cloud/DevOps: AWS/Azure/GCP, infrastructure as code, monitoring, deployment automation
6. Impact: Quantifiable achievements, metrics, business impact, performance improvements

For each criterion:
- Give a score (0-5 integer)
- Provide specific evidence (quote from experience, skill, or GitHub activity)
- Be specific and cite actual examples from the profile

Respond ONLY with valid JSON in this exact format (no markdown, no code blocks):
{
  "judge_scores": [
    {
      "criterion": "APIs",
      "score": 4,
      "evidence": "Built REST APIs with Spring Boot at Company X, reduced API latency by 30%"
    },
    {
      "criterion": "Databases",
      "score": 3,
      "evidence": "Experience with PostgreSQL and MongoDB mentioned in skills"
    }
  ]
}
"""
    
    return prompt

def judge_with_openai(prompt: str) -> Dict:
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
        
        logger.info(f"Successfully received judge scores from OpenAI: {len(result.get('judge_scores', []))} criteria")
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return None

def judge_candidate_heuristic(merged_json: Dict) -> Dict:
    """Fallback heuristic-based judging (original MVP code)"""
    candidate = merged_json.get("candidate", {})
    job_desc = merged_json.get("job_description", {})
    
    # Extract some basic info for placeholder scoring
    skills = candidate.get("skills_raw", [])
    experience = candidate.get("experience", [])
    github = candidate.get("github", {})
    
    # Generate placeholder scores based on simple heuristics
    judge_scores = []
    
    # Check for API-related skills
    api_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['api', 'rest', 'http', 'endpoint'])]
    api_score = min(5, len(api_skills) + 2) if api_skills else 2
    judge_scores.append({
        "criterion": "APIs",
        "score": api_score,
        "evidence": f"Found {len(api_skills)} API-related skills in profile" if api_skills else "Limited API experience"
    })
    
    # Check for database skills
    db_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['sql', 'database', 'mysql', 'postgres', 'mongodb'])]
    db_score = min(5, len(db_skills) + 2) if db_skills else 2
    judge_scores.append({
        "criterion": "Databases",
        "score": db_score,
        "evidence": f"Found {len(db_skills)} database-related skills" if db_skills else "Limited database experience"
    })
    
    # Check for microservices
    microservices_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['microservice', 'docker', 'kubernetes', 'container'])]
    microservices_score = min(5, len(microservices_skills) + 2) if microservices_skills else 1
    judge_scores.append({
        "criterion": "Microservices",
        "score": microservices_score,
        "evidence": f"Found {len(microservices_skills)} microservices-related skills" if microservices_skills else "Limited microservices experience"
    })
    
    # Check for testing/CI
    testing_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['test', 'ci/cd', 'jenkins', 'github actions'])]
    testing_score = min(5, len(testing_skills) + 2) if testing_skills else 1
    judge_scores.append({
        "criterion": "Testing/CI",
        "score": testing_score,
        "evidence": f"Found {len(testing_skills)} testing/CI-related skills" if testing_skills else "Limited testing/CI experience"
    })
    
    # Check for cloud/devops
    cloud_skills = [s.lower() for s in skills if any(term in s.lower() for term in ['aws', 'azure', 'cloud', 'devops', 'terraform'])]
    cloud_score = min(5, len(cloud_skills) + 2) if cloud_skills else 1
    judge_scores.append({
        "criterion": "Cloud/DevOps",
        "score": cloud_score,
        "evidence": f"Found {len(cloud_skills)} cloud/DevOps-related skills" if cloud_skills else "Limited cloud/DevOps experience"
    })
    
    # Check for impact/metrics (from experience highlights)
    impact_score = 2
    for exp in experience:
        highlights = exp.get("highlights", [])
        for highlight in highlights:
            if any(term in highlight.lower() for term in ['reduced', 'improved', 'increased', 'decreased', '%', 'by']):
                impact_score = min(5, impact_score + 1)
                break
    
    judge_scores.append({
        "criterion": "Impact",
        "score": impact_score,
        "evidence": "Found metrics/impact statements in experience" if impact_score > 2 else "Limited impact metrics"
    })
    
    return {
        "judge_scores": judge_scores
    }

def judge_candidate(merged_json: Dict) -> Dict:
    """
    Judge candidate using LLM API (OpenAI) with heuristic fallback
    
    Args:
        merged_json: Merged JSON with candidate and job_description data
    
    Returns:
        Dictionary with judge_scores list
    """
    candidate = merged_json.get("candidate", {})
    job_desc = merged_json.get("job_description", {})
    
    # Try OpenAI LLM first if configured
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        prompt = build_judge_prompt(candidate, job_desc)
        result = judge_with_openai(prompt)
        
        if result:
            logger.info("Using OpenAI LLM for candidate judgment")
            return result
        else:
            logger.warning("OpenAI LLM failed, falling back to heuristic scoring")
    
    # Fallback to heuristic-based scoring
    logger.info("Using heuristic-based scoring for candidate judgment")
    return judge_candidate_heuristic(merged_json)

