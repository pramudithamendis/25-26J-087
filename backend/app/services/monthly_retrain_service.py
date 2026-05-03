# monthly_retrain_service.py
import os
import pickle
import pandas as pd
from pathlib import Path
from app.services.forecast_dataset_service import build_forecast_dataset, get_article_skills

# Paths
MODEL_DIR = Path("app/ml_models")
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "random_forest_model.pkl"
ENCODER_PATH = MODEL_DIR / "label_encoder.pkl"

# Global cache for performance
model = None
encoder = None

def monthly_retrain(forecast_weeks: int = 12):
    """
    Retrain the Random Forest model on the latest forecast dataset.
    Updates the global model and encoder for immediate use.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import LabelEncoder

    global model, encoder

    # 1. Build combined forecast dataset
    df = build_forecast_dataset(weeks_limit=forecast_weeks)

    if df.empty:
        print("[WARN] Forecast dataset is empty. Skipping retraining.")
        return None

    # 2. Encode skill names
    encoder = LabelEncoder()
    df['skill_encoded'] = encoder.fit_transform(df['skill'])

    # 3. Features: skill_encoded, job_count, google_interest
    X = df[['skill_encoded', 'job_count', 'google_interest']]
    y = df['y']

    # 4. Train Random Forest Regressor
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )
    model.fit(X, y)

    # 5. Save model and encoder to disk
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(ENCODER_PATH, "wb") as f:
        pickle.dump(encoder, f)
    
    print(f"[INFO] Model and encoder saved to {MODEL_PATH} and {ENCODER_PATH}")
    return model

def predict_future_skills(skill: str, job_count: int, google_interest: int, forecast_weeks: int = 12):
    """
    Predict the future trend score for a single skill.
    Loads the model and encoder if not already cached.
    """
    from sklearn.preprocessing import LabelEncoder

    global model, encoder

    # Ensure model exists
    if not MODEL_PATH.exists() or not ENCODER_PATH.exists():
        print("[WARN] Model or encoder not found. Retraining...")
        monthly_retrain(forecast_weeks=forecast_weeks)

    # Load model and encoder if not cached
    try:
        if model is None or encoder is None:
            with open(MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            with open(ENCODER_PATH, "rb") as f:
                encoder = pickle.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load model or encoder: {e}")
        return None

    # Encode skill safely
    try:
        skill_encoded = encoder.transform([skill])[0]
    except Exception as e:
        print(f"[WARN] Skill '{skill}' not found in encoder. Returning 0.")
        return 0.0  # fail-safe fallback

    # Prepare input for prediction
    X = pd.DataFrame([{
        "skill_encoded": skill_encoded,
        "job_count": job_count,
        "google_interest": google_interest
    }])

    y_pred = model.predict(X)[0]
    return float(round(y_pred, 4))