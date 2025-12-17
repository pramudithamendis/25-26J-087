from fastapi import HTTPException
from typing import Dict, Any, List
from bson import ObjectId
import numpy as np
import pandas as pd
from app.database import get_cv_collection
from app.services.feature_engineering import create_feature_vector_from_mongo
from app.services.model_loader import predict_with_model, get_model

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
    4. Generate SHAP-based explanations
    5. Generate counterfactual "what-if" scenarios
    6. Return results with full explainability
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
        model = get_model()
        
        print(f" Prediction complete: {RISK_LABELS[predicted_class]} (confidence: {probabilities[predicted_class]:.2%})")
        
        # Step 4: Try to generate SHAP explanations (with timeout protection)
        
        shap_explanation = generate_shap_explanation_safe(features, predicted_class)
        
        # Step 5: Identify risk factors
        if shap_explanation and shap_explanation.get('top_features'):
            print(" Using SHAP-based risk factors")
            risk_factors = identify_risk_factors_shap(features, shap_explanation)
        else:
            print(" Using rule-based risk factors")
            risk_factors = identify_risk_factors(features)
        
        # Step 6: Generate counterfactuals
        if shap_explanation and shap_explanation.get('top_features'):
            print(" Generating SHAP-guided counterfactuals")
            counterfactuals = generate_shap_counterfactuals(
                features, predicted_class, probabilities, model, shap_explanation
            )
        else:
            print(" Generating simple counterfactuals")
            counterfactuals = generate_counterfactuals(features, predicted_class, probabilities, model)
        
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
            "counterfactuals": counterfactuals
        }
        
        print(" Response ready")
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


def generate_shap_explanation_safe(features: Dict[str, float], predicted_class: int, timeout_seconds: int = 5) -> Dict[str, Any]:
    """
    SAFE wrapper for SHAP explanation generation with timeout and fallback
    Returns empty explanation if SHAP fails or times out
    """
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("SHAP generation timed out")
    
    try:
        # Set timeout alarm
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
        
        # Try to load SHAP model and generate explanation
        from app.services.model_loader import get_model_for_shap
        import shap
        
        shap_model = get_model_for_shap()
        
        explanation = generate_shap_explanation_internal(features, shap_model, predicted_class)
        
        # Cancel alarm
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
        
        print("   SHAP explanation generated successfully")
        return explanation
        
    except TimeoutError:
        print("   SHAP generation timed out - continuing without it")
        return get_empty_shap_explanation()
    except ImportError as e:
        print(f"   SHAP library not available: {e}")
        return get_empty_shap_explanation()
    except Exception as e:
        print(f"   SHAP generation failed: {type(e).__name__}: {str(e)[:100]}")
        return get_empty_shap_explanation()
    finally:
        # Always cancel alarm
        if hasattr(signal, 'SIGALRM'):
            try:
                signal.alarm(0)
            except:
                pass


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
    """
    Internal SHAP generation (called by safe wrapper)
    Handles CatBoost's multi-dimensional SHAP output format
    """
    import shap
    
    # Convert features to DataFrame
    feature_df = pd.DataFrame([features])
    feature_names = list(features.keys())
    feature_values = list(features.values())
    
    # Extract classifier from pipeline
    if hasattr(model, 'named_steps'):
        preprocessor = model.named_steps.get('pre')
        clf = model.named_steps.get('clf')
        
        if preprocessor:
            X_transformed = preprocessor.transform(feature_df)
            if hasattr(X_transformed, 'toarray'):
                X_transformed = X_transformed.toarray()
        else:
            X_transformed = feature_df.values
    else:
        clf = model
        X_transformed = feature_df.values
    
    # Create TreeExplainer
    explainer = shap.TreeExplainer(clf)
    shap_values = explainer.shap_values(X_transformed)
    
    # Handle CatBoost's multi-class output format
    # CatBoost returns shape: (n_samples, n_features, n_classes) or list of arrays
    if isinstance(shap_values, np.ndarray):
        # Array format: extract class-specific values
        if len(shap_values.shape) == 3:
            # Shape: (n_samples=1, n_features, n_classes)
            # Extract: shap_values[0, :, predicted_class]
            shap_vals = shap_values[0, :, predicted_class]
            print(f"    Extracted from 3D array: shape {shap_vals.shape}")
        elif len(shap_values.shape) == 2:
            # Shape: (n_features, n_classes) - extract column
            shap_vals = shap_values[:, predicted_class]
            print(f"    Extracted from 2D array: shape {shap_vals.shape}")
        else:
            # Shape: (n_features,) - already 1D
            shap_vals = shap_values
            print(f"    Using 1D array directly: shape {shap_vals.shape}")
    elif isinstance(shap_values, list):
        # List format: [class_0_array, class_1_array, class_2_array]
        if len(shap_values) > predicted_class:
            class_array = shap_values[predicted_class]
            # Ensure it's 1D
            shap_vals = np.array(class_array).flatten()
            print(f"    Extracted from list[{predicted_class}]: shape {shap_vals.shape}")
        else:
            shap_vals = np.array(shap_values[0]).flatten()
            print(f"    Using list[0] as fallback: shape {shap_vals.shape}")
    else:
        raise ValueError(f"Unexpected SHAP values type: {type(shap_values)}")
    
    # Handle expected_value (base prediction)
    if isinstance(explainer.expected_value, (list, np.ndarray)):
        if len(explainer.expected_value) > predicted_class:
            base_value = float(explainer.expected_value[predicted_class])
        else:
            base_value = float(explainer.expected_value[0])
    else:
        base_value = float(explainer.expected_value)
    
    # Create feature contributions
    feature_contributions = []
    
    # Match lengths - handle preprocessor expansion
    n_shap = len(shap_vals)
    n_features = len(feature_names)
    
    if n_shap > n_features:
        # Preprocessor created more features (one-hot encoding)
        # Use only first N matching original features
        print(f"     Preprocessor expanded features: {n_features} -> {n_shap}")
        shap_vals = shap_vals[:n_features]
    elif n_shap < n_features:
        # Pad if needed
        
        shap_vals = np.pad(shap_vals, (0, n_features - n_shap), constant_values=0)
    
    # Zip and create contributions
    for fname, fval, shap_val in zip(feature_names, feature_values, shap_vals):
        try:
            # Safe float conversion
            if isinstance(shap_val, (list, tuple, np.ndarray)):
                shap_float = float(np.array(shap_val).flatten()[0])
            else:
                shap_float = float(shap_val)
            
            # Handle feature value
            if isinstance(fval, (int, float, np.number)):
                value_float = float(fval)
            else:
                value_float = 0.0  # Categorical features
            
            feature_contributions.append({
                "feature": fname,
                "value": value_float,
                "value_display": str(fval),
                "shap_value": shap_float,
                "abs_shap_value": abs(shap_float),
                "impact": "increases_risk" if shap_float > 0 else "decreases_risk"
            })
        except Exception as e:
            print(f"     Skipping feature {fname}: {type(e).__name__}: {e}")
            continue
    
    # Sort by importance
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
    
    # Short average tenure
    if features['avg_tenure_months'] < 12:
        risk_factors.append({
            "factor": "Short average job tenure",
            "value": round(features['avg_tenure_months'], 1),
            "description": "Average time per job is less than 1 year",
            "impact": "high"
        })
    
    # Low location match
    if features['location_match_score'] < 0.5:
        risk_factors.append({
            "factor": "Long commute distance",
            "value": round(features['location_match_score'], 2),
            "description": "Significant distance between candidate location and job location",
            "impact": "medium"
        })
    
    # Sort by impact
    impact_order = {"high": 3, "medium": 2, "low": 1}
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
        'job_hopping_rate': ("Frequent job changes", "High proportion of short-tenure jobs", "high"),
        'skill_match_score': ("Skill-job alignment", "Degree of match between candidate skills and job requirements", "high"),
        'title_match_score': ("Job role similarity", "How well current role matches target position", "medium"),
        'avg_tenure_months': ("Average job tenure", "Average duration per previous job", "high"),
        'location_match_score': ("Location compatibility", "Distance between candidate location and job location", "medium"),
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
    """Generate SHAP-guided counterfactuals"""
    # Use simple counterfactuals as fallback
    return generate_counterfactuals(features, prediction, probabilities, model)


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
            
            if new_pred != prediction or abs(new_proba[new_pred] - probabilities[prediction]) > 0.02:
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