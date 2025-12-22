"""
State management for agentic evaluation workflow.

Tracks current evaluation state, what has been extracted, what needs verification,
and current scores/intermediate results.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EvaluationStage(Enum):
    """Evaluation workflow stages"""
    INITIALIZED = "initialized"
    EXTRACTING = "extracting"
    VERIFYING = "verifying"
    SCORING = "scoring"
    REVIEWING = "reviewing"
    AGGREGATING = "aggregating"
    DATASET_VALIDATION = "dataset_validation"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationState:
    """
    Tracks current evaluation state.
    
    Manages:
    - Current evaluation stage
    - What has been extracted
    - What needs verification
    - Current scores and intermediate results
    - Candidate and job data
    """
    
    def __init__(self, candidate_id: str, job_id: str):
        """
        Initialize evaluation state.
        
        Args:
            candidate_id: Candidate MongoDB ID
            job_id: Job MongoDB ID
        """
        self.candidate_id = candidate_id
        self.job_id = job_id
        self.stage = EvaluationStage.INITIALIZED
        
        # Data storage
        self.candidate_data: Optional[Dict] = None
        self.job_data: Optional[Dict] = None
        
        # Extracted data
        self.cv_data: Optional[Dict] = None
        self.linkedin_data: Optional[Dict] = None
        self.github_data: Optional[Dict] = None
        self.jd_data: Optional[Dict] = None
        self.merged_json: Optional[Dict] = None
        
        # Processing flags
        self.extracted: Dict[str, bool] = {
            "cv": False,
            "linkedin": False,
            "github": False,
            "jd": False
        }
        
        self.verified: Dict[str, bool] = {
            "github_handle": False,
            "skill_evidence": False,
            "experience_consistency": False
        }
        
        # Intermediate results
        self.normalized_skills: Optional[List[str]] = None
        self.semantic_features: Optional[Dict] = None
        self.judge_scores: Optional[Dict] = None
        self.critic_scores: Optional[Dict] = None
        self.aggregated_score: Optional[Dict] = None
        
        # Final results
        self.total_score: Optional[int] = None
        self.decision: Optional[str] = None
        self.role_predictions: Optional[List[Dict]] = None
        self.explanations: Optional[List[str]] = None
        
        # Dataset validation results
        self.dataset_validation: Optional[Dict] = None
        
        # Error tracking
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Metadata
        self.iteration_count: int = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def set_stage(self, stage: EvaluationStage):
        """
        Set current evaluation stage.
        
        Args:
            stage: New stage
        """
        logger.info(f"Stage transition: {self.stage.value} -> {stage.value}")
        self.stage = stage
    
    def mark_extracted(self, source: str, data: Dict):
        """
        Mark data source as extracted.
        
        Args:
            source: Data source ("cv", "linkedin", "github", "jd")
            data: Extracted data
        """
        if source == "cv":
            self.cv_data = data
            self.extracted["cv"] = True
        elif source == "linkedin":
            self.linkedin_data = data
            self.extracted["linkedin"] = True
        elif source == "github":
            self.github_data = data
            self.extracted["github"] = True
        elif source == "jd":
            self.jd_data = data
            self.extracted["jd"] = True
        
        logger.debug(f"Marked {source} as extracted")
    
    def is_extracted(self, source: str) -> bool:
        """
        Check if data source has been extracted.
        
        Args:
            source: Data source
        
        Returns:
            True if extracted
        """
        return self.extracted.get(source, False)
    
    def mark_verified(self, verification_type: str, verified: bool = True):
        """
        Mark verification as complete.
        
        Args:
            verification_type: Verification type
            verified: Whether verification passed
        """
        self.verified[verification_type] = verified
        logger.debug(f"Marked {verification_type} as verified: {verified}")
    
    def is_verified(self, verification_type: str) -> bool:
        """
        Check if verification is complete.
        
        Args:
            verification_type: Verification type
        
        Returns:
            True if verified
        """
        return self.verified.get(verification_type, False)
    
    def set_intermediate_result(self, key: str, value: Any):
        """
        Set intermediate result.
        
        Args:
            key: Result key
            value: Result value
        """
        if key == "normalized_skills":
            self.normalized_skills = value
        elif key == "semantic_features":
            self.semantic_features = value
        elif key == "judge_scores":
            self.judge_scores = value
        elif key == "critic_scores":
            self.critic_scores = value
        elif key == "aggregated_score":
            self.aggregated_score = value
        elif key == "merged_json":
            self.merged_json = value
        
        logger.debug(f"Set intermediate result: {key}")
    
    def get_intermediate_result(self, key: str) -> Optional[Any]:
        """
        Get intermediate result.
        
        Args:
            key: Result key
        
        Returns:
            Result value or None
        """
        result_map = {
            "normalized_skills": self.normalized_skills,
            "semantic_features": self.semantic_features,
            "judge_scores": self.judge_scores,
            "critic_scores": self.critic_scores,
            "aggregated_score": self.aggregated_score,
            "merged_json": self.merged_json
        }
        return result_map.get(key)
    
    def set_dataset_validation(self, result: Dict):
        """
        Set dataset validation result.
        
        Args:
            result: Dataset validation result dictionary
        """
        self.dataset_validation = result
        logger.debug("Dataset validation result stored")
    
    def set_final_result(
        self,
        total_score: int,
        decision: str,
        role_predictions: List[Dict],
        explanations: List[str]
    ):
        """
        Set final evaluation result.
        
        Args:
            total_score: Total score (0-100)
            decision: Decision (Selected/Review/Not Selected)
            role_predictions: Role predictions
            explanations: Explanations
        """
        self.total_score = total_score
        self.decision = decision
        self.role_predictions = role_predictions
        self.explanations = explanations
        self.set_stage(EvaluationStage.COMPLETED)
        logger.info(f"Final result: {decision} (score: {total_score})")
    
    def add_error(self, error: str):
        """
        Add error message.
        
        Args:
            error: Error message
        """
        self.errors.append(error)
        logger.error(f"State error: {error}")
    
    def add_warning(self, warning: str):
        """
        Add warning message.
        
        Args:
            warning: Warning message
        """
        self.warnings.append(warning)
        logger.warning(f"State warning: {warning}")
    
    def increment_iteration(self):
        """Increment iteration count"""
        self.iteration_count += 1
    
    def get_summary(self) -> Dict:
        """
        Get state summary.
        
        Returns:
            Dictionary with state summary
        """
        return {
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "stage": self.stage.value,
            "extracted": self.extracted.copy(),
            "verified": self.verified.copy(),
            "has_intermediate_results": {
                "normalized_skills": self.normalized_skills is not None,
                "semantic_features": self.semantic_features is not None,
                "judge_scores": self.judge_scores is not None,
                "critic_scores": self.critic_scores is not None,
                "aggregated_score": self.aggregated_score is not None
            },
            "total_score": self.total_score,
            "decision": self.decision,
            "dataset_validation": self.dataset_validation is not None,
            "iteration_count": self.iteration_count,
            "errors": len(self.errors),
            "warnings": len(self.warnings)
        }
    
    def is_complete(self) -> bool:
        """
        Check if evaluation is complete.
        
        Returns:
            True if completed
        """
        return self.stage == EvaluationStage.COMPLETED
    
    def has_errors(self) -> bool:
        """
        Check if state has errors.
        
        Returns:
            True if has errors
        """
        return len(self.errors) > 0

