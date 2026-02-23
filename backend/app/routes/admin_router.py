from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from bson import ObjectId
from datetime import datetime
from typing import Optional, List
import csv
import io
import logging

from app.auth.dependencies import get_admin_user
from app.models.user_model import users_collection
from app.models.job_model import jobs_collection
from app.models.application_model import applications_collection
from app.models.evaluation_model import evaluations_collection
from app.schemas.admin_schema import (
    AdminStatsResponse,
    ApplicationListResponse,
    ApplicationListItem,
    ApplicationDetailResponse,
    EvaluationListResponse,
    EvaluationListItem,
    SystemSettings,
    SystemSettingsResponse
)
from app.models.job_model import jobs_collection
from app.config import settings
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Settings file path (simple file-based storage, can be moved to DB later)
SETTINGS_FILE = "admin_settings.json"

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(admin_user=Depends(get_admin_user)):
    """Get dashboard statistics (admin only)"""
    try:
        total_jobs = jobs_collection.count_documents({})
        total_applications = applications_collection.count_documents({})
        total_users = users_collection.count_documents({})
        total_evaluations = evaluations_collection.count_documents({})
        
        return AdminStatsResponse(
            total_jobs=total_jobs,
            total_applications=total_applications,
            total_users=total_users,
            total_evaluations=total_evaluations
        )
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting admin stats: {str(e)}"
        )

@router.get("/applications", response_model=ApplicationListResponse)
async def list_all_applications(
    job_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    has_evaluation: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user=Depends(get_admin_user)
):
    """List all applications with filtering (admin only)"""
    try:
        # Build query
        query = {}
        if job_id:
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format")
            query["job_id"] = job_id
        if user_id:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
            query["user_id"] = user_id
        if status_filter:
            query["status"] = status_filter
        
        # Get applications
        applications_cursor = applications_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        applications = list(applications_cursor)
        
        # Filter by has_evaluation if specified
        if has_evaluation is not None:
            if has_evaluation:
                applications = [app for app in applications if app.get("evaluation_id")]
            else:
                applications = [app for app in applications if not app.get("evaluation_id")]
        
        # Enrich with user and job info
        application_list = []
        for app in applications:
            app_dict = {
                "id": str(app["_id"]),
                "user_id": app.get("user_id", ""),
                "job_id": app.get("job_id", ""),
                "status": app.get("status", "pending"),
                "created_at": app.get("created_at", datetime.utcnow().isoformat() + "Z"),
                "evaluation_id": str(app["evaluation_id"]) if app.get("evaluation_id") else None
            }
            
            # Get user info
            if app.get("user_id"):
                try:
                    user = users_collection.find_one({"_id": ObjectId(app["user_id"])})
                    if user:
                        app_dict["user_email"] = user.get("email", "")
                        first_name = user.get("first_name", "")
                        last_name = user.get("last_name", "")
                        app_dict["user_name"] = f"{first_name} {last_name}".strip() or user.get("name", "")
                except:
                    pass
            
            # Get job info
            if app.get("job_id"):
                try:
                    job = jobs_collection.find_one({"_id": ObjectId(app["job_id"])})
                    if job:
                        app_dict["job_title"] = job.get("title", "")
                except:
                    pass
            
            application_list.append(ApplicationListItem(**app_dict))
        
        total_count = applications_collection.count_documents(query)
        
        return ApplicationListResponse(
            count=total_count,
            applications=application_list
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing applications: {str(e)}"
        )

def convert_objectid_to_str(obj):
    """Recursively convert ObjectId fields to strings in a dictionary"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    else:
        return obj

@router.get("/applications/{application_id}", response_model=ApplicationDetailResponse)
async def get_application_details(
    application_id: str,
    admin_user=Depends(get_admin_user)
):
    """Get full application details (admin only)"""
    try:
        if not ObjectId.is_valid(application_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application ID format")
        
        application = applications_collection.find_one({"_id": ObjectId(application_id)})
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
        # Get user details and convert ObjectIds to strings
        user_dict = {}
        if application.get("user_id"):
            user = users_collection.find_one({"_id": ObjectId(application["user_id"])})
            if user:
                user_dict = convert_objectid_to_str(user)
        
        # Get job details and convert ObjectIds to strings
        job_dict = {}
        if application.get("job_id"):
            job = jobs_collection.find_one({"_id": ObjectId(application["job_id"])})
            if job:
                job_dict = convert_objectid_to_str(job)
        
        return ApplicationDetailResponse(
            id=str(application["_id"]),
            user_id=application.get("user_id", ""),
            job_id=application.get("job_id", ""),
            status=application.get("status", "pending"),
            created_at=application.get("created_at", datetime.utcnow().isoformat() + "Z"),
            evaluation_id=str(application["evaluation_id"]) if application.get("evaluation_id") else None,
            user=user_dict,
            job=job_dict
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting application details: {str(e)}"
        )

@router.post("/applications/{application_id}/approve")
async def approve_application(
    application_id: str,
    admin_user=Depends(get_admin_user)
):
    """Approve an application (admin only)"""
    try:
        if not ObjectId.is_valid(application_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application ID format")
        
        result = applications_collection.update_one(
            {"_id": ObjectId(application_id)},
            {"$set": {"status": "approved"}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
        return {"message": "Application approved successfully", "application_id": application_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving application: {str(e)}"
        )

@router.post("/applications/{application_id}/reject")
async def reject_application(
    application_id: str,
    admin_user=Depends(get_admin_user)
):
    """Reject an application (admin only)"""
    try:
        if not ObjectId.is_valid(application_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application ID format")
        
        result = applications_collection.update_one(
            {"_id": ObjectId(application_id)},
            {"$set": {"status": "rejected"}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
        return {"message": "Application rejected successfully", "application_id": application_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting application: {str(e)}"
        )

@router.get("/applications/{application_id}/resume")
async def download_resume(
    application_id: str,
    admin_user=Depends(get_admin_user)
):
    """Download resume file for an application (admin only)"""
    try:
        if not ObjectId.is_valid(application_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application ID format")
        
        application = applications_collection.find_one({"_id": ObjectId(application_id)})
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
        # Get user to find resume file
        user_id = application.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found for this application")
        
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        cv_file_path = user.get("cv_file_path")
        if not cv_file_path or not os.path.exists(cv_file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file not found")
        
        def generate():
            with open(cv_file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        filename = os.path.basename(cv_file_path)
        return StreamingResponse(
            generate(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading resume: {str(e)}"
        )

@router.get("/applications/{application_id}/linkedin-resume")
async def download_linkedin_resume(
    application_id: str,
    admin_user=Depends(get_admin_user)
):
    """Download LinkedIn resume file for an application (admin only)"""
    try:
        if not ObjectId.is_valid(application_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application ID format")
        
        application = applications_collection.find_one({"_id": ObjectId(application_id)})
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
        # Get user to find LinkedIn resume file
        user_id = application.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found for this application")
        
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        linkedin_file_path = user.get("linkedin_file_path")
        if not linkedin_file_path or not os.path.exists(linkedin_file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LinkedIn resume file not found")
        
        def generate():
            with open(linkedin_file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        filename = os.path.basename(linkedin_file_path)
        return StreamingResponse(
            generate(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading LinkedIn resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading LinkedIn resume: {str(e)}"
        )

@router.get("/export/applications")
async def export_applications(
    job_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    admin_user=Depends(get_admin_user)
):
    """Export applications to CSV (admin only)"""
    try:
        # Build query (same as list endpoint)
        query = {}
        if job_id:
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format")
            query["job_id"] = job_id
        if user_id:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
            query["user_id"] = user_id
        if status_filter:
            query["status"] = status_filter
        
        applications = list(applications_collection.find(query))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Application ID", "User Email", "User Name", "Job Title", 
            "Status", "Created At", "Evaluation ID"
        ])
        
        # Write data
        for app in applications:
            user_email = ""
            user_name = ""
            job_title = ""
            
            if app.get("user_id"):
                try:
                    user = users_collection.find_one({"_id": ObjectId(app["user_id"])})
                    if user:
                        user_email = user.get("email", "")
                        first_name = user.get("first_name", "")
                        last_name = user.get("last_name", "")
                        user_name = f"{first_name} {last_name}".strip() or user.get("name", "")
                except:
                    pass
            
            if app.get("job_id"):
                try:
                    job = jobs_collection.find_one({"_id": ObjectId(app["job_id"])})
                    if job:
                        job_title = job.get("title", "")
                except:
                    pass
            
            writer.writerow([
                str(app["_id"]),
                user_email,
                user_name,
                job_title,
                app.get("status", "pending"),
                app.get("created_at", ""),
                str(app.get("evaluation_id", "")) if app.get("evaluation_id") else ""
            ])
        
        output.seek(0)
        
        def generate():
            yield output.getvalue().encode('utf-8')
        
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="applications.csv"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting applications: {str(e)}"
        )

@router.get("/export/users")
async def export_users(admin_user=Depends(get_admin_user)):
    """Export users to CSV (admin only)"""
    try:
        users = list(users_collection.find({}))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "User ID", "Email", "Role", "First Name", "Last Name", 
            "City", "Phone Number", "GitHub URL", "LinkedIn URL"
        ])
        
        # Write data
        for user in users:
            writer.writerow([
                str(user.get("_id", "")),
                user.get("email", ""),
                user.get("role", "user"),
                user.get("first_name", ""),
                user.get("last_name", ""),
                user.get("city", ""),
                user.get("phone_number", ""),
                user.get("github_url", ""),
                user.get("linkedin_url", "")
            ])
        
        output.seek(0)
        
        def generate():
            yield output.getvalue().encode('utf-8')
        
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="users.csv"'}
        )
    except Exception as e:
        logger.error(f"Error exporting users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting users: {str(e)}"
        )

@router.get("/evaluations", response_model=EvaluationListResponse)
async def list_all_evaluations(
    job_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    max_score: Optional[float] = Query(None),
    decision: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user=Depends(get_admin_user)
):
    """List all evaluations with filtering (admin only)"""
    try:
        # Build query
        query = {}
        if job_id:
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format")
            query["job_id"] = job_id
        if user_id:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
            query["user_id"] = user_id
        if decision:
            query["decision"] = decision
        if min_score is not None or max_score is not None:
            score_query = {}
            if min_score is not None:
                score_query["$gte"] = min_score
            if max_score is not None:
                score_query["$lte"] = max_score
            query["total_score"] = score_query
        
        # Get evaluations
        evaluations_cursor = evaluations_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        evaluations = list(evaluations_cursor)
        
        # Enrich with user and job info
        evaluation_list = []
        for evaluation in evaluations:
            eval_dict = {
                "id": str(evaluation["_id"]),
                "user_id": evaluation.get("user_id", ""),
                "job_id": evaluation.get("job_id", ""),
                "total_score": evaluation.get("total_score", 0),
                "decision": evaluation.get("decision", "Not Selected"),
                "status": evaluation.get("status", "completed"),
                "created_at": evaluation.get("created_at", datetime.utcnow().isoformat() + "Z")
            }
            
            # Get user info
            if evaluation.get("user_id"):
                try:
                    user = users_collection.find_one({"_id": ObjectId(evaluation["user_id"])})
                    if user:
                        eval_dict["user_email"] = user.get("email", "")
                        first_name = user.get("first_name", "")
                        last_name = user.get("last_name", "")
                        eval_dict["user_name"] = f"{first_name} {last_name}".strip() or user.get("name", "")
                except:
                    pass
            
            # Get job info
            if evaluation.get("job_id"):
                try:
                    job = jobs_collection.find_one({"_id": ObjectId(evaluation["job_id"])})
                    if job:
                        eval_dict["job_title"] = job.get("title", "")
                except:
                    pass
            
            evaluation_list.append(EvaluationListItem(**eval_dict))
        
        total_count = evaluations_collection.count_documents(query)
        
        return EvaluationListResponse(
            count=total_count,
            evaluations=evaluation_list
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing evaluations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing evaluations: {str(e)}"
        )

@router.get("/export/evaluations")
async def export_evaluations(
    job_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    admin_user=Depends(get_admin_user)
):
    """Export evaluations to CSV (admin only)"""
    try:
        query = {}
        if job_id:
            if not ObjectId.is_valid(job_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format")
            query["job_id"] = job_id
        if user_id:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
            query["user_id"] = user_id
        
        evaluations = list(evaluations_collection.find(query))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Evaluation ID", "User Email", "User Name", "Job Title",
            "Total Score", "Decision", "Status", "Created At"
        ])
        
        # Write data
        for evaluation in evaluations:
            user_email = ""
            user_name = ""
            job_title = ""
            
            if evaluation.get("user_id"):
                try:
                    user = users_collection.find_one({"_id": ObjectId(evaluation["user_id"])})
                    if user:
                        user_email = user.get("email", "")
                        first_name = user.get("first_name", "")
                        last_name = user.get("last_name", "")
                        user_name = f"{first_name} {last_name}".strip() or user.get("name", "")
                except:
                    pass
            
            if evaluation.get("job_id"):
                try:
                    job = jobs_collection.find_one({"_id": ObjectId(evaluation["job_id"])})
                    if job:
                        job_title = job.get("title", "")
                except:
                    pass
            
            writer.writerow([
                str(evaluation.get("_id", "")),
                user_email,
                user_name,
                job_title,
                evaluation.get("total_score", 0),
                evaluation.get("decision", ""),
                evaluation.get("status", ""),
                evaluation.get("created_at", "")
            ])
        
        output.seek(0)
        
        def generate():
            yield output.getvalue().encode('utf-8')
        
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="evaluations.csv"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting evaluations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting evaluations: {str(e)}"
        )

@router.get("/settings", response_model=SystemSettingsResponse)
async def get_settings(admin_user=Depends(get_admin_user)):
    """Get system settings (admin only)"""
    try:
        import json
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                settings_data = json.load(f)
                return SystemSettingsResponse(settings=SystemSettings(**settings_data))
        else:
            # Return defaults
            return SystemSettingsResponse(settings=SystemSettings())
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting settings: {str(e)}"
        )

@router.put("/settings", response_model=SystemSettingsResponse)
async def update_settings(
    settings_data: SystemSettings,
    admin_user=Depends(get_admin_user)
):
    """Update system settings (admin only)"""
    try:
        import json
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings_data.dict(), f, indent=2)
        
        return SystemSettingsResponse(settings=settings_data)
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating settings: {str(e)}"
        )

