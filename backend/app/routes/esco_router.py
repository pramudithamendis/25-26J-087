from fastapi import APIRouter
from app.services.esco_mapper import get_esco_mapper

router = APIRouter(prefix="/esco", tags=["ESCO"])

@router.get("/map-job-title")
async def map_job_title(job_title: str):
    """Map a job title to ESCO occupation"""
    esco = get_esco_mapper()
    if not esco:
        return {"error": "ESCO not available"}
    
    result = esco.map_job_title(job_title)
    return result or {"error": "No match found"}

@router.get("/map-skill")
async def map_skill(skill: str):
    """Map a skill to ESCO concept"""
    esco = get_esco_mapper()
    if not esco:
        return {"error": "ESCO not available"}
    
    result = esco.map_skill(skill)
    return result or {"error": "No match found"}