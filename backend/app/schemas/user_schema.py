from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from typing import Optional

class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    city: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    password: str

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v):
        if not v or not v.strip():
            raise ValueError("First name is required")
        # Allow letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\-']+$", v.strip()):
            raise ValueError("First name can only contain letters, spaces, hyphens, and apostrophes")
        return v.strip()

    @field_validator('last_name')
    @classmethod
    def validate_last_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Last name is required")
        # Allow letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\-']+$", v.strip()):
            raise ValueError("Last name can only contain letters, spaces, hyphens, and apostrophes")
        return v.strip()

    @field_validator('city')
    @classmethod
    def validate_city(cls, v):
        if not v or not v.strip():
            raise ValueError("City is required")
        return v.strip()

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        if v:
            # Remove common formatting characters for validation
            cleaned = re.sub(r'[\s\-\(\)]', '', v)
            # Allow digits and optional leading +
            if not re.match(r'^\+?[0-9]{7,15}$', cleaned):
                raise ValueError("Phone number must be 7-15 digits, optionally starting with + for country code")
        return v.strip() if v else None

    @field_validator('password')
    def validate_password(cls, v):
        # 1. Check encoding length for bcrypt (max 72 bytes)
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password too long. Maximum 72 characters allowed (due to security hashing limits).")

        # 2. Minimum length
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        # 3. Require variety: uppercase, lowercase, digit, special char
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character.")

        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    github_handle: Optional[str] = Field(None, max_length=39)
    github_url: Optional[str] = Field(None, max_length=200)
    linkedin_url: Optional[str] = Field(None, max_length=200)
    
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

    @field_validator('github_url')
    @classmethod
    def validate_github_url(cls, v):
        if v:
            v = v.strip()
            # Allow full URL or just github.com/username format
            github_url_pattern = r'^(https?://)?(www\.)?github\.com/[a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38}(/)?$'
            if not re.match(github_url_pattern, v, re.IGNORECASE):
                raise ValueError("Invalid GitHub URL format. Use: https://github.com/username or github.com/username")
        return v.strip() if v else None

    @field_validator('linkedin_url')
    @classmethod
    def validate_linkedin_url(cls, v):
        # No validation - accept any string
        return v.strip() if v else None


class UserResponse(BaseModel):
    email: str
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    name: Optional[str] = None  # Keep for backward compatibility
    github_handle: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    cv_file_path: Optional[str] = None
    linkedin_file_path: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True