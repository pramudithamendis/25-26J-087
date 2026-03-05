from fastapi import HTTPException
from typing import Dict, Any, List
from bson import ObjectId
import numpy as np
import pandas as pd
from app.database import cv_collection, turnover_collection
from datetime import datetime
from app.services.feature_engineering import create_feature_vector_from_mongo
from app.services.model_loader import predict_with_model, get_model
from app.services.fairness_utils import extract_fairness_metadata, get_fairness_context
import time
from app.services.feature_engineering import extract_location_from_jd_enhanced
import threading

_shap_lock = threading.Lock()
_shap_explainer = None
_shap_model = None

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
        
        # Step 3: Predict using model
        predicted_class, probabilities = predict_with_model(features)
        model = get_model()

        # Soft-clamp probabilities so UI never shows exactly 0% or 100%
        # This reflects real-world uncertainty even when the model is very confident
        probabilities = np.clip(probabilities, 0.02, 0.96)
        probabilities = probabilities / probabilities.sum()  # renormalize to sum to 1.0

        print(f" Prediction complete: {RISK_LABELS[predicted_class]} (confidence: {probabilities[predicted_class]:.2%})")
        
        # Step 3.5: Override prediction for severe overqualification
        original_prediction = predicted_class
        overqualification_override = False
        
        if features['is_overqualified'] == 1 and features['exp_match_score'] < 0.6:
            print(f"  OVERQUALIFICATION DETECTED: {features['total_exp_years']:.1f} years, exp_match={features['exp_match_score']:.2f}")
            
            # Only override if prediction was Low Risk (class 2)
            if predicted_class == 2:
                print(f"   OVERRIDING prediction from Low Risk → High Risk")
                predicted_class = 0  # Force HIGH RISK
                probabilities = np.array([0.80, 0.15, 0.05])  # Recalibrate
                overqualification_override = True
        
        # Step 4: Generate SHAP explanations (with hard timeout)
        shap_start = time.time()
        shap_explanation = generate_shap_explanation_safe(features, predicted_class, timeout_seconds=8)
        shap_elapsed = time.time() - shap_start

        if shap_elapsed > 8.0:
            print(f"   SHAP generation exceeded timeout ({shap_elapsed:.2f}s)")
            shap_explanation = get_empty_shap_explanation()
        
        # Step 5: Identify risk factors
        if shap_explanation and shap_explanation.get('top_features'):
            print("Using SHAP-based risk factors")
            risk_factors = identify_risk_factors_shap(features, shap_explanation)
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
                features, predicted_class, probabilities, model, shap_explanation
            )
        else:
            print("Generating simple counterfactuals")
            counterfactuals = generate_counterfactuals(features, predicted_class, probabilities, model)
        
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
        
        # Add override metadata if applicable
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

def get_shap_explainer():
    global _shap_explainer, _shap_model
    if _shap_explainer is None:
        from app.services.model_loader import get_model_for_shap
        import shap
        _shap_model = get_model_for_shap()  # ← cache model too
        clf = _shap_model.named_steps.get('clf') if hasattr(_shap_model, 'named_steps') else _shap_model
        _shap_explainer = shap.TreeExplainer(clf)
        print("SHAP explainer cached")
    return _shap_explainer

def generate_shap_explanation_safe(features: Dict[str, float], predicted_class: int, timeout_seconds: int = 8) -> Dict[str, Any]:
    
    print("   Waiting for SHAP lock...")
    # Wait up to 60 seconds for previous SHAP to finish
    lock_acquired = _shap_lock.acquire(blocking=True, timeout=60)
    
    if not lock_acquired:
        print("   Could not acquire SHAP lock after 60s - using rule-based")
        return get_empty_shap_explanation()
    
    try:
        result = {'explanation': None, 'error': None, 'completed': False}
        
        def generate_with_timeout():
            try:
                
                import shap
                explanation = generate_shap_explanation_internal(features, None, predicted_class)
                result['explanation'] = explanation
                result['completed'] = True
            except Exception as e:
                result['error'] = str(e)
                result['completed'] = True
        
        thread = threading.Thread(target=generate_with_timeout, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            print(f"   SHAP timed out after {timeout_seconds}s")
            return get_empty_shap_explanation()
        
        if result['explanation']:
            return result['explanation']
            
        return get_empty_shap_explanation()
        
    finally:
        _shap_lock.release()


def get_empty_shap_explanation() -> Dict[str, Any]:
    """Return empty SHAP explanation structure"""
    return {
        "base_value": 0.0,
        "prediction_value": 0.0,
        "top_features": [],
        "all_features": [],
        "explanation": "SHAP explanation unavailable - using rule-based analysis instead"
    }

def generate_shap_explanation_internal(features: Dict[str, float], model, predicted_class: int) -> Dict[str, Any]:
    """Internal SHAP generation - handles CatBoost multi-dimensional output"""
    import shap
    
    feature_df = pd.DataFrame([features])
    feature_names = list(features.keys())
    feature_values = list(features.values())
    
    global _shap_model
    explainer = get_shap_explainer()
    full_model = _shap_model
    
    if full_model is None:  # safety check
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
    
    # Handle multi-class SHAP output
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
    
    # Simple overqualification detection 
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


def identify_risk_factors_shap(features: Dict[str, float], shap_explanation: Dict) -> List[Dict]:
    """SHAP-based risk factor identification"""
    risk_factors = []
    
    top_risk_features = [
        f for f in shap_explanation.get('top_features', [])
        if f['impact'] == 'increases_risk'
    ][:5]
    
    feature_descriptions = {
        'job_hopping_rate': ("Frequent Job Changes", "High proportion of short-tenure jobs", "high"),
        'skill_match_score': ("Skills Alignment", "Weak skill match may lead to frustration and job searching", "high"),
        'title_match_score': ("Role Similarity", "Different role may cause dissatisfaction or mismatch", "medium"),
        'avg_tenure_months': ("Average Job Tenure", "Average duration per previous job", "high"),
        'location_match_score': ("Location Compatibility", "Distance between candidate location and job location", "medium"),
        'n_skills': ("Skill Breadth", "Candidate has a strong variety of skills", "low"),
        'has_progression': ("Career Progression", "Career progression across jobs shows ambition", "low"),
        'overall_match_score': ("Overall Job Fit", "Poor overall fit increases likelihood of early departure", "high"),
        'exp_match_score': ("Experience Match", "Mismatch between candidate experience and job requirements", "medium"),
        'edu_match_score': ("Education Match", "Education level doesn't align well with job requirements", "medium"),
        'is_overqualified': ("Overqualification", "Overqualified candidates often leave for better opportunities", "medium"),
        'is_underqualified': ("Underqualification", "Underqualified candidates may struggle and leave early", "high"),
        'current_job_tenure': ("Current Role Stability", "Time spent in current job indicates commitment level", "medium"),
        'total_exp_years': ("Total Experience", "Overall years of work experience", "medium"),
        'total_jobs': ("Number of Jobs", "Total number of positions held", "medium"),
        'short_stints_count': ("Short Stints", "Number of jobs held for less than a year", "high"),
        'tenure_slope': ("Tenure Trend", "Whether job tenures are increasing or decreasing over time", "medium"),
        'industry_switches': ("Industry Switches", "Number of times candidate changed industry", "medium"),
        'progression_jumps': ("Promotion History", "Number of upward career moves", "low"),
        'has_masters': ("Advanced Education", "Holds a postgraduate degree", "low"),
        'n_education': ("Education Count", "Number of educational qualifications", "low"),
        'n_certifications': ("Certifications", "Number of professional certifications held", "low"),
        'is_remote_cv': ("Remote Work History", "Candidate has remote work experience", "low"),
        'is_remote_jd': ("Remote Role", "This position is remote", "low"),
        'work_mode_mismatch': ("Work Mode Mismatch", "Mismatch between candidate work preference and role type", "medium"),
        'has_career_gap': ("Career Gap", "Candidate has a gap in employment history", "medium"),
        'career_gap_months': ("Career Gap Duration", "Length of employment gap in months", "medium"),
        'is_remote_preference': ("Remote Preference", "Candidate prefers remote work", "low"),
    }
    
    for feat_data in top_risk_features:
        feature_name = feat_data['feature']
        desc = feature_descriptions.get(feature_name, (feature_name.replace('_', ' ').title(), f"Feature value: {feat_data['value']:.2f}", "medium"))
        
        risk_factors.append({
            "factor": desc[0],
            "value": round(feat_data['value'], 2),
            "description": desc[1],
            "impact": desc[2],
            "shap_importance": round(feat_data['shap_value'], 4),
            "shap_explanation": f"Contributes +{abs(feat_data['shap_value']):.3f} to risk"
        })
    
    return risk_factors


def generate_shap_counterfactuals(features: Dict, prediction: int, probabilities: np.ndarray, model, shap_explanation: Dict) -> List[Dict]:
    """Generate personalized counterfactuals based on top SHAP features"""
    counterfactuals = []
    
    if not shap_explanation or not shap_explanation.get('top_features'):
        return generate_counterfactuals(features, prediction, probabilities, model)
    
    # Get top 3 features that increase risk
    risk_features = [f for f in shap_explanation['top_features'][:5] 
                     if f['impact'] == 'increases_risk'][:3]
    
    for feat_data in risk_features:
        feature_name = feat_data['feature']
        current_value = feat_data['value']
        
        # Skip categorical features
        if not isinstance(current_value, (int, float)):
            continue
        
        # Determine improvement direction
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
        
        # Test counterfactual
        modified_features = features.copy()
        modified_features[feature_name] = new_value
        
        try:
            new_pred, new_proba = predict_with_model(modified_features)
            
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


def generate_counterfactuals(features: Dict, prediction: int, probabilities: np.ndarray, model) -> List[Dict]:
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
            new_pred, new_proba = predict_with_model(modified_features)
            
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