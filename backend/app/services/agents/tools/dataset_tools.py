"""
Dataset tools for agents.

Tools for dataset operations that agents can call during evaluation.
"""

from typing import Dict, Any, List
import logging
from app.services.dataset_loader import (
    find_similar_pairs,
    get_dataset_statistics,
    load_dataset
)

logger = logging.getLogger(__name__)


def find_similar_cases_tool(
    candidate_profile: str,
    job_description: str,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Find similar cases from dataset.
    
    Args:
        candidate_profile: JSON string or dict representation of candidate profile
        job_description: JSON string or dict representation of job description
        top_k: Number of similar cases to return
    
    Returns:
        Dictionary with similar cases
    """
    try:
        import json
        
        # Parse inputs if they're strings
        if isinstance(candidate_profile, str):
            candidate_profile = json.loads(candidate_profile)
        if isinstance(job_description, str):
            job_description = json.loads(job_description)
        
        # Find similar pairs
        similar_pairs = find_similar_pairs(
            candidate_profile,
            job_description,
            top_k=top_k
        )
        
        return {
            "status": "success",
            "count": len(similar_pairs),
            "similar_cases": similar_pairs
        }
    except Exception as e:
        logger.error(f"find_similar_cases_tool failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "count": 0,
            "similar_cases": []
        }


def get_dataset_statistics_tool() -> Dict[str, Any]:
    """
    Get dataset score/decision distributions.
    
    Returns:
        Dictionary with dataset statistics
    """
    try:
        stats = get_dataset_statistics()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"get_dataset_statistics_tool failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "statistics": {}
        }


def validate_score_against_dataset_tool(
    score: int,
    candidate_profile: str,
    job_description: str
) -> Dict[str, Any]:
    """
    Validate score consistency against dataset patterns.
    
    Args:
        score: Current evaluation score
        candidate_profile: JSON string or dict representation of candidate profile
        job_description: JSON string or dict representation of job description
    
    Returns:
        Dictionary with validation results
    """
    try:
        import json
        
        # Parse inputs if they're strings
        if isinstance(candidate_profile, str):
            candidate_profile = json.loads(candidate_profile)
        if isinstance(job_description, str):
            job_description = json.loads(job_description)
        
        # Get similar cases
        similar_pairs = find_similar_pairs(
            candidate_profile,
            job_description,
            top_k=5
        )
        
        if not similar_pairs:
            return {
                "status": "warning",
                "message": "No similar cases found in dataset",
                "is_consistent": True  # Can't validate without similar cases
            }
        
        # Get average ground truth score
        avg_ground_truth = sum(
            case['ground_truth_score'] for case in similar_pairs
        ) / len(similar_pairs)
        
        # Check if score is within reasonable range
        score_diff = abs(score - avg_ground_truth)
        is_consistent = score_diff <= 15  # Allow 15 point difference
        
        # Get decision distribution
        decisions = [case['ground_truth_decision'] for case in similar_pairs]
        most_common_decision = max(set(decisions), key=decisions.count) if decisions else None
        
        return {
            "status": "success",
            "is_consistent": is_consistent,
            "score_difference": score_diff,
            "average_ground_truth_score": avg_ground_truth,
            "most_common_decision": most_common_decision,
            "similar_cases_count": len(similar_pairs)
        }
    except Exception as e:
        logger.error(f"validate_score_against_dataset_tool failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "is_consistent": True  # Default to consistent on error
        }




