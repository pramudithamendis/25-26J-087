from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class CVParsed(BaseModel):
    """Parsed CV data structure"""
    cv_id: str
    name: Optional[str] = None
    emails: List[str] = []
    phones: List[str] = []
    links: Dict[str, List[str]] = {}
    sections: Dict[str, str] = {}
    raw_text: str = ""
    uploaded_at: Optional[datetime] = None
    user_email: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True

class CVSubmitResponse(BaseModel):
    """Response after CV submission"""
    status: str
    message: str
    cv_id: str
    parsed_data: CVParsed