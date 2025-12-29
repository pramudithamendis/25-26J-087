"""
Skill categorization module.

Dynamically categorizes skills into:
- technical: Programming languages, frameworks, tools (SQL, Power BI, Python, etc.)
- soft: Communication, teamwork, leadership, etc.
- work_arrangement: Remote work, on-site, hybrid, etc.
- concept: Data analysis, data insights, business acumen, etc.
"""

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
            logger.info("OpenAI client initialized for skill categorization")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def categorize_skill(skill: str) -> str:
    """
    Categorize a single skill as: technical, soft, work_arrangement, or concept.
    
    Uses LLM for dynamic categorization.
    
    Args:
        skill: Skill string to categorize
    
    Returns:
        Category: "technical", "soft", "work_arrangement", or "concept"
    """
    if not skill or not skill.strip():
        return "concept"  # Default for empty skills
    
    # Quick heuristic check first (fast path)
    skill_lower = skill.lower().strip()
    
    # Work arrangements
    work_keywords = ["remote work", "on-site", "onsite", "hybrid", "work from home", "wfh"]
    if any(keyword in skill_lower for keyword in work_keywords):
        return "work_arrangement"
    
    # Soft skills (common patterns)
    soft_keywords = ["communication", "teamwork", "leadership", "problem solving", 
                     "critical thinking", "time management", "collaboration"]
    if any(keyword in skill_lower for keyword in soft_keywords):
        return "soft"
    
    # If it's a known technical skill pattern, return technical
    # This is a fast path - LLM will handle ambiguous cases
    technical_patterns = ["sql", "python", "java", "javascript", "react", "angular", 
                         "vue", "flutter", "dart", "power bi", "excel", "aws", 
                         "docker", "kubernetes", "git", "rest api", "graphql"]
    if any(pattern in skill_lower for pattern in technical_patterns):
        return "technical"
    
    # Conceptual skills patterns (should use semantic matching, not exact match)
    # These are concepts that can be matched semantically to related technical skills
    concept_patterns = [
        # Data processing concepts
        "etl", "etl process", "etl processes", "extract transform load",
        "data pipeline", "data pipelines", "data processing",
        "data transformation", "data integration",
        
        # Database concepts
        "relational database", "relational databases", "database design",
        "database modeling", "data modeling", "schema design",
        
        # Analytics concepts
        "data analysis", "data analytics", "data insights", 
        "business intelligence", "data warehousing", "data mining",
        "predictive analytics", "statistical analysis",
        
        # General methodology concepts
        "agile methodology", "scrum", "devops", "ci/cd",
        "test driven development", "tdd", "bdd"
    ]
    
    # Check if skill contains any concept pattern
    if any(pattern in skill_lower for pattern in concept_patterns):
        return "concept"
    
    # For ambiguous cases, use LLM
    return categorize_skill_with_llm(skill)

def categorize_skill_with_llm(skill: str) -> str:
    """
    Use LLM to categorize a skill when heuristics are insufficient.
    
    Args:
        skill: Skill string to categorize
    
    Returns:
        Category: "technical", "soft", "work_arrangement", or "concept"
    """
    client = get_openai_client()
    
    if not client:
        # Fallback: assume technical if it looks like a technology name
        if len(skill.split()) <= 3 and not any(word in skill.lower() for word in ["skill", "ability", "work"]):
            return "technical"
        return "concept"
    
    prompt = f"""Categorize this skill into exactly one category:

Skill: "{skill}"

Categories:
- "technical": Programming languages, frameworks, tools, technologies (e.g., SQL, Python, Power BI, React, AWS, Docker)
- "soft": Interpersonal skills, communication, teamwork, leadership (e.g., communication skills, teamwork, problem-solving)
- "work_arrangement": Work location/arrangement preferences (e.g., remote work, on-site, hybrid)
- "concept": General concepts, methodologies, business terms (e.g., data analysis, data insights, business acumen, agile)

Return ONLY the category name (technical, soft, work_arrangement, or concept) as a JSON string:
{{"category": "technical"}}
"""
    
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert at categorizing skills. Return only the category name as JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=50
        )
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        category = result.get("category", "concept")
        
        # Validate category
        if category not in ["technical", "soft", "work_arrangement", "concept"]:
            logger.warning(f"Invalid category '{category}' for skill '{skill}', defaulting to 'concept'")
            return "concept"
        
        return category
        
    except Exception as e:
        logger.warning(f"Error categorizing skill '{skill}' with LLM: {str(e)}, defaulting to 'concept'")
        return "concept"

def categorize_skills_batch(skills: List[str]) -> Dict[str, List[str]]:
    """
    Categorize a batch of skills efficiently.
    
    Args:
        skills: List of skill strings
    
    Returns:
        Dictionary with keys: technical, soft, work_arrangement, concept
        Each value is a list of skills in that category
    """
    if not skills:
        return {
            "technical": [],
            "soft": [],
            "work_arrangement": [],
            "concept": []
        }
    
    categorized = {
        "technical": [],
        "soft": [],
        "work_arrangement": [],
        "concept": []
    }
    
    for skill in skills:
        if not skill or not skill.strip():
            continue
        category = categorize_skill(skill)
        categorized[category].append(skill)
    
    return categorized

def filter_technical_skills(skills: List[str]) -> List[str]:
    """
    Filter a list of skills to only include technical skills.
    
    Args:
        skills: List of skill strings
    
    Returns:
        List of only technical skills
    """
    categorized = categorize_skills_batch(skills)
    return categorized["technical"]

def is_technical_skill(skill: str) -> bool:
    """
    Check if a skill is a technical skill.
    
    Args:
        skill: Skill string to check
    
    Returns:
        True if technical, False otherwise
    """
    return categorize_skill(skill) == "technical"

