from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class AdminStatsResponse(BaseModel):
    total_jobs: int
    total_applications: int
    total_users: int
    total_evaluations: int

class UserListItem(BaseModel):
    id: str = Field(..., alias="_id")
    email: str
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class UserListResponse(BaseModel):
    count: int
    users: List[UserListItem]

class ApplicationListItem(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    job_id: str
    status: str
    created_at: str
    evaluation_id: Optional[str] = None
    evaluation_status: Optional[str] = None  # "pending" | "processing" | "evaluated" | "failed"
    processing_started_at: Optional[str] = None
    processing_completed_at: Optional[str] = None
    error_message: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    job_title: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class ApplicationListResponse(BaseModel):
    count: int
    applications: List[ApplicationListItem]

class ApplicationDetailResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    job_id: str
    status: str
    created_at: str
    evaluation_id: Optional[str] = None
    evaluation_status: Optional[str] = None  # "pending" | "processing" | "evaluated" | "failed"
    processing_started_at: Optional[str] = None
    processing_completed_at: Optional[str] = None
    error_message: Optional[str] = None
    user: dict  # Full user profile
    job: dict  # Full job details

    class Config:
        from_attributes = True
        populate_by_name = True

class EvaluationListItem(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    job_id: str
    total_score: float
    decision: str
    status: str
    created_at: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    job_title: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class EvaluationListResponse(BaseModel):
    count: int
    evaluations: List[EvaluationListItem]

class SystemSettings(BaseModel):
    evaluation_threshold_selected: int = 75  # Minimum score for "Selected"
    evaluation_threshold_review: int = 60   # Minimum score for "Review"
    email_notifications_enabled: bool = True

class SystemSettingsResponse(BaseModel):
    settings: SystemSettings

