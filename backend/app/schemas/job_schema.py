from pydantic import BaseModel, Field
from typing import Optional, Literal

# Allowed project types for evaluation weight presets
ProjectTypeLiteral = Literal["r_and_d", "production", "support", "general"]
PROJECT_TYPE_VALUES = ("r_and_d", "production", "support", "general")


class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    jd_text: str = Field(..., min_length=50, max_length=50000)
    location: Optional[str] = None
    project_type: Optional[ProjectTypeLiteral] = None

class JobResponse(BaseModel):
    _id: str
    title: str
    jd_text: str
    created_at: str
    project_type: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    jd_text: Optional[str] = Field(None, min_length=50, max_length=50000)
    location: Optional[str] = None
    project_type: Optional[ProjectTypeLiteral] = None
