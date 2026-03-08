# backend/app/schemas/forecast_schema.py
from pydantic import BaseModel
from typing import List, Optional

class ForecastRecord(BaseModel):
    ds: str  # week_id
    skill: str
    job_count: int
    google_interest: int
    y: float  # normalized trend score

class ForecastDatasetResponse(BaseModel):
    success: bool
    weeks_limit: int
    forecast_dataset: List[ForecastRecord]

class ColdStartResponse(BaseModel):
    success: bool
    stored_count: int
    message: Optional[str]=None
    
class PredictSkillRequest(BaseModel):
    skill: str
    job_count: int
    google_interest: int