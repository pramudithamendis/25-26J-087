from fastapi import APIRouter, Form, Depends, HTTPException
from app.auth.dependencies import get_current_user
from app.services.turnover_service import predict_turnover_from_cv_id
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

ATTRITION_SERVICE_URL = os.getenv("ATTRITION_SERVICE_URL")

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
    
    result = await predict_turnover_from_cv_id(cv_id, job_description, job_location, user=user)
    
    return result

@router.get("/health")
async def health_check():
    """Check if model is loaded"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{ATTRITION_SERVICE_URL}/health")
            response.raise_for_status()
            ml_status = response.json()
            return {
                "status": "healthy" if ml_status.get("model_loaded") else "unhealthy",
                "ml_service_status": ml_status,
                "message": "Turnover prediction service is operational",
                "explainability": "SHAP-based explanations enabled"
            }
        except Exception as e:
            raise HTTPException(500, f"ML service health check failed: {str(e)}")


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
            
        cursor = turnover_coll.find(
            {},
            {"cv_id": 1, "cv_name": 1, "prediction": 1, "calculated_at": 1, "result_id": 1}
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
        
        result = turnover_coll.find_one(
            {"cv_id": cv_id, "user_email": user.get("email")},
            sort=[("calculated_at", -1)]
        )
        
        if not result:
            raise HTTPException(404, f"No turnover assessment found for CV {cv_id}")
        
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
            {"_id": ObjectId(result_id)}
        )
        
        if not result:
            raise HTTPException(404, f"Result not found")
        
        result.pop("_id", None)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching result: {str(e)}")
    

@router.get("/latest-results/batch")
async def get_batch_results(
    cv_ids: str,
    user: dict = Depends(get_current_user)
):
    """Get latest turnover results for multiple CVs in one query"""
    from app.database import turnover_collection

    try:
        id_list = [cid.strip() for cid in cv_ids.split(",") if cid.strip()]
        if not id_list:
            return {"results": []}

        pipeline = [
            {"$match": {"cv_id": {"$in": id_list}}},
            {"$sort": {"calculated_at": -1}},
            {"$group": {"_id": "$cv_id", "doc": {"$first": "$$ROOT"}}},
            {"$replaceRoot": {"newRoot": "$doc"}}
        ]
        results = list(turnover_collection.aggregate(pipeline))
        for r in results:
            r.pop("_id", None)

        return {"results": results}

    except Exception as e:
        raise HTTPException(500, f"Error fetching batch results: {str(e)}")


@router.get("/candidates")
async def get_all_candidates(
    user: dict = Depends(get_current_user)
):
    """Fetch all candidates from cv_collection"""
    from app.database import cv_collection

    try:
        cursor = cv_collection.find(
            {},
            {"name": 1, "basics": 1, "emails": 1, "uploaded_at": 1}
        ).sort("uploaded_at", -1)

        candidates = []
        for doc in cursor:
            candidates.append({
                "_id": str(doc["_id"]),
                "name": doc.get("name") or doc.get("basics", {}).get("name", "Unknown"),
                "email": (doc.get("emails", [""])[0] if doc.get("emails")
                          else doc.get("basics", {}).get("email", "")),
                "uploaded_at": doc.get("uploaded_at", "")
            })

        return {"status": "success", "candidates": candidates}

    except Exception as e:
        print(f"ERROR in candidates: {e}") 
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

@router.get("/cv-by-email")
async def get_cv_by_email(
    email: str,
    user: dict = Depends(get_current_user)
):
    """Find cv_id in cv_collection by candidate email"""
    from app.database import cv_collection

    try:
        # Try matching by emails array field (old format)
        doc = cv_collection.find_one(
            {"emails": {"$in": [email]}},
            {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1}
        )

        # Fallback: try email field directly
        if not doc:
            doc = cv_collection.find_one(
                {"email": email},
                {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1}
            )

        # Fallback: try basics.email (new 5-step format)
        if not doc:
            doc = cv_collection.find_one(
                {"basics.email": email},
                {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1}
            )

        # Fallback: try user_email field
        if not doc:
            doc = cv_collection.find_one(
                {"user_email": email},
                {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1}
            )

        if not doc:
            return {"status": "not_found", "cv_id": None, "message": "CV not yet processed for this candidate"}

        return {
            "status": "found",
            "cv_id": str(doc["_id"]),
            "name": doc.get("name") or doc.get("basics", {}).get("name", "Unknown"),
            "uploaded_at": doc.get("uploaded_at", "")
        }

    except Exception as e:
        raise HTTPException(500, f"Error looking up CV: {str(e)}")


@router.get("/result-by-job")
async def get_result_by_job(
    cv_id: str,
    job_id: str,
    user: dict = Depends(get_current_user)
):
    """Get existing turnover prediction for a specific cv+job combination"""
    from app.database import turnover_collection

    try:
        result = turnover_collection.find_one(
            {"cv_id": cv_id, "job_id": job_id},
            sort=[("calculated_at", -1)]
        )

        if not result:
            return {"status": "not_found", "result": None}

        result["_id"] = str(result["_id"])
        return {"status": "found", "result": result}

    except Exception as e:
        raise HTTPException(500, f"Error fetching result: {str(e)}")

@router.post("/predict-with-job")
async def predict_turnover_with_job_api(
    cv_id: str = Form(...),
    job_description: str = Form(...),
    job_id: str = Form(...),
    job_location: str = Form(None),
    job_title: str = Form(None),
    user: dict = Depends(get_current_user)
):
    """Predict turnover risk - job-aware version that stores job_id"""

    if not cv_id:
        raise HTTPException(400, "cv_id is required")

    if not job_description or len(job_description.strip()) < 50:
        raise HTTPException(400, "Job description must be at least 50 characters")

    result = await predict_turnover_from_cv_id(
        cv_id, job_description, job_location,
        user=user, job_id=job_id, job_title=job_title
    )

    return result