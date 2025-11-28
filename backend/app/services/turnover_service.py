from fastapi import HTTPException
from typing import Dict, Any
from bson import ObjectId
from app.database import get_cv_collection
from app.services.feature_engineering import create_feature_vector_from_mongo
from app.services.model_loader import predict_with_model

RISK_LABELS = {
    0: "High Risk (leaves within 6 months)",
    1: "Medium Risk (leaves within 6-12 months)",
    2: "Low Risk (stays longer than 1 year)"
}

async def predict_turnover_from_cv_id(cv_id: str, job_description: str, job_location: str = None) -> Dict[str, Any]:
    """
    Main prediction pipeline using MongoDB stored CV
    
    Steps:
    1. Retrieve parsed CV from MongoDB by cv_id
    2. Extract/engineer features compatible with model (including commute distance)
    3. Run model prediction
    4. Return results with explanation
    """
    
    try:
        # Step 1: Retrieve CV from MongoDB
        cv_collection = get_cv_collection()
        
        try:
            cv_document = await cv_collection.find_one({"_id": ObjectId(cv_id)})
        except:
            raise HTTPException(400, f"Invalid CV ID format: {cv_id}")
        
        if not cv_document:
            raise HTTPException(404, f"CV not found with ID: {cv_id}")
        
        # Step 2: Convert MongoDB document to feature format
        
        features = await create_feature_vector_from_mongo(
            cv_document, 
            job_description,
            jd_location=job_location
        )
        
        # Step 3: Predict using model
        predicted_class, probabilities = predict_with_model(features)
        
        # Step 4: Identify top risk factors
        risk_factors = identify_risk_factors(features)
        
        # Step 5: Build response
        result = {
            "status": "success",
            "cv_id": cv_id,
            "cv_name": cv_document.get("name", "Unknown"),
            "prediction": {
                "risk_level": predicted_class,
                "risk_label": RISK_LABELS[predicted_class],
                "confidence": float(probabilities[predicted_class]),
                "probabilities": {
                    "high_risk": float(probabilities[0]),
                    "medium_risk": float(probabilities[1]),
                    "low_risk": float(probabilities[2])
                }
            },
            "features": {
                # Return key features for transparency
                "skill_match": round(features['skill_match_score'], 2),
                "title_match": round(features['title_match_score'], 2),
                "exp_match": round(features['exp_match_score'], 2),
                "location_match": round(features['location_match_score'], 2),
                "overall_match": round(features['overall_match_score'], 2),
                "job_hopping_rate": round(features['job_hopping_rate'], 2),
                "total_jobs": int(features['total_jobs']),
                "total_experience": round(features['total_exp_years'], 1),
                "avg_tenure_months": round(features['avg_tenure_months'], 1)
            },
            "risk_factors": risk_factors
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc(),
            "prediction": None
        }

def identify_risk_factors(features: Dict[str, float]) -> list:
    """
    Identify top risk factors based on feature values
    Provides transparency for model decisions
    """
    risk_factors = []
    
    # Job hopping
    if features['job_hopping_rate'] >= 0.5:
        risk_factors.append({
            "factor": "Frequent job changes",
            "value": round(features['job_hopping_rate'], 2),
            "description": "High proportion of short-tenure jobs",
            "impact": "high"
        })
    
    # Low skill match
    if features['skill_match_score'] < 0.4:
        risk_factors.append({
            "factor": "Low skill-job match",
            "value": round(features['skill_match_score'], 2),
            "description": "Limited overlap between candidate skills and job requirements",
            "impact": "high"
        })
    
    # Low title similarity
    if features['title_match_score'] < 0.4:
        risk_factors.append({
            "factor": "Job role mismatch",
            "value": round(features['title_match_score'], 2),
            "description": "Current role differs significantly from target position",
            "impact": "medium"
        })
    
    # Overqualification
    if features['is_overqualified'] == 1:
        risk_factors.append({
            "factor": "Overqualification",
            "value": "Yes",
            "description": "Candidate may be overqualified for this position",
            "impact": "medium"
        })
    
    # Underqualification
    if features['is_underqualified'] == 1:
        risk_factors.append({
            "factor": "Underqualification",
            "value": "Yes",
            "description": "Candidate may lack required experience level",
            "impact": "high"
        })
    
    # Low experience
    if features['total_exp_years'] < 2:
        risk_factors.append({
            "factor": "Limited work experience",
            "value": round(features['total_exp_years'], 1),
            "description": "Early career stage with limited job market experience",
            "impact": "medium"
        })
    
    # Short average tenure
    if features['avg_tenure_months'] < 12:
        risk_factors.append({
            "factor": "Short average job tenure",
            "value": round(features['avg_tenure_months'], 1),
            "description": "Average time per job is less than 1 year",
            "impact": "high"
        })
    
    # Work mode mismatch
    if features['work_mode_mismatch'] == 1:
        risk_factors.append({
            "factor": "Work mode incompatibility",
            "value": "Yes",
            "description": "Mismatch between candidate preference and job requirements",
            "impact": "low"
        })
    
    # Sort by impact (high > medium > low) and return top 5
    impact_order = {"high": 3, "medium": 2, "low": 1}
    risk_factors.sort(key=lambda x: impact_order.get(x["impact"], 0), reverse=True)
    
    return risk_factors[:5]  # Return top 5 risk factors