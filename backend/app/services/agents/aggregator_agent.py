"""
Aggregator Agent for CV evaluation.

Combines scores using hybrid approach: 30% rule-based (existing aggregator.py)
+ 70% agentic reasoning. Uses existing aggregator for baseline, then agentic
component adjusts weights based on context.
"""

from typing import Dict, List, Optional
import logging
import json
from .base_agent import BaseAgent
from .state import EvaluationState
from app.services.aggregator import aggregate_scores

logger = logging.getLogger(__name__)


class AggregatorAgent(BaseAgent):
    """
    Aggregator agent that combines scores into final result.
    
    Uses hybrid approach:
    - 30% rule-based (existing aggregator.py)
    - 70% agentic reasoning (adjusts based on context)
    """
    
    def __init__(self):
        """Initialize aggregator agent"""
        system_prompt = """You are an aggregator agent for CV evaluation system. Your role is to:
1. Combine all scores into a final 0-100 total score
2. Use hybrid approach: 30% rule-based baseline + 70% agentic adjustment
3. Consider context: job requirements, candidate experience level, role type
4. Adjust weights based on what's most important for this specific role

Score components:
- Semantic fit: 30 pts (similarity between candidate and job)
- Role competency: 30 pts (judge scores average)
- Experience recency: 15 pts (time-decay on last 3 years)
- GitHub evidence: 15 pts (activity, relevance, quality)
- Bonus/Malus: ±10 pts (awards, contradictions, keyword stuffing)

Respond with JSON in this format:
{
  "total_score": 85,
  "baseline_score": 80,
  "agentic_adjustment": 5,
  "breakdown": {
    "semantic_fit": 25.5,
    "role_competency": 28.0,
    "experience_recency": 12.0,
    "github_evidence": 13.5,
    "bonus_malus": 6.0
  },
  "reasoning": "Explanation of adjustments made"
}"""
        
        super().__init__(
            name="AggregatorAgent",
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500
        )
    
    def aggregate_hybrid(
        self,
        semantic_features: Dict,
        judge_scores: Dict,
        github_info: Dict,
        experience_info: List[Dict],
        merged_json: Dict
    ) -> Dict:
        """
        Aggregate scores using hybrid approach.
        
        Args:
            semantic_features: Semantic similarity features
            judge_scores: Judge scores output
            github_info: GitHub data
            experience_info: Experience list
            merged_json: Full merged JSON for context
        
        Returns:
            Dictionary with total_score and breakdown
        """
        # Step 1: Get baseline from rule-based aggregator (30%)
        baseline_result = aggregate_scores(
            semantic_features,
            judge_scores,
            github_info,
            experience_info,
            merged_json
        )
        baseline_score = baseline_result.get("total_score", 0)
        baseline_breakdown = baseline_result.get("breakdown", {})
        
        # Step 2: Agentic adjustment (70%)
        agentic_result = self._agentic_adjustment(
            baseline_score,
            baseline_breakdown,
            semantic_features,
            judge_scores,
            github_info,
            experience_info,
            merged_json
        )
        
        # Step 3: Combine (30% baseline + 70% agentic)
        agentic_score = agentic_result.get("total_score", baseline_score)
        final_score = int(0.3 * baseline_score + 0.7 * agentic_score)
        final_score = max(0, min(100, final_score))  # Clamp to 0-100
        
        # Use agentic breakdown if available, otherwise baseline
        final_breakdown = agentic_result.get("breakdown", baseline_breakdown)
        
        return {
            "total_score": final_score,
            "baseline_score": baseline_score,
            "agentic_score": agentic_score,
            "agentic_adjustment": final_score - baseline_score,
            "breakdown": final_breakdown,
            "reasoning": agentic_result.get("reasoning", "Standard aggregation")
        }
    
    def _agentic_adjustment(
        self,
        baseline_score: int,
        baseline_breakdown: Dict,
        semantic_features: Dict,
        judge_scores: Dict,
        github_info: Dict,
        experience_info: List[Dict],
        merged_json: Dict
    ) -> Dict:
        """
        Apply agentic reasoning to adjust scores.
        
        Args:
            baseline_score: Baseline score from rule-based aggregator
            baseline_breakdown: Baseline breakdown
            semantic_features: Semantic features
            judge_scores: Judge scores
            github_info: GitHub info
            experience_info: Experience info
            merged_json: Merged JSON
        
        Returns:
            Agentic-adjusted result
        """
        # Build context for LLM
        context = {
            "baseline_score": baseline_score,
            "baseline_breakdown": baseline_breakdown,
            "semantic_similarity": semantic_features.get("sim_profile_to_jd", 0.0),
            "judge_avg": sum(
                s.get("score", 0) for s in judge_scores.get("judge_scores", [])
            ) / max(1, len(judge_scores.get("judge_scores", []))),
            "judge_scores_count": len(judge_scores.get("judge_scores", [])),
            "judge_scores_detail": [
                {"criterion": s.get("criterion", ""), "score": s.get("score", 0)}
                for s in judge_scores.get("judge_scores", [])[:10]  # First 10 for context
            ],
            "github_activity": github_info.get("commits_last_12m", 0),
            "experience_count": len(experience_info),
            "job_title": merged_json.get("job_description", {}).get("title", "")
        }
        
        user_prompt = f"""Given the baseline score and context, determine if any adjustments are needed:

Baseline Score: {baseline_score}
Breakdown: {json.dumps(baseline_breakdown, indent=2)}
Context: {json.dumps(context, indent=2)}

Consider:
1. Is the baseline score appropriate for this candidate-job match?
2. Are there any factors that should increase/decrease the score?
3. What adjustments (if any) should be made to the breakdown?

Respond with JSON containing total_score, breakdown, and reasoning."""
        
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
            
            # Validate and merge with baseline
            total_score = result.get("total_score", baseline_score)
            total_score = max(0, min(100, int(total_score)))
            
            # CRITICAL: Preserve penalties and GitHub evidence from baseline breakdown
            breakdown = result.get("breakdown", {})
            # Merge with baseline to ensure penalties and GitHub evidence are included
            final_breakdown = baseline_breakdown.copy()
            
            # Update semantic_fit (no validation needed)
            if "semantic_fit" in breakdown:
                final_breakdown["semantic_fit"] = breakdown["semantic_fit"]
            
            # Special handling for experience_recency: preserve baseline if agentic gives 0 but baseline has value
            if "experience_recency" in breakdown:
                agentic_recency = breakdown.get("experience_recency", 0)
                baseline_recency = baseline_breakdown.get("experience_recency", 0)
                # If agentic gives 0 but baseline has a value (meaning there IS recent experience), preserve baseline
                if agentic_recency == 0 and baseline_recency > 0:
                    logger.warning(f"Agentic adjustment set experience_recency to 0, preserving baseline value: {baseline_recency}")
                    final_breakdown["experience_recency"] = baseline_recency
                else:
                    final_breakdown["experience_recency"] = agentic_recency
            else:
                # If agentic didn't provide experience_recency, use baseline
                final_breakdown["experience_recency"] = baseline_breakdown.get("experience_recency", 0)
            
            # CRITICAL: Always preserve baseline role_competency - it's calculated from judge scores
            # Agentic adjustments should not modify role_competency as it's based on objective judge scores
            baseline_role = baseline_breakdown.get("role_competency", 0)
            if "role_competency" in breakdown:
                agentic_role = breakdown.get("role_competency", 0)
                # Only use agentic if it's very close to baseline (within 10%) and reasonable
                if abs(agentic_role - baseline_role) <= baseline_role * 0.1 and 5 <= agentic_role <= 30:
                    logger.info(f"Agentic role_competency ({agentic_role}) close to baseline ({baseline_role}), using agentic")
                    final_breakdown["role_competency"] = agentic_role
                else:
                    logger.info(f"Preserving baseline role_competency: {baseline_role} (agentic: {agentic_role})")
                    final_breakdown["role_competency"] = baseline_role
            else:
                # If agentic didn't provide role_competency, use baseline
                final_breakdown["role_competency"] = baseline_role
            
            # CRITICAL: Always preserve bonus_malus from baseline (agentic shouldn't adjust this)
            # bonus_malus is calculated from certifications/endorsements, not agentic reasoning
            baseline_bonus = baseline_breakdown.get("bonus_malus", 0)
            if baseline_bonus != 0:
                logger.info(f"Preserving baseline bonus_malus: {baseline_bonus} (agentic value ignored)")
                final_breakdown["bonus_malus"] = baseline_bonus
            else:
                # Only use agentic if baseline is 0
                final_breakdown["bonus_malus"] = breakdown.get("bonus_malus", 0)
            
            # CRITICAL: Preserve GitHub evidence from baseline if agentic adjustment set it to 0 or missing
            if "github_evidence" in breakdown:
                agentic_github = breakdown.get("github_evidence", 0)
                baseline_github = baseline_breakdown.get("github_evidence", 0)
                # Use baseline if agentic set it to 0 but baseline has a value
                if agentic_github == 0 and baseline_github > 0:
                    logger.warning(f"Agentic adjustment set GitHub evidence to 0, preserving baseline value: {baseline_github}")
                    final_breakdown["github_evidence"] = baseline_github
                else:
                    final_breakdown["github_evidence"] = agentic_github
            else:
                # If agentic didn't provide GitHub evidence, use baseline
                final_breakdown["github_evidence"] = baseline_breakdown.get("github_evidence", 0)
            
            # Ensure penalties are always included from baseline
            if "skill_mismatch_penalty" in baseline_breakdown:
                final_breakdown["skill_mismatch_penalty"] = baseline_breakdown["skill_mismatch_penalty"]
            if "technology_mismatch_penalty" in baseline_breakdown:
                final_breakdown["technology_mismatch_penalty"] = baseline_breakdown["technology_mismatch_penalty"]
            
            # Recalculate total_score from final_breakdown to ensure consistency
            total_score = (
                final_breakdown.get("semantic_fit", 0) +
                final_breakdown.get("role_competency", 0) +
                final_breakdown.get("experience_recency", 0) +
                final_breakdown.get("github_evidence", 0) +
                final_breakdown.get("bonus_malus", 0) -
                final_breakdown.get("skill_mismatch_penalty", 0) -
                final_breakdown.get("technology_mismatch_penalty", 0)
            )
            # Clamp to 0-100 and round to integer
            total_score = max(0, min(100, int(round(total_score))))
            logger.info(f"Recalculated total_score from breakdown: {total_score} (components: semantic_fit={final_breakdown.get('semantic_fit', 0)}, role_competency={final_breakdown.get('role_competency', 0)}, experience_recency={final_breakdown.get('experience_recency', 0)}, github_evidence={final_breakdown.get('github_evidence', 0)}, bonus_malus={final_breakdown.get('bonus_malus', 0)}, skill_penalty={final_breakdown.get('skill_mismatch_penalty', 0)}, tech_penalty={final_breakdown.get('technology_mismatch_penalty', 0)})")
            
            reasoning = result.get("reasoning", "Agentic adjustment applied")
            
            return {
                "total_score": total_score,
                "breakdown": final_breakdown,
                "reasoning": reasoning
            }
            
        except Exception as e:
            logger.error(f"Agentic adjustment failed: {str(e)}, using baseline")
            return {
                "total_score": baseline_score,
                "breakdown": baseline_breakdown,
                "reasoning": "Agentic adjustment failed, using baseline"
            }
    
    def determine_weights(self, context: Dict) -> Dict:
        """
        Determine weight distribution based on context.
        
        Args:
            context: Context information
        
        Returns:
            Dictionary with weight distribution
        """
        # Default weights
        weights = {
            "semantic_fit": 0.30,
            "role_competency": 0.30,
            "experience_recency": 0.15,
            "github_evidence": 0.15,
            "bonus_malus": 0.10
        }
        
        # Adjust based on context
        job_title = context.get("job_title", "").lower()
        
        if "senior" in job_title or "lead" in job_title:
            # Senior roles: more weight on experience and competency
            weights["role_competency"] = 0.35
            weights["experience_recency"] = 0.20
            weights["semantic_fit"] = 0.25
            weights["github_evidence"] = 0.10
        elif "junior" in job_title or "intern" in job_title:
            # Junior roles: more weight on potential and GitHub
            weights["github_evidence"] = 0.20
            weights["semantic_fit"] = 0.35
            weights["role_competency"] = 0.25
            weights["experience_recency"] = 0.10
        
        return weights
    
    def adjust_for_context(self, baseline_score: float, context: Dict) -> float:
        """
        Adjust score based on context.
        
        Args:
            baseline_score: Baseline score
            context: Context information
        
        Returns:
            Adjusted score
        """
        adjustment = 0
        
        # Adjust based on job level
        job_title = context.get("job_title", "").lower()
        if "senior" in job_title or "lead" in job_title:
            # Senior roles: expect higher scores
            if baseline_score < 70:
                adjustment = -5  # Penalize low scores for senior roles
        elif "junior" in job_title or "intern" in job_title:
            # Junior roles: more lenient
            if baseline_score > 60:
                adjustment = 5  # Boost good scores for junior roles
        
        # Adjust based on GitHub activity
        github_activity = context.get("github_activity", 0)
        if github_activity > 100:
            adjustment += 2  # Active GitHub profile
        elif github_activity == 0:
            adjustment -= 1  # No GitHub activity
        
        return max(0, min(100, baseline_score + adjustment))
    
    def execute(self, state: Dict) -> Dict:
        """
        Execute aggregator agent.
        
        Args:
            state: Current evaluation state or aggregation request
        
        Returns:
            Aggregated scores
        """
        if isinstance(state, EvaluationState):
            # CRITICAL: Use original judge_scores for role_competency calculation, not critic_scores
            # Critic scores may have adjusted individual scores, but role_competency should be based on original judge scores
            # We'll use judge_scores for aggregation, but log if critic_scores exist
            judge_scores_to_use = state.judge_scores or []
            if state.critic_scores and state.judge_scores:
                logger.info(f"Using original judge_scores ({len(judge_scores_to_use)} criteria) for role_competency calculation. Critic reviewed {len(state.critic_scores)} criteria.")
                # Log if critic made adjustments
                for i, (judge_score, critic_score) in enumerate(zip(judge_scores_to_use, state.critic_scores)):
                    if judge_score.get("score") != critic_score.get("score"):
                        logger.info(f"  Critic adjusted {judge_score.get('criterion')}: {judge_score.get('score')} → {critic_score.get('score')}")
            elif state.critic_scores:
                logger.warning("Only critic_scores available, using them (judge_scores missing)")
                judge_scores_to_use = state.critic_scores
            
            # CRITICAL: Ensure GitHub data is available for aggregation
            github_info = state.github_data or {}
            if not github_info:
                logger.info("No GitHub data in state - scoring as 0.0 (neutral, not penalized)")
                # Use empty dict to ensure neutral scoring
                github_info = {}
            else:
                repos_count = len(github_info.get("repos", []))
                commits = github_info.get("commits_last_12m", 0)
                prs = github_info.get("external_prs_merged", 0)
                logger.info(f"GitHub data for aggregation: {repos_count} repos, {commits} commits, {prs} PRs")
            
            # Aggregate from state
            return self.aggregate_hybrid(
                state.semantic_features or {},
                {"judge_scores": judge_scores_to_use},
                github_info,  # Use explicitly checked GitHub data
                state.merged_json.get("candidate", {}).get("experience", []) if state.merged_json else [],
                state.merged_json or {}
            )
        else:
            # Direct aggregation request
            return self.aggregate_hybrid(
                state.get("semantic_features", {}),
                state.get("judge_scores", {}),
                state.get("github_info", {}),
                state.get("experience_info", []),
                state.get("merged_json", {})
            )

