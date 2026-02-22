from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
import logging
import re

from app.models.job_model import jobs_collection
from app.models.user_model import users_collection
from app.models.application_model import applications_collection
from app.schemas.job_schema import JobCreate, JobResponse, JobUpdate
from app.schemas.application_schema import ApplicationCreate, ApplicationResponse, ApplicationStatusResponse
from app.auth.dependencies import get_current_user, get_admin_user
from app.utils.file_handler import save_uploaded_file
from app.config import settings
from fastapi import BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


class JobListResponse(BaseModel):
    """Response model for job list"""
    count: int
    jobs: List[JobResponse]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_job(
    job: JobCreate,
    admin_user = Depends(get_admin_user)
):
    """Create a new job posting (Admin only)"""
    try:
        # Create job document
        job_doc = {
            "title": job.title,
            "jd_text": job.jd_text,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Insert into MongoDB
        result = jobs_collection.insert_one(job_doc)
        
        # Return as dict to ensure _id is included in JSON serialization
        return {
            "_id": str(result.inserted_id),
            "title": job_doc["title"],
            "jd_text": job_doc["jd_text"],
            "created_at": job_doc["created_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job: {str(e)}"
        )


@router.get("")
async def list_jobs(
    current_user = Depends(get_current_user)
):
    """List all job postings (JWT protected)"""
    try:
        # Get all jobs from MongoDB
        jobs_cursor = jobs_collection.find({})
        jobs = list(jobs_cursor)
        
        # Get application counts for all jobs
        application_counts = {}
        pipeline = [
            {"$group": {"_id": "$job_id", "count": {"$sum": 1}}}
        ]
        counts_result = list(applications_collection.aggregate(pipeline))
        for item in counts_result:
            application_counts[item["_id"]] = item["count"]
        
        # Convert ObjectId to string and return as dicts
        # This ensures _id is included in the JSON response
        job_list = []
        for job in jobs:
            job_id_str = str(job["_id"])
            application_count = application_counts.get(job_id_str, 0)
            
            job_dict = {
                "_id": job_id_str,
                "title": job.get("title", ""),
                "jd_text": job.get("jd_text", ""),
                "created_at": job.get("created_at", datetime.utcnow().isoformat() + "Z"),
                "application_count": application_count
            }
            job_list.append(job_dict)
        
        # Return as dict to ensure _id is included in JSON serialization
        return {
            "count": len(job_list),
            "jobs": job_list
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing jobs: {str(e)}"
        )


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """Get job details by ID (JWT protected)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Get application count for this job
        application_count = applications_collection.count_documents({"job_id": job_id})
        
        # Return as dict to ensure _id is included in JSON serialization
        return {
            "_id": str(job["_id"]),
            "title": job.get("title", ""),
            "jd_text": job.get("jd_text", ""),
            "created_at": job.get("created_at", datetime.utcnow().isoformat() + "Z"),
            "application_count": application_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting job: {str(e)}"
        )


@router.put("/{job_id}")
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    admin_user = Depends(get_admin_user)
):
    """Update job details (Admin only)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        # Check if job exists
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Build update document (only include fields that are provided)
        update_data = {}
        if job_update.title is not None:
            update_data["title"] = job_update.title
        if job_update.jd_text is not None:
            update_data["jd_text"] = job_update.jd_text
        
        # Update job
        jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        # Return updated job as dict to ensure _id is included
        updated_job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        return {
            "_id": str(updated_job["_id"]),
            "title": updated_job.get("title", ""),
            "jd_text": updated_job.get("jd_text", ""),
            "created_at": updated_job.get("created_at", datetime.utcnow().isoformat() + "Z")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating job: {str(e)}"
        )


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    admin_user = Depends(get_admin_user)
):
    """Delete a job (Admin only)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        # Check if job exists
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if there are applications for this job
        application_count = applications_collection.count_documents({"job_id": job_id})
        if application_count > 0:
            # Optionally: Delete associated applications or just warn
            # For now, we'll allow deletion but log a warning
            logger.warning(f"Deleting job {job_id} with {application_count} associated applications")
        
        # Delete the job
        result = jobs_collection.delete_one({"_id": ObjectId(job_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return {"message": "Job deleted successfully", "job_id": job_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting job: {str(e)}"
        )


@router.post("/{job_id}/apply", status_code=status.HTTP_200_OK)
async def apply_to_job(
    job_id: str,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    github_url: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    linkedin_resume: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user = Depends(get_current_user)
):
    """
    Apply to a job posting (User-only)
    
    Updates user profile with provided information and files,
    then automatically triggers an evaluation.
    """
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        # Verify job exists
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Get current user
        email = current_user.get("email")
        user_doc = users_collection.find_one({"email": email})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_id = str(user_doc["_id"])
        
        # Check if user already applied to this job
        existing_application = applications_collection.find_one({
            "user_id": user_id,
            "job_id": job_id
        })
        if existing_application:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already applied to this job"
            )
        
        # Build update data
        update_data = {}
        if first_name is not None:
            update_data["first_name"] = first_name.strip()
        if last_name is not None:
            update_data["last_name"] = last_name.strip()
        if city is not None:
            update_data["city"] = city.strip()
        if phone_number is not None:
            update_data["phone_number"] = phone_number.strip() if phone_number.strip() else None
        
        # Validate and update URLs - always save them (even if empty) to persist in profile
        if github_url is not None:
            github_url_cleaned = github_url.strip() if github_url else ""
            if github_url_cleaned:
                # Validate GitHub URL format
                github_pattern = r'^(https?://)?(www\.)?github\.com/[a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38}(/)?$'
                if not re.match(github_pattern, github_url_cleaned, re.IGNORECASE):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid GitHub URL format. Use: https://github.com/username or github.com/username"
                    )
                update_data["github_url"] = github_url_cleaned
                logger.info(f"Updating user GitHub URL: {github_url_cleaned}")
            else:
                # Empty string means clear the URL
                update_data["github_url"] = None
                logger.info("Clearing user GitHub URL (empty string provided)")
        
        if linkedin_url is not None:
            linkedin_url_cleaned = linkedin_url.strip() if linkedin_url else ""
            if linkedin_url_cleaned:
                update_data["linkedin_url"] = linkedin_url_cleaned
                logger.info(f"Updating user LinkedIn URL: {linkedin_url_cleaned}")
            else:
                # Empty string means clear the URL
                update_data["linkedin_url"] = None
                logger.info("Clearing user LinkedIn URL (empty string provided)")
        
        # Handle file uploads
        if resume:
            if not resume.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No resume file selected"
                )
            file_path = await save_uploaded_file(
                resume,
                settings.CV_UPLOAD_FOLDER,
                user_id,
                'cv'
            )
            if file_path:
                update_data["cv_file_path"] = file_path
        
        if linkedin_resume:
            if not linkedin_resume.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No LinkedIn resume file selected"
                )
            file_path = await save_uploaded_file(
                linkedin_resume,
                settings.LINKEDIN_UPLOAD_FOLDER,
                user_id,
                'linkedin'
            )
            if file_path:
                update_data["linkedin_file_path"] = file_path
        
        # Update user profile
        if update_data:
            users_collection.update_one(
                {"email": email},
                {"$set": update_data}
            )
        
        # Create application record immediately
        application_doc = {
            "user_id": user_id,
            "job_id": job_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        application_result = applications_collection.insert_one(application_doc)
        application_id = str(application_result.inserted_id)
        
        # Trigger evaluation in background (don't wait for it)
        background_tasks.add_task(
            run_evaluation_background,
            user_id,
            job_id,
            application_id
        )
        
        # Return immediate confirmation
        return {
            "message": "Application submitted successfully",
            "application_id": application_id,
            "status": "pending"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying to job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying to job: {str(e)}"
        )


async def run_evaluation_background(user_id: str, job_id: str, application_id: str):
    """
    Background task to run evaluation and update application record
    """
    try:
        # Trigger evaluation by calling the evaluation services directly
        from app.services.orchestrator import run_evaluation
        from app.services.normalization import normalize_skills
        from app.services.semantic import build_semantic_features
        from app.services.judge import judge_candidate
        from app.services.critic import critic_review
        from app.services.aggregator import aggregate_scores
        from app.services.role_classifier import classify_roles
        from app.models.evaluation_model import evaluations_collection
        from app.services.agents.orchestrator_agent import AgenticOrchestrator
        
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
        
        logger.info(f"Starting background evaluation for user {user_id} and job {job_id}")
        
        evaluation_result = None
        evaluation_id = None
        
        if settings.USE_AGENTIC_EVALUATION:
            logger.info("Using agentic evaluation system")
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
        
        # Update application record with evaluation ID and status
        applications_collection.update_one(
            {"_id": ObjectId(application_id)},
            {
                "$set": {
                    "evaluation_id": evaluation_id,
                    "status": "completed"
                }
            }
        )
        
        logger.info(f"Evaluation completed for application {application_id}")
    
    except Exception as e:
        logger.error(f"Error in background evaluation for application {application_id}: {str(e)}")
        # Update application status to failed
        try:
            applications_collection.update_one(
                {"_id": ObjectId(application_id)},
                {"$set": {"status": "failed"}}
            )
        except:
            pass


@router.get("/{job_id}/applications/count", status_code=status.HTTP_200_OK)
async def get_application_count(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get the count of applications for a specific job
    """
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        # Count applications for this job
        count = applications_collection.count_documents({"job_id": job_id})
        
        return {
            "job_id": job_id,
            "application_count": count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application count: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting application count: {str(e)}"
        )


@router.get("/{job_id}/application-status", response_model=ApplicationStatusResponse, status_code=status.HTTP_200_OK)
async def get_application_status(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """
    Check if current user has applied to this job
    """
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(job_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID format"
            )
        
        # Get current user
        email = current_user.get("email")
        user_doc = users_collection.find_one({"email": email})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_id = str(user_doc["_id"])
        
        # Check if application exists
        application = applications_collection.find_one({
            "user_id": user_id,
            "job_id": job_id
        })
        
        if application:
            return ApplicationStatusResponse(
                has_applied=True,
                application_id=str(application["_id"])
            )
        else:
            return ApplicationStatusResponse(
                has_applied=False,
                application_id=None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking application status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking application status: {str(e)}"
        )

