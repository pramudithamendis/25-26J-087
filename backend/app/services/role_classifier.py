from typing import Dict, List

# Role taxonomy
ROLE_TAXONOMY = [
    "Backend Engineer",
    "Frontend Engineer",
    "Full-Stack Engineer",
    "Data Scientist",
    "DevOps Engineer",
    "Mobile Developer",
    "QA Engineer",
    "Software Architect"
]

# Role skill patterns (simple rule-based matching)
ROLE_PATTERNS = {
    "Backend Engineer": [
        "java", "spring", "python", "node.js", "api", "rest", "microservices",
        "database", "sql", "postgresql", "mongodb", "server", "backend"
    ],
    "Frontend Engineer": [
        "react", "vue", "angular", "javascript", "typescript", "html", "css",
        "frontend", "ui", "ux", "webpack", "npm"
    ],
    "Full-Stack Engineer": [
        "full stack", "fullstack", "mern", "mean", "react", "node.js",
        "javascript", "python", "django", "flask"
    ],
    "Data Scientist": [
        "python", "r", "machine learning", "ml", "data science", "pandas",
        "numpy", "tensorflow", "pytorch", "jupyter", "sql", "statistics"
    ],
    "DevOps Engineer": [
        "docker", "kubernetes", "ci/cd", "jenkins", "terraform", "aws",
        "azure", "devops", "infrastructure", "monitoring", "ansible"
    ],
    "Mobile Developer": [
        "android", "ios", "swift", "kotlin", "react native", "flutter",
        "mobile", "app development"
    ],
    "QA Engineer": [
        "testing", "qa", "selenium", "test automation", "junit", "pytest",
        "quality assurance", "manual testing"
    ],
    "Software Architect": [
        "architecture", "system design", "microservices", "distributed systems",
        "scalability", "aws", "azure", "kubernetes", "docker"
    ]
}

def classify_roles(canonical_skills: List[str], jd_info: Dict) -> List[Dict]:
    """
    Classify candidate into role categories
    
    Uses simple rule-based matching: if skills match role patterns → assign role
    
    Args:
        canonical_skills: List of normalized skill names
        jd_info: Job description information
    
    Returns:
        List of role predictions with similarity scores
    """
    if not canonical_skills:
        return []
    
    # Convert skills to lowercase for matching
    skills_lower = [s.lower() for s in canonical_skills]
    
    # Also check JD title and requirements
    jd_title = jd_info.get("title", "").lower()
    jd_must_have = [s.lower() for s in jd_info.get("must_have", [])]
    jd_nice_to_have = [s.lower() for s in jd_info.get("nice_to_have", [])]
    all_jd_skills = jd_must_have + jd_nice_to_have
    
    role_scores = {}
    
    # Score each role based on skill matches
    for role, patterns in ROLE_PATTERNS.items():
        score = 0.0
        
        # Check skill matches
        for pattern in patterns:
            # Check in candidate skills
            if any(pattern in skill for skill in skills_lower):
                score += 1.0
            
            # Check in JD skills
            if any(pattern in skill for skill in all_jd_skills):
                score += 0.5
            
            # Check in JD title
            if pattern in jd_title:
                score += 0.5
        
        # Normalize score (max possible = len(patterns) * 2.0)
        max_score = len(patterns) * 2.0
        normalized_score = score / max_score if max_score > 0 else 0.0
        
        if normalized_score > 0:
            role_scores[role] = normalized_score
    
    # Sort by score (descending)
    sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Build result list
    role_predictions = []
    for role, similarity in sorted_roles:
        # Only include roles above threshold (0.1 = 10% match)
        if similarity >= 0.1:
            # Determine reason
            if similarity >= 0.5:
                reason = "Strong skill match with role requirements"
            elif similarity >= 0.3:
                reason = "Moderate skill match with role requirements"
            else:
                reason = "Partial skill match"
            
            role_predictions.append({
                "role": role,
                "similarity": round(similarity, 2),
                "reason": reason
            })
    
    return role_predictions

