# /backend/app/routes/trends_router.py

from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_admin_user, get_current_user
from app.services.goolge_trends_service import fetch_google_trends
from app.services.trend_calculation_service import calculate_skill_trends
from app.services.cv_trend_score_service import calculate_all_cv_trend_score, calculate_single_cv_trend_score, get_job_applicants_scores
from app.utils.date_utils import current_week_id
from app.models.cv_trend_score_model import cv_trend_scores_collection

router = APIRouter(prefix="/api/trends", tags=["Trends"])

@router.post("/google/fetch")
def fetch_google_trends_endpoint(
    user=Depends(get_admin_user)
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
    user=Depends(get_admin_user)
):
    result = calculate_skill_trends()
    return{
        "success": True,
        "week_id": result.get("week_id"),
        "month_id": result.get("month_id"),
        "skill_processed": result.get("skill_processed",0),
        "results": result.get("results", [])
    }

@router.post("/cv/calculate")
def calculate_all_cv_trend_scores_endpoint(
    user=Depends(get_admin_user)
):
    """
    Compute trend scores for ALL resumes
    for the current week.
    """
    result = calculate_all_cv_trend_score()
    return {
        "success": True,
        "week_id": result.get("week_id"),
        "resumes_processed": result.get("resumes_processed", 0),
        "results": result.get("cv_processed", [])
    }

@router.get("/cv/calculate")
def get_all_cv_trend_scores_endpoint(
    week_id: str | None = None,
    user=Depends(get_admin_user)
):
    """
    Fetch CV trend scores (no calculation).
    Default: current week.
    """
    if not week_id:
        week_id = current_week_id()

    docs = list(cv_trend_scores_collection.find({"week_id": week_id}))

    results = []
    for d in docs:
        d["_id"] = str(d["_id"])
        d["cv_id"] = str(d["cv_id"])
        results.append(d)

    return {
        "success": True,
        "week_id": week_id,
        "resumes_processed": len(results),
        "results": results
    }
    

@router.post("/cv/{cv_id}/calculate")
def calculate_single_cv_trend_score_endpoint(
    cv_id: str,
    user=Depends(get_current_user)
):
    """
    Compute trend score for a single CV
    for the current week.
    """
    try:
        result = calculate_single_cv_trend_score(cv_id)
        return {
            "success": True,
            "week_id": result.get("week_id"),
            "cv_trend_score": result.get("cv_trend_score", 0),
            "skills_matched": result.get("skills_matched", []),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend calculation failed: {str(e)}")

@router.get("/{job_id}/evaluation")
def job_evaluation(job_id: str, user=Depends(get_current_user)):
    week_id = current_week_id()
    return get_job_applicants_scores(job_id, week_id)