from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class EvaluationRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)

class DatasetValidationResult(BaseModel):
    """Dataset validation result structure"""
    original_score: Optional[int] = None
    calibrated_score: Optional[int] = None
    confidence: float = 0.0
    calibration_adjustment: int = 0
    validation_status: str = "unknown"
    similar_cases_count: int = 0
    similar_cases: List[Dict[str, Any]] = []
    reasoning: str = ""
    status: str = "unknown"

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
    dataset_validation: Optional[Dict[str, Any]] = None  # Optional to maintain backward compatibility
    
    class Config:
        from_attributes = True

