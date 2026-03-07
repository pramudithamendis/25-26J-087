"""
Agentic Orchestrator for CV evaluation.

Main entry point for agentic evaluation. Coordinates all agents and manages
dynamic workflow (not fixed pipeline). Handles agent communication and fallback.
"""

from typing import Dict, List, Optional
from bson import ObjectId
import logging
import time
from app.models.user_model import users_collection
from app.models.job_model import jobs_collection
from app.config import settings
from .state import EvaluationState, EvaluationStage
from .planning_agent import PlanningAgent
from .extraction_agent import ExtractionAgent
from .verification_agent import VerificationAgent
from .judge_agent import JudgeAgent
from .critic_agent import CriticAgent
from .aggregator_agent import AggregatorAgent
from .dataset_guided_agent import DatasetGuidedAgent
from app.services.normalization import normalize_skills
from app.services.semantic import build_semantic_features
from app.services.role_classifier import classify_roles
from app.services.extractors.cv_extractor import extract_handle_from_url

logger = logging.getLogger(__name__)


class AgenticOrchestrator:
    """
    Orchestrates agentic evaluation workflow.
    
    Coordinates all agents, manages dynamic workflow, handles agent communication,
    and implements fallback mechanisms.
    """
    
    def __init__(self):
        """Initialize orchestrator with all agents"""
        self.planning_agent = PlanningAgent()
        self.extraction_agent = ExtractionAgent()
        self.verification_agent = VerificationAgent()
        self.judge_agent = JudgeAgent()
        self.critic_agent = CriticAgent()
        self.aggregator_agent = AggregatorAgent()
        self.dataset_guided_agent = DatasetGuidedAgent()
        
        self.max_iterations = getattr(settings, 'MAX_AGENT_ITERATIONS', 20)
        self.fallback_to_pipeline = getattr(settings, 'AGENTIC_FALLBACK_TO_PIPELINE', True)
    
    def run_agentic_evaluation(self, user_id: str, job_id: str) -> Dict:
        """
        Run full agentic evaluation pipeline.
        
        Args:
            user_id: MongoDB user document ID
            job_id: MongoDB job document ID
        
        Returns:
            Complete evaluation result
        """
        try:
            # Initialize state
            state = EvaluationState(user_id, job_id)
            state.start_time = time.time()
            
            # Load user and job from MongoDB
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            job = jobs_collection.find_one({"_id": ObjectId(job_id)})
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Map user to candidate structure for compatibility
            candidate = {
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "github_handle": user.get("github_handle", ""),
                "github_url": user.get("github_url", ""),
                "cv_file_path": user.get("cv_file_path"),
                "linkedin_file_path": user.get("linkedin_file_path")
            }
            state.candidate_data = candidate
            state.job_data = job
            
            logger.info(f"=== Starting evaluation: candidate={user_id}, job={job_id} ===")
            
            # Track action history in state for better loop detection
            if not hasattr(state, 'action_history'):
                state.action_history = []
            max_repeat_actions = 3
            
            # Main agentic loop
            while self.planning_agent.should_continue(state) and not state.is_complete():
                state.increment_iteration()
                
                if state.iteration_count > self.max_iterations:
                    logger.warning(f"Max iterations ({self.max_iterations}) reached")
                    # Complete evaluation with available data
                    self._complete_evaluation_if_needed(state)
                    break
                
                # Planning agent decides next action
                try:
                    plan = self.planning_agent.plan_next_action(state)
                    action = plan.get("action")
                    agent_name = plan.get("agent")
                    next_stage = plan.get("next_stage")
                    
                    logger.info(f"Iteration {state.iteration_count}: Action={action}, Agent={agent_name}")
                    
                    # Enhanced loop detection - track action history
                    state.action_history.append(action)
                    if len(state.action_history) > 10:  # Keep last 10 actions
                        state.action_history.pop(0)
                    
                    # Check for loops: same action repeated 3+ times in a row
                    recent_actions = state.action_history[-max_repeat_actions:] if len(state.action_history) >= max_repeat_actions else state.action_history
                    if len(recent_actions) >= max_repeat_actions and len(set(recent_actions)) == 1:
                        logger.warning(f"🚨 Loop detected: action '{action}' repeated {max_repeat_actions} times in a row")
                        logger.warning(f"   Action history: {state.action_history[-5:]}")
                        logger.warning(f"   Current state: extracted={state.extracted}, verified={state.verified}")
                        
                        # Force progression by using default action logic with context
                        forced_action = self._get_forced_action(state)
                        if forced_action and forced_action != action:
                            logger.info(f"   Forcing progression: {forced_action} instead of {action}")
                            action = forced_action
                            agent_name = self._get_agent_for_action(action)
                            next_stage = self._get_stage_for_action(action)
                            # Don't reset action_history, keep it for tracking
                        else:
                            logger.warning(f"   No alternative action found, skipping '{action}' and trying next step")
                            # Skip this action and try to complete evaluation
                            if state.aggregated_score:
                                logger.info("   Evaluation has aggregated score, completing evaluation")
                                self._complete_evaluation_if_needed(state)
                                break
                            # Try to force next logical step
                            if not state.is_extracted("jd") and state.job_data:
                                action = "extract_jd"
                            elif not state.semantic_features:
                                action = "calculate_similarity"
                            elif not state.judge_scores:
                                action = "score_candidate"
                            elif not state.aggregated_score:
                                action = "aggregate"
                            else:
                                action = "complete"
                            agent_name = self._get_agent_for_action(action)
                            next_stage = self._get_stage_for_action(action)
                            logger.info(f"   Forced next step: {action}")
                    
                    # Update stage
                    if next_stage:
                        try:
                            state.set_stage(EvaluationStage[next_stage])
                        except KeyError:
                            pass
                    
                    # Execute action based on plan
                    result = self._execute_action(action, agent_name, state)
                    
                    # Update state based on result
                    self._update_state_from_result(state, action, result)
                    
                except Exception as e:
                    logger.error(f"Error in agentic loop: {str(e)}")
                    recovery = self.planning_agent.handle_failure(e, state)
                    if recovery.get("action") == "skip":
                        continue
                    elif recovery.get("action") == "retry":
                        state.iteration_count -= 1  # Don't count retry as new iteration
                        continue
                    else:
                        # Fallback to pipeline on critical errors
                        if self.fallback_to_pipeline:
                            logger.info("Falling back to pipeline due to error")
                            return self._fallback_to_pipeline(user_id, job_id)
                        raise
            
            # Complete evaluation if not already complete
            if not state.is_complete():
                logger.warning("Evaluation not complete after loop, completing with available data")
                self._complete_evaluation_if_needed(state)
            
            # Build final result
            state.end_time = time.time()
            result = self._build_final_result(state)
            
            # Log final summary
            total_score = result.get("total_score", 0)
            decision = result.get("decision", "Unknown")
            breakdown = result.get("breakdown", {})
            logger.info(f"=== Evaluation complete: score={total_score}, decision={decision} ===")
            logger.info(f"Breakdown: semantic_fit={breakdown.get('semantic_fit', 0)}, role_competency={breakdown.get('role_competency', 0)}, experience_recency={breakdown.get('experience_recency', 0)}, github_evidence={breakdown.get('github_evidence', 0)}, bonus_malus={breakdown.get('bonus_malus', 0)}, skill_penalty={breakdown.get('skill_mismatch_penalty', 0)}, tech_penalty={breakdown.get('technology_mismatch_penalty', 0)}")
            logger.info(f"Evaluation time: {state.end_time - state.start_time:.2f}s, iterations: {state.iteration_count}")
            
            return result
            
        except Exception as e:
            logger.error(f"Agentic evaluation failed: {str(e)}")
            if self.fallback_to_pipeline:
                logger.info("Falling back to pipeline")
                return self._fallback_to_pipeline(user_id, job_id)
            raise
    
    def _execute_action(self, action: str, agent_name: Optional[str], state: EvaluationState) -> Dict:
        """Execute action using appropriate agent"""
        
        if action == "extract_cv":
            return self._extract_cv(state)
        elif action == "extract_linkedin":
            return self._extract_linkedin(state)
        elif action == "extract_github":
            return self._extract_github(state)
        elif action == "extract_jd":
            return self._extract_jd(state)
        elif action == "verify_github":
            return self._verify_github(state)
        elif action == "verify_consistency":
            return self._verify_consistency(state)
        elif action == "calculate_similarity":
            return self._calculate_similarity(state)
        elif action == "score_candidate":
            return self._score_candidate(state)
        elif action == "review_scores":
            return self._review_scores(state)
        elif action == "aggregate":
            return self._aggregate(state)
        elif action == "validate_with_dataset":
            return self._validate_with_dataset(state)
        elif action == "complete":
            return {"status": "complete"}
        else:
            logger.warning(f"Unknown action: {action}")
            return {"status": "unknown_action"}
    
    def _extract_cv(self, state: EvaluationState) -> Dict:
        """Extract CV data"""
        # Check if already extracted
        if state.is_extracted("cv") and state.cv_data:
            logger.info("CV already extracted, skipping redundant extraction")
            return {"status": "skipped", "reason": "Already extracted", "cv_data": state.cv_data}
        
        cv_path = state.candidate_data.get("cv_file_path")
        if not cv_path:
            return {"status": "skipped", "reason": "No CV file path"}
        
        result = self.extraction_agent.execute(state)
        if result.get("cv_data"):
            state.mark_extracted("cv", result["cv_data"])
            state.cv_data = result["cv_data"]
            # Extract GitHub handle from CV
            github_handle = result["cv_data"].get("github_handle", "")
            if github_handle:
                state.candidate_data["github_handle"] = github_handle
                logger.info(f"GitHub handle extracted from CV: {github_handle}")
            else:
                # Fallback: Try to extract handle from user.github_url
                github_url = state.candidate_data.get("github_url", "")
                if github_url:
                    extracted_handle = extract_handle_from_url(github_url)
                    if extracted_handle:
                        state.candidate_data["github_handle"] = extracted_handle
                        logger.info(f"GitHub handle extracted from user.github_url: {extracted_handle}")
                    else:
                        logger.debug(f"Could not extract handle from github_url: {github_url}")
                else:
                    # Final fallback: Use user.github_handle if available
                    user_handle = state.candidate_data.get("github_handle", "")
                    if user_handle:
                        logger.info(f"Using GitHub handle from user.github_handle: {user_handle}")
                    else:
                        logger.info("No GitHub handle found in CV, user.github_url, or user.github_handle")
        
        # CRITICAL: Also update LinkedIn state if LinkedIn was extracted together with CV
        # This prevents redundant LinkedIn extraction later
        if result.get("linkedin_data") and not state.is_extracted("linkedin"):
            state.mark_extracted("linkedin", result["linkedin_data"])
            state.linkedin_data = result["linkedin_data"]
            logger.info(f"LinkedIn also extracted with CV, stored in state: {len(result['linkedin_data'].get('skills_raw', []))} skills found")
        
        return result
    
    def _extract_linkedin(self, state: EvaluationState) -> Dict:
        """Extract LinkedIn data"""
        # Check if already extracted - return early without calling execute()
        if state.is_extracted("linkedin") and state.linkedin_data:
            logger.info("LinkedIn already extracted, skipping redundant extraction")
            return {"status": "skipped", "reason": "Already extracted", "linkedin_data": state.linkedin_data}
        
        linkedin_path = state.candidate_data.get("linkedin_file_path")
        if not linkedin_path:
            return {"status": "skipped", "reason": "No LinkedIn file path"}
        
        # Only call extraction agent if LinkedIn is not already extracted
        # The extraction agent will check state again, but we've already checked here
        result = self.extraction_agent.execute(state)
        if result.get("linkedin_data"):
            state.mark_extracted("linkedin", result["linkedin_data"])
            state.linkedin_data = result["linkedin_data"]
            logger.info(f"LinkedIn extracted and stored in state: {len(result['linkedin_data'].get('skills_raw', []))} skills found")
        return result
    
    def _extract_github(self, state: EvaluationState) -> Dict:
        """Extract GitHub data"""
        # Priority order: 1) CV extraction, 2) Extract from github_url, 3) Use github_handle
        github_handle = ""
        source = ""
        
        # First, check CV data
        if state.cv_data and state.cv_data.get("github_handle", ""):
            github_handle = state.cv_data.get("github_handle", "").strip()
            source = "CV"
        else:
            # Second, try to extract from github_url
            github_url = state.candidate_data.get("github_url", "")
            if github_url:
                extracted_handle = extract_handle_from_url(github_url)
                if extracted_handle:
                    github_handle = extracted_handle
                    source = "user.github_url"
                else:
                    logger.debug(f"Could not extract handle from github_url: {github_url}")
            
            # Third, fallback to github_handle from user
            if not github_handle:
                user_handle = state.candidate_data.get("github_handle", "")
                if user_handle:
                    github_handle = user_handle.strip()
                    source = "user.github_handle"
        
        if not github_handle:
            logger.info("No GitHub handle found in CV, user.github_url, or user.github_handle")
            return {"status": "skipped", "reason": "No GitHub handle"}
        
        logger.info(f"Using GitHub handle: {github_handle} (source: {source})")
        
        # Use verification agent to get GitHub data
        verification_result = self.verification_agent.verify_github_profile(github_handle)
        if verification_result.get("verified"):
            state.github_data = verification_result.get("data")
            state.mark_extracted("github", state.github_data)
            state.mark_verified("github_handle", True)
        return verification_result
    
    def _extract_jd(self, state: EvaluationState) -> Dict:
        """Extract job description data"""
        # Check if already extracted
        if state.is_extracted("jd") and state.jd_data:
            logger.info("JD already extracted, skipping redundant extraction")
            return {"status": "skipped", "reason": "Already extracted", "jd_data": state.jd_data}
        
        jd_text = state.job_data.get("jd_text", "")
        if not jd_text:
            return {"status": "error", "reason": "No JD text"}
        
        # Fix the JD text if it has "ob Description" issue
        if jd_text.startswith("ob Description"):
            jd_text = "Job Description" + jd_text[14:]
        
        # Extract JD directly using the tool (not through extraction agent)
        # The extraction agent's execute() method doesn't extract JD, only CV/LinkedIn
        from app.services.agents.tools.extraction_tools import extract_jd_tool
        # Pass job_id for caching to ensure same job always extracts same skills
        jd_result = extract_jd_tool(jd_text, job_id=state.job_id)
        
        if jd_result.get("status") == "success" and jd_result.get("data"):
            jd_data = jd_result["data"]
            # CRITICAL: Set state.jd_data and mark as extracted to ensure persistence
            state.jd_data = jd_data
            state.mark_extracted("jd", jd_data)
            logger.info(f"JD extracted and stored in state: title={jd_data.get('title', 'N/A')}, must_have count={len(jd_data.get('must_have', []))}")
            return {"status": "success", "jd_data": jd_data}
        else:
            error_msg = jd_result.get("error", "Unknown error")
            logger.error(f"JD extraction failed: {error_msg}")
            return {"status": "error", "reason": error_msg, "jd_data": None}
    
    def _verify_github(self, state: EvaluationState) -> Dict:
        """Verify GitHub handle"""
        github_handle = (
            state.cv_data.get("github_handle", "") if state.cv_data
            else state.candidate_data.get("github_handle", "")
        )
        
        if not github_handle:
            return {"status": "skipped", "reason": "No GitHub handle"}
        
        result = self.verification_agent.verify_github_profile(github_handle)
        state.mark_verified("github_handle", result.get("verified", False))
        if result.get("data"):
            state.github_data = result["data"]
        return result
    
    def _verify_consistency(self, state: EvaluationState) -> Dict:
        """Verify consistency between CV and LinkedIn"""
        # Check if already verified to prevent loops
        if state.is_verified("experience_consistency"):
            logger.info("Consistency already verified, skipping redundant verification")
            return {"status": "skipped", "reason": "Already verified", "consistent": True}
        
        if not state.cv_data or not state.linkedin_data:
            # Mark as verified even if skipped to prevent loops
            state.mark_verified("experience_consistency", True)
            return {"status": "skipped", "reason": "Missing CV or LinkedIn data", "consistent": True}
        
        contradictions = self.verification_agent.check_consistency(state.cv_data, state.linkedin_data)
        state.mark_verified("experience_consistency", len(contradictions) == 0)
        return {"contradictions": contradictions, "consistent": len(contradictions) == 0}
    
    def _calculate_similarity(self, state: EvaluationState) -> Dict:
        """Calculate semantic similarity"""
        # Build candidate profile text
        candidate_block = self._build_candidate_profile_text(state)
        
        # Get JD text - prefer from jd_data if available, otherwise from job_data
        jd_block = ""
        if state.jd_data and state.jd_data.get("jd_text"):
            jd_block = state.jd_data["jd_text"]
        elif state.job_data and state.job_data.get("jd_text"):
            jd_block = state.job_data["jd_text"]
        
        if not jd_block:
            logger.warning("No JD text available for semantic similarity calculation")
        
        github_summary = self._build_github_summary(state.github_data or {})
        
        semantic_features = build_semantic_features(candidate_block, jd_block, github_summary)
        state.set_intermediate_result("semantic_features", semantic_features)
        state.semantic_features = semantic_features
        return {"semantic_features": semantic_features}
    
    def _score_candidate(self, state: EvaluationState) -> Dict:
        """Score candidate using judge agent"""
        # CRITICAL: Ensure JD is extracted before scoring
        # Judge agent needs JD data for accurate scoring and technology mismatch detection
        if not state.is_extracted("jd") or not state.jd_data:
            logger.info("JD not extracted before scoring, extracting now")
            jd_result = self._extract_jd(state)
            if jd_result.get("status") == "error":
                logger.warning(f"JD extraction failed before scoring: {jd_result.get('reason')}")
            elif jd_result.get("jd_data"):
                logger.info("JD successfully extracted before scoring")
        
        # Normalize skills first if not done
        if not state.normalized_skills:
            skills_raw = []
            if state.cv_data:
                skills_raw.extend(state.cv_data.get("skills_raw", []))
            if state.linkedin_data:
                skills_raw.extend(state.linkedin_data.get("skills_raw", []))
            state.normalized_skills = normalize_skills(skills_raw)
            state.set_intermediate_result("normalized_skills", state.normalized_skills)
        
        result = self.judge_agent.execute(state)
        judge_scores = result.get("judge_scores", [])
        state.set_intermediate_result("judge_scores", result)
        state.judge_scores = judge_scores
        
        # Log judge scores for debugging
        if judge_scores:
            score_summary = [f"{s.get('criterion', 'N/A')}: {s.get('score', 0)}" for s in judge_scores]
            avg_score = sum(s.get("score", 0) for s in judge_scores) / len(judge_scores)
            logger.info(f"Stage: SCORING, Judge scores: {len(judge_scores)} criteria, avg={avg_score:.2f}")
            logger.info(f"  Individual scores: {score_summary}")
        
        return result
    
    def _review_scores(self, state: EvaluationState) -> Dict:
        """Review scores using critic agent"""
        # Build merged_json for critic
        merged_json = self._build_merged_json(state)
        state.merged_json = merged_json
        
        result = self.critic_agent.execute(state)
        critic_scores = result.get("judge_scores", [])
        state.set_intermediate_result("critic_scores", result)
        state.critic_scores = critic_scores
        
        # Log if critic adjusted any scores
        if critic_scores and state.judge_scores:
            adjustments = []
            for judge_score, critic_score in zip(state.judge_scores, critic_scores):
                if judge_score.get("score") != critic_score.get("score"):
                    adjustments.append(f"{judge_score.get('criterion')}: {judge_score.get('score')}→{critic_score.get('score')}")
            if adjustments:
                logger.info(f"Critic adjusted scores: {', '.join(adjustments)}")
            else:
                logger.info("Critic reviewed scores: no adjustments made")
        
        # If critic found issues, might need to re-score
        if result.get("flags") or result.get("contradictions"):
            logger.info("Critic found issues, may need re-scoring")
        
        return result
    
    def _aggregate(self, state: EvaluationState) -> Dict:
        """Aggregate scores using aggregator agent"""
        # Ensure semantic features are calculated before aggregation
        if not state.semantic_features:
            logger.warning("Semantic features missing, calculating now before aggregation")
            self._calculate_similarity(state)
        
        # Ensure skills are normalized before aggregation
        if not state.normalized_skills:
            logger.warning("Skills not normalized, normalizing now")
            all_skills = []
            if state.cv_data:
                all_skills.extend(state.cv_data.get("skills_raw", []))
            if state.linkedin_data:
                all_skills.extend(state.linkedin_data.get("skills_raw", []))
            if all_skills:
                state.normalized_skills = normalize_skills(all_skills)
                state.set_intermediate_result("normalized_skills", state.normalized_skills)
        
        # CRITICAL: Ensure GitHub data is available before aggregation
        if not state.github_data:
            logger.warning("GitHub data missing, using empty dict (neutral scoring, not penalized)")
            state.github_data = {}
        else:
            repos_count = len(state.github_data.get("repos", []))
            commits = state.github_data.get("commits_last_12m", 0)
            prs = state.github_data.get("external_prs_merged", 0)
            logger.info(f"GitHub data available for aggregation: {repos_count} repos, {commits} commits, {prs} PRs")
        
        # CRITICAL: Build merged_json before aggregation to ensure all fields are present
        if not state.merged_json:
            logger.warning("merged_json missing, building now before aggregation")
            state.merged_json = self._build_merged_json(state)
        
        # Log to verify must_have skills are present
        job_desc = state.merged_json.get("job_description", {}) if state.merged_json else {}
        must_have = job_desc.get("must_have", [])
        logger.info(f"Before aggregation: merged_json has {len(must_have) if must_have else 0} must-have skills")
        if must_have:
            logger.debug(f"First 5 must-have skills: {must_have[:5]}")
        else:
            logger.warning("WARNING: merged_json has NO must-have skills before aggregation!")
        
        result = self.aggregator_agent.execute(state)
        state.set_intermediate_result("aggregated_score", result)
        state.aggregated_score = result
        
        # Log aggregation results
        total_score = result.get("total_score", 0)
        breakdown = result.get("breakdown", {})
        logger.info(f"Stage: AGGREGATING, Total score: {total_score}")
        logger.info(f"  Breakdown: semantic_fit={breakdown.get('semantic_fit', 0)}, role_competency={breakdown.get('role_competency', 0)}, experience_recency={breakdown.get('experience_recency', 0)}, github_evidence={breakdown.get('github_evidence', 0)}, bonus_malus={breakdown.get('bonus_malus', 0)}, skill_penalty={breakdown.get('skill_mismatch_penalty', 0)}, tech_penalty={breakdown.get('technology_mismatch_penalty', 0)}")
        
        # Determine decision and generate explanations
        role_predictions = self._classify_roles(state)
        job_title = state.jd_data.get("title", "") if state.jd_data else ""
        decision = self._determine_decision(total_score, role_predictions, job_title)
        explanations = self._generate_explanations(state, total_score, breakdown, role_predictions)
        
        # Store aggregated result but don't set final result yet
        # Dataset validation will happen next if enabled
        return result
    
    def _validate_with_dataset(self, state: EvaluationState) -> Dict:
        """Validate and calibrate score using dataset"""
        try:
            result = self.dataset_guided_agent.execute(state)
            
            # Always store result in state, even if it failed
            state.set_dataset_validation(result)
            state.set_stage(EvaluationStage.DATASET_VALIDATION)
            
            # Check if validation was successful
            if result.get("status") == "error" or result.get("status") == "skipped":
                # Validation failed or was skipped, use original score
                original_score = state.aggregated_score.get("total_score", 0) if state.aggregated_score else 0
                logger.info(f"Dataset validation {result.get('status', 'failed')}, using original score: {original_score}")
                
                role_predictions = state.role_predictions or self._classify_roles(state)
                job_title = state.jd_data.get("title", "") if state.jd_data else ""
                decision = self._determine_decision(original_score, role_predictions, job_title)
                role_predictions = self._classify_roles(state)
                explanations = self._generate_explanations(
                    state,
                    original_score,
                    state.aggregated_score.get("breakdown", {}) if state.aggregated_score else {},
                    role_predictions
                )
                
                reason = result.get("reason", result.get("error", "Dataset validation unavailable"))
                explanations.append(f"Dataset validation: {reason}")
                
                state.set_final_result(original_score, decision, role_predictions, explanations)
                return result
            
            # Use calibrated score if confidence is high enough
            confidence = result.get("confidence", 0.0)
            confidence_threshold = 0.7
            original_score = state.aggregated_score.get("total_score", 0) if state.aggregated_score else 0
            calibrated_score = result.get("calibrated_score", original_score)
            
            if confidence >= confidence_threshold:
                # Only use calibrated score if it's different from original or if original is 0
                if calibrated_score != original_score or original_score == 0:
                    logger.info(f"Using calibrated score: {calibrated_score} (confidence: {confidence:.2f}, original: {original_score})")
                    
                    # Update aggregated score with calibrated value
                    if state.aggregated_score:
                        state.aggregated_score["total_score"] = calibrated_score
                        state.aggregated_score["dataset_calibration"] = result
                    
                    # Determine decision and generate explanations with calibrated score
                    role_predictions = self._classify_roles(state) if not state.role_predictions else state.role_predictions
                    job_title = state.jd_data.get("title", "") if state.jd_data else ""
                    decision = self._determine_decision(calibrated_score, role_predictions, job_title)
                    explanations = self._generate_explanations(
                        state, 
                        calibrated_score, 
                        state.aggregated_score.get("breakdown", {}) if state.aggregated_score else {},
                        role_predictions
                    )
                    
                    # Add dataset explanation
                    if result.get("reasoning"):
                        explanations.append(f"Dataset validation: {result['reasoning']}")
                    
                    state.set_final_result(calibrated_score, decision, role_predictions, explanations)
                else:
                    # Calibrated score same as original, use original path
                    logger.info(f"Calibrated score same as original: {original_score} (confidence: {confidence:.2f})")
                    role_predictions = self._classify_roles(state) if not state.role_predictions else state.role_predictions
                    job_title = state.jd_data.get("title", "") if state.jd_data else ""
                    decision = self._determine_decision(original_score, role_predictions, job_title)
                    explanations = self._generate_explanations(
                        state,
                        original_score,
                        state.aggregated_score.get("breakdown", {}) if state.aggregated_score else {},
                        role_predictions
                    )
                    explanations.append(f"Dataset validation: {result.get('reasoning', 'Score aligns with dataset patterns')}")
                    state.set_final_result(original_score, decision, role_predictions, explanations)
            else:
                # Use original score if confidence is low
                logger.info(f"Using original score: {original_score} (confidence: {confidence:.2f})")
                
                role_predictions = self._classify_roles(state) if not state.role_predictions else state.role_predictions
                job_title = state.jd_data.get("title", "") if state.jd_data else ""
                decision = self._determine_decision(original_score, role_predictions, job_title)
                explanations = self._generate_explanations(
                    state,
                    original_score,
                    state.aggregated_score.get("breakdown", {}) if state.aggregated_score else {},
                    role_predictions
                )
                
                if original_score == 0:
                    explanations.append(f"Dataset validation: Found {len(result.get('similar_cases', []))} similar cases (confidence: {confidence:.2f})")
                else:
                    explanations.append(f"Dataset validation confidence too low ({confidence:.2f}), using original score")
                
                state.set_final_result(original_score, decision, role_predictions, explanations)
            
            return result
            
        except Exception as e:
            logger.error(f"Dataset validation failed: {str(e)}", exc_info=True)
            # Create error result
            error_result = {
                "status": "error",
                "error": str(e),
                "original_score": state.aggregated_score.get("total_score", 0) if state.aggregated_score else 0,
                "calibrated_score": state.aggregated_score.get("total_score", 0) if state.aggregated_score else 0,
                "confidence": 0.0,
                "calibration_adjustment": 0,
                "similar_cases": [],
                "validation_status": "error",
                "reasoning": f"Dataset validation failed: {str(e)}"
            }
            state.set_dataset_validation(error_result)
            
            # Fallback to original score
            original_score = state.aggregated_score.get("total_score", 0) if state.aggregated_score else 0
            role_predictions = self._classify_roles(state) if not state.role_predictions else state.role_predictions
            job_title = state.jd_data.get("title", "") if state.jd_data else ""
            decision = self._determine_decision(original_score, role_predictions, job_title)
            explanations = self._generate_explanations(
                state,
                original_score,
                state.aggregated_score.get("breakdown", {}) if state.aggregated_score else {},
                role_predictions
            )
            explanations.append("Dataset validation failed, using original score")
            state.set_final_result(original_score, decision, role_predictions, explanations)
            return error_result
    
    def _update_state_from_result(self, state: EvaluationState, action: str, result: Dict):
        """Update state based on action result"""
        # State updates are handled in individual action methods
        pass
    
    def _get_forced_action(self, state: EvaluationState) -> Optional[str]:
        """Get forced action when loop is detected - provides better context-aware progression"""
        # Force progression through workflow with better context
        # Check what's missing and suggest next logical step
        
        # 1. Extract JD if missing
        if not state.is_extracted("jd") and state.job_data:
            logger.info("Forced action: extract_jd (JD not extracted)")
            return "extract_jd"
        
        # 2. Extract CV if missing
        if not state.is_extracted("cv") and state.candidate_data and state.candidate_data.get("cv_file_path"):
            logger.info("Forced action: extract_cv (CV not extracted)")
            return "extract_cv"
        
        # 3. Extract GitHub if CV is extracted but GitHub is not
        if state.is_extracted("cv") and not state.is_extracted("github"):
            github_handle = None
            if state.cv_data:
                github_handle = state.cv_data.get("github_handle", "")
            if not github_handle and state.candidate_data:
                github_handle = state.candidate_data.get("github_handle", "") or state.candidate_data.get("github_url", "")
            if github_handle:
                logger.info("Forced action: extract_github (GitHub handle available but not extracted)")
                return "extract_github"
        
        # 4. Calculate similarity if CV and JD are extracted but similarity not calculated
        if state.is_extracted("cv") and state.is_extracted("jd") and not state.semantic_features:
            logger.info("Forced action: calculate_similarity (CV and JD extracted but similarity not calculated)")
            return "calculate_similarity"
        
        # 5. Score candidate if similarity is calculated but judge scores not available
        if state.semantic_features and not state.judge_scores:
            logger.info("Forced action: score_candidate (Similarity calculated but judge scores not available)")
            return "score_candidate"
        
        # 6. Review scores if judge scores available but critic scores not
        if state.judge_scores and not state.critic_scores:
            logger.info("Forced action: review_scores (Judge scores available but critic scores not)")
            return "review_scores"
        
        # 7. Aggregate if critic scores available but aggregated score not
        if state.critic_scores and not state.aggregated_score:
            logger.info("Forced action: aggregate (Critic scores available but aggregated score not)")
            return "aggregate"
        
        # 8. Validate with dataset if aggregated score available but dataset validation not done
        if state.aggregated_score and not state.dataset_validation and settings.DATASET_VALIDATION_ENABLED:
            logger.info("Forced action: validate_with_dataset (Aggregated score available but dataset validation not done)")
            return "validate_with_dataset"
        
        # 9. Complete if aggregated score available
        if state.aggregated_score:
            logger.info("Forced action: complete (Aggregated score available, evaluation can be completed)")
            return "complete"
        
        logger.warning("No forced action found - evaluation may be stuck")
        return None
    
    def _get_agent_for_action(self, action: str) -> Optional[str]:
        """Get agent name for action"""
        action_to_agent = {
            "extract_cv": "extraction",
            "extract_linkedin": "extraction",
            "extract_github": "extraction",
            "extract_jd": "extraction",
            "verify_github": "verification",
            "verify_consistency": "verification",
            "calculate_similarity": "analysis",
            "score_candidate": "judge",
            "review_scores": "critic",
            "aggregate": "aggregator",
            "validate_with_dataset": "dataset_guided",
            "complete": None
        }
        return action_to_agent.get(action)
    
    def _get_stage_for_action(self, action: str) -> Optional[str]:
        """Get stage for action"""
        action_to_stage = {
            "extract_cv": "EXTRACTING",
            "extract_linkedin": "EXTRACTING",
            "extract_github": "EXTRACTING",
            "extract_jd": "EXTRACTING",
            "verify_github": "VERIFYING",
            "verify_consistency": "VERIFYING",
            "calculate_similarity": "SCORING",
            "score_candidate": "SCORING",
            "review_scores": "REVIEWING",
            "aggregate": "AGGREGATING",
            "validate_with_dataset": "DATASET_VALIDATION",
            "complete": "COMPLETED"
        }
        return action_to_stage.get(action)
    
    def _complete_evaluation_if_needed(self, state: EvaluationState):
        """Complete evaluation with available data if not already complete"""
        try:
            # If we have aggregated score, we can complete
            if state.aggregated_score and state.total_score is None:
                total_score = state.aggregated_score.get("total_score", 0)
                role_predictions = self._classify_roles(state) if not state.role_predictions else state.role_predictions
                job_title = state.jd_data.get("title", "") if state.jd_data else ""
                decision = self._determine_decision(total_score, role_predictions, job_title)
                explanations = self._generate_explanations(
                    state,
                    total_score,
                    state.aggregated_score.get("breakdown", {}),
                    role_predictions
                ) if not state.explanations else state.explanations
                
                state.set_final_result(total_score, decision, role_predictions, explanations)
                logger.info(f"Completed evaluation with score: {total_score}, decision: {decision}")
            # If we don't have aggregated score but have judge scores, try to aggregate
            elif state.judge_scores and not state.aggregated_score:
                logger.warning("Attempting to complete evaluation with judge scores only")
                # Try to aggregate with available data
                if state.semantic_features:
                    result = self.aggregator_agent.execute(state)
                    state.set_intermediate_result("aggregated_score", result)
                    state.aggregated_score = result
                    total_score = result.get("total_score", 0)
                    role_predictions = self._classify_roles(state)
                    job_title = state.jd_data.get("title", "") if state.jd_data else ""
                    decision = self._determine_decision(total_score, role_predictions, job_title)
                    explanations = self._generate_explanations(
                        state,
                        total_score,
                        result.get("breakdown", {}),
                        role_predictions
                    )
                    state.set_final_result(total_score, decision, role_predictions, explanations)
                    logger.info(f"Completed evaluation with partial data: score: {total_score}, decision: {decision}")
            # If we have nothing, set defaults
            elif state.total_score is None:
                logger.error("No evaluation data available, setting defaults")
                state.set_final_result(0, "Do Not Proceed", [], ["Evaluation incomplete - insufficient data"])
        except Exception as e:
            logger.error(f"Error completing evaluation: {str(e)}")
            # Set defaults as last resort
            if state.total_score is None:
                state.set_final_result(0, "Do Not Proceed", [], [f"Evaluation failed: {str(e)}"])
    
    def _build_merged_json(self, state: EvaluationState) -> Dict:
        """Build merged JSON from state"""
        # Combine skills
        all_skills = []
        if state.cv_data:
            all_skills.extend(state.cv_data.get("skills_raw", []))
        if state.linkedin_data:
            all_skills.extend(state.linkedin_data.get("skills_raw", []))
        all_skills = list(set(all_skills))
        
        # Combine experience (prefer CV)
        all_experience = []
        if state.cv_data:
            all_experience = state.cv_data.get("experience", [])
        if not all_experience and state.linkedin_data:
            all_experience = state.linkedin_data.get("experience", [])
        
        # Combine education
        all_education = []
        if state.cv_data:
            all_education.extend(state.cv_data.get("education", []))
        if state.linkedin_data:
            all_education.extend(state.linkedin_data.get("education", []))
        all_education = list(set(all_education))
        
        # CRITICAL: Ensure GitHub data is included in merged_json
        github_data = state.github_data or {}
        if not github_data:
            logger.info("No GitHub data in state, using empty dict for merged_json (neutral scoring)")
        
        candidate = {
            "skills_raw": all_skills,
            "skills_canonical": state.normalized_skills or [],
            "experience": all_experience,
            "education": all_education,
            "github": github_data,  # Always include, even if empty
            "cv_data": state.cv_data or {},
            "linkedin_data": state.linkedin_data or {}
        }
        
        if state.linkedin_data:
            candidate["certifications"] = state.linkedin_data.get("certifications", [])
            candidate["publications"] = state.linkedin_data.get("publications", [])
            candidate["projects"] = state.linkedin_data.get("projects", [])
            candidate["linkedin"] = {
                "endorsements": state.linkedin_data.get("endorsements", []),
                "summary": state.linkedin_data.get("summary", "")
            }
        
        # Build job description, ensuring ALL fields are preserved
        # CRITICAL: Always use the latest jd_data from state (from extraction)
        # This ensures technology mismatch detection uses the most recent extracted data
        # Check if JD is already extracted first
        if state.is_extracted("jd") and state.jd_data:
            # Make a copy to avoid mutating the original
            job_description = dict(state.jd_data)
            logger.debug(f"Using extracted JD data from state: title={job_description.get('title', 'N/A')}, must_have count={len(job_description.get('must_have', []))}")
        elif state.job_data and state.job_data.get("jd_text"):
            # JD not extracted yet, extract it ONCE and update state
            logger.info("JD not yet extracted, extracting now and storing in state")
            from app.services.extractors.jd_extractor import extract_from_jd
            jd_text = state.job_data.get("jd_text", "")
            # Fix the JD text if it has "ob Description" issue
            if jd_text.startswith("ob Description"):
                jd_text = "Job Description" + jd_text[14:]
            
            try:
                extracted = extract_from_jd(jd_text)
                if extracted:
                    # Store in state to prevent future extractions
                    state.jd_data = extracted
                    state.mark_extracted("jd", extracted)
                    job_description = dict(extracted)
                    logger.info(f"JD extracted and stored in state: title={job_description.get('title', 'N/A')}, must_have count={len(job_description.get('must_have', []))}")
                else:
                    job_description = {}
                    logger.warning("JD extraction returned empty result")
            except Exception as e:
                logger.error(f"JD extraction failed: {str(e)}")
                job_description = {}
        else:
            job_description = {}
            logger.warning("No jd_data in state and no jd_text in job_data")
        
        # If jd_data is missing fields, try to get them from job_data (fallback only)
        if state.job_data and not job_description.get("must_have"):
            # Ensure title is present
            if not job_description.get("title") and state.job_data.get("title"):
                job_description["title"] = state.job_data["title"]
            
            # Ensure must_have is present (fallback)
            if not job_description.get("must_have") and state.job_data.get("must_have"):
                job_description["must_have"] = state.job_data["must_have"]
            
            # Ensure nice_to_have is present (fallback)
            if not job_description.get("nice_to_have") and state.job_data.get("nice_to_have"):
                job_description["nice_to_have"] = state.job_data["nice_to_have"]
            
            # Ensure min_years is present (fallback)
            if "min_years" not in job_description and "min_years" in state.job_data:
                job_description["min_years"] = state.job_data["min_years"]

        # Pass project_type from job document for evaluation weight presets
        if state.job_data and state.job_data.get("project_type") is not None:
            job_description["project_type"] = state.job_data["project_type"]

        # Ensure jd_text is present and fixed
        if not job_description.get("jd_text"):
            if state.job_data and "jd_text" in state.job_data:
                jd_text = state.job_data["jd_text"]
                # Fix the JD text if it has "ob Description" issue
                if jd_text.startswith("ob Description"):
                    jd_text = "Job Description" + jd_text[14:]
                job_description["jd_text"] = jd_text
        else:
            # Fix jd_text if it has "ob Description" issue
            jd_text = job_description["jd_text"]
            if jd_text.startswith("ob Description"):
                job_description["jd_text"] = "Job Description" + jd_text[14:]
        
        return {
            "candidate": candidate,
            "job_description": job_description
        }
    
    def _build_candidate_profile_text(self, state: EvaluationState) -> str:
        """Build candidate profile text for semantic analysis"""
        parts = []
        
        # Add skills (both raw and canonical for completeness)
        if state.normalized_skills:
            skills_text = ", ".join(state.normalized_skills[:30])  # Limit to first 30 for token efficiency
            parts.append(f"Skills: {skills_text}")
        else:
            # Fallback to raw skills if normalized not available
            all_skills = []
            if state.cv_data:
                all_skills.extend(state.cv_data.get("skills_raw", []))
            if state.linkedin_data:
                all_skills.extend(state.linkedin_data.get("skills_raw", []))
            if all_skills:
                skills_text = ", ".join(all_skills[:30])
                parts.append(f"Skills: {skills_text}")
        
        # Add experience with highlights
        experience = []
        if state.cv_data:
            experience = state.cv_data.get("experience", [])
        if not experience and state.linkedin_data:
            experience = state.linkedin_data.get("experience", [])
        
        for exp in experience[:3]:  # Limit to first 3 experiences
            title = exp.get("title", "")
            company = exp.get("company", "")
            highlights = exp.get("highlights", [])
            if title:
                parts.append(f"{title} at {company}")
            if highlights:
                parts.extend(highlights[:2])  # Limit to 2 highlights per experience
        
        # Add education
        education = []
        if state.cv_data:
            education = state.cv_data.get("education", [])
        if state.linkedin_data:
            education.extend(state.linkedin_data.get("education", []))
        if education:
            # Convert education to strings if needed
            edu_strings = []
            for edu in education[:2]:  # Limit to first 2 education entries
                if isinstance(edu, str):
                    edu_strings.append(edu)
                elif isinstance(edu, dict):
                    # Format education dict
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    if degree or institution:
                        edu_strings.append(f"{degree} from {institution}".strip())
                else:
                    edu_strings.append(str(edu))
            if edu_strings:
                parts.append("Education: " + ", ".join(edu_strings))
        
        candidate_block = " ".join(parts)
        
        # Validate minimum length
        if len(candidate_block) < 200:
            logger.warning(f"Candidate block too short ({len(candidate_block)} chars), may affect semantic matching")
            # Try to rebuild with more data if available
            if len(candidate_block) < 100:
                logger.warning("Candidate block very short, attempting to include more data")
                # Add more experience highlights if available
                if experience and len(experience) > 3:
                    for exp in experience[3:5]:
                        highlights = exp.get("highlights", [])
                        if highlights:
                            parts.extend(highlights[:1])
                candidate_block = " ".join(parts)
                logger.info(f"Rebuilt candidate block: {len(candidate_block)} chars")
        
        logger.info(f"Built candidate profile block: {len(candidate_block)} characters")
        return candidate_block
    
    def _build_github_summary(self, github_info: Dict) -> str:
        """Build GitHub summary text"""
        if not github_info:
            return ""
        
        parts = []
        repos = github_info.get("repos", [])
        commits = github_info.get("commits_last_12m", 0)
        prs = github_info.get("external_prs_merged", 0)
        
        if repos:
            parts.append(f"{len(repos)} repositories")
        if commits > 0:
            parts.append(f"{commits} commits in last 12 months")
        if prs > 0:
            parts.append(f"{prs} external PRs merged")
        
        return ", ".join(parts)
    
    def _determine_decision(
        self,
        total_score: int,
        role_predictions: Optional[List[Dict]] = None,
        job_title: Optional[str] = None
    ) -> str:
        """
        Determine decision based on score thresholds, with optional role match adjustments.
        
        Args:
            total_score: Total evaluation score
            role_predictions: Optional list of predicted roles
            job_title: Optional job title for role matching
        
        Returns:
            Decision string: "Proceed", "Review", or "Do Not Proceed"
        """
        # Default thresholds
        selected_threshold = 70
        review_threshold = 60
        
        # Adjust thresholds based on role match if available
        if role_predictions and job_title:
            from app.utils.role_matcher import calculate_role_match, get_adjusted_threshold
            
            role_match = calculate_role_match(job_title, role_predictions)
            thresholds = get_adjusted_threshold(total_score, role_match, selected_threshold, review_threshold)
            selected_threshold = thresholds["selected_threshold"]
            review_threshold = thresholds["review_threshold"]
        
        if total_score >= selected_threshold:
            return "Proceed"
        elif total_score >= review_threshold:
            return "Review"
        else:
            return "Do Not Proceed"
    
    def _classify_roles(self, state: EvaluationState) -> List[Dict]:
        """Classify candidate into roles"""
        # Ensure skills are normalized
        if not state.normalized_skills:
            all_skills = []
            if state.cv_data:
                all_skills.extend(state.cv_data.get("skills_raw", []))
            if state.linkedin_data:
                all_skills.extend(state.linkedin_data.get("skills_raw", []))
            if all_skills:
                state.normalized_skills = normalize_skills(all_skills)
            else:
                logger.warning("No skills available for role classification")
                return []
        
        # Get JD data - prefer jd_data, fallback to job_data
        jd_info = state.jd_data or {}
        if not jd_info and state.job_data:
            # If jd_data is empty but we have job_data, try to extract JD
            jd_text = state.job_data.get("jd_text", "")
            if jd_text:
                from app.services.extractors.jd_extractor import extract_from_jd
                jd_info = extract_from_jd(jd_text)
                # Ensure jd_text is preserved
                if "jd_text" not in jd_info:
                    jd_info["jd_text"] = jd_text
                state.jd_data = jd_info
        
        if not jd_info:
            logger.warning("No JD data available for role classification")
            return []
        
        logger.info(f"Classifying roles with {len(state.normalized_skills)} skills and JD title: {jd_info.get('title', 'N/A')}")
        return classify_roles(state.normalized_skills, jd_info)
    
    def _generate_explanations(
        self,
        state: EvaluationState,
        total_score: int,
        breakdown: Dict,
        role_predictions: List[Dict]
    ) -> List[str]:
        """Generate explanations for the score"""
        explanations = []
        
        # Check must-have skills
        must_have = state.jd_data.get("must_have", []) if state.jd_data else []
        if must_have and state.normalized_skills:
            matched = [
                skill for skill in must_have
                if any(s.lower() in skill.lower() or skill.lower() in s.lower() for s in state.normalized_skills)
            ]
            if len(matched) == len(must_have):
                explanations.append("All must-have skills present")
            elif len(matched) > 0:
                explanations.append(f"Matched {len(matched)}/{len(must_have)} must-have skills")
            else:
                explanations.append("Missing some must-have skills")
        
        # Role predictions
        if role_predictions:
            top_role = role_predictions[0]
            explanations.append(f"Best fit: {top_role['role']} ({top_role['similarity']*100:.0f}% match)")
            
            # Add role match bonus explanation if applicable
            role_match_bonus = breakdown.get("role_match_bonus", 0)
            if role_match_bonus != 0:
                job_title = state.jd_data.get("title", "") if state.jd_data else ""
                if job_title:
                    from app.utils.role_matcher import calculate_role_match
                    role_match = calculate_role_match(job_title, role_predictions)
                    match_type = role_match.get("match_type", "")
                    
                    if match_type == "overqualified" and role_match_bonus > 0:
                        explanations.append(f"Strong role match: Predicted as {top_role['role']} (overqualified for {job_title}) - bonus applied")
                    elif match_type == "exact_match" and role_match_bonus > 0:
                        explanations.append(f"Exact role match: Predicted role aligns with job title - bonus applied")
                    elif match_type == "underqualified" and role_match_bonus < 0:
                        explanations.append(f"Role mismatch: Predicted role level below job requirements")
        
        # Breakdown highlights
        if breakdown.get("semantic_fit", 0) > 20:
            explanations.append("Strong semantic match with job description")
        if breakdown.get("role_competency", 0) > 20:
            explanations.append("Good competency match for role requirements")
        if breakdown.get("github_evidence", 0) > 10:
            explanations.append("Active GitHub profile with relevant contributions")
        
        # Score context
        if total_score >= 70:
            explanations.append("High overall score - strong candidate")
        elif total_score >= 60:
            explanations.append("Moderate score - requires review")
        else:
            explanations.append("Low score - may not be suitable")
        
        return explanations
    
    def _build_final_result(self, state: EvaluationState) -> Dict:
        """Build final evaluation result"""
        # Ensure we have valid values - never None
        total_score = state.total_score if state.total_score is not None else 0
        decision = state.decision if state.decision is not None else "Do Not Proceed"
        role_predictions = state.role_predictions or []
        explanations = state.explanations or []
        
        # If we still don't have a score, try to get it from aggregated_score
        if total_score == 0 and state.aggregated_score:
            total_score = state.aggregated_score.get("total_score", 0)
            if decision == "Do Not Proceed" and total_score > 0:
                decision = self._determine_decision(total_score)
        
        # If still no score and we have some data, set a default
        if total_score == 0 and not state.aggregated_score:
            logger.warning("No score available, using default")
            explanations.append("Evaluation incomplete - using default score")
        
        result = {
            "user_id": state.user_id,
            "job_id": state.job_id,
            "total_score": total_score,
            "decision": decision,
            "role_predictions": role_predictions,
            "why": explanations,
            "breakdown": state.aggregated_score.get("breakdown", {}) if state.aggregated_score else {},
            "raw_pipeline": self._build_merged_json(state),
            "evaluation_time": state.end_time - state.start_time if state.end_time and state.start_time else None,
            "iterations": state.iteration_count
        }
        
        # Always include dataset validation results (even if None/empty)
        if state.dataset_validation:
            result["dataset_validation"] = {
                "original_score": state.dataset_validation.get("original_score"),
                "calibrated_score": state.dataset_validation.get("calibrated_score"),
                "confidence": state.dataset_validation.get("confidence", 0.0),
                "calibration_adjustment": state.dataset_validation.get("calibration_adjustment", 0),
                "validation_status": state.dataset_validation.get("validation_status", "unknown"),
                "similar_cases_count": len(state.dataset_validation.get("similar_cases", [])),
                "similar_cases": state.dataset_validation.get("similar_cases", [])[:3],  # Include top 3 for reference
                "reasoning": state.dataset_validation.get("reasoning", ""),
                "status": state.dataset_validation.get("status", "unknown")
            }
        else:
            # Include empty dataset_validation if not available
            result["dataset_validation"] = {
                "original_score": total_score,
                "calibrated_score": total_score,
                "confidence": 0.0,
                "calibration_adjustment": 0,
                "validation_status": "not_available",
                "similar_cases_count": 0,
                "similar_cases": [],
                "reasoning": "Dataset validation not performed",
                "status": "not_available"
            }
        
        return result
    
    def _fallback_to_pipeline(self, candidate_id: str, job_id: str) -> Dict:
        """Fallback to original pipeline"""
        logger.info("Using pipeline fallback")
        from app.services.orchestrator import run_evaluation
        from app.services.normalization import normalize_skills
        from app.services.semantic import build_semantic_features
        from app.services.judge import judge_candidate
        from app.services.critic import critic_review
        from app.services.aggregator import aggregate_scores
        from app.services.role_classifier import classify_roles
        
        # Run pipeline
        merged_json = run_evaluation(candidate_id, job_id)
        
        # Normalize skills
        candidate_data = merged_json.get("candidate", {})
        skills_raw = candidate_data.get("skills_raw", [])
        skills_canonical = normalize_skills(skills_raw)
        merged_json["candidate"]["skills_canonical"] = skills_canonical
        
        # Semantic features
        candidate_block = self._build_candidate_profile_text_from_merged(merged_json)
        jd_block = merged_json.get("job_description", {}).get("jd_text", "")
        github_summary = self._build_github_summary(candidate_data.get("github", {}))
        semantic_features = build_semantic_features(candidate_block, jd_block, github_summary)
        merged_json["semantic_features"] = semantic_features
        
        # Judge
        judge_output = judge_candidate(merged_json)
        merged_json["judge_scores"] = judge_output.get("judge_scores", [])
        
        # Critic
        critic_output = critic_review(merged_json, judge_output)
        merged_json["critic_scores"] = critic_output.get("judge_scores", [])
        
        # Aggregate
        aggregated = aggregate_scores(
            semantic_features,
            judge_output,
            candidate_data.get("github", {}),
            candidate_data.get("experience", []),
            merged_json
        )
        total_score = aggregated["total_score"]
        breakdown = aggregated["breakdown"]
        
        # Classify roles
        jd_info = merged_json.get("job_description", {})
        role_predictions = classify_roles(skills_canonical, jd_info)
        
        # Decision
        decision = "Proceed" if total_score >= 70 else ("Review" if total_score >= 60 else "Do Not Proceed")
        
        return {
            "user_id": user_id,
            "job_id": job_id,
            "total_score": total_score,
            "decision": decision,
            "role_predictions": role_predictions,
            "why": [],
            "breakdown": breakdown,
            "raw_pipeline": merged_json,
            "fallback_used": True
        }
    
    def _build_candidate_profile_text_from_merged(self, merged_json: Dict) -> str:
        """Build candidate profile text from merged JSON"""
        candidate = merged_json.get("candidate", {})
        parts = []
        
        skills = candidate.get("skills_canonical", candidate.get("skills_raw", []))
        if skills:
            parts.append("Skills: " + ", ".join(skills))
        
        experience = candidate.get("experience", [])
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            highlights = exp.get("highlights", [])
            if title:
                parts.append(f"{title} at {company}")
            if highlights:
                parts.extend(highlights[:3])
        
        education = candidate.get("education", [])
        if education:
            parts.append("Education: " + ", ".join(education[:3]))
        
        return " ".join(parts)

