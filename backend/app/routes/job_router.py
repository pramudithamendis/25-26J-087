from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import datetime
from typing import List
import logging

from app.models.job_model import jobs_collection
from app.schemas.job_schema import JobCreate, JobResponse, JobUpdate
from app.auth.dependencies import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


class JobListResponse(BaseModel):
    """Response model for job list"""
    count: int
    jobs: List[JobResponse]


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job: JobCreate,
    current_user = Depends(get_current_user)
):
    """Create a new job posting (JWT protected)"""
    try:
        # Create job document
        job_doc = {
            "title": job.title,
            "jd_text": job.jd_text,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Insert into MongoDB
        result = jobs_collection.insert_one(job_doc)
        
        # Return created job
        job_doc["_id"] = str(result.inserted_id)
        return JobResponse(**job_doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job: {str(e)}"
        )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    current_user = Depends(get_current_user)
):
    """List all job postings (JWT protected)"""
    try:
        # Get all jobs from MongoDB
        jobs_cursor = jobs_collection.find({})
        jobs = list(jobs_cursor)
        
        # Convert ObjectId to string
        job_list = []
        for job in jobs:
            job["_id"] = str(job["_id"])
            job_list.append(JobResponse(**job))
        
        return JobListResponse(
            count=len(job_list),
            jobs=job_list
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing jobs: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobResponse)
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
        
        job["_id"] = str(job["_id"])
        return JobResponse(**job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting job: {str(e)}"
        )


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    current_user = Depends(get_current_user)
):
    """Update job details (JWT protected)"""
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
        
        # Return updated job
        updated_job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        updated_job["_id"] = str(updated_job["_id"])
        return JobResponse(**updated_job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating job: {str(e)}"
        )

