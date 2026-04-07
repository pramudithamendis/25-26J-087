import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from bson import ObjectId
from fastapi import HTTPException

from app.database import cv_collection, turnover_collection
from app.services.fairness_utils import extract_fairness_metadata, get_fairness_context
from app.services.feature_engineering import (
    create_feature_vector_from_mongo,
    extract_location_from_jd_enhanced,
)
from app.services.model_loader import get_model, predict_with_model

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

# Display labels for the three early attrition risk classes
RISK_LABELS = {
    0: "High Early Attrition Risk",
    1: "Moderate Early Attrition Risk",
    2: "Low Early Attrition Risk",
}

# Probability soft-clamp bounds - prevents UI from showing exactly 0% or 100%
PROB_CLAMP_MIN = 0.02
PROB_CLAMP_MAX = 0.96

# SHAP generation timeout in seconds - falls back to rule-based if exceeded
SHAP_TIMEOUT_SECONDS = 8

# SHAP lock acquisition timeout in seconds
SHAP_LOCK_TIMEOUT_SECONDS = 25

# Overqualification override threshold - exp_match below this triggers override
OVERQUALIFICATION_EXP_MATCH_THRESHOLD = 0.6

# SLA threshold for prediction time in seconds
PREDICTION_SLA_SECONDS = 5.0

# Thresholds for rule-based risk factor identification
JOB_HOPPING_HIGH_THRESHOLD = 0.5
SKILL_MATCH_LOW_THRESHOLD = 0.4
TITLE_MATCH_LOW_THRESHOLD = 0.4
TENURE_LOW_THRESHOLD = 12  # months
LOCATION_MATCH_LOW_THRESHOLD = 0.5

# Overqualification override probabilities
OVERQUALIFICATION_OVERRIDE_PROBABILITIES = [0.80, 0.15, 0.05]

# ============================================================
# SHAP STATE - module-level singletons
# ============================================================

_shap_lock = threading.Lock()
_shap_explainer = None
_shap_model = None

# ============================================================
# MAIN PREDICTION PIPELINE
# ============================================================

async def predict_turnover_from_cv_id(
    cv_id: str,
    job_description: str,
    job_location: str = None,
    user: dict = None,
    job_id: str = None,
    job_title: str = None,
) -> Dict[str, Any]:
    """
    Run the full early attrition risk prediction pipeline for a candidate.

    Retrieves the candidate's CV from MongoDB, engineers 22 features from
    the CV and job description, runs the calibrated ensemble model, generates
    SHAP-based explanations and counterfactual scenarios, and saves the result.

    Args:
        cv_id: MongoDB ObjectId string of the stored CV document.
        job_description: Raw job description text used for feature computation.
        job_location: Optional job location string. Extracted from JD if not provided.
        user: Authenticated user dict (used to record the requesting user's email).
        job_id: Optional job posting ID for result traceability.
        job_title: Optional job title passed directly for title match scoring.

    Returns:
        Dictionary containing prediction label, confidence scores, SHAP explanation,
        risk factors, counterfactual scenarios, fairness context, and performance metadata.
    """
    start_time = time.time()

    try:
        # ----------------------------------------------------------
        # Step 1: Retrieve CV document from MongoDB
        # ----------------------------------------------------------
        try:
            cv_document = cv_collection.find_one({"_id": ObjectId(cv_id)})
        except Exception:
            raise HTTPException(400, f"Invalid CV ID format: {cv_id}")

        if not cv_document:
            raise HTTPException(404, f"CV not found with ID: {cv_id}")

        # ----------------------------------------------------------
        # Step 1.5: Extract fairness metadata from CV
        # Region, university tier, and career gap are tracked for
        # demographic parity auditing. No protected attributes used.
        # ----------------------------------------------------------
        fairness_metadata = extract_fairness_metadata(cv_document)

        # ----------------------------------------------------------
        # Step 2: Resolve job location
        # Use explicitly provided location; fall back to JD extraction.
        # ----------------------------------------------------------
        if not job_location:
            jd_location = extract_location_from_jd_enhanced(job_description)
            logger.info(f"Extracted JD location from text: {jd_location}")
        else:
            jd_location = job_location

        # ----------------------------------------------------------
        # Step 3: Engineer 22 features from CV and JD
        # Features cover job fit, career stability, progression,
        # and contextual factors (location, work mode).
        # ----------------------------------------------------------
        features = await create_feature_vector_from_mongo(
            cv_document,
            job_description,
            jd_location=jd_location,
            job_title=job_title,
        )

        # ----------------------------------------------------------
        # Step 4: Run ensemble model prediction
        # ----------------------------------------------------------
        predicted_class, probabilities = predict_with_model(features)
        model = get_model()

        # Soft-clamp probabilities to avoid displaying 0% or 100% in the UI,
        # which can mislead HR decision-makers into over-certainty.
        probabilities = np.clip(probabilities, PROB_CLAMP_MIN, PROB_CLAMP_MAX)
        probabilities = probabilities / probabilities.sum()

        logger.info(
            f"Prediction: {RISK_LABELS[predicted_class]} "
            f"(confidence: {probabilities[predicted_class]:.2%})"
        )

        # ----------------------------------------------------------
        # Step 4.5: Override for severe overqualification
        # If the model predicts Low Risk but the candidate is clearly
        # overqualified (exp_match < 0.6), override to High Risk.
        # ----------------------------------------------------------
        original_prediction = predicted_class
        overqualification_override = False

        if (
            features["is_overqualified"] == 1
            and features["exp_match_score"] < OVERQUALIFICATION_EXP_MATCH_THRESHOLD
        ):
            logger.warning(
                f"Overqualification detected: {features['total_exp_years']:.1f} years, "
                f"exp_match={features['exp_match_score']:.2f}"
            )
            if predicted_class == 2:
                logger.warning(
                    "Overriding prediction: Low Early Attrition Risk → High Early Attrition Risk"
                )
                predicted_class = 0
                probabilities = np.array(OVERQUALIFICATION_OVERRIDE_PROBABILITIES)
                overqualification_override = True

        # ----------------------------------------------------------
        # Step 5: Generate SHAP explanations
        # Uses CatBoost TreeExplainer with a thread-based timeout.
        # Falls back to an empty explanation if timeout is exceeded.
        # ----------------------------------------------------------
        shap_start = time.time()
        shap_explanation = generate_shap_explanation_safe(
            features, predicted_class, timeout_seconds=SHAP_TIMEOUT_SECONDS
        )
        shap_elapsed = time.time() - shap_start

        if shap_elapsed > SHAP_TIMEOUT_SECONDS:
            logger.warning(f"SHAP generation exceeded timeout ({shap_elapsed:.2f}s)")
            shap_explanation = get_empty_shap_explanation()

        # ----------------------------------------------------------
        # Step 6: Identify key risk factors
        # SHAP-based factors are preferred; rule-based is the fallback.
        # ----------------------------------------------------------
        if shap_explanation and shap_explanation.get("top_features"):
            logger.info("Using SHAP-based risk factors")
            risk_factors = identify_risk_factors_shap(
                features, shap_explanation, predicted_class
            )
        else:
            logger.info("Using rule-based risk factors (SHAP unavailable)")
            risk_factors = identify_risk_factors(features)

        # Prepend overqualification warning if prediction was overridden
        if overqualification_override:
            risk_factors.insert(
                0,
                {
                    "factor": "SEVERE OVERQUALIFICATION (Prediction Override)",
                    "value": f"{features['total_exp_years']:.1f} years for entry-level role",
                    "description": (
                        f"Candidate is significantly overqualified "
                        f"(exp_match: {features['exp_match_score']:.2f}). "
                        f"Original prediction was '{RISK_LABELS[original_prediction]}', "
                        f"overridden to High Early Attrition Risk due to career level "
                        f"mismatch and high likelihood of early departure."
                    ),
                    "impact": "critical",
                    "override_applied": True,
                    "original_prediction": RISK_LABELS[original_prediction],
                },
            )

        # ----------------------------------------------------------
        # Step 7: Generate counterfactual scenarios
        # Shows HR how specific profile changes would shift the risk class.
        # SHAP-guided counterfactuals are preferred over simple ones.
        # ----------------------------------------------------------
        if shap_explanation and shap_explanation.get("top_features"):
            logger.info("Generating SHAP-guided counterfactual scenarios")
            counterfactuals = generate_shap_counterfactuals(
                features, predicted_class, probabilities, model, shap_explanation
            )
        else:
            logger.info("Generating simple counterfactual scenarios")
            counterfactuals = generate_counterfactuals(
                features, predicted_class, probabilities, model
            )

        # For confident low-risk predictions, no realistic counterfactuals may exist
        counterfactuals_note = None
        if not counterfactuals and predicted_class == 2:
            counterfactuals_note = {
                "reason": "highly_confident_low_risk_prediction",
                "explanation": (
                    "This candidate's profile demonstrates strong retention indicators. "
                    "No realistic changes to individual features would significantly "
                    "alter the low early attrition risk prediction."
                ),
                "key_strengths": [
                    f"Stable job history: {features['avg_tenure_months']:.0f} months average tenure",
                    f"Low job hopping rate: {features['job_hopping_rate']:.2f}",
                    f"Current role stability: {features['current_job_tenure']:.0f} months",
                ],
            }

        # ----------------------------------------------------------
        # Step 7.5: Get fairness context for response
        # ----------------------------------------------------------
        fairness_context = get_fairness_context(fairness_metadata)

        elapsed_time = time.time() - start_time

        # ----------------------------------------------------------
        # Step 8: Build response payload
        # ----------------------------------------------------------
        result = {
            "status": "success",
            "cv_id": cv_id,
            "cv_name": cv_document.get("name")
            or cv_document.get("basics", {}).get("name", "Unknown"),
            "prediction": {
                "risk_level": predicted_class,
                "risk_label": RISK_LABELS[predicted_class],
                "confidence": float(probabilities[predicted_class]),
                "probabilities": {
                    "high_risk": float(probabilities[0]),
                    "medium_risk": float(probabilities[1]),
                    "low_risk": float(probabilities[2]),
                },
            },
            "features": {
                "skill_match": round(features["skill_match_score"], 2),
                "title_match": round(features["title_match_score"], 2),
                "exp_match": round(features["exp_match_score"], 2),
                "location_match": round(features["location_match_score"], 2),
                "overall_match": round(features["overall_match_score"], 2),
                "job_hopping_rate": round(features["job_hopping_rate"], 2),
                "total_jobs": int(features["total_jobs"]),
                "total_experience": round(features["total_exp_years"], 1),
                "avg_tenure_months": round(features["avg_tenure_months"], 1),
            },
            "shap_explanation": shap_explanation,
            "risk_factors": risk_factors,
            "counterfactuals": counterfactuals,
            "fairness": fairness_context,
            "performance": {
                "prediction_time_seconds": round(elapsed_time, 3),
                "meets_sla": elapsed_time < PREDICTION_SLA_SECONDS,
                "note": (
                    "Prediction time includes CV parsing, feature engineering, "
                    "model inference, and SHAP calculation"
                ),
            },
        }

        if counterfactuals_note:
            result["counterfactuals_note"] = counterfactuals_note

        if overqualification_override:
            result["override_metadata"] = {
                "override_type": "severe_overqualification",
                "original_prediction": RISK_LABELS[original_prediction],
                "final_prediction": RISK_LABELS[predicted_class],
                "reason": "Candidate significantly overqualified for role",
            }

        # ----------------------------------------------------------
        # Step 9: Persist result to MongoDB
        # ----------------------------------------------------------
        try:
            db_entry = result.copy()
            db_entry["cv_id"] = cv_id
            db_entry["job_description"] = job_description
            db_entry["job_location"] = job_location
            db_entry["job_id"] = job_id
            db_entry["calculated_at"] = datetime.utcnow()
            db_entry["user_email"] = user.get("email") if user else None
            insert_result = turnover_collection.insert_one(db_entry)
            result["result_id"] = str(insert_result.inserted_id)
            logger.info(f"Saved prediction result for CV {cv_id} to MongoDB")
        except Exception as e:
            logger.error(f"Failed to save prediction result to MongoDB: {e}")

        if elapsed_time > PREDICTION_SLA_SECONDS:
            logger.warning(
                f"Prediction took {elapsed_time:.2f}s — exceeds {PREDICTION_SLA_SECONDS}s SLA"
            )
        else:
            logger.info(f"Prediction completed in {elapsed_time:.2f}s")

        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        logger.error(f"Unexpected error in prediction pipeline: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc(),
            "prediction": None,
        }


# ============================================================
# SHAP EXPLAINABILITY
# ============================================================

def get_shap_explainer():
    """
    Return a cached SHAP TreeExplainer for the CatBoost model.

    Uses a module-level singleton to avoid reloading the explainer
    on every prediction request. CatBoost is used because TreeExplainer
    provides exact (not approximate) Shapley values for tree-based models.
    """
    global _shap_explainer, _shap_model

    if _shap_explainer is None:
        import shap
        from app.services.model_loader import get_model_for_shap

        _shap_model = get_model_for_shap()
        clf = (
            _shap_model.named_steps.get("clf")
            if hasattr(_shap_model, "named_steps")
            else _shap_model
        )
        _shap_explainer = shap.TreeExplainer(clf)
        logger.info("SHAP TreeExplainer cached successfully")

    return _shap_explainer


def generate_shap_explanation_safe(
    features: Dict[str, float],
    predicted_class: int,
    timeout_seconds: int = SHAP_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Generate SHAP explanation with thread-based timeout and lock protection.

    SHAP calculation can be slow on first call so a threading lock prevents
    concurrent SHAP calls from overloading the server. If SHAP does not
    complete within timeout_seconds, an empty explanation is returned and
    the rule-based fallback is used instead.

    Args:
        features: Dictionary of 22 engineered feature values.
        predicted_class: Integer class index (0=High, 1=Moderate, 2=Low).
        timeout_seconds: Maximum seconds to wait for SHAP before fallback.

    Returns:
        SHAP explanation dict with top_features and all_features, or empty dict.
    """
    logger.debug("Waiting for SHAP lock...")
    lock_acquired = _shap_lock.acquire(
        blocking=True, timeout=SHAP_LOCK_TIMEOUT_SECONDS
    )

    if not lock_acquired:
        logger.warning(
            f"Could not acquire SHAP lock after {SHAP_LOCK_TIMEOUT_SECONDS}s — "
            f"using rule-based fallback"
        )
        return get_empty_shap_explanation()

    try:
        result = {"explanation": None, "error": None, "completed": False}

        def generate_with_timeout():
            try:
                explanation = generate_shap_explanation_internal(
                    features, None, predicted_class
                )
                result["explanation"] = explanation
                result["completed"] = True
            except Exception as e:
                result["error"] = str(e)
                result["completed"] = True

        thread = threading.Thread(target=generate_with_timeout, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            logger.warning(f"SHAP timed out after {timeout_seconds}s — using fallback")
            return get_empty_shap_explanation()

        if result["explanation"]:
            return result["explanation"]

        return get_empty_shap_explanation()

    finally:
        _shap_lock.release()


def get_empty_shap_explanation() -> Dict[str, Any]:
    """
    Return a placeholder SHAP explanation used when SHAP is unavailable.

    Returned when SHAP times out or the lock cannot be acquired.
    The rule-based risk factor identification is used as a fallback.
    """
    return {
        "base_value": 0.0,
        "prediction_value": 0.0,
        "top_features": [],
        "all_features": [],
        "explanation": "SHAP explanation unavailable. Using rule-based analysis instead",
    }


def generate_shap_explanation_internal(
    features: Dict[str, float],
    model,
    predicted_class: int,
) -> Dict[str, Any]:
    """
    Compute SHAP values for a single prediction using the CatBoost TreeExplainer.

    Transforms the feature dict through any pipeline preprocessor, computes
    per-feature Shapley values for the predicted class, and returns them sorted
    by absolute magnitude so the most influential features appear first.

    Args:
        features: Dictionary of 22 engineered feature values.
        model: Unused — kept for interface consistency. Uses cached _shap_model.
        predicted_class: Integer class index to explain (0, 1, or 2).

    Returns:
        Dictionary with base_value, prediction_value, top_features (top 10),
        all_features, and a summary explanation string.
    """
    import shap

    feature_df = pd.DataFrame([features])
    feature_names = list(features.keys())
    feature_values = list(features.values())

    global _shap_model
    explainer = get_shap_explainer()
    full_model = _shap_model

    if full_model is None:
        raise ValueError("SHAP model not initialized")

    # Apply pipeline preprocessor if present
    if hasattr(full_model, "named_steps"):
        preprocessor = full_model.named_steps.get("pre")
        if preprocessor:
            X_transformed = preprocessor.transform(feature_df)
            if hasattr(X_transformed, "toarray"):
                X_transformed = X_transformed.toarray()
        else:
            X_transformed = feature_df.values
    else:
        X_transformed = feature_df.values

    shap_values = explainer.shap_values(X_transformed)

    # Handle different SHAP output shapes (ndarray vs list of arrays)
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

    # Extract base value for the predicted class
    if isinstance(explainer.expected_value, (list, np.ndarray)):
        base_value = (
            float(explainer.expected_value[predicted_class])
            if len(explainer.expected_value) > predicted_class
            else float(explainer.expected_value[0])
        )
    else:
        base_value = float(explainer.expected_value)

    # Align SHAP values array length with feature count
    n_shap = len(shap_vals)
    n_features = len(feature_names)
    if n_shap > n_features:
        shap_vals = shap_vals[:n_features]
    elif n_shap < n_features:
        shap_vals = np.pad(shap_vals, (0, n_features - n_shap), constant_values=0)

    # Build per-feature contribution records
    feature_contributions = []
    for fname, fval, shap_val in zip(feature_names, feature_values, shap_vals):
        try:
            shap_float = (
                float(np.array(shap_val).flatten()[0])
                if isinstance(shap_val, (list, tuple, np.ndarray))
                else float(shap_val)
            )
            value_float = (
                float(fval) if isinstance(fval, (int, float, np.number)) else 0.0
            )
            feature_contributions.append(
                {
                    "feature": fname,
                    "value": value_float,
                    "value_display": str(fval),
                    "shap_value": shap_float,
                    "abs_shap_value": abs(shap_float),
                    "impact": "increases_risk" if shap_float > 0 else "decreases_risk",
                }
            )
        except Exception as e:
            logger.debug(f"Skipping feature {fname} in SHAP computation: {e}")
            continue

    feature_contributions.sort(key=lambda x: x["abs_shap_value"], reverse=True)
    prediction_value = float(base_value + np.sum(shap_vals))

    return {
        "base_value": base_value,
        "prediction_value": prediction_value,
        "top_features": feature_contributions[:10],
        "all_features": feature_contributions,
        "explanation": f"Base prediction: {base_value:.3f}, Final: {prediction_value:.3f}",
    }


# ============================================================
# RISK FACTOR IDENTIFICATION
# ============================================================

def identify_risk_factors(features: Dict[str, float]) -> list:
    """
    Identify key risk factors using rule-based thresholds.
    Used as a fallback when SHAP explanation is unavailable.

    Args:
        features: Dictionary of 22 engineered feature values.

    Returns:
        List of up to 5 risk factor dicts sorted by impact severity.
    """
    risk_factors = []

    if features["job_hopping_rate"] >= JOB_HOPPING_HIGH_THRESHOLD:
        risk_factors.append(
            {
                "factor": "Frequent job changes",
                "value": round(features["job_hopping_rate"], 2),
                "description": "High proportion of short-tenure jobs",
                "impact": "high",
            }
        )

    if features["skill_match_score"] < SKILL_MATCH_LOW_THRESHOLD:
        risk_factors.append(
            {
                "factor": "Low skill-job match",
                "value": round(features["skill_match_score"], 2),
                "description": "Limited overlap between candidate skills and job requirements",
                "impact": "high",
            }
        )

    if features["title_match_score"] < TITLE_MATCH_LOW_THRESHOLD:
        risk_factors.append(
            {
                "factor": "Job role mismatch",
                "value": round(features["title_match_score"], 2),
                "description": "Current role differs significantly from target position",
                "impact": "medium",
            }
        )

    if features["is_overqualified"] == 1:
        risk_factors.append(
            {
                "factor": "Overqualification",
                "value": "Yes",
                "description": "Candidate may be overqualified for this position",
                "impact": "medium",
            }
        )

    if features["is_underqualified"] == 1:
        risk_factors.append(
            {
                "factor": "Underqualification",
                "value": "Yes",
                "description": "Candidate may lack required experience level",
                "impact": "high",
            }
        )

    if features["avg_tenure_months"] < TENURE_LOW_THRESHOLD:
        risk_factors.append(
            {
                "factor": "Short average job tenure",
                "value": round(features["avg_tenure_months"], 1),
                "description": "Average time per job is less than 1 year",
                "impact": "high",
            }
        )

    if features["location_match_score"] < LOCATION_MATCH_LOW_THRESHOLD:
        risk_factors.append(
            {
                "factor": "Long commute distance",
                "value": round(features["location_match_score"], 2),
                "description": "Significant distance between candidate and job location",
                "impact": "medium",
            }
        )

    impact_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    risk_factors.sort(
        key=lambda x: impact_order.get(x["impact"], 0), reverse=True
    )

    return risk_factors[:5]


def _get_feature_description(
    feature_name: str, value: float, predicted_class: int
) -> tuple:
    """
    Map a feature name and value to a human-readable label, description, and impact level.

    Descriptions are written to reflect whether the feature value is
    positive or negative for the candidate's predicted risk class.

    Args:
        feature_name: Internal feature name (e.g. 'skill_match_score').
        value: Computed feature value for this candidate.
        predicted_class: Predicted risk class (0=High, 1=Moderate, 2=Low).

    Returns:
        Tuple of (label, description, impact) where impact is one of
        'low', 'medium', 'high', or 'critical'.
    """
    if feature_name == "skill_match_score":
        if value >= 0.6:
            return ("Skills Alignment", "Good skill overlap with job requirements supports retention", "low")
        elif value >= 0.4:
            return ("Skills Alignment", "Moderate skill match. Some gaps may lead to frustration", "medium")
        else:
            return ("Skills Alignment", "Weak skill match may lead to frustration and early job searching", "high")

    if feature_name == "title_match_score":
        if value >= 0.7:
            return ("Role Similarity", "Strong alignment between candidate background and this role", "low")
        elif value >= 0.4:
            return ("Role Similarity", "Partial role alignment. Candidate may need adjustment period", "medium")
        else:
            return ("Role Similarity", "Significant role mismatch may cause dissatisfaction", "high")

    if feature_name == "overall_match_score":
        if value >= 0.7:
            return ("Overall Job Fit", "Strong overall fit. Candidate is well-suited for this role", "low")
        elif value >= 0.5:
            return ("Overall Job Fit", "Moderate overall fit. Some areas need attention", "medium")
        else:
            return ("Overall Job Fit", "Poor overall fit increases likelihood of early departure", "high")

    if feature_name == "exp_match_score":
        if value >= 0.8:
            return ("Experience Match", "Experience level fits well with position requirements", "low")
        elif value >= 0.5:
            return ("Experience Match", "Experience partially matches. Minor gaps present", "medium")
        else:
            return ("Experience Match", "Significant mismatch between experience and job requirements", "high")

    if feature_name == "avg_tenure_months":
        if value >= 24:
            return ("Average Job Tenure", f"Stays an average of {value/12:.1f} years per job. Shows strong commitment", "low")
        elif value >= 12:
            return ("Average Job Tenure", f"Average tenure of {value:.0f} months. Moderate stability", "medium")
        else:
            return ("Average Job Tenure", f"Short average tenure of {value:.0f} months suggests commitment issues", "high")

    if feature_name == "current_job_tenure":
        if value >= 24:
            return ("Current Role Stability", f"Has been in current role for {value:.0f} months. Strong stability indicator", "low")
        elif value >= 12:
            return ("Current Role Stability", f"Moderate time in current role ({value:.0f} months)", "medium")
        else:
            return ("Current Role Stability", f"Short time in current role ({value:.0f} months) may indicate instability", "high")

    if feature_name == "job_hopping_rate":
        if value <= 0.2:
            return ("Job Stability", "Minimal job hopping. Very stable work history", "low")
        elif value <= 0.4:
            return ("Job Stability", "Some job changes. Moderate stability", "medium")
        else:
            return ("Job Stability", "High job hopping rate suggests difficulty committing to roles", "high")

    if feature_name == "location_match_score":
        if value >= 0.8:
            return ("Location Compatibility", "Convenient commute distance. Less likely to leave due to travel", "low")
        elif value >= 0.5:
            return ("Location Compatibility", "Moderate commute distance. May be a minor concern", "medium")
        else:
            return ("Location Compatibility", "Long commute distance increases early attrition risk", "high")

    if feature_name == "n_skills":
        if value >= 15:
            return ("Skill Breadth", f"Strong skill portfolio with {value:.0f} skills. Well-rounded candidate", "low")
        else:
            return ("Skill Breadth", f"Limited skill variety ({value:.0f} skills identified)", "medium")

    if feature_name == "has_progression":
        if value == 1:
            return ("Career Progression", "Shows upward career progression. Ambitious and growth-oriented", "low")
        else:
            return ("Career Progression", "Limited career progression detected", "medium")

    if feature_name == "is_overqualified":
        if value == 1:
            return ("Overqualification", "Candidate may be overqualified. Risk of leaving for better opportunities", "high")
        else:
            return ("Qualification Fit", "Qualification level appropriate for this role", "low")

    if feature_name == "is_underqualified":
        if value == 1:
            return ("Underqualification", "Candidate may lack required experience. Risk of struggling and leaving early", "high")
        else:
            return ("Qualification Fit", "Meets minimum qualification requirements", "low")

    if feature_name == "n_certifications":
        if value >= 3:
            return ("Certifications", f"{value:.0f} professional certifications. Demonstrates continuous learning", "low")
        else:
            return ("Certifications", f"{value:.0f} certifications noted", "low")

    if feature_name == "has_masters":
        if value == 1:
            return ("Advanced Education", "Holds a postgraduate degree. Strong academic background", "low")
        else:
            return ("Education Level", "No postgraduate degree. Undergraduate level qualification", "low")

    if feature_name == "short_stints_count":
        if value == 0:
            return ("Job Stability", "No short-tenure jobs. Consistent employment history", "low")
        else:
            return ("Short Stints", f"{value:.0f} job(s) held for less than a year", "high" if value >= 2 else "medium")

    if feature_name == "industry_switches":
        if value == 0:
            return ("Industry Focus", "Stayed within same industry. Domain expertise builds over time", "low")
        else:
            return ("Industry Switches", f"Switched industries {value:.0f} time(s). May indicate varied interests", "medium")

    if feature_name == "tenure_slope":
        if value > 0:
            return ("Tenure Trend", "Job tenures are increasing over time. Growing commitment", "low")
        else:
            return ("Tenure Trend", "Job tenures decreasing over time. May indicate restlessness", "medium")

    if feature_name == "total_exp_years":
        return ("Total Experience", f"{value:.1f} years of total work experience", "low")

    if feature_name == "total_jobs":
        return ("Number of Jobs", f"Has held {value:.0f} position(s) in their career", "low")

    if feature_name == "progression_jumps":
        if value >= 2:
            return ("Promotion History", f"{value:.0f} upward career moves. Strong progression", "low")
        elif value == 1:
            return ("Promotion History", "One upward career move noted", "low")
        else:
            return ("Promotion History", "No clear upward progression detected", "medium")

    if feature_name == "work_mode_mismatch":
        if value == 1:
            return ("Work Mode Mismatch", "Candidate work preference may not align with role type", "medium")
        else:
            return ("Work Mode Compatibility", "Work mode preference aligns with role requirements", "low")

    if feature_name == "has_career_gap":
        if value == 1:
            return ("Career Gap", "Employment gap detected. Worth discussing in interview", "medium")
        else:
            return ("Employment Continuity", "No significant career gaps. Consistent employment", "low")

    # Default fallback for unrecognised feature names
    return (
        feature_name.replace("_", " ").title(),
        f"Feature value: {value:.2f}",
        "medium",
    )


def identify_risk_factors_shap(
    features: Dict[str, float],
    shap_explanation: Dict,
    predicted_class: int = 2,
) -> List[Dict]:
    """
    Build key influencing factor cards from SHAP feature attributions.

    Takes the top 5 features by absolute SHAP value and maps each to
    a human-readable label and description using _get_feature_description.
    Direction of impact (positive/negative) is included in each card.

    Args:
        features: Dictionary of 22 engineered feature values.
        shap_explanation: Output of generate_shap_explanation_internal.
        predicted_class: Predicted risk class index (0, 1, or 2).

    Returns:
        List of up to 5 risk factor dicts with SHAP attribution metadata.
    """
    risk_factors = []

    top_features = sorted(
        shap_explanation.get("top_features", []),
        key=lambda x: x["abs_shap_value"],
        reverse=True,
    )[:5]

    for feat_data in top_features:
        feature_name = feat_data["feature"]
        value = feat_data["value"]

        label, description, impact = _get_feature_description(
            feature_name, value, predicted_class
        )

        risk_factors.append(
            {
                "factor": label,
                "value": round(value, 2) if isinstance(value, float) else value,
                "description": description,
                "impact": impact,
                "shap_importance": round(feat_data["shap_value"], 4),
                "shap_explanation": (
                    f"Contributes "
                    f"{'+' if feat_data['shap_value'] > 0 else ''}"
                    f"{feat_data['shap_value']:.3f} to prediction"
                ),
            }
        )

    return risk_factors


# ============================================================
# COUNTERFACTUAL SCENARIO GENERATION
# ============================================================

def generate_shap_counterfactuals(
    features: Dict,
    prediction: int,
    probabilities: np.ndarray,
    model,
    shap_explanation: Dict,
) -> List[Dict]:
    """
    Generate personalised what-if scenarios guided by SHAP feature attributions.

    For each of the top risk-increasing features, simulates a realistic
    improvement (e.g. +0.3 skill match, +24 months tenure) and re-runs
    the model to check if the risk class improves. Only scenarios that
    actually change the predicted class are included.

    Args:
        features: Dictionary of 22 engineered feature values.
        prediction: Current predicted class index.
        probabilities: Current class probability array.
        model: Ensemble model (used via predict_with_model).
        shap_explanation: SHAP explanation dict with top_features.

    Returns:
        List of up to 3 counterfactual scenario dicts.
    """
    counterfactuals = []

    if not shap_explanation or not shap_explanation.get("top_features"):
        return generate_counterfactuals(features, prediction, probabilities, model)

    # Only consider features that are actively increasing risk
    risk_features = [
        f for f in shap_explanation["top_features"][:5]
        if f["impact"] == "increases_risk"
    ][:3]

    for feat_data in risk_features:
        feature_name = feat_data["feature"]
        current_value = feat_data["value"]

        if not isinstance(current_value, (int, float)):
            continue

        # Define realistic improvement for each feature type
        if "match" in feature_name or "score" in feature_name:
            new_value = min(current_value + 0.3, 1.0)
            description = f"had 30% better {feature_name.replace('_', ' ')}"
        elif "tenure" in feature_name:
            new_value = current_value + 24
            if "avg" in feature_name:
                description = "had 2 years longer average tenure per job"
            elif "current" in feature_name:
                description = "stayed 2 more years in current role"
            else:
                description = "had 2 years longer tenure"
        elif "hopping" in feature_name:
            new_value = max(current_value - 0.3, 0)
            description = "had more stable job history"
        else:
            continue

        modified_features = features.copy()
        modified_features[feature_name] = new_value

        try:
            new_pred, new_proba = predict_with_model(modified_features)

            # Only include scenario if the risk class actually improves
            if new_pred > prediction:
                counterfactuals.append(
                    {
                        "scenario": f"If candidate {description}",
                        "original_risk": RISK_LABELS[prediction],
                        "new_risk": RISK_LABELS[new_pred],
                        "confidence_change": float(
                            new_proba[new_pred] - probabilities[prediction]
                        ),
                        "impact": "positive" if new_pred > prediction else "negative",
                        "feature_changed": feature_name,
                        "original_value": float(current_value),
                        "new_value": float(new_value),
                        "shap_importance": float(feat_data["shap_value"]),
                    }
                )
        except Exception as e:
            logger.debug(f"Skipping counterfactual for {feature_name}: {e}")
            continue

    return counterfactuals[:3]


def generate_counterfactuals(
    features: Dict,
    prediction: int,
    probabilities: np.ndarray,
    model,
) -> List[Dict]:
    """
    Generate simple what-if scenarios using fixed feature modifications.

    Fallback used when SHAP explanation is unavailable. Tests three
    standard scenarios (tenure, job hopping, skill match) and returns
    only those that produce an improved risk class prediction.

    Args:
        features: Dictionary of 22 engineered feature values.
        prediction: Current predicted class index.
        probabilities: Current class probability array.
        model: Ensemble model (used via predict_with_model).

    Returns:
        List of up to 3 counterfactual scenario dicts.
    """
    counterfactuals = []

    test_scenarios = [
        (
            "avg_tenure_months",
            min(features["avg_tenure_months"] + 24, 48),
            "had 2 years average tenure per job",
        ),
        (
            "job_hopping_rate",
            max(features["job_hopping_rate"] - 0.5, 0),
            "had much more stable job history",
        ),
        (
            "skill_match_score",
            min(features["skill_match_score"] + 0.3, 1.0),
            "had 30% better skill match",
        ),
    ]

    for feature_name, new_value, description in test_scenarios:
        modified_features = features.copy()
        modified_features[feature_name] = new_value

        try:
            new_pred, new_proba = predict_with_model(modified_features)

            if new_pred > prediction:
                counterfactuals.append(
                    {
                        "scenario": f"If candidate {description}",
                        "original_risk": RISK_LABELS[prediction],
                        "new_risk": RISK_LABELS[new_pred],
                        "confidence_change": float(
                            new_proba[new_pred] - probabilities[prediction]
                        ),
                        "impact": "positive" if new_pred > prediction else "negative",
                        "feature_changed": feature_name,
                        "original_value": float(features[feature_name]),
                        "new_value": float(new_value),
                    }
                )
        except Exception as e:
            logger.debug(f"Skipping simple counterfactual for {feature_name}: {e}")
            continue

    return counterfactuals[:3]