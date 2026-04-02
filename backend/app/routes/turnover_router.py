import logging
from fastapi import APIRouter, Depends, Form, HTTPException
from app.auth.dependencies import get_current_user
from app.services.turnover_service import predict_turnover_from_cv_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/turnover", tags=["Early Attrition Risk Prediction"])

# ============================================================
# PREDICTION ENDPOINTS
# ============================================================

@router.post("/predict")
async def predict_turnover_api(
    cv_id: str = Form(..., description="CV ID from MongoDB (obtained after CV submission)"),
    job_description: str = Form(..., description="Job description text"),
    job_location: str = Form(
        None,
        description="Job location (e.g. 'Colombo, Sri Lanka'). "
                    "Extracted from job description if not provided."
    ),
    user: dict = Depends(get_current_user),
):
    """
    Predict early attrition risk for a candidate given their CV and a job description.

    Runs the full prediction pipeline: feature engineering, ensemble model inference,
    SHAP explainability, and counterfactual scenario generation.

    Risk levels returned:
    - 0: High Early Attrition Risk (likely to leave within 6 months)
    - 1: Moderate Early Attrition Risk (likely to leave within 6-12 months)
    - 2: Low Early Attrition Risk (likely to complete the first year)
    """
    if not cv_id:
        raise HTTPException(400, "cv_id is required")

    if not job_description or len(job_description.strip()) < 50:
        raise HTTPException(400, "Job description must be at least 50 characters")

    logger.info(f"Early attrition risk prediction requested for CV: {cv_id}")
    result = await predict_turnover_from_cv_id(
        cv_id, job_description, job_location, user=user
    )
    return result


@router.post("/predict-with-job")
async def predict_turnover_with_job_api(
    cv_id: str = Form(...),
    job_description: str = Form(...),
    job_id: str = Form(...),
    job_location: str = Form(None),
    job_title: str = Form(None),
    user: dict = Depends(get_current_user),
):
    """
    Job-aware variant of the prediction endpoint.

    Accepts an explicit job_id and job_title in addition to the job description,
    enabling the result to be stored and retrieved per CV-job combination.
    """
    if not cv_id:
        raise HTTPException(400, "cv_id is required")

    if not job_description or len(job_description.strip()) < 50:
        raise HTTPException(400, "Job description must be at least 50 characters")

    logger.info(
        f"Job-aware attrition prediction requested — CV: {cv_id}, Job: {job_id}"
    )
    result = await predict_turnover_from_cv_id(
        cv_id, job_description, job_location,
        user=user, job_id=job_id, job_title=job_title,
    )
    return result


@router.post("/explain")
async def explain_prediction(
    cv_id: str = Form(..., description="CV ID to explain"),
    job_description: str = Form(..., description="Job description text"),
    job_location: str = Form(None, description="Job location (optional)"),
    user: dict = Depends(get_current_user),
):
    """
    Return a detailed SHAP explanation for a specific prediction.

    Runs the full prediction pipeline and appends explanation metadata
    indicating the SHAP method used and whether visualisation data is available.
    """
    logger.info(f"Detailed SHAP explanation requested for CV: {cv_id}")
    result = await predict_turnover_from_cv_id(cv_id, job_description, job_location)

    if result.get("status") == "success":
        result["explanation_metadata"] = {
            "generated_for": "detailed_analysis",
            "shap_method": "TreeExplainer",
            "visualization_ready": True,
            "full_feature_set": len(
                result.get("shap_explanation", {}).get("all_features", [])
            ),
            "note": "Use 'all_features' for complete SHAP analysis",
        }

    return result


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
async def health_check():
    """
    Check whether the early attrition risk model is loaded and operational.

    Returns model load status and service health. Used for monitoring
    and pre-demo verification.
    """
    from app.services.model_loader import get_model

    try:
        model = get_model()
        logger.info("Health check passed — model loaded successfully")
        return {
            "status": "healthy",
            "model_loaded": model is not None,
            "message": "Early attrition risk prediction service is operational",
            "explainability": "SHAP-based explanations enabled",
        }
    except Exception as e:
        logger.error(f"Health check failed — model not loaded: {e}")
        raise HTTPException(500, f"Model not loaded: {str(e)}")


# ============================================================
# HISTORY AND RESULT RETRIEVAL
# ============================================================

@router.get("/history")
async def get_prediction_history(
    user: dict = Depends(get_current_user),
    limit: int = 10,
):
    """
    Retrieve the most recent early attrition risk assessments.

    Returns a summarised list of past predictions sorted by assessment date,
    limited to the specified number of results.
    """
    from app.database import turnover_collection

    try:
        cursor = turnover_collection.find(
            {},
            {
                "cv_id": 1,
                "cv_name": 1,
                "prediction": 1,
                "calculated_at": 1,
                "result_id": 1,
            },
        ).sort("calculated_at", -1).limit(limit)

        history = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            history.append(doc)

        logger.info(f"Returned {len(history)} prediction history records")
        return {"status": "success", "count": len(history), "predictions": history}

    except Exception as e:
        logger.error(f"Error fetching prediction history: {e}")
        raise HTTPException(500, f"Error fetching history: {str(e)}")


@router.get("/result/{cv_id}")
async def get_prediction_result(
    cv_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve the most recent stored attrition risk result for a given CV ID.

    Scoped to the requesting user's email to prevent cross-user data access.
    """
    from app.database import turnover_collection

    try:
        result = turnover_collection.find_one(
            {"cv_id": cv_id, "user_email": user.get("email")},
            sort=[("calculated_at", -1)],
        )

        if not result:
            raise HTTPException(
                404, f"No attrition risk assessment found for CV {cv_id}"
            )

        result.pop("_id", None)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching result for CV {cv_id}: {e}")
        raise HTTPException(500, f"Error fetching result: {str(e)}")


@router.get("/result-by-id/{result_id}")
async def get_prediction_by_result_id(
    result_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve a specific prediction result by its unique MongoDB result ID.
    """
    from app.database import turnover_collection
    from bson import ObjectId

    try:
        result = turnover_collection.find_one({"_id": ObjectId(result_id)})

        if not result:
            raise HTTPException(404, "Result not found")

        result.pop("_id", None)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching result by ID {result_id}: {e}")
        raise HTTPException(500, f"Error fetching result: {str(e)}")


@router.get("/result-by-job")
async def get_result_by_job(
    cv_id: str,
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Retrieve an existing attrition risk prediction for a specific CV and job combination.

    Returns the most recent result if one exists, or a not_found status
    so the caller can trigger a fresh prediction.
    """
    from app.database import turnover_collection

    try:
        result = turnover_collection.find_one(
            {"cv_id": cv_id, "job_id": job_id},
            sort=[("calculated_at", -1)],
        )

        if not result:
            return {"status": "not_found", "result": None}

        result["_id"] = str(result["_id"])
        return {"status": "found", "result": result}

    except Exception as e:
        logger.error(f"Error fetching result for CV {cv_id}, Job {job_id}: {e}")
        raise HTTPException(500, f"Error fetching result: {str(e)}")


@router.get("/latest-results/batch")
async def get_batch_results(
    cv_ids: str,
    user: dict = Depends(get_current_user),
):
    """
    Fetch the latest attrition risk results for multiple CV IDs in a single query.

    Accepts a comma-separated string of CV IDs. Uses a MongoDB aggregation
    pipeline to efficiently retrieve the most recent result per CV.
    """
    from app.database import turnover_collection

    try:
        id_list = [cid.strip() for cid in cv_ids.split(",") if cid.strip()]
        if not id_list:
            return {"results": []}

        pipeline = [
            {"$match": {"cv_id": {"$in": id_list}}},
            {"$sort": {"calculated_at": -1}},
            {"$group": {"_id": "$cv_id", "doc": {"$first": "$$ROOT"}}},
            {"$replaceRoot": {"newRoot": "$doc"}},
        ]
        results = list(turnover_collection.aggregate(pipeline))
        for r in results:
            r.pop("_id", None)

        logger.info(f"Batch fetch returned results for {len(results)} CVs")
        return {"results": results}

    except Exception as e:
        logger.error(f"Error fetching batch results: {e}")
        raise HTTPException(500, f"Error fetching batch results: {str(e)}")


# ============================================================
# CANDIDATE AND JOB LOOKUP
# ============================================================

@router.get("/candidates")
async def get_all_candidates(
    user: dict = Depends(get_current_user),
):
    """
    Fetch all candidates stored in the CV collection.

    Returns basic candidate info (name, email, upload date) for display
    in the admin attrition risk assessment view.
    """
    from app.database import cv_collection

    try:
        cursor = cv_collection.find(
            {},
            {"name": 1, "basics": 1, "emails": 1, "uploaded_at": 1},
        ).sort("uploaded_at", -1)

        candidates = []
        for doc in cursor:
            candidates.append(
                {
                    "_id": str(doc["_id"]),
                    "name": doc.get("name")
                    or doc.get("basics", {}).get("name", "Unknown"),
                    "email": (
                        doc.get("emails", [""])[0]
                        if doc.get("emails")
                        else doc.get("basics", {}).get("email", "")
                    ),
                    "uploaded_at": doc.get("uploaded_at", ""),
                }
            )

        logger.info(f"Returned {len(candidates)} candidates")
        return {"status": "success", "candidates": candidates}

    except Exception as e:
        logger.error(f"Error fetching candidates: {e}")
        raise HTTPException(500, f"Error fetching candidates: {str(e)}")


@router.get("/jobs")
async def get_all_jobs(
    user: dict = Depends(get_current_user),
):
    """
    Fetch all job postings from the jobs collection.

    Returns job title, description text, and creation date for use
    in the attrition risk assessment job selection dropdown.
    """
    from app.models.job_model import jobs_collection

    try:
        cursor = jobs_collection.find(
            {},
            {"title": 1, "jd_text": 1, "created_at": 1, "location": 1},
        ).sort("created_at", -1)

        jobs = []
        for doc in cursor:
            jobs.append(
                {
                    "_id": str(doc["_id"]),
                    "title": doc.get("title", "Untitled"),
                    "jd_text": doc.get("jd_text", ""),
                    "created_at": doc.get("created_at", ""),
                    "location": doc.get("location", ""),
                }
            )

        logger.info(f"Returned {len(jobs)} job postings")
        return {"status": "success", "jobs": jobs}

    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        raise HTTPException(500, f"Error fetching jobs: {str(e)}")


@router.get("/cv-by-email")
async def get_cv_by_email(
    email: str,
    user: dict = Depends(get_current_user),
):
    """
    Look up a candidate's CV ID from the CV collection using their email address.

    Tries multiple email field formats to handle both legacy and current
    CV document schemas. Returns cv_id if found, or a not_found status.
    """
    from app.database import cv_collection

    try:
        # Try emails array field (legacy format)
        doc = cv_collection.find_one(
            {"emails": {"$in": [email]}},
            {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1},
        )

        # Fallback: flat email field
        if not doc:
            doc = cv_collection.find_one(
                {"email": email},
                {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1},
            )

        # Fallback: nested basics.email (5-step evaluator format)
        if not doc:
            doc = cv_collection.find_one(
                {"basics.email": email},
                {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1},
            )

        # Fallback: user_email field
        if not doc:
            doc = cv_collection.find_one(
                {"user_email": email},
                {"_id": 1, "name": 1, "basics": 1, "uploaded_at": 1},
            )

        if not doc:
            logger.info(f"No CV found for email: {email}")
            return {
                "status": "not_found",
                "cv_id": None,
                "message": "CV not yet processed for this candidate",
            }

        logger.info(f"CV found for email: {email}")
        return {
            "status": "found",
            "cv_id": str(doc["_id"]),
            "name": doc.get("name") or doc.get("basics", {}).get("name", "Unknown"),
            "uploaded_at": doc.get("uploaded_at", ""),
        }

    except Exception as e:
        logger.error(f"Error looking up CV for email {email}: {e}")
        raise HTTPException(500, f"Error looking up CV: {str(e)}")