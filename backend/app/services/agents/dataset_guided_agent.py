"""
Dataset-Guided Evaluation Agent for CV evaluation.

Validates and calibrates evaluation scores using the ground truth dataset.
Performs pattern recognition, score calibration, confidence scoring, and
ground truth validation.
"""

from typing import Dict, List, Optional
import logging
import json
from .base_agent import BaseAgent
from .state import EvaluationState
from app.services.dataset_loader import find_similar_pairs, get_dataset_statistics
from app.config import settings

logger = logging.getLogger(__name__)


class DatasetGuidedAgent(BaseAgent):
    """
    Dataset-guided agent that validates and calibrates evaluation scores.
    
    Uses the 592-pair ground truth dataset to:
    1. Find similar candidate-job pairs
    2. Calibrate scores based on dataset patterns
    3. Provide confidence scores
    4. Validate evaluations against ground truth
    """
    
    def __init__(self):
        """Initialize dataset-guided agent"""
        system_prompt = """You are a dataset-guided validation agent for CV evaluation system. Your role is to:
1. Find similar candidate-job pairs from the ground truth dataset (592 pairs)
2. Calibrate evaluation scores based on dataset patterns
3. Calculate confidence scores based on dataset coverage
4. Validate evaluations against ground truth patterns
5. Provide explainability by referencing similar dataset cases

You have access to:
- Ground truth dataset with 592 evaluation pairs
- Similarity search using semantic embeddings
- Dataset statistics (score distributions, decision patterns)

Always respond with JSON in this format:
{
  "original_score": 75,
  "calibrated_score": 73,
  "confidence": 0.85,
  "calibration_adjustment": -2,
  "similar_cases": [...],
  "validation_status": "passed",
  "reasoning": "Explanation of calibration",
  "dataset_statistics": {...}
}"""
        
        super().__init__(
            name="DatasetGuidedAgent",
            system_prompt=system_prompt,
            temperature=0.2,  # Low temperature for consistent calibration
            max_tokens=2000
        )
    
    def execute(self, state: EvaluationState) -> Dict:
        """
        Execute dataset-guided validation and calibration.
        
        Args:
            state: Current evaluation state
        
        Returns:
            Dictionary with calibration results
        """
        try:
            # Check if dataset validation is enabled
            if not settings.DATASET_VALIDATION_ENABLED:
                logger.info("Dataset validation is disabled, skipping")
                return {
                    "status": "skipped",
                    "reason": "Dataset validation disabled"
                }
            
            # Get aggregated score from state
            aggregated_score = state.aggregated_score
            if not aggregated_score:
                logger.warning("No aggregated score found in state")
                return {
                    "status": "error",
                    "error": "No aggregated score available"
                }
            
            current_score = aggregated_score.get("total_score", 0)
            
            # Get candidate and job data
            candidate = state.merged_json.get("candidate", {}) if state.merged_json else {}
            job_desc = state.merged_json.get("job_description", {}) if state.merged_json else {}
            
            if not candidate or not job_desc:
                logger.warning("Missing candidate or job data")
                return {
                    "status": "error",
                    "error": "Missing candidate or job data"
                }
            
            # Find similar cases
            similar_cases = self.find_similar_cases(candidate, job_desc)
            
            # Calibrate score (even if score is 0, use similar cases for calibration)
            if current_score == 0 and similar_cases:
                logger.info("Total score is 0, but found similar cases - attempting calibration based on ground truth")
                # Get average ground truth from similar cases
                ground_truth_scores = [case['ground_truth_score'] for case in similar_cases]
                avg_ground_truth = sum(ground_truth_scores) / len(ground_truth_scores)
                
                # Use ground truth as strong signal when original score is 0
                # Apply 50% weight to average ground truth for conservative calibration
                calibrated_score = int(avg_ground_truth * 0.5)
                calibrated_score = max(0, min(100, calibrated_score))
                adjustment = calibrated_score - current_score
                
                calibration_result = {
                    "calibrated_score": calibrated_score,
                    "adjustment": adjustment,
                    "reasoning": f"Original score was 0, but calibrated to {calibrated_score} based on similar cases (avg ground truth: {avg_ground_truth:.1f})",
                    "average_ground_truth": avg_ground_truth
                }
            elif current_score == 0:
                # No similar cases found, cannot calibrate
                logger.info("Total score is 0 and no similar cases found")
                calibration_result = {
                    "calibrated_score": current_score,
                    "adjustment": 0,
                    "reasoning": "Score is 0, no similar cases found for calibration."
                }
            else:
                calibration_result = self.calibrate_score(current_score, similar_cases)
            
            # Calculate confidence
            confidence = self.calculate_confidence(similar_cases)
            
            # Validate against patterns
            validation_result = self.validate_against_patterns(
                calibration_result.get("calibrated_score", current_score),
                similar_cases
            )
            
            # Get dataset statistics
            dataset_stats = get_dataset_statistics()
            
            # Build final result
            result = {
                "original_score": current_score,
                "calibrated_score": calibration_result.get("calibrated_score", current_score),
                "confidence": confidence,
                "calibration_adjustment": calibration_result.get("adjustment", 0),
                "similar_cases": similar_cases[:5],  # Top 5
                "validation_status": validation_result.get("status", "passed"),
                "reasoning": calibration_result.get("reasoning", "No calibration needed"),
                "dataset_statistics": dataset_stats,
                "status": "success"
            }
            
            if current_score == 0:
                if similar_cases:
                    logger.info(
                        f"Dataset validation complete: Score was 0, calibrated to {result['calibrated_score']} "
                        f"based on {len(similar_cases)} similar cases (confidence: {confidence:.2f})"
                    )
                else:
                    logger.info(
                        f"Dataset validation complete: Score is 0, no similar cases found "
                        f"(confidence: {confidence:.2f})"
                    )
            else:
                logger.info(
                    f"Dataset validation complete: {current_score} -> "
                    f"{result['calibrated_score']} (confidence: {confidence:.2f})"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Dataset-guided validation failed: {str(e)}", exc_info=True)
            # Return original score on error (don't break evaluation)
            return {
                "status": "error",
                "error": str(e),
                "original_score": state.aggregated_score.get("total_score", 0) if state.aggregated_score else 0,
                "calibrated_score": state.aggregated_score.get("total_score", 0) if state.aggregated_score else 0,
                "confidence": 0.0,
                "calibration_adjustment": 0,
                "similar_cases": [],
                "validation_status": "error",
                "reasoning": f"Validation failed: {str(e)}"
            }
    
    def find_similar_cases(
        self,
        candidate: Dict,
        job: Dict,
        top_k: int = None
    ) -> List[Dict]:
        """
        Find similar candidate-job pairs from dataset.
        
        Args:
            candidate: Candidate profile dictionary
            job: Job description dictionary
            top_k: Number of similar cases to retrieve
        
        Returns:
            List of similar cases with similarity scores
        """
        try:
            top_k = top_k or settings.DATASET_TOP_K
            logger.debug(f"Searching for top {top_k} similar cases")
            similar_pairs = find_similar_pairs(candidate, job, top_k=top_k)
            if similar_pairs:
                logger.info(f"Found {len(similar_pairs)} similar cases (top similarity: {similar_pairs[0].get('similarity', 0):.3f})")
            else:
                logger.warning("No similar cases found in dataset")
            return similar_pairs
        except Exception as e:
            logger.error(f"Failed to find similar cases: {str(e)}", exc_info=True)
            return []
    
    def calibrate_score(
        self,
        current_score: int,
        similar_cases: List[Dict]
    ) -> Dict:
        """
        Calibrate score based on dataset patterns.
        
        Args:
            current_score: Current evaluation score
            similar_cases: List of similar cases from dataset
        
        Returns:
            Dictionary with calibrated score and reasoning
        """
        try:
            if not similar_cases:
                return {
                    "calibrated_score": current_score,
                    "adjustment": 0,
                    "reasoning": "No similar cases found, using original score"
                }
            
            # Get average ground truth score from similar cases
            ground_truth_scores = [
                case['ground_truth_score'] for case in similar_cases
            ]
            avg_ground_truth = sum(ground_truth_scores) / len(ground_truth_scores)
            
            # Calculate adjustment
            score_diff = avg_ground_truth - current_score
            
            # Apply calibration weight (only adjust if difference is significant)
            calibration_weight = settings.DATASET_CALIBRATION_WEIGHT
            if abs(score_diff) > 5:  # Only adjust if difference > 5 points
                adjustment = int(score_diff * calibration_weight)
                calibrated_score = current_score + adjustment
                calibrated_score = max(0, min(100, calibrated_score))  # Clamp to 0-100
            else:
                adjustment = 0
                calibrated_score = current_score
            
            # Generate reasoning using LLM
            reasoning = self._generate_calibration_reasoning(
                current_score,
                calibrated_score,
                similar_cases,
                avg_ground_truth
            )
            
            return {
                "calibrated_score": calibrated_score,
                "adjustment": adjustment,
                "reasoning": reasoning,
                "average_ground_truth": avg_ground_truth
            }
            
        except Exception as e:
            logger.error(f"Score calibration failed: {str(e)}")
            return {
                "calibrated_score": current_score,
                "adjustment": 0,
                "reasoning": f"Calibration failed: {str(e)}"
            }
    
    def _generate_calibration_reasoning(
        self,
        original_score: int,
        calibrated_score: int,
        similar_cases: List[Dict],
        avg_ground_truth: float
    ) -> str:
        """
        Generate reasoning for calibration using LLM.
        
        Args:
            original_score: Original score
            calibrated_score: Calibrated score
            similar_cases: Similar cases from dataset
            avg_ground_truth: Average ground truth score
        
        Returns:
            Reasoning string
        """
        try:
            adjustment = calibrated_score - original_score
            
            if abs(adjustment) < 1:
                return f"Score aligns with dataset patterns (avg ground truth: {avg_ground_truth:.1f})"
            
            # Build context
            top_cases = similar_cases[:3]
            cases_summary = "\n".join([
                f"- {case['candidate_name']} for {case['job_title']}: "
                f"score {case['ground_truth_score']}, decision {case['ground_truth_decision']}"
                for case in top_cases
            ])
            
            user_prompt = f"""Original score: {original_score}
Calibrated score: {calibrated_score}
Adjustment: {adjustment:+d}
Average ground truth from similar cases: {avg_ground_truth:.1f}

Similar cases:
{cases_summary}

Explain why the score was adjusted (or not adjusted) based on these similar cases from the dataset.
Keep it concise (1-2 sentences)."""
            
            response = self.call_llm(user_prompt)
            reasoning = response.get("content", "").strip()
            
            # Fallback if LLM fails
            if not reasoning:
                if adjustment > 0:
                    reasoning = f"Score increased by {adjustment} points based on dataset patterns (avg: {avg_ground_truth:.1f})"
                elif adjustment < 0:
                    reasoning = f"Score decreased by {abs(adjustment)} points based on dataset patterns (avg: {avg_ground_truth:.1f})"
                else:
                    reasoning = f"Score aligns with dataset patterns (avg: {avg_ground_truth:.1f})"
            
            return reasoning
            
        except Exception as e:
            logger.warning(f"Failed to generate LLM reasoning: {str(e)}")
            return f"Score adjusted based on {len(similar_cases)} similar cases (avg ground truth: {avg_ground_truth:.1f})"
    
    def calculate_confidence(
        self,
        similar_cases: List[Dict],
        dataset_coverage: float = 1.0
    ) -> float:
        """
        Calculate confidence score based on dataset similarity.
        
        Args:
            similar_cases: List of similar cases
            dataset_coverage: Dataset coverage factor (default 1.0)
        
        Returns:
            Confidence score (0.0 to 1.0)
        """
        try:
            if not similar_cases:
                return 0.3  # Low confidence if no similar cases
            
            # Base confidence on similarity scores
            similarities = [case['similarity'] for case in similar_cases]
            avg_similarity = sum(similarities) / len(similarities)
            
            # Confidence increases with:
            # 1. Higher average similarity
            # 2. More similar cases found
            # 3. Consistency in ground truth scores
            
            # Similarity component (0-0.6)
            similarity_confidence = avg_similarity * 0.6
            
            # Coverage component (0-0.3)
            coverage_confidence = min(0.3, len(similar_cases) / 10.0 * 0.3)
            
            # Consistency component (0-0.1)
            if len(similar_cases) > 1:
                scores = [case['ground_truth_score'] for case in similar_cases]
                score_std = sum(abs(s - sum(scores)/len(scores)) for s in scores) / len(scores)
                consistency_confidence = max(0, 0.1 - (score_std / 100.0))
            else:
                consistency_confidence = 0.05
            
            total_confidence = similarity_confidence + coverage_confidence + consistency_confidence
            total_confidence = min(1.0, max(0.0, total_confidence))
            
            return round(total_confidence, 2)
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            return 0.5  # Default medium confidence
    
    def validate_against_patterns(
        self,
        score: int,
        similar_cases: List[Dict]
    ) -> Dict:
        """
        Validate evaluation against dataset patterns.
        
        Args:
            score: Evaluation score
            similar_cases: Similar cases from dataset
        
        Returns:
            Validation result dictionary
        """
        try:
            if not similar_cases:
                return {
                    "status": "warning",
                    "message": "No similar cases found for validation"
                }
            
            # Check if score is within reasonable range of ground truth
            ground_truth_scores = [case['ground_truth_score'] for case in similar_cases]
            avg_ground_truth = sum(ground_truth_scores) / len(ground_truth_scores)
            
            score_diff = abs(score - avg_ground_truth)
            
            # Validation passes if score is within 15 points of average ground truth
            if score_diff <= 15:
                return {
                    "status": "passed",
                    "message": f"Score ({score}) is consistent with dataset patterns (avg: {avg_ground_truth:.1f})"
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Score ({score}) differs significantly from dataset patterns (avg: {avg_ground_truth:.1f}, diff: {score_diff:.1f})"
                }
                
        except Exception as e:
            logger.error(f"Pattern validation failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Validation failed: {str(e)}"
            }

