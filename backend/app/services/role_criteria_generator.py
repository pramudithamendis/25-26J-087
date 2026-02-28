"""
Role-aware criteria generator for candidate evaluation.

Dynamically generates role-specific evaluation criteria using LLM analysis of job descriptions.
Supports all IT roles: Data Analyst, Software Engineer, UI/UX Designer, Data Scientist, DevOps, QA, etc.
"""

from typing import Dict, List, Optional
from app.config import settings
import logging
import json
import hashlib

logger = logging.getLogger(__name__)

_openai_client = None
_criteria_cache = {}  # In-memory cache: {cache_key: criteria_dict}

def get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for role criteria generation")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def _generate_cache_key(job_desc: Dict) -> str:
    """
    Generate cache key from job description.
    
    Uses job title and must-have skills to create a stable cache key.
    """
    jd_title = job_desc.get("title", "").lower().strip()
    must_have = job_desc.get("must_have", [])
    # Use first 5 must-have skills for cache key
    skills_key = "|".join(sorted([s.lower().strip() for s in must_have[:5]]))
    cache_string = f"{jd_title}|||{skills_key}"
    return hashlib.md5(cache_string.encode()).hexdigest()

def generate_role_criteria(job_desc: Dict, candidate: Dict = None, use_cache: bool = True) -> Dict:
    """
    Generate role-specific evaluation criteria from job description.
    
    Uses LLM to analyze job description and extract appropriate evaluation criteria
    for the specific role (Data Analyst, Software Engineer, UI/UX, etc.).
    
    Args:
        job_desc: Dictionary with job description data (title, must_have, nice_to_have, jd_text)
        candidate: Optional candidate data (for context, not currently used)
        use_cache: Whether to use cached criteria if available
    
    Returns:
        Dictionary with:
        {
            "role_category": "Data Analyst" | "Software Engineer" | "UI/UX Designer" | etc.,
            "criteria": [
                {
                    "criterion": "Data Analysis",
                    "description": "Ability to analyze data, identify patterns, generate insights"
                },
                ...
            ],
            "total_criteria": 6
        }
    """
    client = get_openai_client()
    
    if not client:
        logger.warning("OpenAI client not available, using default criteria")
        return _get_default_criteria()
    
    # Check cache first
    if use_cache:
        cache_key = _generate_cache_key(job_desc)
        if cache_key in _criteria_cache:
            logger.info(f"Using cached criteria for role category")
            return _criteria_cache[cache_key]
    
    # Extract job description information
    jd_title = job_desc.get("title", "")
    jd_text = job_desc.get("jd_text", "")
    must_have = job_desc.get("must_have", [])
    nice_to_have = job_desc.get("nice_to_have", [])
    
    # Build prompt for LLM
    prompt = f"""Analyze this job description and generate appropriate evaluation criteria for candidate assessment.

JOB DESCRIPTION:
Title: {jd_title}
Description: {jd_text[:1500]}
Required Skills: {', '.join(must_have[:15])}
Nice-to-Have Skills: {', '.join(nice_to_have[:10])}

Your task:
1. Identify the primary role category (e.g., Data Analyst, Software Engineer, UI/UX Designer, DevOps Engineer, Data Scientist, QA Engineer, Product Manager, etc.)
2. Generate 4-8 evaluation criteria specific to this role
3. ALWAYS include "Impact" as one criterion (quantifiable achievements, metrics, business impact, performance improvements)
4. For each criterion, provide a clear description of what to evaluate
5. Ensure criteria are measurable and evidence-based

Role-specific examples:
- Data Analyst: Data Analysis, Data Visualization, SQL/BI Tools, Statistical Analysis, ETL Processes, Business Intelligence, Impact
- Software Engineer: APIs, Databases, Architecture/Design Patterns, Testing/CI, Cloud/DevOps, Code Quality, Impact
- UI/UX Designer: Design Tools, Prototyping, User Research, Wireframing, Visual Design, Interaction Design, Impact
- Data Scientist: Machine Learning, Statistical Modeling, Data Analysis, Python/R, Research & Experimentation, Impact
- DevOps Engineer: CI/CD, Infrastructure as Code, Monitoring & Observability, Cloud Platforms, Automation, Security, Impact
- QA Engineer: Test Automation, Test Planning, Bug Tracking, Quality Assurance, Testing Tools, Impact

IMPORTANT:
- Generate criteria that are RELEVANT to the specific role
- Do NOT include criteria that don't apply (e.g., don't include "Microservices" for Data Analyst roles)
- Make criteria specific and measurable
- Always include "Impact" as the last criterion

Return your analysis as JSON with this exact structure:
{{
  "role_category": "Role Name",
  "criteria": [
    {{
      "criterion": "Criterion Name",
      "description": "Clear description of what to evaluate for this criterion"
    }},
    {{
      "criterion": "Impact",
      "description": "Quantifiable achievements, metrics, business impact, performance improvements"
    }}
  ]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in IT recruitment and role analysis. Generate appropriate evaluation criteria for candidate assessment based on job descriptions. Always respond with valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            max_tokens=1500
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
        if "role_category" not in result or "criteria" not in result:
            logger.warning("Invalid criteria structure from LLM, using default")
            return _get_default_criteria()
        
        # Ensure Impact is included
        criteria_list = result.get("criteria", [])
        has_impact = any(c.get("criterion", "").lower() == "impact" for c in criteria_list)
        if not has_impact:
            criteria_list.append({
                "criterion": "Impact",
                "description": "Quantifiable achievements, metrics, business impact, performance improvements"
            })
        
        # Validate criteria count (4-8)
        if len(criteria_list) < 4:
            logger.warning(f"Too few criteria ({len(criteria_list)}), using default")
            return _get_default_criteria()
        if len(criteria_list) > 8:
            logger.warning(f"Too many criteria ({len(criteria_list)}), truncating to 8")
            criteria_list = criteria_list[:8]
        
        result["criteria"] = criteria_list
        result["total_criteria"] = len(criteria_list)
        
        # Cache the result
        if use_cache:
            cache_key = _generate_cache_key(job_desc)
            _criteria_cache[cache_key] = result
            logger.info(f"Generated and cached criteria for role: {result.get('role_category')} ({len(criteria_list)} criteria)")
        
        logger.info(f"Generated criteria for role: {result.get('role_category')} with {len(criteria_list)} criteria")
        logger.debug(f"Criteria: {[c.get('criterion') for c in criteria_list]}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from criteria generation: {str(e)}")
        logger.warning("Using default criteria")
        return _get_default_criteria()
    except Exception as e:
        logger.error(f"Error generating role criteria: {str(e)}")
        logger.warning("Using default criteria")
        return _get_default_criteria()

def _get_default_criteria() -> Dict:
    """
    Get default criteria (software engineering) as fallback.
    
    Returns:
        Default criteria structure matching software engineering role
    """
    return {
        "role_category": "Software Engineer",
        "criteria": [
            {
                "criterion": "APIs",
                "description": "REST API design, HTTP endpoints, API architecture, API security"
            },
            {
                "criterion": "Databases",
                "description": "SQL/NoSQL knowledge, database design, query optimization, data modeling"
            },
            {
                "criterion": "Microservices",
                "description": "Containerization (Docker), orchestration (Kubernetes), service architecture, distributed systems"
            },
            {
                "criterion": "Testing/CI",
                "description": "Unit testing, integration testing, CI/CD pipelines, test automation, quality assurance"
            },
            {
                "criterion": "Cloud/DevOps",
                "description": "AWS/Azure/GCP, infrastructure as code, monitoring, deployment automation"
            },
            {
                "criterion": "Impact",
                "description": "Quantifiable achievements, metrics, business impact, performance improvements"
            }
        ],
        "total_criteria": 6
    }

def clear_criteria_cache():
    """Clear the criteria cache (useful for testing or when criteria need to be regenerated)"""
    global _criteria_cache
    _criteria_cache = {}
    logger.info("Criteria cache cleared")

