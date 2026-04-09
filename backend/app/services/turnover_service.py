from fastapi import HTTPException
from typing import Dict, Any, List
from bson import ObjectId
import numpy as np
import pandas as pd
from app.database import cv_collection, turnover_collection
from datetime import datetime
from app.services.feature_engineering import create_feature_vector_from_mongo
from app.services.fairness_utils import extract_fairness_metadata, get_fairness_context
import time
from app.services.feature_engineering import extract_location_from_jd_enhanced
from dotenv import load_dotenv
import os
import httpx

load_dotenv()

# Modified
# ML Microservice connection
ATTRITION_SERVICE_URL = os.getenv("ATTRITION_SERVICE_URL")
ATTRITION_PREDICT_URL = f"{ATTRITION_SERVICE_URL}/predict"
ATTRITION_SHAP_URL = f"{ATTRITION_SERVICE_URL}/shap"

# Modified
def _sync_predict(features: Dict[str, float]) -> tuple:
    """
    Synchronous HTTP call to the prehire-attrition ML microservice.
    Used for counterfactual generation (synchronous context).
    Returns (predicted_class: int, probabilities: np.ndarray)
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(ATTRITION_PREDICT_URL, json={"features": features})
            response.raise_for_status()
            data = response.json()
        if data.get("status") == "error":
            raise RuntimeError(f"ML service error: {data.get('message')}")
        return int(data["prediction"]), np.array(data["probability"], dtype=float)
    except httpx.ConnectError:
        raise RuntimeError(
            f"Prehire-attrition ML service unreachable at {ATTRITION_SERVICE_URL}. "
            "Make sure it is running: uvicorn main:app --port 8001"
        )
        
# Modified
async def _async_predict(features: Dict[str, float]) -> tuple:
    """
    Async HTTP call to the prehire-attrition ML microservice.
    Used in the main async prediction pipeline.
    Returns (predicted_class: int, probabilities: np.ndarray)
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(ATTRITION_PREDICT_URL, json={"features": features})
            response.raise_for_status()
            data = response.json()
        if data.get("status") == "error":
            raise RuntimeError(f"ML service error: {data.get('message')}")
        return int(data["prediction"]), np.array(data["probability"], dtype=float)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Prehire-attrition ML service is unreachable at {ATTRITION_SERVICE_URL}. "
                "Make sure it is running: uvicorn main:app --port 8001"
            ),
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="ML service request timed out after 30s.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"ML service returned HTTP {exc.response.status_code}: {exc.response.text}",
        )


RISK_LABELS = {
    0: "High Risk (leaves within 6 months)",
    1: "Medium Risk (leaves within 6-12 months)",
    2: "Low Risk (stays longer than 1 year)"
}

async def predict_turnover_from_cv_id(cv_id: str, job_description: str, job_location: str = None, user: dict = None, job_id: str = None, job_title: str = None) -> Dict[str, Any]:
    """
    Main prediction pipeline using MongoDB stored CV
    """
    start_time = time.time()
    
    try:
        # Step 1: Retrieve CV from MongoDB
               
        try:
            cv_document = cv_collection.find_one({"_id": ObjectId(cv_id)})
        except:
            raise HTTPException(400, f"Invalid CV ID format: {cv_id}")
        
        if not cv_document:
            raise HTTPException(404, f"CV not found with ID: {cv_id}")
        
        # Step 1.5: Extract fairness metadata
        fairness_metadata = extract_fairness_metadata(cv_document)
        
        if not job_location:
            jd_location = extract_location_from_jd_enhanced(job_description)
            print(f" Extracted JD location: {jd_location}")
        else:
            jd_location = job_location

        # Step 2: Convert MongoDB document to feature format
        features = await create_feature_vector_from_mongo(
            cv_document,
            job_description,
            jd_location=jd_location,
            job_title=job_title 
        )
        
        # Step 3: Predict via prehire-attrition ML microservice
        # Modified
        predicted_class, probabilities = await _async_predict(features)

        # Soft-clamp probabilities so UI never shows exactly 0% or 100%
        probabilities = np.clip(probabilities, 0.02, 0.96)
        probabilities = probabilities / probabilities.sum()

        print(f" Prediction complete: {RISK_LABELS[predicted_class]} (confidence: {probabilities[predicted_class]:.2%})")
        
        # Step 3.5: Override prediction for severe overqualification
        original_prediction = predicted_class
        overqualification_override = False
        
        if features['is_overqualified'] == 1 and features['exp_match_score'] < 0.6:
            print(f"  OVERQUALIFICATION DETECTED: {features['total_exp_years']:.1f} years, exp_match={features['exp_match_score']:.2f}")
            
            if predicted_class == 2:
                print(f"   OVERRIDING prediction from Low Risk → High Risk")
                predicted_class = 0
                probabilities = np.array([0.80, 0.15, 0.05])
                overqualification_override = True
        
        # Step 4: Generate SHAP explanations (delegated to ML microservice, 8s timeout)
        #Modified
        shap_explanation = await generate_shap_explanation_safe(features, predicted_class, timeout_seconds=8)
        
        # Step 5: Identify risk factors
        if shap_explanation and shap_explanation.get('top_features'):
            print("Using SHAP-based risk factors")
            risk_factors = identify_risk_factors_shap(features, shap_explanation, predicted_class)
        else:
            print("Using rule-based risk factors")
            risk_factors = identify_risk_factors(features)
        
        # Add overqualification warning if override occurred
        if overqualification_override:
            risk_factors.insert(0, {
                "factor": " SEVERE OVERQUALIFICATION (Prediction Override)",
                "value": f"{features['total_exp_years']:.1f} years for entry-level role",
                "description": f"Candidate is significantly overqualified (exp_match: {features['exp_match_score']:.2f}). Original prediction was '{RISK_LABELS[original_prediction]}', but overridden to High Risk due to career level mismatch and high likelihood of early departure.",
                "impact": "critical",
                "override_applied": True,
                "original_prediction": RISK_LABELS[original_prediction]
            })
        
        # Step 6: Generate counterfactuals
        if shap_explanation and shap_explanation.get('top_features'):
            print("Generating SHAP-guided counterfactuals")
            counterfactuals = generate_shap_counterfactuals(
            #Modified
                features, predicted_class, probabilities, shap_explanation
            )
        else:
            print("Generating simple counterfactuals")
            #Modified
            counterfactuals = generate_counterfactuals(features, predicted_class, probabilities)
        
        # Handle empty counterfactuals for low-risk candidates
        if not counterfactuals and predicted_class == 2:
            counterfactuals_note = {
                "reason": "highly_confident_low_risk_prediction",
                "explanation": "This candidate's profile demonstrates strong retention indicators. No realistic changes to individual features would significantly alter the low-risk prediction.",
                "key_strengths": [
                    f"Stable job history: {features['avg_tenure_months']:.0f} months average tenure",
                    f"Low job hopping: {features['job_hopping_rate']:.2f} rate",
                    f"Current role stability: {features['current_job_tenure']:.0f} months"
                ]
            }
        else:
            counterfactuals_note = None

        # Step 6.5: Get fairness context
        fairness_context = get_fairness_context(fairness_metadata)

        # STOP TIMER
        elapsed_time = time.time() - start_time
        
        # Step 7: Build response
        result = {
            "status": "success",
            "cv_id": cv_id,
            "cv_name": cv_document.get("name") or cv_document.get("basics", {}).get("name", "Unknown"),
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
            "shap_explanation": shap_explanation,
            "risk_factors": risk_factors,
            "counterfactuals": counterfactuals,
            "fairness": fairness_context,
            "performance": {
                "prediction_time_seconds": round(elapsed_time, 3),
                "meets_sla": elapsed_time < 5.0,
                "note": "Prediction time includes CV parsing, feature engineering, model inference, and SHAP calculation"
            }
        }
        
        if counterfactuals_note:
            result["counterfactuals_note"] = counterfactuals_note
        
        if overqualification_override:
            result["override_metadata"] = {
                "override_type": "severe_overqualification",
                "original_prediction": RISK_LABELS[original_prediction],
                "final_prediction": RISK_LABELS[predicted_class],
                "reason": "Candidate significantly overqualified for role"
            }

        # Save to MongoDB
        if result.get("status") == "success":
            try:
                turnover_coll = turnover_collection
                db_entry = result.copy()
                db_entry["cv_id"] = cv_id
                db_entry["job_description"] = job_description
                db_entry["job_location"] = job_location
                db_entry["job_id"] = job_id
                db_entry["calculated_at"] = datetime.utcnow()
                db_entry["user_email"] = user.get("email") if user else None 
                insert_result = turnover_coll.insert_one(db_entry)  
                result["result_id"] = str(insert_result.inserted_id) 
                print(f"Saved turnover result for CV {cv_id} to MongoDB")
            except Exception as e:
                print(f"Error saving turnover result to MongoDB: {e}")

        if elapsed_time > 5.0:
            print(f" WARNING: Prediction took {elapsed_time:.2f}s (exceeds 5s SLA)")
        else:
            print(f" Prediction completed in {elapsed_time:.2f}s")

        print("Response ready")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f" Error in prediction pipeline: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc(),
            "prediction": None
        }
#Modified
async def generate_shap_explanation_safe(
    features: Dict[str, float], predicted_class: int, timeout_seconds: int = 8
) -> Dict[str, Any]:
    """
    Request SHAP explanation from the ML microservice.
    Falls back to empty explanation on timeout or error.
    """
    try:
        async with httpx.AsyncClient(timeout=float(timeout_seconds)) as client:
            response = await client.post(
                ATTRITION_SHAP_URL,
                json={"features": features, "predicted_class": predicted_class},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") == "error":
            print(f"   SHAP service error: {data.get('message')}")
            return get_empty_shap_explanation()

        return data

    except httpx.TimeoutException:
        print(f"   SHAP request timed out after {timeout_seconds}s - using rule-based")
        return get_empty_shap_explanation()
    except Exception as e:
        print(f"   SHAP request failed: {e} - using rule-based")
        return get_empty_shap_explanation()


def get_empty_shap_explanation() -> Dict[str, Any]:
    return {
        "base_value": 0.0,
        "prediction_value": 0.0,
        "top_features": [],
        "all_features": [],
        "explanation": "SHAP explanation unavailable - using rule-based analysis instead"
    }

def generate_shap_explanation_internal(features: Dict[str, float], model, predicted_class: int) -> Dict[str, Any]:
    import shap
    
    feature_df = pd.DataFrame([features])
    feature_names = list(features.keys())
    feature_values = list(features.values())
    
    global _shap_model
    explainer = get_shap_explainer()
    full_model = _shap_model
    
    if full_model is None:
        raise ValueError("SHAP model not initialized")

    if hasattr(full_model, 'named_steps'):
        preprocessor = full_model.named_steps.get('pre')
        if preprocessor:
            X_transformed = preprocessor.transform(feature_df)
            if hasattr(X_transformed, 'toarray'):
                X_transformed = X_transformed.toarray()
        else:
            X_transformed = feature_df.values
    else:
        X_transformed = feature_df.values
    
    explainer = get_shap_explainer()
    shap_values = explainer.shap_values(X_transformed)
    
    if isinstance(shap_values, np.ndarray):
        if len(shap_values.shape) == 3:
            shap_vals = shap_values[0, :, predicted_class]
        elif len(shap_values.shape) == 2:
            shap_vals = shap_values[:, predicted_class]
        else:
            shap_vals = shap_values
    elif isinstance(shap_values, list):
        if len(shap_values) > predicted_class:
            shap_vals = np.array(shap_values[predicted_class]).flatten()
        else:
            shap_vals = np.array(shap_values[0]).flatten()
    else:
        raise ValueError(f"Unexpected SHAP values type: {type(shap_values)}")
    
    if isinstance(explainer.expected_value, (list, np.ndarray)):
        base_value = float(explainer.expected_value[predicted_class]) if len(explainer.expected_value) > predicted_class else float(explainer.expected_value[0])
    else:
        base_value = float(explainer.expected_value)
    
    feature_contributions = []
    n_shap = len(shap_vals)
    n_features = len(feature_names)
    
    if n_shap > n_features:
        shap_vals = shap_vals[:n_features]
    elif n_shap < n_features:
        shap_vals = np.pad(shap_vals, (0, n_features - n_shap), constant_values=0)
    
    for fname, fval, shap_val in zip(feature_names, feature_values, shap_vals):
        try:
            shap_float = float(np.array(shap_val).flatten()[0]) if isinstance(shap_val, (list, tuple, np.ndarray)) else float(shap_val)
            value_float = float(fval) if isinstance(fval, (int, float, np.number)) else 0.0
            
            feature_contributions.append({
                "feature": fname,
                "value": value_float,
                "value_display": str(fval),
                "shap_value": shap_float,
                "abs_shap_value": abs(shap_float),
                "impact": "increases_risk" if shap_float > 0 else "decreases_risk"
            })
        except Exception as e:
            print(f"     Skipping feature {fname}: {e}")
            continue
    
    feature_contributions.sort(key=lambda x: x['abs_shap_value'], reverse=True)
    
    return {
        "base_value": base_value,
        "prediction_value": float(base_value + np.sum(shap_vals)),
        "top_features": feature_contributions[:10],
        "all_features": feature_contributions,
        "explanation": f"Base prediction: {base_value:.3f}, Final: {float(base_value + np.sum(shap_vals)):.3f}"
    }


def identify_risk_factors(features: Dict[str, float]) -> list:
    """Rule-based risk factor identification (fallback)"""
    risk_factors = []
    
    if features['job_hopping_rate'] >= 0.5:
        risk_factors.append({
            "factor": "Frequent job changes",
            "value": round(features['job_hopping_rate'], 2),
            "description": "High proportion of short-tenure jobs",
            "impact": "high"
        })
    
    if features['skill_match_score'] < 0.4:
        risk_factors.append({
            "factor": "Low skill-job match",
            "value": round(features['skill_match_score'], 2),
            "description": "Limited overlap between candidate skills and job requirements",
            "impact": "high"
        })
    
    if features['title_match_score'] < 0.4:
        risk_factors.append({
            "factor": "Job role mismatch",
            "value": round(features['title_match_score'], 2),
            "description": "Current role differs significantly from target position",
            "impact": "medium"
        })
    
    if features['is_overqualified'] == 1:
        risk_factors.append({
            "factor": "Overqualification",
            "value": "Yes",
            "description": "Candidate may be overqualified for this position",
            "impact": "medium"
        })
    
    if features['is_underqualified'] == 1:
        risk_factors.append({
            "factor": "Underqualification",
            "value": "Yes",
            "description": "Candidate may lack required experience level",
            "impact": "high"
        })
    
    if features['avg_tenure_months'] < 12:
        risk_factors.append({
            "factor": "Short average job tenure",
            "value": round(features['avg_tenure_months'], 1),
            "description": "Average time per job is less than 1 year",
            "impact": "high"
        })
    
    if features['location_match_score'] < 0.5:
        risk_factors.append({
            "factor": "Long commute distance",
            "value": round(features['location_match_score'], 2),
            "description": "Significant distance between candidate location and job location",
            "impact": "medium"
        })
    
    impact_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    risk_factors.sort(key=lambda x: impact_order.get(x["impact"], 0), reverse=True)
    
    return risk_factors[:5]


def _get_feature_description(feature_name: str, value: float, predicted_class: int) -> tuple:
    """
    Return (label, description, impact) based on feature name, actual value,
    and predicted risk class. Descriptions reflect whether the feature is
    positive or negative for this candidate.
    is_low_risk = predicted_class == 2
    """
    is_low_risk = predicted_class == 2

    if feature_name == 'skill_match_score':
        if value >= 0.6:
            return ("Skills Alignment", "Good skill overlap with job requirements supports retention", "low")
        elif value >= 0.4:
            return ("Skills Alignment", "Moderate skill match. Some gaps may lead to frustration", "medium")
        else:
            return ("Skills Alignment", "Weak skill match may lead to frustration and early job searching", "high")

    if feature_name == 'title_match_score':
        if value >= 0.7:
            return ("Role Similarity", "Strong alignment between candidate's background and this role", "low")
        elif value >= 0.4:
            return ("Role Similarity", "Partial role alignment. Candidate may need adjustment period", "medium")
        else:
            return ("Role Similarity", "Significant role mismatch may cause dissatisfaction", "high")

    if feature_name == 'overall_match_score':
        if value >= 0.7:
            return ("Overall Job Fit", "Strong overall fit. Candidate is well-suited for this role", "low")
        elif value >= 0.5:
            return ("Overall Job Fit", "Moderate overall fit. Some areas need attention", "medium")
        else:
            return ("Overall Job Fit", "Poor overall fit increases likelihood of early departure", "high")

    if feature_name == 'exp_match_score':
        if value >= 0.8:
            return ("Experience Match", "Experience level fits well with position requirements", "low")
        elif value >= 0.5:
            return ("Experience Match", "Experience partially matches. Minor gaps present", "medium")
        else:
            return ("Experience Match", "Significant mismatch between experience and job requirements", "high")

    if feature_name == 'avg_tenure_months':
        if value >= 24:
            return ("Average Job Tenure", f"Stays an average of {value/12:.1f} years per job. Shows strong commitment", "low")
        elif value >= 12:
            return ("Average Job Tenure", f"Average tenure of {value:.0f} months. Moderate stability", "medium")
        else:
            return ("Average Job Tenure", f"Short average tenure of {value:.0f} months suggests commitment issues", "high")

    if feature_name == 'current_job_tenure':
        if value >= 24:
            return ("Current Role Stability", f"Has been in current role for {value:.0f} months. Strong stability indicator", "low")
        elif value >= 12:
            return ("Current Role Stability", f"Moderate time in current role ({value:.0f} months)", "medium")
        else:
            return ("Current Role Stability", f"Short time in current role ({value:.0f} months) may indicate instability", "high")

    if feature_name == 'job_hopping_rate':
        if value <= 0.2:
            return ("Job Stability", "Minimal job hopping. Very stable work history", "low")
        elif value <= 0.4:
            return ("Job Stability", "Some job changes. Moderate stability", "medium")
        else:
            return ("Job Stability", "High job hopping rate suggests difficulty committing", "high")

    if feature_name == 'location_match_score':
        if value >= 0.8:
            return ("Location Compatibility", "Convenient commute distance. Less likely to leave due to travel", "low")
        elif value >= 0.5:
            return ("Location Compatibility", "Moderate commute distance. May be a minor concern", "medium")
        else:
            return ("Location Compatibility", "Long commute distance increases risk of early departure", "high")

    if feature_name == 'n_skills':
        if value >= 15:
            return ("Skill Breadth", f"Strong skill portfolio with {value:.0f} skills. Well-rounded candidate", "low")
        else:
            return ("Skill Breadth", f"Limited skill variety ({value:.0f} skills identified)", "medium")

    if feature_name == 'has_progression':
        if value == 1:
            return ("Career Progression", "Shows upward career progression. Ambitious and growth-oriented", "low")
        else:
            return ("Career Progression", "Limited career progression detected", "medium")

    if feature_name == 'is_overqualified':
        if value == 1:
            return ("Overqualification", "Candidate may be overqualified. Risk of leaving for better opportunities", "high")
        else:
            return ("Qualification Fit", "Qualification level appropriate for this role", "low")

    if feature_name == 'is_underqualified':
        if value == 1:
            return ("Underqualification", "Candidate may lack required experience. Risk of struggling and leaving early", "high")
        else:
            return ("Qualification Fit", "Meets minimum qualification requirements", "low")

    if feature_name == 'n_certifications':
        if value >= 3:
            return ("Certifications", f"{value:.0f} professional certifications. Demonstrates continuous learning", "low")
        else:
            return ("Certifications", f"{value:.0f} certifications noted", "low")

    if feature_name == 'has_masters':
        if value == 1:
            return ("Advanced Education", "Holds a postgraduate degree. Strong academic background", "low")
        else:
            return ("Education Level", "No postgraduate degree. Undergraduate level qualification", "low")

    if feature_name == 'short_stints_count':
        if value == 0:
            return ("Job Stability", "No short-tenure jobs. Consistent employment history", "low")
        else:
            return ("Short Stints", f"{value:.0f} job(s) held for less than a year", "high" if value >= 2 else "medium")

    if feature_name == 'industry_switches':
        if value == 0:
            return ("Industry Focus", "Stayed within same industry. Domain expertise builds over time", "low")
        else:
            return ("Industry Switches", f"Switched industries {value:.0f} time(s). May indicate varied interests", "medium")

    if feature_name == 'tenure_slope':
        if value > 0:
            return ("Tenure Trend", "Job tenures are increasing over time. Growing commitment", "low")
        else:
            return ("Tenure Trend", "Job tenures decreasing over time. May indicate restlessness", "medium")

    if feature_name == 'total_exp_years':
        return ("Total Experience", f"{value:.1f} years of total work experience", "low")

    if feature_name == 'total_jobs':
        return ("Number of Jobs", f"Has held {value:.0f} position(s) in their career", "low")

    if feature_name == 'progression_jumps':
        if value >= 2:
            return ("Promotion History", f"{value:.0f} upward career moves. Strong progression", "low")
        elif value == 1:
            return ("Promotion History", "One upward career move noted", "low")
        else:
            return ("Promotion History", "No clear upward progression detected", "medium")

    if feature_name == 'work_mode_mismatch':
        if value == 1:
            return ("Work Mode Mismatch", "Candidate work preference may not align with role type", "medium")
        else:
            return ("Work Mode Compatibility", "Work mode preference aligns with role requirements", "low")

    if feature_name == 'has_career_gap':
        if value == 1:
            return ("Career Gap", "Employment gap detected. Worth discussing in interview", "medium")
        else:
            return ("Employment Continuity", "No significant career gaps. Consistent employment", "low")

    # Default fallback
    return (
        feature_name.replace('_', ' ').title(),
        f"Feature value: {value:.2f}",
        "medium"
    )


def identify_risk_factors_shap(features: Dict[str, float], shap_explanation: Dict, predicted_class: int = 2) -> List[Dict]:
    """SHAP-based key influencing factors — descriptions reflect actual feature values"""
    risk_factors = []

    # Take top 5 features by absolute SHAP value regardless of direction
    top_features = sorted(
        shap_explanation.get('top_features', []),
        key=lambda x: x['abs_shap_value'],
        reverse=True
    )[:5]

    for feat_data in top_features:
        feature_name = feat_data['feature']
        value = feat_data['value']

        label, description, impact = _get_feature_description(feature_name, value, predicted_class)

        risk_factors.append({
            "factor": label,
            "value": round(value, 2) if isinstance(value, float) else value,
            "description": description,
            "impact": impact,
            "shap_importance": round(feat_data['shap_value'], 4),
            "shap_explanation": f"Contributes {'+' if feat_data['shap_value'] > 0 else ''}{feat_data['shap_value']:.3f} to prediction"
        })

    return risk_factors


def generate_shap_counterfactuals(features: Dict, prediction: int, probabilities: np.ndarray, shap_explanation: Dict) -> List[Dict]:
    """Generate personalized counterfactuals based on top SHAP features"""
    counterfactuals = []
    
    if not shap_explanation or not shap_explanation.get('top_features'):
        return generate_counterfactuals(features, prediction, probabilities)
    
    risk_features = [f for f in shap_explanation['top_features'][:5] 
                     if f['impact'] == 'increases_risk'][:3]
    
    for feat_data in risk_features:
        feature_name = feat_data['feature']
        current_value = feat_data['value']
        
        if not isinstance(current_value, (int, float)):
            continue
        
        if 'match' in feature_name or 'score' in feature_name:
            new_value = min(current_value + 0.3, 1.0)
            description = f"had 30% better {feature_name.replace('_', ' ')}"
        elif 'tenure' in feature_name:
            new_value = current_value + 24
            if 'avg' in feature_name:
                description = f"had 2 years longer average tenure per job"
            elif 'current' in feature_name:
                description = f"stayed 2 more years in current role"
            else:
                description = f"had 2 years longer tenure"
        elif 'hopping' in feature_name:
            new_value = max(current_value - 0.3, 0)
            description = f"had more stable job history"
        else:
            continue
        
        modified_features = features.copy()
        modified_features[feature_name] = new_value
        
        try:
            new_pred, new_proba = _sync_predict(modified_features)

            if new_pred > prediction:
                counterfactuals.append({
                    "scenario": f"If candidate {description}",
                    "original_risk": RISK_LABELS[prediction],
                    "new_risk": RISK_LABELS[new_pred],
                    "confidence_change": float(new_proba[new_pred] - probabilities[prediction]),
                    "impact": "positive" if new_pred > prediction else "negative",
                    "feature_changed": feature_name,
                    "original_value": float(current_value),
                    "new_value": float(new_value),
                    "shap_importance": float(feat_data['shap_value'])
                })
        except:
            continue
    
    return counterfactuals[:3]


def generate_counterfactuals(features: Dict, prediction: int, probabilities: np.ndarray) -> List[Dict]:
    """Generate simple counterfactual scenarios"""
    counterfactuals = []
    
    test_scenarios = [
        ("avg_tenure_months", min(features["avg_tenure_months"] + 24, 48), "had 2 years average tenure per job"),
        ("job_hopping_rate", max(features["job_hopping_rate"] - 0.5, 0), "had much more stable job history"),
        ("skill_match_score", min(features["skill_match_score"] + 0.3, 1.0), "had 30% better skill match"),
    ]
    
    for feature_name, new_value, description in test_scenarios:
        modified_features = features.copy()
        modified_features[feature_name] = new_value
        
        try:
            new_pred, new_proba = _sync_predict(modified_features)

            if new_pred > prediction:
                counterfactuals.append({
                    "scenario": f"If candidate {description}",
                    "original_risk": RISK_LABELS[prediction],
                    "new_risk": RISK_LABELS[new_pred],
                    "confidence_change": float(new_proba[new_pred] - probabilities[prediction]),
                    "impact": "positive" if new_pred > prediction else "negative",
                    "feature_changed": feature_name,
                    "original_value": float(features[feature_name]),
                    "new_value": float(new_value)
                })
        except:
            continue
    
    return counterfactuals[:3]