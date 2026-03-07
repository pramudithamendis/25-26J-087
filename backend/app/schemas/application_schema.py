from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApplicationCreate(BaseModel):
    """Schema for creating a new application"""
    user_id: str
    job_id: str
    status: str = "pending"  # pending, completed, failed

class ApplicationResponse(BaseModel):
    """Schema for application response"""
    _id: str
    user_id: str
    job_id: str
    status: str
    created_at: str
    evaluation_id: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True

class ApplicationStatusResponse(BaseModel):
    """Schema for checking if user has applied"""
    has_applied: bool
    application_id: Optional[str] = None


class UserApplicationStatusResponse(BaseModel):
    """Schema for user application status (basic info only, no evaluation details)"""
    application_id: str
    job_id: str
    status: str  # "submitted", "under_review", "reviewed"
    created_at: str
    job_title: Optional[str] = None
