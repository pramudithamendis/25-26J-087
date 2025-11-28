from fastapi import APIRouter, Form, Depends, HTTPException
from app.auth.dependencies import get_current_user
from app.services.turnover_service import predict_turnover_from_cv_id

router = APIRouter(prefix="/turnover", tags=["Turnover Prediction"])

@router.post("/predict")
async def predict_turnover_api(
    cv_id: str = Form(..., description="CV ID from MongoDB (obtained after CV submission)"),
    job_description: str = Form(..., description="Job description text"),
    job_location: str = Form(None, description="Job location (e.g., 'Colombo, Sri Lanka'). Optional - will be extracted from JD if not provided"),
    user: dict = Depends(get_current_user)
):
    """
    Predict employee turnover risk
    
    **Workflow:**
    1. User submits CV via `/cv/submit` → gets `cv_id`
    2. User calls this endpoint with `cv_id` + job description + job location (optional)
    3. System retrieves parsed CV from MongoDB
    4. Calculates commute distance using geocoding API (geocode.maps.co)
    5. Extracts features aligned with ML model
    6. Returns prediction with risk factors
    
    **Commute Distance Feature:**
    - Uses geocode.maps.co API (free tier: 25,000 requests)
    - Calculates distance between CV location and job location
    - Converts distance to location match score:
      * < 5 km: High match (1.0)
      * 5-15 km: Medium match (0.7)
      * 15-30 km: Low match (0.4)
      * > 30 km: Very low match (0.2)
    
    **Risk Levels:**
    - 0: High Risk (leaves within 6 months)
    - 1: Medium Risk (leaves in 6-12 months)  
    - 2: Low Risk (stays longer than 1 year)
    """
    
    if not cv_id:
        raise HTTPException(400, "cv_id is required")
    
    if not job_description or len(job_description.strip()) < 50:
        raise HTTPException(400, "Job description must be at least 50 characters")
    
    # Call prediction service (uses MongoDB data + geocoding)
    result = await predict_turnover_from_cv_id(cv_id, job_description, job_location)
    
    return result

@router.get("/health")
async def health_check():
    """Check if model is loaded"""
    from app.services.model_loader import get_model
    
    try:
        model = get_model()
        return {
            "status": "healthy",
            "model_loaded": model is not None,
            "message": "Turnover prediction service is operational"
        }
    except Exception as e:
        raise HTTPException(500, f"Model not loaded: {str(e)}")