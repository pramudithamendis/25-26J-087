from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, List
from datetime import datetime

# ==========================================================
# BASICS (Header Section)
# ==========================================================

class Basics(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    summary: Optional[str] = None
    address: Optional[str] = None  # address field

# ==========================================================
# EDUCATION
# ==========================================================

class Education(BaseModel):
    institution: Optional[str] = None
    area: Optional[str] = None          # Major / Field
    studyType: Optional[str] = None     # BSc, MSc, etc.
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    gpa: Optional[str] = None
    courses: List[str] = Field(default_factory=list)

# ==========================================================
# WORK EXPERIENCE
# ==========================================================

class Work(BaseModel):
    name: Optional[str] = None          # Company name
    position: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)

# ==========================================================
# SKILLS
# ==========================================================

class Skill(BaseModel):
    name: Optional[str] = None
    level: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

# ==========================================================
# PROJECTS
# ==========================================================

class Project(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    url: Optional[str] = None

# ==========================================================
# CERTIFICATES
# ==========================================================

class Certificate(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    date: Optional[str] = None

# ==========================================================
# MAIN CV MODEL (OpenResume-Compatible)
# ==========================================================

class CVParsed(BaseModel):
    cv_id: str

    basics: Optional[Basics] = None
    education: List[Education] = Field(default_factory=list)
    work: List[Work] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certificates: List[Certificate] = Field(default_factory=list)

    raw_text: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    user_email: Optional[EmailStr] = None

# ==========================================================
# RESPONSE MODEL
# ==========================================================

class CVSubmitResponse(BaseModel):
    status: str
    message: str
    cv_id: str
    parsed_data: CVParsed