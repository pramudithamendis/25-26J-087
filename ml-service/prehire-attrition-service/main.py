from fastapi import FastAPI
from pydantic import BaseModel
from loader import predict_with_model, model_health_check, get_model_for_shap
import numpy as np
import pandas as pd

app = FastAPI()

class InputData(BaseModel):
    features: dict

class ShapRequest(BaseModel):
    features: dict
    predicted_class: int


@app.post("/predict")
def attrition_predict_api(data: InputData):
    try:
        pred, prob = predict_with_model(data.features)
        return {"prediction": pred, "probability": prob.tolist()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/shap")
def shap_explain(data: ShapRequest):
    """
    Compute SHAP explanation for a given feature set and predicted class.
    Returns base_value, prediction_value, top_features, all_features.
    """
    try:
        import shap

        features = data.features
        predicted_class = data.predicted_class

        feature_df = pd.DataFrame([features])
        feature_names = list(features.keys())
        feature_values = list(features.values())

        model = get_model_for_shap()

        # Build SHAP explainer on the raw classifier
        clf = model.named_steps.get("clf") if hasattr(model, "named_steps") else model
        explainer = shap.TreeExplainer(clf)

        # Pre-process features if a preprocessor step exists
        if hasattr(model, "named_steps"):
            preprocessor = model.named_steps.get("pre")
            if preprocessor:
                X_transformed = preprocessor.transform(feature_df)
                if hasattr(X_transformed, "toarray"):
                    X_transformed = X_transformed.toarray()
            else:
                X_transformed = feature_df.values
        else:
            X_transformed = feature_df.values

        shap_values = explainer.shap_values(X_transformed)

        # Extract values for the predicted class
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
            return {"status": "error", "message": f"Unexpected SHAP values type: {type(shap_values)}"}

        # Base value
        if isinstance(explainer.expected_value, (list, np.ndarray)):
            base_value = (
                float(explainer.expected_value[predicted_class])
                if len(explainer.expected_value) > predicted_class
                else float(explainer.expected_value[0])
            )
        else:
            base_value = float(explainer.expected_value)

        # Align SHAP vector length with feature count
        n_shap, n_features = len(shap_vals), len(feature_names)
        if n_shap > n_features:
            shap_vals = shap_vals[:n_features]
        elif n_shap < n_features:
            shap_vals = np.pad(shap_vals, (0, n_features - n_shap), constant_values=0)

        # Build per-feature contribution list
        feature_contributions = []
        for fname, fval, shap_val in zip(feature_names, feature_values, shap_vals):
            try:
                shap_float = (
                    float(np.array(shap_val).flatten()[0])
                    if isinstance(shap_val, (list, tuple, np.ndarray))
                    else float(shap_val)
                )
                value_float = float(fval) if isinstance(fval, (int, float)) else 0.0
                feature_contributions.append({
                    "feature": fname,
                    "value": value_float,
                    "value_display": str(fval),
                    "shap_value": shap_float,
                    "abs_shap_value": abs(shap_float),
                    "impact": "increases_risk" if shap_float > 0 else "decreases_risk",
                })
            except Exception:
                continue

        feature_contributions.sort(key=lambda x: x["abs_shap_value"], reverse=True)
        prediction_value = float(base_value + float(np.sum(shap_vals)))

        return {
            "base_value": base_value,
            "prediction_value": prediction_value,
            "top_features": feature_contributions[:10],
            "all_features": feature_contributions,
            "explanation": f"Base prediction: {base_value:.3f}, Final: {prediction_value:.3f}",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/health")
def health():
    return model_health_check()
