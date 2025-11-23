from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from bson import ObjectId
from datetime import datetime
from typing import Optional
import logging

from app.models.candidate_model import candidates_collection
from app.schemas.candidate_schema import CandidateCreate, CandidateResponse, CandidateUpdate
from app.utils.file_handler import save_uploaded_file
from app.auth.dependencies import get_current_user
from app.config import settings
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])

# Ensure upload directories exist
os.makedirs(settings.CV_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(settings.LINKEDIN_UPLOAD_FOLDER, exist_ok=True)


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate: CandidateCreate,
    current_user = Depends(get_current_user)
):
    """Create a new candidate (JWT protected)"""
    try:
        # Check if email already exists
        existing = candidates_collection.find_one({"email": candidate.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create candidate document
        candidate_doc = {
            "name": candidate.name,
            "email": candidate.email,
            "github_handle": candidate.github_handle,
            "cv_file_path": None,
            "linkedin_file_path": None,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Insert into MongoDB
        result = candidates_collection.insert_one(candidate_doc)
        
        # Return created candidate
        candidate_doc["_id"] = str(result.inserted_id)
        return CandidateResponse(**candidate_doc)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating candidate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating candidate: {str(e)}"
        )


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    current_user = Depends(get_current_user)
):
    """Get candidate details by ID (JWT protected)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate ID format"
            )
        
        candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        candidate["_id"] = str(candidate["_id"])
        return CandidateResponse(**candidate)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting candidate: {str(e)}"
        )


@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    candidate_update: CandidateUpdate,
    current_user = Depends(get_current_user)
):
    """Update candidate details (JWT protected)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate ID format"
            )
        
        # Check if candidate exists
        candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Build update document (only include fields that are provided)
        update_data = {}
        if candidate_update.name is not None:
            update_data["name"] = candidate_update.name
        if candidate_update.email is not None:
            # Check if new email already exists (and is different from current)
            if candidate_update.email != candidate.get("email"):
                existing = candidates_collection.find_one({"email": candidate_update.email})
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
            update_data["email"] = candidate_update.email
        if candidate_update.github_handle is not None:
            update_data["github_handle"] = candidate_update.github_handle
        
        # Update candidate
        candidates_collection.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": update_data}
        )
        
        # Return updated candidate
        updated_candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        updated_candidate["_id"] = str(updated_candidate["_id"])
        return CandidateResponse(**updated_candidate)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating candidate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating candidate: {str(e)}"
        )


@router.post("/{candidate_id}/upload-cv", status_code=status.HTTP_200_OK)
async def upload_cv(
    candidate_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload CV PDF for a candidate (JWT protected)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate ID format"
            )
        
        # Verify candidate exists
        candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file selected"
            )
        
        # Save file using FastAPI-compatible handler
        file_path = await save_uploaded_file(
            file,
            settings.CV_UPLOAD_FOLDER,
            candidate_id,
            'cv'
        )
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to save file. Only PDF files are allowed."
            )
        
        # Update candidate document
        candidates_collection.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"cv_file_path": file_path}}
        )
        
        return {
            "message": "CV uploaded successfully",
            "file_path": file_path
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading CV: {str(e)}"
        )


@router.post("/{candidate_id}/upload-linkedin", status_code=status.HTTP_200_OK)
async def upload_linkedin(
    candidate_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload LinkedIn PDF for a candidate (JWT protected)"""
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate ID format"
            )
        
        # Verify candidate exists
        candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file selected"
            )
        
        # Save file using FastAPI-compatible handler
        file_path = await save_uploaded_file(
            file,
            settings.LINKEDIN_UPLOAD_FOLDER,
            candidate_id,
            'linkedin'
        )
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to save file. Only PDF files are allowed."
            )
        
        # Update candidate document
        candidates_collection.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$set": {"linkedin_file_path": file_path}}
        )
        
        return {
            "message": "LinkedIn PDF uploaded successfully",
            "file_path": file_path
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading LinkedIn PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading LinkedIn PDF: {str(e)}"
        )

