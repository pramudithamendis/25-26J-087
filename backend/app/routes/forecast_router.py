# backend/app/routes/forecast_router.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.auth.dependencies import get_admin_user
from app.services.forecast_dataset_service import build_forecast_dataset, fetch_cold_start_data
from app.services.monthly_retrain_service import monthly_retrain, predict_future_skills
from app.schemas.forecast_schema import ForecastDatasetResponse, ColdStartResponse, PredictSkillRequest

router = APIRouter(prefix="/api/forecast", tags=["Forecast"])

@router.post("/dataset", response_model=ForecastDatasetResponse)
def get_forecast_dataset(weeks_limit: int = 12, user=Depends(get_admin_user)):
    """
    Build and return the forecast dataset for the latest `weeks_limit` weeks.
    """
    try:
        df = build_forecast_dataset(weeks_limit)
        if df.empty:
            return {"success": True, "message": "No forecast data available", "forecast_dataset": []}
        
        data = df.to_dict(orient="records")
        return {"success": True, "weeks_limit": weeks_limit, "forecast_dataset": data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build forecast dataset: {e}")


@router.post("/cold-start", response_model=ColdStartResponse)
def trigger_cold_start(month_limit: int = 3, batch_size: int = 5, user=Depends(get_admin_user)):
    """
    Trigger fetching Google Trends cold-start data.
    """
    try:
        stored = fetch_cold_start_data(month_limit=month_limit, batch_size=batch_size)
        return {"success": True, "stored_count": len(stored), "stored_records": stored}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cold-start data: {e}")

@router.post("/retrain")
def retrain_model(forecast_weeks: int = 12, user=Depends(get_admin_user)):
    """
    Trigger monthly retraining of the combined skill model.
    """
    model = monthly_retrain(forecast_weeks=forecast_weeks)
    if not model:
        raise HTTPException(status_code=400, detail="Retraining failed or no data available.")
    return {"message": f"Combined skill model retrained for last {forecast_weeks} weeks."}

@router.post("/predict")
def predict_skill_trend(request: PredictSkillRequest, user=Depends(get_admin_user)):
    """
    Predict the trend score for a given skill.
    """
    y_pred = predict_future_skills(
        skill=request.skill,
        job_count=request.job_count,
        google_interest=request.google_interest
    )
    if y_pred is None:
        raise HTTPException(status_code=404, detail=f"Skill '{request.skill}' unseen or model not available.")
    return {"skill": request.skill, "predicted_trend_score": y_pred}