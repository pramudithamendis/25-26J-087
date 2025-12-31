# /backend/app/routes/trends_router.py

from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.services.goolge_trends_service import fetch_google_trends
from app.services.trend_calculation_service import calculate_skill_trends 

router = APIRouter(prefix="/trends", tags=["Trends"])

@router.post("/google/fetch")
def fetch_google_trends_endpoint(
    user=Depends(get_current_user)
):
    data = fetch_google_trends()
    return{
        "sucess": True,
        "week_id": data.get("week_id"),
        "skills_processed": data.get("skills_processed",0),
        "results": data.get("results", [])
    }

@router.post("/calculation")
def calculate_trends_endpoint(
    user=Depends(get_current_user)
):
    result = calculate_skill_trends()
    return{
        "success": True,
        "week_id": result.get("week_id"),
        "month_id": result.get("month_id"),
        "skill_processed": result.get("skill_processed",0),
        "results": result.get("results", [])

    }

