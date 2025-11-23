from typing import List, Dict

# Skill mapping dictionary: maps variations to canonical skill names
SKILL_MAP: Dict[str, str] = {
    # Java variations
    "server-side java": "Java",
    "java programming": "Java",
    "java development": "Java",
    "java ee": "Java",
    "java se": "Java",
    
    # Spring variations
    "spring": "Spring Boot",
    "spring framework": "Spring Boot",
    "spring mvc": "Spring Boot",
    "spring core": "Spring Boot",
    
    # API variations
    "http endpoints": "REST APIs",
    "rest api": "REST APIs",
    "restful api": "REST APIs",
    "rest services": "REST APIs",
    "api development": "REST APIs",
    "api design": "REST APIs",
    
    # Database variations
    "sql database": "SQL",
    "mysql": "SQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "nosql": "NoSQL",
    "mongodb": "MongoDB",
    
    # Frontend variations
    "react.js": "React",
    "reactjs": "React",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "angular.js": "Angular",
    "angularjs": "Angular",
    
    # Cloud variations
    "aws cloud": "AWS",
    "amazon web services": "AWS",
    "azure cloud": "Azure",
    "microsoft azure": "Azure",
    "gcp": "Google Cloud",
    "google cloud platform": "Google Cloud",
    
    # DevOps variations
    "docker containers": "Docker",
    "kubernetes orchestration": "Kubernetes",
    "k8s": "Kubernetes",
    "ci/cd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous deployment": "CI/CD",
    
    # Testing variations
    "unit testing": "Testing",
    "integration testing": "Testing",
    "test automation": "Testing",
    "qa": "Testing",
    
    # Version control
    "git version control": "Git",
    "github": "Git",
    "gitlab": "Git",
    
    # Python variations
    "python programming": "Python",
    "python development": "Python",
    
    # JavaScript variations
    "javascript": "JavaScript",
    "js": "JavaScript",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    
    # Microservices
    "microservices architecture": "Microservices",
    "microservice": "Microservices",
}

def normalize_skills(skills_raw: List[str]) -> List[str]:
    """
    Normalize skill names to canonical forms
    
    Maps messy skill phrases to canonical skill names using SKILL_MAP,
    handles case-insensitive matching, and deduplicates
    
    Args:
        skills_raw: List of raw skill strings from CV/LinkedIn
    
    Returns:
        List of canonical skill names (deduplicated)
    """
    if not skills_raw:
        return []

    canonical_skills = []
    
    for skill in skills_raw:
        if not skill:
            continue
        
        # Normalize: lowercase, strip whitespace
        skill_normalized = skill.lower().strip()
        
        # Remove common prefixes/suffixes
        skill_normalized = remove_common_prefixes(skill_normalized)
        
        # Try exact match in SKILL_MAP
        if skill_normalized in SKILL_MAP:
            canonical = SKILL_MAP[skill_normalized]
            if canonical not in canonical_skills:
                canonical_skills.append(canonical)
            continue
        
        # Try fuzzy matching (contains check)
        matched = False
        for key, value in SKILL_MAP.items():
            if key in skill_normalized or skill_normalized in key:
                canonical = value
                if canonical not in canonical_skills:
                    canonical_skills.append(canonical)
                matched = True
                break
        
        # If no match found, use original (capitalized properly)
        if not matched:
            # Capitalize first letter of each word
            canonical = ' '.join(word.capitalize() for word in skill_normalized.split())
            if canonical not in canonical_skills:
                canonical_skills.append(canonical)
    
    # Sort for consistency
    canonical_skills.sort()
    
    return canonical_skills

def remove_common_prefixes(skill: str) -> str:
    """Remove common prefixes from skill names"""
    prefixes = [
        "experience with ",
        "knowledge of ",
        "proficient in ",
        "strong ",
        "expert in ",
        "skilled in ",
        "familiar with ",
    ]
    
    skill_lower = skill.lower()
    for prefix in prefixes:
        if skill_lower.startswith(prefix):
            skill = skill[len(prefix):].strip()
            break
    
    return skill

