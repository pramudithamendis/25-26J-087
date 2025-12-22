"""
Planning Agent for CV evaluation workflow.

Implements ReAct pattern (Reasoning + Acting) to orchestrate the evaluation workflow.
Decides next actions, selects appropriate agents/tools, and monitors progress.
"""

from typing import Dict, List, Optional
import logging
import json
from .base_agent import BaseAgent
from .state import EvaluationState, EvaluationStage

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    """
    Planning agent that orchestrates the evaluation workflow.
    
    Analyzes current state and decides next action, selects appropriate agent/tool,
    monitors progress, and handles failures.
    """
    
    def __init__(self):
        """Initialize planning agent"""
        system_prompt = """You are a planning agent for CV evaluation system. Your role is to:
1. Analyze the current evaluation state
2. Decide what action to take next
3. Select the appropriate agent or tool for the task
4. Monitor progress and handle failures
5. Determine when evaluation is complete

Available agents:
- ExtractionAgent: Extracts data from CV/LinkedIn/GitHub
- VerificationAgent: Verifies claims and checks consistency
- JudgeAgent: Scores candidate on criteria
- CriticAgent: Reviews and validates scores
- AggregatorAgent: Combines scores into final result
- DatasetGuidedAgent: Validates and calibrates scores using ground truth dataset

Available stages:
- INITIALIZED: Just started
- EXTRACTING: Extracting candidate data
- VERIFYING: Verifying extracted data
- SCORING: Scoring candidate
- REVIEWING: Reviewing scores
- AGGREGATING: Aggregating final score
- DATASET_VALIDATION: Validating with dataset
- COMPLETED: Evaluation complete

Always respond with JSON in this format:
{
  "action": "extract_cv" | "extract_linkedin" | "extract_github" | "verify_github" | "verify_consistency" | "score_candidate" | "review_scores" | "aggregate" | "validate_with_dataset" | "complete",
  "agent": "extraction" | "verification" | "judge" | "critic" | "aggregator" | "dataset_guided" | null,
  "reasoning": "Explanation of why this action was chosen",
  "next_stage": "stage_name"
}"""
        
        super().__init__(
            name="PlanningAgent",
            system_prompt=system_prompt,
            temperature=0.2  # Lower temperature for more consistent planning
        )
    
    def plan_next_action(self, state: EvaluationState) -> Dict:
        """
        Decide what action to take next based on current state.
        
        Args:
            state: Current evaluation state
        
        Returns:
            Dictionary with action, agent, reasoning, and next_stage
        """
        # Build state summary for LLM
        state_summary = self._build_state_summary(state)
        
        user_prompt = f"""Current evaluation state:
{json.dumps(state_summary, indent=2)}

What should be done next? Consider:
1. What data has been extracted?
2. What needs verification? (DO NOT suggest verify_consistency if experience_consistency is already verified)
3. What stages are complete?
4. Are there any errors?

IMPORTANT: If "experience_consistency" is already verified, DO NOT suggest "verify_consistency" action again.

Respond with JSON containing action, agent, reasoning, and next_stage."""
        
        try:
            response = self.call_llm(
                user_prompt,
                response_format={"type": "json_object"}
            )
            
            content = response.get("content", "{}")
            if isinstance(content, str):
                # Remove markdown if present
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            
            result = json.loads(content) if isinstance(content, str) else content
            
            # Validate result
            if "action" not in result:
                logger.warning("Invalid planning response, using default action")
                result = self._get_default_action(state)
            
            # Prevent redundant verify_consistency calls
            if result.get("action") == "verify_consistency" and state.is_verified("experience_consistency"):
                logger.warning("Planning agent suggested verify_consistency but already verified, using default action")
                result = self._get_default_action(state)
            
            logger.info(f"Planning decision: {result.get('action')} -> {result.get('agent')}")
            return result
            
        except Exception as e:
            logger.error(f"Planning failed: {str(e)}, using default action")
            return self._get_default_action(state)
    
    def _build_state_summary(self, state: EvaluationState) -> Dict:
        """Build summary of current state for LLM"""
        return {
            "stage": state.stage.value,
            "extracted": {
                "cv": state.is_extracted("cv"),
                "linkedin": state.is_extracted("linkedin"),
                "github": state.is_extracted("github"),
                "jd": state.is_extracted("jd")
            },
            "verified": {
                "github_handle": state.is_verified("github_handle"),
                "skill_evidence": state.is_verified("skill_evidence"),
                "experience_consistency": state.is_verified("experience_consistency")
            },
            "has_intermediate_results": {
                "normalized_skills": state.normalized_skills is not None,
                "semantic_features": state.semantic_features is not None,
                "judge_scores": state.judge_scores is not None,
                "critic_scores": state.critic_scores is not None,
                "aggregated_score": state.aggregated_score is not None
            },
            "errors": state.errors,
            "warnings": state.warnings,
            "iteration_count": state.iteration_count
        }
    
    def _get_default_action(self, state: EvaluationState) -> Dict:
        """Get default action based on state (fallback logic)"""
        # Simple state machine
        if not state.is_extracted("cv") and state.candidate_data and state.candidate_data.get("cv_file_path"):
            return {
                "action": "extract_cv",
                "agent": "extraction",
                "reasoning": "CV not yet extracted, need to extract CV first",
                "next_stage": "EXTRACTING"
            }
        
        if not state.is_extracted("jd") and state.job_data:
            return {
                "action": "extract_jd",
                "agent": "extraction",
                "reasoning": "Job description not yet extracted",
                "next_stage": "EXTRACTING"
            }
        
        if state.is_extracted("cv") and not state.is_extracted("github") and state.cv_data:
            github_handle = state.cv_data.get("github_handle", "")
            if github_handle:
                return {
                    "action": "extract_github",
                    "agent": "verification",
                    "reasoning": "GitHub handle found in CV, need to extract GitHub data",
                    "next_stage": "VERIFYING"
                }
        
        # Skip verify_consistency if already verified to prevent loops
        if state.is_extracted("cv") and state.is_extracted("linkedin") and not state.is_verified("experience_consistency"):
            return {
                "action": "verify_consistency",
                "agent": "verification",
                "reasoning": "Need to verify consistency between CV and LinkedIn",
                "next_stage": "VERIFYING"
            }
        
        if state.is_extracted("cv") and state.is_extracted("jd") and not state.semantic_features:
            return {
                "action": "calculate_similarity",
                "agent": "analysis",
                "reasoning": "Need to calculate semantic similarity",
                "next_stage": "SCORING"
            }
        
        if state.semantic_features and not state.judge_scores:
            return {
                "action": "score_candidate",
                "agent": "judge",
                "reasoning": "Need to score candidate on criteria",
                "next_stage": "SCORING"
            }
        
        if state.judge_scores and not state.critic_scores:
            return {
                "action": "review_scores",
                "agent": "critic",
                "reasoning": "Need to review judge scores",
                "next_stage": "REVIEWING"
            }
        
        if state.critic_scores and not state.aggregated_score:
            return {
                "action": "aggregate",
                "agent": "aggregator",
                "reasoning": "Need to aggregate final score",
                "next_stage": "AGGREGATING"
            }
        
        # After aggregation, validate with dataset if enabled
        if state.aggregated_score and not state.dataset_validation:
            from app.config import settings
            if settings.DATASET_VALIDATION_ENABLED:
                return {
                    "action": "validate_with_dataset",
                    "agent": "dataset_guided",
                    "reasoning": "Need to validate and calibrate score using ground truth dataset",
                    "next_stage": "DATASET_VALIDATION"
                }
        
        return {
            "action": "complete",
            "agent": None,
            "reasoning": "Evaluation complete",
            "next_stage": "COMPLETED"
        }
    
    def select_agent(self, task: str) -> Optional[str]:
        """
        Select appropriate agent for a task.
        
        Args:
            task: Task description
        
        Returns:
            Agent name or None
        """
        task_lower = task.lower()
        
        if any(keyword in task_lower for keyword in ["extract", "cv", "linkedin", "github", "jd"]):
            return "extraction"
        elif any(keyword in task_lower for keyword in ["verify", "check", "consistency"]):
            return "verification"
        elif any(keyword in task_lower for keyword in ["score", "evaluate", "judge"]):
            return "judge"
        elif any(keyword in task_lower for keyword in ["review", "critic", "validate"]):
            return "critic"
        elif any(keyword in task_lower for keyword in ["aggregate", "combine", "final"]):
            return "aggregator"
        elif any(keyword in task_lower for keyword in ["dataset", "validate", "calibrate", "ground truth"]):
            return "dataset_guided"
        
        return None
    
    def should_continue(self, state: EvaluationState) -> bool:
        """
        Determine if evaluation should continue.
        
        Args:
            state: Current evaluation state
        
        Returns:
            True if should continue
        """
        if state.is_complete():
            return False
        
        if state.has_errors() and len(state.errors) > 3:
            logger.warning("Too many errors, stopping evaluation")
            return False
        
        max_iterations = getattr(state, 'max_iterations', 20)
        if state.iteration_count >= max_iterations:
            logger.warning(f"Max iterations ({max_iterations}) reached")
            return False
        
        return True
    
    def handle_failure(self, error: Exception, state: EvaluationState) -> Dict:
        """
        Handle failure and decide recovery action.
        
        Args:
            error: Exception that occurred
            state: Current evaluation state
        
        Returns:
            Recovery action
        """
        error_msg = str(error)
        state.add_error(error_msg)
        
        logger.error(f"Handling failure: {error_msg}")
        
        # Try to recover based on error type
        if "OpenAI" in error_msg or "API" in error_msg:
            # API error - might be temporary, try again
            return {
                "action": "retry",
                "agent": None,
                "reasoning": f"API error occurred: {error_msg}. Will retry.",
                "next_stage": state.stage.value
            }
        elif "extract" in error_msg.lower():
            # Extraction error - try fallback method
            return {
                "action": "extract_fallback",
                "agent": "extraction",
                "reasoning": f"Extraction failed: {error_msg}. Trying fallback method.",
                "next_stage": "EXTRACTING"
            }
        else:
            # Unknown error - skip this step
            return {
                "action": "skip",
                "agent": None,
                "reasoning": f"Error occurred: {error_msg}. Skipping this step.",
                "next_stage": state.stage.value
            }
    
    def execute(self, state: Dict) -> Dict:
        """
        Execute planning agent.
        
        Args:
            state: Current evaluation state (EvaluationState object)
        
        Returns:
            Planning result with next action
        """
        if isinstance(state, dict):
            # Convert dict to EvaluationState if needed
            from .state import EvaluationState
            state = EvaluationState(state.get("candidate_id", ""), state.get("job_id", ""))
        
        if not isinstance(state, EvaluationState):
            raise ValueError("State must be EvaluationState instance")
        
        return self.plan_next_action(state)

