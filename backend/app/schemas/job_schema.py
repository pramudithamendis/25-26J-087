from pydantic import BaseModel, Field
from typing import Optional

class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    jd_text: str = Field(..., min_length=50, max_length=50000)
    location: Optional[str] = None

class JobResponse(BaseModel):
    _id: str
    title: str
    jd_text: str
    created_at: str
    
    class Config:
        from_attributes = True
        populate_by_name = True

class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    jd_text: Optional[str] = Field(None, min_length=50, max_length=50000)
    location: Optional[str] = None
