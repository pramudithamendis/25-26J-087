from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import datetime
from typing import Dict, List
import logging

from app.models.evaluation_model import evaluations_collection
from app.models.candidate_model import candidates_collection
from app.schemas.evaluation_schema import EvaluationRequest, EvaluationResponse
from app.auth.dependencies import get_current_user, get_admin_user
from app.services.orchestrator import run_evaluation
from app.services.normalization import normalize_skills
from app.services.semantic import build_semantic_features
from app.services.judge import judge_candidate
from app.services.critic import critic_review
from app.services.aggregator import aggregate_scores
from app.services.role_classifier import classify_roles
from app.services.agents.orchestrator_agent import AgenticOrchestrator
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Evaluations"])


def build_candidate_profile_text(merged_json: Dict) -> str:
    """Build a text block from candidate data for semantic analysis"""
    candidate = merged_json.get("candidate", {})
    
    parts = []
    
    # Add skills
    skills = candidate.get("skills_canonical", candidate.get("skills_raw", []))
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    
    # Add experience highlights
    experience = candidate.get("experience", [])
    for exp in experience:
        title = exp.get("title", "")
        company = exp.get("company", "")
        highlights = exp.get("highlights", [])
        if title:
            parts.append(f"{title} at {company}")
        if highlights:
            parts.extend(highlights[:3])  # Top 3 highlights
    
    # Add education
    education = candidate.get("education", [])
    if education:
        parts.append("Education: " + ", ".join(education))
    
    return " ".join(parts)


def build_github_summary(github_info: Dict) -> str:
    """Build a summary text from GitHub data"""
    if not github_info:
        return ""
    
    repos = github_info.get("repos", [])
    commits = github_info.get("commits_last_12m", 0)
    prs = github_info.get("external_prs_merged", 0)
    
    parts = []
    if repos:
        parts.append(f"{len(repos)} repositories")
    if commits > 0:
        parts.append(f"{commits} commits in last 12 months")
    if prs > 0:
        parts.append(f"{prs} external PRs merged")
    
    return ", ".join(parts)


def determine_decision(total_score: int) -> str:
    """Determine decision based on score thresholds"""
    if total_score >= 75:
        return "Selected"
    elif total_score >= 60:
        return "Review"
    else:
        return "Not Selected"


def generate_explanations(
    merged_json: Dict, 
    total_score: int, 
    breakdown: Dict, 
    role_predictions: List[Dict]
) -> List[str]:
    """Generate human-readable explanations for the score"""
    explanations = []
    
    candidate = merged_json.get("candidate", {})
    jd_info = merged_json.get("job_description", {})
    
    # Check must-have skills
    must_have = jd_info.get("must_have", [])
    skills_canonical = candidate.get("skills_canonical", [])
    
    if must_have:
        matched_must_have = [
            skill for skill in must_have 
            if any(s.lower() in skill.lower() or skill.lower() in s.lower() for s in skills_canonical)
        ]
        if len(matched_must_have) == len(must_have):
            explanations.append("All must-have skills present")
        elif len(matched_must_have) > 0:
            explanations.append(f"Matched {len(matched_must_have)}/{len(must_have)} must-have skills")
        else:
            explanations.append("Missing some must-have skills")
    
    # Check role predictions
    if role_predictions:
        top_role = role_predictions[0]
        explanations.append(f"Best fit: {top_role['role']} ({top_role['similarity']*100:.0f}% match)")
    
    # Check breakdown highlights
    if breakdown.get("semantic_fit", 0) > 20:
        explanations.append("Strong semantic match with job description")
    
    if breakdown.get("role_competency", 0) > 20:
        explanations.append("Good competency match for role requirements")
    
    if breakdown.get("github_evidence", 0) > 10:
        explanations.append("Active GitHub profile with relevant contributions")
    
    # Add score context
    if total_score >= 75:
        explanations.append("High overall score - strong candidate")
    elif total_score >= 60:
        explanations.append("Moderate score - requires review")
    else:
        explanations.append("Low score - may not be suitable")
    
    return explanations


@router.post("/evaluate", response_model=EvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_candidate(
    request: EvaluationRequest,
    admin_user = Depends(get_admin_user)
):
    """
    Run full evaluation pipeline for a candidate against a job (Admin-only)
    
    Pipeline flow:
    1. Orchestrator: Extract and merge data from CV/LinkedIn/GitHub/JD
    2. Normalization: Normalize skills to canonical forms
    3. Semantic features: Build similarity scores using OpenAI embeddings
    4. Judge: Score candidate on criteria using OpenAI LLM
    5. Critic: Review and validate scores
    6. Aggregator: Combine scores into 0-100 total
    7. Role classifier: Predict suitable roles
    8. Build final JSON with decision
    9. Save to evaluations collection
    10. Return complete evaluation result
    """
    try:
        candidate_id = request.candidate_id
        job_id = request.job_id
        
        # Validate ObjectId formats
        if not ObjectId.is_valid(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate ID format"
            )
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        # Verify candidate exists
        candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found"
            )
        
        # Step 1: Run orchestrator (agentic or pipeline based on config)
        logger.info(f"Starting evaluation for candidate {candidate_id} and job {job_id}")
        
        if settings.USE_AGENTIC_EVALUATION:
            logger.info("Using agentic evaluation system")
            orchestrator = AgenticOrchestrator()
            evaluation_result = orchestrator.run_agentic_evaluation(candidate_id, job_id)
            
            # Save to evaluations collection
            evaluation_doc = {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "pipeline_output": evaluation_result.get("raw_pipeline", {}),
                "total_score": evaluation_result.get("total_score", 0),
                "decision": evaluation_result.get("decision", "Not Selected"),
                "role_predictions": evaluation_result.get("role_predictions", []),
                "status": "completed",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "agentic": True,
                "iterations": evaluation_result.get("iterations", 0)
            }
            
            result = evaluations_collection.insert_one(evaluation_doc)
            evaluation_result["_id"] = str(result.inserted_id)
            evaluation_result["created_at"] = evaluation_doc["created_at"]
            
            return EvaluationResponse(**evaluation_result)
        
        # Fallback to pipeline
        logger.info("Using pipeline evaluation system")
        merged_json = run_evaluation(candidate_id, job_id)
        
        # Step 2: Normalize skills
        candidate_data = merged_json.get("candidate", {})
        skills_raw = candidate_data.get("skills_raw", [])
        skills_canonical = normalize_skills(skills_raw)
        merged_json["candidate"]["skills_canonical"] = skills_canonical
        
        # Step 3: Build semantic features
        # Create candidate profile text block
        candidate_block = build_candidate_profile_text(merged_json)
        jd_block = merged_json.get("job_description", {}).get("jd_text", "")
        if not jd_block:
            logger.warning(f"JD text is empty! Job description keys: {list(merged_json.get('job_description', {}).keys())}")
        github_summary = build_github_summary(candidate_data.get("github", {}))
        
        logger.info(f"Building semantic features: candidate_block length={len(candidate_block)}, jd_block length={len(jd_block)}")
        semantic_features = build_semantic_features(candidate_block, jd_block, github_summary)
        logger.info(f"Semantic features computed: {semantic_features}")
        merged_json["semantic_features"] = semantic_features
        
        # Step 4: Judge candidate
        judge_output = judge_candidate(merged_json)
        merged_json["judge_scores"] = judge_output.get("judge_scores", [])
        
        # Step 5: Critic review
        critic_output = critic_review(merged_json, judge_output)
        merged_json["critic_scores"] = critic_output.get("judge_scores", [])
        
        # Step 6: Aggregate scores
        github_info = candidate_data.get("github", {})
        if not github_info:
            logger.warning("GitHub info is missing from candidate data")
        else:
            logger.debug(f"GitHub info for aggregation: repos={len(github_info.get('repos', []))}, commits={github_info.get('commits_last_12m', 0)}, prs={github_info.get('external_prs_merged', 0)}")
        
        aggregated = aggregate_scores(
            semantic_features,
            judge_output,
            github_info,
            candidate_data.get("experience", []),
            merged_json
        )
        total_score = aggregated["total_score"]
        breakdown = aggregated["breakdown"]
        
        # Step 7: Classify roles
        jd_info = merged_json.get("job_description", {})
        role_predictions = classify_roles(skills_canonical, jd_info)
        
        # Step 8: Build final JSON with decision
        decision = determine_decision(total_score)
        why = generate_explanations(merged_json, total_score, breakdown, role_predictions)
        
        # Build final evaluation result
        evaluation_result = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "total_score": total_score,
            "decision": decision,
            "role_predictions": role_predictions,
            "why": why,
            "breakdown": breakdown,
            "raw_pipeline": merged_json
        }
        
        # Step 9: Save to evaluations collection
        evaluation_doc = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "pipeline_output": merged_json,
            "total_score": total_score,
            "decision": decision,
            "role_predictions": role_predictions,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        result = evaluations_collection.insert_one(evaluation_doc)
        evaluation_result["_id"] = str(result.inserted_id)
        evaluation_result["created_at"] = evaluation_doc["created_at"]
        
        logger.info(f"Evaluation completed successfully: {evaluation_result['_id']}")
        
        # Step 10: Return complete evaluation result
        return EvaluationResponse(**evaluation_result)
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Value error in evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error running evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running evaluation: {str(e)}"
        )


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: str,
    current_user = Depends(get_current_user)
):
    """Get evaluation details by ID (JWT protected)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(evaluation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid evaluation ID format"
            )
        
        evaluation = evaluations_collection.find_one({"_id": ObjectId(evaluation_id)})
        
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evaluation not found"
            )
        
        # Build response from stored evaluation
        pipeline_output = evaluation.get("pipeline_output", {})
        
        # Extract breakdown from pipeline_output if available
        breakdown = {}
        if pipeline_output:
            # Try to reconstruct breakdown from stored data
            semantic_features = pipeline_output.get("semantic_features", {})
            candidate_data = pipeline_output.get("candidate", {})
            github_info = candidate_data.get("github", {})
            experience_info = candidate_data.get("experience", [])
            judge_scores = pipeline_output.get("judge_scores", [])
            
            # Reconstruct breakdown by re-running aggregator logic
            if semantic_features and judge_scores:
                try:
                    # Re-run aggregator to get breakdown
                    judge_output = {"judge_scores": judge_scores}
                    aggregated = aggregate_scores(
                        semantic_features,
                        judge_output,
                        github_info,
                        experience_info,
                        pipeline_output
                    )
                    breakdown = aggregated.get("breakdown", {})
                except Exception as e:
                    logger.warning(f"Could not reconstruct breakdown: {str(e)}")
                    breakdown = {}
        
        # Generate why explanations
        why = []
        if pipeline_output:
            try:
                role_predictions = evaluation.get("role_predictions", [])
                why = generate_explanations(
                    pipeline_output,
                    evaluation.get("total_score", 0),
                    breakdown,
                    role_predictions
                )
            except Exception as e:
                logger.warning(f"Could not generate explanations: {str(e)}")
                why = []
        
        evaluation_result = {
            "_id": str(evaluation["_id"]),
            "candidate_id": evaluation.get("candidate_id", ""),
            "job_id": evaluation.get("job_id", ""),
            "total_score": evaluation.get("total_score", 0),
            "decision": evaluation.get("decision", "Not Selected"),
            "role_predictions": evaluation.get("role_predictions", []),
            "why": why,
            "breakdown": breakdown,
            "raw_pipeline": pipeline_output,
            "created_at": evaluation.get("created_at")
        }
        
        return EvaluationResponse(**evaluation_result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting evaluation: {str(e)}"
        )


@router.post("/evaluate/agentic", response_model=EvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_candidate_agentic(
    request: EvaluationRequest,
    admin_user = Depends(get_admin_user)
):
    """
    Run agentic evaluation for a candidate against a job (Admin-only)
    
    Uses agentic AI system with dynamic workflow instead of fixed pipeline.
    """
    try:
        candidate_id = request.candidate_id
        job_id = request.job_id
        
        # Validate ObjectId formats
        if not ObjectId.is_valid(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate ID format"
            )
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        # Verify candidate exists
        candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found"
            )
        
        logger.info(f"Starting agentic evaluation for candidate {candidate_id} and job {job_id}")
        orchestrator = AgenticOrchestrator()
        evaluation_result = orchestrator.run_agentic_evaluation(candidate_id, job_id)
        
        # Save to evaluations collection
        evaluation_doc = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "pipeline_output": evaluation_result.get("raw_pipeline", {}),
            "total_score": evaluation_result.get("total_score", 0),
            "decision": evaluation_result.get("decision", "Not Selected"),
            "role_predictions": evaluation_result.get("role_predictions", []),
            "status": "completed",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "agentic": True,
            "iterations": evaluation_result.get("iterations", 0)
        }
        
        result = evaluations_collection.insert_one(evaluation_doc)
        evaluation_result["_id"] = str(result.inserted_id)
        evaluation_result["created_at"] = evaluation_doc["created_at"]
        
        return EvaluationResponse(**evaluation_result)
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Value error in agentic evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error running agentic evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running agentic evaluation: {str(e)}"
        )


