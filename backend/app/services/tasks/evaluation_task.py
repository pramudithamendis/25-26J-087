"""
Background task for processing evaluations using Redis Queue
"""
import logging
from datetime import datetime
from bson import ObjectId
from app.models.application_model import applications_collection
from app.models.evaluation_model import evaluations_collection
from app.config import settings

logger = logging.getLogger(__name__)


def process_evaluation(user_id: str, job_id: str, application_id: str):
    """
    Process evaluation in background (called by RQ worker)
    
    This function:
    1. Updates application status to "processing"
    2. Runs evaluation (agentic or pipeline)
    3. Saves evaluation to database
    4. Links evaluation_id to application
    5. Updates application status to "evaluated"
    6. Handles errors and updates status to "failed" if needed
    
    Args:
        user_id: User MongoDB ID
        job_id: Job MongoDB ID
        application_id: Application MongoDB ID
    """
    processing_started_at = datetime.utcnow().isoformat() + "Z"
    
    try:
        # Step 1: Update application status to "processing"
        applications_collection.update_one(
            {"_id": ObjectId(application_id)},
            {
                "$set": {
                    "evaluation_status": "processing",
                    "processing_started_at": processing_started_at
                }
            }
        )
        logger.info(f"Started processing evaluation for application {application_id}")
        
        # Step 2: Run evaluation
        evaluation_result = None
        evaluation_id = None
        
        if settings.USE_AGENTIC_EVALUATION:
            logger.info("Using agentic evaluation system")
            from app.services.agents.orchestrator_agent import AgenticOrchestrator
            orchestrator = AgenticOrchestrator()
            evaluation_result = orchestrator.run_agentic_evaluation(user_id, job_id)
            
            # Save to evaluations collection
            evaluation_doc = {
                "user_id": user_id,
                "job_id": job_id,
                "pipeline_output": evaluation_result.get("raw_pipeline", {}),
                "total_score": evaluation_result.get("total_score", 0),
                "decision": evaluation_result.get("decision", "Do Not Proceed"),
                "role_predictions": evaluation_result.get("role_predictions", []),
                "breakdown": evaluation_result.get("breakdown", {}),
                "status": "completed",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "agentic": True,
                "iterations": evaluation_result.get("iterations", 0)
            }
            
            result = evaluations_collection.insert_one(evaluation_doc)
            evaluation_id = str(result.inserted_id)
        else:
            # Fallback to pipeline
            logger.info("Using pipeline evaluation system")
            from app.services.orchestrator import run_evaluation
            from app.services.normalization import normalize_skills
            from app.services.semantic import build_semantic_features
            from app.services.judge import judge_candidate
            from app.services.critic import critic_review
            from app.services.aggregator import aggregate_scores
            from app.services.role_classifier import classify_roles
            
            def build_candidate_profile_text(merged_json):
                """Build a text block from candidate data for semantic analysis"""
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
                    for edu in education[:2]:
                        degree = edu.get("degree", "")
                        school = edu.get("school", "")
                        if degree:
                            parts.append(f"{degree} from {school}")
                return " ".join(parts)
            
            merged_json = run_evaluation(user_id, job_id)
            
            # Normalize skills
            candidate_data = merged_json.get("candidate", {})
            skills_raw = candidate_data.get("skills_raw", [])
            skills_canonical = normalize_skills(skills_raw)
            merged_json["candidate"]["skills_canonical"] = skills_canonical
            
            # Build semantic features
            candidate_block = build_candidate_profile_text(merged_json)
            jd_block = merged_json.get("job_description", {}).get("jd_text", "")
            if not jd_block:
                logger.warning(f"No JD text found for job {job_id}")
            
            semantic_features = build_semantic_features(candidate_block, jd_block, "")
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
            
            # Determine decision
            decision = "Proceed" if total_score >= 70 else ("Review" if total_score >= 60 else "Do Not Proceed")
            
            # Generate explanations
            why = []
            if total_score >= 70:
                why.append(f"Strong match with score of {total_score}/100")
            elif total_score >= 60:
                why.append(f"Moderate match with score of {total_score}/100 - requires review")
            else:
                why.append(f"Low match score of {total_score}/100")
            
            # Save to evaluations collection
            evaluation_doc = {
                "user_id": user_id,
                "job_id": job_id,
                "pipeline_output": merged_json,
                "total_score": total_score,
                "decision": decision,
                "role_predictions": role_predictions,
                "breakdown": breakdown,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            result = evaluations_collection.insert_one(evaluation_doc)
            evaluation_id = str(result.inserted_id)
        
        # Step 3: Update application with evaluation results
        processing_completed_at = datetime.utcnow().isoformat() + "Z"
        applications_collection.update_one(
            {"_id": ObjectId(application_id)},
            {
                "$set": {
                    "evaluation_status": "evaluated",
                    "evaluation_id": evaluation_id,
                    "processing_completed_at": processing_completed_at,
                    "status": "evaluated"  # Update main status as well
                }
            }
        )
        
        logger.info(f"Successfully completed evaluation for application {application_id}, evaluation_id={evaluation_id}")
        return {
            "success": True,
            "application_id": application_id,
            "evaluation_id": evaluation_id,
            "processing_time": processing_completed_at
        }
        
    except Exception as e:
        # Step 4: Handle errors
        error_message = str(e)
        logger.error(f"Error processing evaluation for application {application_id}: {error_message}")
        
        processing_completed_at = datetime.utcnow().isoformat() + "Z"
        applications_collection.update_one(
            {"_id": ObjectId(application_id)},
            {
                "$set": {
                    "evaluation_status": "failed",
                    "processing_completed_at": processing_completed_at,
                    "error_message": error_message
                }
            }
        )
        
        # Re-raise exception so RQ can track it
        raise Exception(f"Evaluation processing failed: {error_message}")


