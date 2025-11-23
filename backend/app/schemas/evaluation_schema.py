from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class EvaluationRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)

class EvaluationResponse(BaseModel):
    _id: str
    candidate_id: str
    job_id: str
    total_score: int
    decision: str
    role_predictions: List[Dict[str, Any]]
    why: List[str]
    breakdown: Dict[str, Any]
    raw_pipeline: Dict[str, Any]
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True

