# /backend/app/routes/trends_router.py

from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.services.goolge_trends_service import fetch_google_trends

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
