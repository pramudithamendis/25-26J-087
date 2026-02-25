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
    Predict employee turnover risk with SHAP-based explainability
    
    **Risk Levels:**
    - 0: High Risk (leaves within 6 months)
    - 1: Medium Risk (leaves in 6-12 months)  
    - 2: Low Risk (stays longer than 1 year)
    
    """
    
    if not cv_id:
        raise HTTPException(400, "cv_id is required")
    
    if not job_description or len(job_description.strip()) < 50:
        raise HTTPException(400, "Job description must be at least 50 characters")
    
    # Call prediction service
    result = await predict_turnover_from_cv_id(cv_id, job_description, job_location, user=user)
    
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
            "message": "Turnover prediction service is operational",
            "explainability": "SHAP-based explanations enabled"
        }
    except Exception as e:
        raise HTTPException(500, f"Model not loaded: {str(e)}")


@router.post("/explain")
async def explain_prediction(
    cv_id: str = Form(..., description="CV ID to explain"),
    job_description: str = Form(..., description="Job description text"),
    job_location: str = Form(None, description="Job location (optional)"),
    user: dict = Depends(get_current_user)
):
    """
    Get detailed SHAP explanation for a specific predictions

    """
    
    result = await predict_turnover_from_cv_id(cv_id, job_description, job_location)
    
    # Add additional metadata for explanation-focused use
    if result.get("status") == "success":
        result["explanation_metadata"] = {
            "generated_for": "detailed_analysis",
            "shap_method": "TreeExplainer",
            "visualization_ready": True,
            "full_feature_set": len(result.get("shap_explanation", {}).get("all_features", [])),
            "note": "Use 'all_features' for complete SHAP analysis"
        }
    
    return result

@router.get("/history")
async def get_prediction_history(
    user: dict = Depends(get_current_user),
    limit: int = 10
):
    """
    Get prediction history for the current user
    """
    from app.database import turnover_collection
    
    try:
        turnover_coll = turnover_collection
        
        # Find predictions for this user
        cursor = turnover_coll.find(
            {"user_email": user.get("email")},
            {"cv_id": 1, "cv_name": 1, "prediction": 1, "calculated_at": 1, "result_id": 1}  # ← remove "_id": 0, add result_id
            ).sort("calculated_at", -1).limit(limit)
        
        history = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            history.append(doc)
        
        return {
            "status": "success",
            "count": len(history),
            "predictions": history
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error fetching history: {str(e)}")


@router.get("/result/{cv_id}")
async def get_prediction_result(
    cv_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get stored prediction result for a CV
    """
    from app.database import turnover_collection
    
    try:
        turnover_coll = turnover_collection
        
        # Find most recent prediction for this CV by this user
        result = turnover_coll.find_one(
            {"cv_id": cv_id, "user_email": user.get("email")},
            sort=[("calculated_at", -1)]
        )
        
        if not result:
            raise HTTPException(404, f"No prediction found for CV {cv_id}")
        
        # Remove MongoDB _id
        result.pop("_id", None)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching result: {str(e)}")
    

@router.get("/result-by-id/{result_id}")
async def get_prediction_by_result_id(
    result_id: str,
    user: dict = Depends(get_current_user)
):
    """Get prediction result by unique result ID"""
    from app.database import turnover_collection
    from bson import ObjectId
    
    try:
        result = turnover_collection.find_one(
            {"_id": ObjectId(result_id), "user_email": user.get("email")}
        )
        
        if not result:
            raise HTTPException(404, f"Result not found")
        
        result.pop("_id", None)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching result: {str(e)}")
    

@router.get("/candidates")
async def get_all_candidates(
    user: dict = Depends(get_current_user)
):
    """Fetch all candidates from cv_collection"""
    from app.database import cv_collection

    try:
        print("DEBUG: fetching candidates")
        cursor = cv_collection.find(
            {},
            {"name": 1, "emails": 1, "uploaded_at": 1}
        ).sort("uploaded_at", -1)

        candidates = []
        for doc in cursor:
            print(f"DEBUG doc: {doc.get('name')}")
            candidates.append({
                "_id": str(doc["_id"]),
                "name": doc.get("name", "Unknown"),
                "email": doc.get("emails", [""])[0] if doc.get("emails") else "",
                "uploaded_at": doc.get("uploaded_at", "")
            })

        return {"status": "success", "candidates": candidates}

    except Exception as e:
        print(f"ERROR in candidates: {e}")  # ← this will show the real error
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error fetching candidates: {str(e)}")


@router.get("/jobs")
async def get_all_jobs(
    user: dict = Depends(get_current_user)
):
    """Fetch all jobs from jobs_collection"""
    from app.models.job_model import jobs_collection

    try:
        cursor = jobs_collection.find(
            {},
            {"title": 1, "jd_text": 1, "created_at": 1}
        ).sort("created_at", -1)

        jobs = []
        for doc in cursor:
            jobs.append({
                "_id": str(doc["_id"]),
                "title": doc.get("title", "Untitled"),
                "jd_text": doc.get("jd_text", ""),
                "created_at": doc.get("created_at", "")
            })

        return {"status": "success", "jobs": jobs}

    except Exception as e:
        raise HTTPException(500, f"Error fetching jobs: {str(e)}")