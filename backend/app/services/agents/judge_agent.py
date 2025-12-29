"""
Judge Agent for CV evaluation.

Scores candidate on role-specific criteria with agentic reasoning, reusing judge.py logic.
Uses dynamic criteria generation based on job role (Data Analyst, Software Engineer, UI/UX, etc.).
"""

from typing import Dict, List, Optional
import logging
import json
from .base_agent import BaseAgent
from .state import EvaluationState
from app.services.judge import build_judge_prompt, judge_with_openai, judge_candidate_heuristic
from app.services.role_criteria_generator import generate_role_criteria
from app.config import settings

logger = logging.getLogger(__name__)


class JudgeAgent(BaseAgent):
    """
    Judge agent that scores candidates on role-specific criteria.
    
    Uses existing judge.py logic but adds agentic reasoning for:
    - Requesting additional information if evidence insufficient
    - Adjusting scores based on verification results
    - Providing detailed evidence for each score
    - Using role-specific criteria (dynamically generated)
    """
    
    def __init__(self):
        """Initialize judge agent with dynamic system prompt"""
        # System prompt will be built dynamically based on role
        super().__init__(
            name="JudgeAgent",
            system_prompt="",  # Will be set dynamically
            temperature=0.3,  # Same as original judge
            max_tokens=2000
        )
    
    def _build_system_prompt(self, role_criteria: Dict) -> str:
        """Build dynamic system prompt based on role criteria"""
        criteria_list = role_criteria.get("criteria", [])
        role_category = role_criteria.get("role_category", "IT Professional")
        
        criteria_desc = "\n".join([
            f"   - {c.get('criterion', '')}: {c.get('description', '')}"
            for c in criteria_list
        ])
        
        return f"""You are a judge agent for CV evaluation system. Your role is to:
1. Score candidates on {len(criteria_list)} criteria (0-5 scale) for {role_category} role:
{criteria_desc}

2. Provide specific evidence for each score
3. Request additional information if evidence is insufficient
4. Adjust scores based on verification results
5. Evaluate based on role-specific requirements, not generic software engineering criteria

Always respond with JSON in this format:
{{
  "judge_scores": [
    {{
      "criterion": "Criterion Name",
      "score": 4,
      "evidence": "Specific evidence from candidate profile",
      "confidence": 0.9
    }}
  ],
  "needs_more_info": ["criterion_name"] if any,
  "reasoning": "Overall assessment reasoning"
}}

IMPORTANT: You must score ALL {len(criteria_list)} criteria listed above. Include all criteria in your response.
"""
    
    def evaluate_criteria(self, candidate: Dict, job_desc: Dict, role_criteria: Optional[Dict] = None) -> Dict:
        """
        Evaluate candidate on role-specific criteria.
        
        Args:
            candidate: Candidate data
            job_desc: Job description data
            role_criteria: Optional pre-generated role criteria (if None, will generate)
        
        Returns:
            Dictionary with judge_scores
        """
        # Generate role criteria if not provided
        if role_criteria is None:
            role_criteria = generate_role_criteria(job_desc, candidate)
        
        # Update system prompt dynamically based on role
        self.system_prompt = self._build_system_prompt(role_criteria)
        
        # Use existing judge prompt builder with role criteria
        prompt, framework_mismatch_detected, mismatch_details, role_criteria = build_judge_prompt(candidate, job_desc, role_criteria)
        
        # Try OpenAI first
        if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            result = judge_with_openai(prompt, candidate, job_desc, framework_mismatch_detected, role_criteria)
            if result:
                role_category = role_criteria.get("role_category", "IT Professional")
                logger.info(f"Using OpenAI LLM for candidate judgment ({role_category} role)")
                return result
        
        # Fallback to heuristic
        logger.warning("OpenAI LLM failed, using heuristic fallback")
        merged_json = {
            "candidate": candidate,
            "job_description": job_desc
        }
        return judge_candidate_heuristic(merged_json, role_criteria)
    
    def request_additional_info(self, criterion: str, current_evidence: Dict) -> str:
        """
        Determine what additional information is needed for a criterion.
        
        Args:
            criterion: Criterion name
            current_evidence: Current evidence available
        
        Returns:
            Description of what additional info is needed
        """
        user_prompt = f"""For the criterion "{criterion}", I have the following evidence:
{json.dumps(current_evidence, indent=2)}

What additional information would help provide a more accurate score? 
Respond with a brief description of what to look for."""
        
        try:
            response = self.call_llm(user_prompt)
            return response.get("content", "No additional information needed")
        except Exception as e:
            logger.error(f"Failed to request additional info: {str(e)}")
            return "Unable to determine additional information needed"
    
    def adjust_score_based_on_verification(
        self,
        score: int,
        criterion: str,
        verification_result: Dict
    ) -> int:
        """
        Adjust score based on verification results.
        
        Args:
            score: Original score
            criterion: Criterion name
            verification_result: Verification results
        
        Returns:
            Adjusted score
        """
        # If verification found contradictions or issues, reduce score
        contradictions = verification_result.get("contradictions", [])
        if contradictions:
            # Reduce score by 1 for each major contradiction (min 0)
            adjustment = min(len(contradictions), score)
            adjusted_score = max(0, score - adjustment)
            logger.info(f"Adjusted score for {criterion}: {score} -> {adjusted_score} (due to {len(contradictions)} contradictions)")
            return adjusted_score
        
        # If verification confirmed evidence, could increase confidence but not score
        # (scores are based on evidence, not verification)
        return score
    
    def execute(self, state: Dict) -> Dict:
        """
        Execute judge agent.
        
        Args:
            state: Current evaluation state or evaluation request
        
        Returns:
            Judge scores
        """
        if isinstance(state, EvaluationState):
            # Build candidate and job_desc from state
            candidate = {
                "skills_canonical": state.normalized_skills or [],
                "skills_raw": [],
                "experience": [],
                "education": [],
                "github": state.github_data or {}
            }
            
            # Get skills and experience from merged data
            if state.cv_data:
                candidate["skills_raw"] = state.cv_data.get("skills_raw", [])
                candidate["experience"] = state.cv_data.get("experience", [])
                candidate["education"] = state.cv_data.get("education", [])
            
            if state.linkedin_data:
                # Merge LinkedIn data
                candidate["skills_raw"] = list(set(
                    candidate.get("skills_raw", []) + 
                    state.linkedin_data.get("skills_raw", [])
                ))
                if not candidate["experience"]:
                    candidate["experience"] = state.linkedin_data.get("experience", [])
                candidate["education"] = list(set(
                    candidate.get("education", []) + 
                    state.linkedin_data.get("education", [])
                ))
            
            # CRITICAL: Use jd_data from state, not job_data
            # This ensures technology mismatch detection uses the latest extracted JD data
            job_desc = state.jd_data or {}
            if not job_desc:
                logger.warning("No jd_data in state for judge evaluation - missing JD extraction")
                # Fallback to job_data if absolutely necessary (may be incomplete)
                if state.job_data:
                    logger.warning("Falling back to job_data for JD (may be incomplete or stale)")
                    job_desc = state.job_data
                else:
                    logger.error("No JD data available for evaluation")
                    job_desc = {}
        else:
            # Direct evaluation request
            candidate = state.get("candidate", {})
            job_desc = state.get("job_description", {})
        
        # Log which JD data is being used for debugging
        if job_desc:
            logger.debug(f"Judge agent using JD data: title={job_desc.get('title', 'N/A')}, must_have count={len(job_desc.get('must_have', []))}, source={'state.jd_data' if isinstance(state, EvaluationState) and state.jd_data else 'fallback'}")
        
        # Generate role criteria
        role_criteria = generate_role_criteria(job_desc, candidate)
        
        # Evaluate criteria with role-specific criteria
        result = self.evaluate_criteria(candidate, job_desc, role_criteria)
        
        # Add agentic reasoning if needed
        if isinstance(state, EvaluationState):
            # Check if any scores are low and might need more info
            judge_scores = result.get("judge_scores", [])
            needs_more_info = []
            for score_entry in judge_scores:
                if score_entry.get("score", 0) < 2:
                    criterion = score_entry.get("criterion", "")
                    if criterion:
                        needs_more_info.append(criterion)
            
            if needs_more_info:
                result["needs_more_info"] = needs_more_info
                logger.info(f"Judge identified criteria needing more info: {needs_more_info}")
        
        return result

