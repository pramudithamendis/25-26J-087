from typing import Dict, List
from datetime import datetime, timedelta

def aggregate_scores(
    semantic_features: Dict,
    judge_scores: Dict,
    github_info: Dict,
    experience_info: List[Dict],
    merged_json: Dict
) -> Dict:
    """
    Aggregate all scores into a 0-100 total score
    
    Combines:
    - Semantic fit: 30 pts (from similarity scores)
    - Role competency: 30 pts (from judge scores, average * 6)
    - Experience recency: 15 pts (time-decay on last 3 years)
    - GitHub evidence: 15 pts (activity, relevance, quality)
    - Bonus/Malus: ±10 pts (awards, contradictions, keyword stuffing)
    
    Args:
        semantic_features: Dictionary with similarity scores
        judge_scores: Dictionary with judge_scores list
        github_info: Dictionary with GitHub data
        experience_info: List of experience entries
        merged_json: Full merged JSON for context
    
    Returns:
        Dictionary with total_score and breakdown
    """
    # 1. Semantic fit (30 pts max)
    sim_profile = semantic_features.get("sim_profile_to_jd", 0.0)
    sim_github = semantic_features.get("sim_github_to_jd", 0.0)
    semantic_fit = (sim_profile * 0.7 + sim_github * 0.3) * 30
    semantic_fit = round(semantic_fit, 1)
    
    # 2. Role competency (30 pts max)
    # Average judge scores and scale to 30
    scores_list = judge_scores.get("judge_scores", [])
    if scores_list:
        avg_score = sum(score["score"] for score in scores_list) / len(scores_list)
        role_competency = (avg_score / 5.0) * 30  # Scale from 0-5 to 0-30
    else:
        role_competency = 0
    role_competency = round(role_competency, 1)
    
    # 3. Experience recency (15 pts max)
    # Time-decay: more recent experience = higher score
    experience_recency = calculate_experience_recency(experience_info)
    experience_recency = round(experience_recency, 1)
    
    # 4. GitHub evidence (15 pts max)
    github_evidence = calculate_github_score(github_info)
    github_evidence = round(github_evidence, 1)
    
    # 5. Bonus/Malus (±10 pts)
    bonus_malus = calculate_bonus_malus(merged_json)
    bonus_malus = round(bonus_malus, 1)
    
    # Calculate total score
    total_score = semantic_fit + role_competency + experience_recency + github_evidence + bonus_malus
    
    # Clamp to 0-100
    total_score = max(0, min(100, round(total_score)))
    
    return {
        "total_score": total_score,
        "breakdown": {
            "semantic_fit": semantic_fit,
            "role_competency": role_competency,
            "experience_recency": experience_recency,
            "github_evidence": github_evidence,
            "bonus_malus": bonus_malus
        }
    }

def calculate_experience_recency(experience: List[Dict]) -> float:
    """Calculate experience recency score (0-15 pts)"""
    if not experience:
        return 0.0
    
    now = datetime.now()
    three_years_ago = now - timedelta(days=3*365)
    
    total_months = 0
    recent_months = 0
    
    for exp in experience:
        start_str = exp.get("start", "")
        end_str = exp.get("end", "")
        
        if not start_str:
            continue
        
        # Parse dates (YYYY-MM format)
        try:
            start_date = datetime.strptime(start_str[:7], "%Y-%m")
            end_date = datetime.strptime(end_str[:7], "%Y-%m") if end_str else now
            
            # Calculate months
            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            total_months += months
            
            # Check if recent (last 3 years)
            if end_date >= three_years_ago:
                recent_months += months
        except:
            continue
    
    if total_months == 0:
        return 0.0
    
    # Score based on percentage of recent experience
    recent_ratio = recent_months / total_months if total_months > 0 else 0
    score = recent_ratio * 15
    
    return score

def calculate_github_score(github_info: Dict) -> float:
    """Calculate GitHub evidence score (0-15 pts)"""
    if not github_info:
        return 0.0
    
    repos = github_info.get("repos", [])
    commits = github_info.get("commits_last_12m", 0)
    prs = github_info.get("external_prs_merged", 0)
    
    score = 0.0
    
    # Repos: up to 5 pts
    if repos:
        repo_count = len(repos)
        score += min(5, repo_count * 0.5)
    
    # Commits: up to 5 pts (100+ commits = 5 pts)
    if commits > 0:
        score += min(5, (commits / 100.0) * 5)
    
    # External PRs: up to 5 pts (5+ PRs = 5 pts)
    if prs > 0:
        score += min(5, prs)
    
    return score

def calculate_bonus_malus(merged_json: Dict) -> float:
    """Calculate bonus/malus score (±10 pts)"""
    score = 0.0
    
    candidate = merged_json.get("candidate", {})
    
    # Bonus: Certifications (+1 pt each, max +5)
    certifications = candidate.get("certifications", [])
    score += min(5, len(certifications))
    
    # Bonus: LinkedIn endorsements (+0.5 pt per 5 endorsements, max +3)
    linkedin = candidate.get("linkedin", {})
    endorsements = linkedin.get("endorsements", [])
    score += min(3, len(endorsements) * 0.1)
    
    # Malus: Check for potential keyword stuffing (too many skills)
    skills = candidate.get("skills_raw", [])
    if len(skills) > 50:  # Suspiciously high
        score -= 2
    
    # Malus: Check for contradictions (future: implement actual contradiction detection)
    # For now, no malus for contradictions
    
    # Clamp to ±10
    score = max(-10, min(10, score))
    
    return score

