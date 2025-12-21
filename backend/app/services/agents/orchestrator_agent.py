"""
Agentic Orchestrator for CV evaluation.

Main entry point for agentic evaluation. Coordinates all agents and manages
dynamic workflow (not fixed pipeline). Handles agent communication and fallback.
"""

from typing import Dict, List, Optional
from bson import ObjectId
import logging
import time
from app.models.candidate_model import candidates_collection
from app.models.job_model import jobs_collection
from app.config import settings
from .state import EvaluationState, EvaluationStage
from .planning_agent import PlanningAgent
from .extraction_agent import ExtractionAgent
from .verification_agent import VerificationAgent
from .judge_agent import JudgeAgent
from .critic_agent import CriticAgent
from .aggregator_agent import AggregatorAgent
from app.services.normalization import normalize_skills
from app.services.semantic import build_semantic_features
from app.services.role_classifier import classify_roles

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
        
        self.max_iterations = getattr(settings, 'MAX_AGENT_ITERATIONS', 20)
        self.fallback_to_pipeline = getattr(settings, 'AGENTIC_FALLBACK_TO_PIPELINE', True)
    
    def run_agentic_evaluation(self, candidate_id: str, job_id: str) -> Dict:
        """
        Run full agentic evaluation pipeline.
        
        Args:
            candidate_id: MongoDB candidate document ID
            job_id: MongoDB job document ID
        
        Returns:
            Complete evaluation result
        """
        try:
            # Initialize state
            state = EvaluationState(candidate_id, job_id)
            state.start_time = time.time()
            
            # Load candidate and job from MongoDB
            candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
            if not candidate:
                raise ValueError(f"Candidate {candidate_id} not found")
            
            job = jobs_collection.find_one({"_id": ObjectId(job_id)})
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            state.candidate_data = candidate
            state.job_data = job
            
            logger.info(f"Starting agentic evaluation for candidate {candidate_id} and job {job_id}")
            
            # Main agentic loop
            while self.planning_agent.should_continue(state) and not state.is_complete():
                state.increment_iteration()
                
                if state.iteration_count > self.max_iterations:
                    logger.warning(f"Max iterations ({self.max_iterations}) reached")
                    if self.fallback_to_pipeline:
                        logger.info("Falling back to pipeline")
                        return self._fallback_to_pipeline(candidate_id, job_id)
                    break
                
                # Planning agent decides next action
                try:
                    plan = self.planning_agent.plan_next_action(state)
                    action = plan.get("action")
                    agent_name = plan.get("agent")
                    next_stage = plan.get("next_stage")
                    
                    logger.info(f"Iteration {state.iteration_count}: Action={action}, Agent={agent_name}")
                    
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
                            return self._fallback_to_pipeline(candidate_id, job_id)
                        raise
            
            # Build final result
            state.end_time = time.time()
            return self._build_final_result(state)
            
        except Exception as e:
            logger.error(f"Agentic evaluation failed: {str(e)}")
            if self.fallback_to_pipeline:
                logger.info("Falling back to pipeline")
                return self._fallback_to_pipeline(candidate_id, job_id)
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
        elif action == "complete":
            return {"status": "complete"}
        else:
            logger.warning(f"Unknown action: {action}")
            return {"status": "unknown_action"}
    
    def _extract_cv(self, state: EvaluationState) -> Dict:
        """Extract CV data"""
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
        return result
    
    def _extract_linkedin(self, state: EvaluationState) -> Dict:
        """Extract LinkedIn data"""
        linkedin_path = state.candidate_data.get("linkedin_file_path")
        if not linkedin_path:
            return {"status": "skipped", "reason": "No LinkedIn file path"}
        
        result = self.extraction_agent.execute(state)
        if result.get("linkedin_data"):
            state.mark_extracted("linkedin", result["linkedin_data"])
            state.linkedin_data = result["linkedin_data"]
        return result
    
    def _extract_github(self, state: EvaluationState) -> Dict:
        """Extract GitHub data"""
        github_handle = (
            state.cv_data.get("github_handle", "") if state.cv_data
            else state.candidate_data.get("github_handle", "")
        )
        
        if not github_handle:
            return {"status": "skipped", "reason": "No GitHub handle"}
        
        # Use verification agent to get GitHub data
        verification_result = self.verification_agent.verify_github_profile(github_handle)
        if verification_result.get("verified"):
            state.github_data = verification_result.get("data")
            state.mark_extracted("github", state.github_data)
            state.mark_verified("github_handle", True)
        return verification_result
    
    def _extract_jd(self, state: EvaluationState) -> Dict:
        """Extract job description data"""
        jd_text = state.job_data.get("jd_text", "")
        if not jd_text:
            return {"status": "error", "reason": "No JD text"}
        
        result = self.extraction_agent.execute(state)
        if result.get("jd_data"):
            state.mark_extracted("jd", result["jd_data"])
            state.jd_data = result["jd_data"]
        return result
    
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
        if not state.cv_data or not state.linkedin_data:
            return {"status": "skipped", "reason": "Missing CV or LinkedIn data"}
        
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
        
        # Determine decision and generate explanations
        total_score = result.get("total_score", 0)
        decision = self._determine_decision(total_score)
        role_predictions = self._classify_roles(state)
        explanations = self._generate_explanations(state, total_score, result.get("breakdown", {}), role_predictions)
        
        state.set_final_result(total_score, decision, role_predictions, explanations)
        return result
    
    def _update_state_from_result(self, state: EvaluationState, action: str, result: Dict):
        """Update state based on action result"""
        # State updates are handled in individual action methods
        pass
    
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
        
        candidate = {
            "skills_raw": all_skills,
            "skills_canonical": state.normalized_skills or [],
            "experience": all_experience,
            "education": all_education,
            "github": state.github_data or {},
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
        # Start with jd_data (from extraction) which has title, must_have, nice_to_have, etc.
        if state.jd_data:
            # Make a copy to avoid mutating the original
            job_description = dict(state.jd_data)
        else:
            job_description = {}
        
        # If jd_data is missing fields, try to get them from job_data
        if state.job_data:
            # Ensure title is present
            if not job_description.get("title") and state.job_data.get("title"):
                job_description["title"] = state.job_data["title"]
            
            # Ensure must_have is present
            if not job_description.get("must_have") and state.job_data.get("must_have"):
                job_description["must_have"] = state.job_data["must_have"]
            
            # Ensure nice_to_have is present
            if not job_description.get("nice_to_have") and state.job_data.get("nice_to_have"):
                job_description["nice_to_have"] = state.job_data["nice_to_have"]
            
            # Ensure min_years is present
            if "min_years" not in job_description and "min_years" in state.job_data:
                job_description["min_years"] = state.job_data["min_years"]
        
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
        
        # If jd_data is still empty or missing critical fields, try to extract from job_data
        if not job_description or (not job_description.get("must_have") and state.job_data and state.job_data.get("jd_text")):
            logger.warning("JD data missing must_have skills, attempting to extract from job_data")
            from app.services.extractors.jd_extractor import extract_from_jd
            jd_text = state.job_data.get("jd_text", "") if state.job_data else ""
            if jd_text:
                try:
                    extracted = extract_from_jd(jd_text)
                    if extracted:
                        # Merge extracted data, preserving existing fields
                        for key, value in extracted.items():
                            if key not in job_description or not job_description[key]:
                                job_description[key] = value
                        logger.info(f"Extracted JD data: title={job_description.get('title')}, must_have count={len(job_description.get('must_have', []))}")
                except Exception as e:
                    logger.error(f"Failed to extract JD data: {str(e)}")
        
        return {
            "candidate": candidate,
            "job_description": job_description
        }
    
    def _build_candidate_profile_text(self, state: EvaluationState) -> str:
        """Build candidate profile text for semantic analysis"""
        parts = []
        
        if state.normalized_skills:
            parts.append("Skills: " + ", ".join(state.normalized_skills))
        
        experience = []
        if state.cv_data:
            experience = state.cv_data.get("experience", [])
        if not experience and state.linkedin_data:
            experience = state.linkedin_data.get("experience", [])
        
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            highlights = exp.get("highlights", [])
            if title:
                parts.append(f"{title} at {company}")
            if highlights:
                parts.extend(highlights[:3])
        
        if state.normalized_skills:
            education = []
            if state.cv_data:
                education = state.cv_data.get("education", [])
            if state.linkedin_data:
                education.extend(state.linkedin_data.get("education", []))
            if education:
                parts.append("Education: " + ", ".join(education[:3]))
        
        return " ".join(parts)
    
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
    
    def _determine_decision(self, total_score: int) -> str:
        """Determine decision based on score"""
        if total_score >= 75:
            return "Selected"
        elif total_score >= 60:
            return "Review"
        else:
            return "Not Selected"
    
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
        
        # Breakdown highlights
        if breakdown.get("semantic_fit", 0) > 20:
            explanations.append("Strong semantic match with job description")
        if breakdown.get("role_competency", 0) > 20:
            explanations.append("Good competency match for role requirements")
        if breakdown.get("github_evidence", 0) > 10:
            explanations.append("Active GitHub profile with relevant contributions")
        
        # Score context
        if total_score >= 75:
            explanations.append("High overall score - strong candidate")
        elif total_score >= 60:
            explanations.append("Moderate score - requires review")
        else:
            explanations.append("Low score - may not be suitable")
        
        return explanations
    
    def _build_final_result(self, state: EvaluationState) -> Dict:
        """Build final evaluation result"""
        return {
            "candidate_id": state.candidate_id,
            "job_id": state.job_id,
            "total_score": state.total_score,
            "decision": state.decision,
            "role_predictions": state.role_predictions or [],
            "why": state.explanations or [],
            "breakdown": state.aggregated_score.get("breakdown", {}) if state.aggregated_score else {},
            "raw_pipeline": self._build_merged_json(state),
            "evaluation_time": state.end_time - state.start_time if state.end_time and state.start_time else None,
            "iterations": state.iteration_count
        }
    
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
        decision = "Selected" if total_score >= 75 else ("Review" if total_score >= 60 else "Not Selected")
        
        return {
            "candidate_id": candidate_id,
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

