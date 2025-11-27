from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from typing import Optional

class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    github_handle: Optional[str] = Field(None, max_length=39)
    
    @field_validator('github_handle')
    @classmethod
    def validate_github_handle(cls, v):
        if v:
            v = v.strip()
            # GitHub username rules: alphanumeric, hyphens, max 39 chars, cannot start/end with hyphen
            github_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38}$'
            if not re.match(github_pattern, v):
                raise ValueError("Invalid GitHub handle format (must be 1-39 alphanumeric characters, hyphens allowed but not at start/end)")
        return v.strip() if v else None

class CandidateResponse(BaseModel):
    _id: str
    name: str
    email: str
    github_handle: Optional[str] = None
    cv_file_path: Optional[str] = None
    linkedin_file_path: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True

class CandidateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    github_handle: Optional[str] = Field(None, max_length=39)
    
    @field_validator('github_handle')
    @classmethod
    def validate_github_handle(cls, v):
        if v:
            v = v.strip()
            github_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38}$'
            if not re.match(github_pattern, v):
                raise ValueError("Invalid GitHub handle format (must be 1-39 alphanumeric characters, hyphens allowed but not at start/end)")
        return v.strip() if v else None

