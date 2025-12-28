from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from bson import ObjectId
from datetime import datetime
from typing import Optional
import logging
import os

from app.auth.dependencies import get_current_user, get_admin_user
from app.models.user_model import users_collection
from app.schemas.user_schema import UserResponse, UserUpdate
from app.schemas.admin_schema import UserListResponse, UserListItem
from app.utils.file_handler import save_uploaded_file
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

# Ensure upload directories exist
os.makedirs(settings.CV_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(settings.LINKEDIN_UPLOAD_FOLDER, exist_ok=True)


@router.get("", response_model=UserListResponse)
def list_all_users(
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user=Depends(get_admin_user)
):
    """List all users with filtering (admin only)"""
    try:
        # Build query
        query = {}
        if role:
            query["role"] = role
        if search:
            # Search in email, first_name, last_name
            query["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"first_name": {"$regex": search, "$options": "i"}},
                {"last_name": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}}
            ]
        
        # Get users
        users_cursor = users_collection.find(query).skip(skip).limit(limit).sort("email", 1)
        users = list(users_cursor)
        
        # Convert to response format
        user_list = []
        for user in users:
            user_list.append(UserListItem(
                id=str(user["_id"]),
                email=user.get("email", ""),
                role=user.get("role", "user"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                city=user.get("city"),
                created_at=user.get("created_at", datetime.utcnow().isoformat() + "Z") if user.get("created_at") else None
            ))
        
        total_count = users_collection.count_documents(query)
        
        return UserListResponse(
            count=total_count,
            users=user_list
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
def get_me(user=Depends(get_current_user)):
    """Get current user's full profile including candidate fields"""
    try:
        email = user.get("email")
        user_doc = users_collection.find_one({"email": email})
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Build response with all fields
        return UserResponse(
            email=user_doc.get("email", email),
            role=user_doc.get("role", "user"),
            first_name=user_doc.get("first_name"),
            last_name=user_doc.get("last_name"),
            city=user_doc.get("city"),
            phone_number=user_doc.get("phone_number"),
            name=user_doc.get("name"),  # Keep for backward compatibility
            github_handle=user_doc.get("github_handle"),
            github_url=user_doc.get("github_url"),
            linkedin_url=user_doc.get("linkedin_url"),
            cv_file_path=user_doc.get("cv_file_path"),
            linkedin_file_path=user_doc.get("linkedin_file_path")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user profile: {str(e)}"
        )


@router.put("/me", response_model=UserResponse)
def update_me(
    user_update: UserUpdate,
    current_user=Depends(get_current_user)
):
    """Update current user's profile (name, github_handle)"""
    try:
        email = current_user.get("email")
        user_doc = users_collection.find_one({"email": email})
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Build update document (only include fields that are provided)
        update_data = {}
        if user_update.name is not None:
            update_data["name"] = user_update.name
        if user_update.github_handle is not None:
            update_data["github_handle"] = user_update.github_handle
        if user_update.github_url is not None:
            update_data["github_url"] = user_update.github_url
        if user_update.linkedin_url is not None:
            update_data["linkedin_url"] = user_update.linkedin_url
        
        # Update user
        if update_data:
            users_collection.update_one(
                {"email": email},
                {"$set": update_data}
            )
        
        # Return updated user
        updated_user = users_collection.find_one({"email": email})
        return UserResponse(
            email=updated_user.get("email", email),
            role=updated_user.get("role", "user"),
            first_name=updated_user.get("first_name"),
            last_name=updated_user.get("last_name"),
            city=updated_user.get("city"),
            phone_number=updated_user.get("phone_number"),
            name=updated_user.get("name"),  # Keep for backward compatibility
            github_handle=updated_user.get("github_handle"),
            github_url=updated_user.get("github_url"),
            linkedin_url=updated_user.get("linkedin_url"),
            cv_file_path=updated_user.get("cv_file_path"),
            linkedin_file_path=updated_user.get("linkedin_file_path")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user profile: {str(e)}"
        )


@router.post("/me/upload-cv", status_code=status.HTTP_200_OK)
async def upload_cv(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """Upload CV PDF for current user (JWT protected)"""
    try:
        email = current_user.get("email")
        user_doc = users_collection.find_one({"email": email})
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file selected"
            )
        
        # Use user's email as identifier for file storage
        user_id = str(user_doc.get("_id", ""))
        
        # Save file using FastAPI-compatible handler
        file_path = await save_uploaded_file(
            file,
            settings.CV_UPLOAD_FOLDER,
            user_id,
            'cv'
        )
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to save file. Only PDF files are allowed."
            )
        
        # Update user document
        users_collection.update_one(
            {"email": email},
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


@router.post("/me/upload-linkedin", status_code=status.HTTP_200_OK)
async def upload_linkedin(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """Upload LinkedIn PDF for current user (JWT protected)"""
    try:
        email = current_user.get("email")
        user_doc = users_collection.find_one({"email": email})
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file selected"
            )
        
        # Use user's email as identifier for file storage
        user_id = str(user_doc.get("_id", ""))
        
        # Save file using FastAPI-compatible handler
        file_path = await save_uploaded_file(
            file,
            settings.LINKEDIN_UPLOAD_FOLDER,
            user_id,
            'linkedin'
        )
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to save file. Only PDF files are allowed."
            )
        
        # Update user document
        users_collection.update_one(
            {"email": email},
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
