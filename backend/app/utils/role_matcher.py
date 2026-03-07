"""
Role Matching Utility

Compares job titles with predicted roles to determine match quality,
seniority alignment, and calculate role match bonuses.
"""

from typing import Dict, List, Optional
import logging
from app.services.seniority_detector import detect_seniority

logger = logging.getLogger(__name__)


def calculate_role_match(
    job_title: str,
    role_predictions: List[Dict],
    role_similarity_threshold: float = 0.7
) -> Dict:
    """
    Calculate role match quality between job title and predicted roles.
    
    Args:
        job_title: The job title from the job description
        role_predictions: List of predicted roles with similarity scores
        role_similarity_threshold: Minimum similarity to consider a match (default 0.7)
    
    Returns:
        Dictionary with:
        - match_type: str (exact_match, overqualified, underqualified, role_mismatch, no_predictions)
        - similarity: float (0.0-1.0) - best similarity score
        - seniority_diff: int (predicted_level - job_level)
        - bonus: float (calculated bonus points, -5 to +5)
        - matched_role: str (the matched predicted role name)
        - job_level: int
        - predicted_level: int
    """
    if not job_title or not job_title.strip():
        logger.warning("Empty job title provided")
        return _no_match_result()
    
    if not role_predictions or len(role_predictions) == 0:
        logger.info("No role predictions available")
        return _no_match_result()
    
    # Detect seniority for job title
    job_seniority = detect_seniority(job_title)
    job_level = job_seniority["level"]
    job_base_role = job_seniority["base_role"]
    
    logger.info(f"Job title '{job_title}': level={job_level}, base_role='{job_base_role}'")
    
    # Find best matching predicted role
    best_match = None
    best_similarity = 0.0
    
    for pred_role in role_predictions:
        pred_role_name = pred_role.get("role", "")
        pred_similarity = pred_role.get("similarity", 0.0)
        
        if not pred_role_name or pred_similarity < role_similarity_threshold:
            continue
        
        # Detect seniority for predicted role
        pred_seniority = detect_seniority(pred_role_name)
        pred_level = pred_seniority["level"]
        pred_base_role = pred_seniority["base_role"]
        
        # Calculate base role similarity (simple string matching for now)
        base_role_similarity = _calculate_base_role_similarity(job_base_role, pred_base_role)
        
        # Combined similarity: use predicted role similarity weighted with base role match
        combined_similarity = (pred_similarity * 0.7) + (base_role_similarity * 0.3)
        
        if combined_similarity > best_similarity:
            best_similarity = combined_similarity
            best_match = {
                "role_name": pred_role_name,
                "similarity": pred_similarity,
                "base_role": pred_base_role,
                "level": pred_level,
                "combined_similarity": combined_similarity
            }
    
    if not best_match:
        logger.info(f"No role prediction met similarity threshold ({role_similarity_threshold})")
        return _no_match_result()
    
    # Determine match type
    seniority_diff = best_match["level"] - job_level
    match_type = _determine_match_type(seniority_diff, best_match["combined_similarity"])
    
    # Calculate bonus
    bonus = _calculate_bonus(match_type, best_match["combined_similarity"], seniority_diff)
    
    result = {
        "match_type": match_type,
        "similarity": round(best_match["combined_similarity"], 2),
        "seniority_diff": seniority_diff,
        "bonus": round(bonus, 1),
        "matched_role": best_match["role_name"],
        "job_level": job_level,
        "predicted_level": best_match["level"],
        "job_base_role": job_base_role,
        "predicted_base_role": best_match["base_role"]
    }
    
    logger.info(f"Role match: type={match_type}, similarity={result['similarity']:.2f}, "
                f"seniority_diff={seniority_diff}, bonus={bonus:.1f}")
    
    return result


def _calculate_base_role_similarity(role1: str, role2: str) -> float:
    """
    Calculate similarity between two base role names.
    
    Uses simple string matching - can be enhanced with semantic similarity later.
    
    Args:
        role1: First role name
        role2: Second role name
    
    Returns:
        Similarity score (0.0-1.0)
    """
    if not role1 or not role2:
        return 0.0
    
    role1_lower = role1.lower().strip()
    role2_lower = role2.lower().strip()
    
    # Exact match
    if role1_lower == role2_lower:
        return 1.0
    
    # One contains the other
    if role1_lower in role2_lower or role2_lower in role1_lower:
        return 0.8
    
    # Word overlap
    words1 = set(role1_lower.split())
    words2 = set(role2_lower.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    jaccard_similarity = len(intersection) / len(union)
    return jaccard_similarity


def _determine_match_type(seniority_diff: int, similarity: float) -> str:
    """
    Determine the type of role match based on seniority difference and similarity.
    
    Args:
        seniority_diff: predicted_level - job_level
        similarity: Combined similarity score
    
    Returns:
        Match type string
    """
    if similarity < 0.5:
        return "role_mismatch"
    
    if seniority_diff > 0:
        return "overqualified"
    elif seniority_diff < 0:
        return "underqualified"
    else:
        return "exact_match"


def _calculate_bonus(match_type: str, similarity: float, seniority_diff: int) -> float:
    """
    Calculate role match bonus based on match type and similarity.
    
    Bonus ranges from -5 to +5 points.
    
    Args:
        match_type: Type of match (exact_match, overqualified, underqualified, role_mismatch)
        similarity: Combined similarity score (0.0-1.0)
        seniority_diff: Difference in seniority levels
    
    Returns:
        Bonus points (-5 to +5)
    """
    if match_type == "role_mismatch":
        # Penalty for role mismatch
        return -2.0
    
    if match_type == "overqualified":
        # Positive bonus for overqualified candidates
        if similarity >= 0.8:
            return 5.0
        elif similarity >= 0.7:
            return 3.0
        else:
            return 2.0
    
    if match_type == "exact_match":
        # Moderate bonus for exact matches
        if similarity >= 0.8:
            return 3.0
        elif similarity >= 0.7:
            return 2.0
        else:
            return 1.0
    
    if match_type == "underqualified":
        # Penalty for underqualified candidates
        if abs(seniority_diff) >= 2:
            return -5.0
        elif abs(seniority_diff) == 1:
            return -3.0
        else:
            return -2.0
    
    return 0.0


def _no_match_result() -> Dict:
    """Return default result when no match is found."""
    return {
        "match_type": "no_predictions",
        "similarity": 0.0,
        "seniority_diff": 0,
        "bonus": 0.0,
        "matched_role": "",
        "job_level": 2,  # Default to mid-level
        "predicted_level": 2,
        "job_base_role": "",
        "predicted_base_role": ""
    }


def get_adjusted_threshold(
    total_score: int,
    role_match: Dict,
    default_selected: int = 70,
    default_review: int = 60
) -> Dict[str, int]:
    """
    Get adjusted decision thresholds based on role match quality.
    
    Args:
        total_score: Current total score
        role_match: Role match result from calculate_role_match()
        default_selected: Default threshold for "Proceed" (default 70)
        default_review: Default threshold for "Review" (default 60)
    
    Returns:
        Dictionary with adjusted thresholds:
        - selected_threshold: Adjusted threshold for "Proceed"
        - review_threshold: Adjusted threshold for "Review"
        - adjustment_applied: Whether adjustment was made
    """
    match_type = role_match.get("match_type", "no_predictions")
    similarity = role_match.get("similarity", 0.0)
    seniority_diff = role_match.get("seniority_diff", 0)
    
    # No adjustments if no match
    if match_type in ["no_predictions", "role_mismatch"]:
        return {
            "selected_threshold": default_selected,
            "review_threshold": default_review,
            "adjustment_applied": False
        }
    
    selected_threshold = default_selected
    review_threshold = default_review
    adjustment_applied = False
    
    # Adjust thresholds for overqualified candidates with high similarity
    if match_type == "overqualified":
        if similarity >= 0.8:
            selected_threshold = 65  # Lower threshold by 5 points
            adjustment_applied = True
            logger.info(f"Threshold adjusted: Selected threshold lowered to {selected_threshold} (overqualified + high similarity)")
        elif similarity >= 0.7:
            selected_threshold = 68  # Lower threshold by 2 points
            adjustment_applied = True
            logger.info(f"Threshold adjusted: Selected threshold lowered to {selected_threshold} (overqualified + medium similarity)")
    
    # Adjust thresholds for exact matches with high similarity
    elif match_type == "exact_match":
        if similarity >= 0.8:
            selected_threshold = 68  # Lower threshold by 2 points
            adjustment_applied = True
            logger.info(f"Threshold adjusted: Selected threshold lowered to {selected_threshold} (exact match + high similarity)")
    
    return {
        "selected_threshold": selected_threshold,
        "review_threshold": review_threshold,
        "adjustment_applied": adjustment_applied
    }





