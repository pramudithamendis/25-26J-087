import joblib
import os
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

# Global variables to store loaded models
_model = None
_preprocessor = None
_model_dir = None

def get_model_directory() -> Path:
    """
    Get the directory where models are stored
    Structure: backend/app/services/model_loader.py
               backend/../notebooks/models/
    """
    global _model_dir
    
    if _model_dir is None:
        # Get the project root (go up from backend/app/services/)
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parent.parent.parent  # Go to backend/
        project_root = backend_dir.parent  # Go to project root
        _model_dir = project_root / "notebooks" / "models"
    
    return _model_dir

def load_model():
    """
    Load the trained ensemble model
    Tries multiple possible model files in order of preference
    """
    global _model
    
    if _model is not None:
        return _model
    
    model_dir = get_model_directory()
    
    # Try loading models in order of preference
    model_candidates = [
        "ensemble_soft_weighted_calibrated.joblib",
        "ensemble_soft_weighted.joblib",
        "final_ensemble.pkl",
        "cat.pkl",  # Fallback to individual models
        "xgb.pkl",
        "rf.pkl",
    ]
    
    print(f" Looking for models in: {model_dir}")
    
    for model_file in model_candidates:
        model_path = model_dir / model_file
        if model_path.exists():
            try:
                print(f" Loading model: {model_file}")
                _model = joblib.load(model_path)
                print(f" Model loaded successfully: {model_file}")
                return _model
            except Exception as e:
                print(f"  Failed to load {model_file}: {e}")
                continue
    
    # If no model found, raise error
    available_files = list(model_dir.glob("*.pkl")) + list(model_dir.glob("*.joblib"))
    raise FileNotFoundError(
        f"No trained model found in {model_dir}\n"
        f"Available files: {[f.name for f in available_files]}\n"
        f"Please run the training notebook (04_model_training.py)"
    )

def load_preprocessor():
    """
    Load the feature preprocessor (scaler)
    """
    global _preprocessor
    
    if _preprocessor is not None:
        return _preprocessor
    
    model_dir = get_model_directory()
    preprocessor_path = model_dir / "scaler.pkl"
    
    if not preprocessor_path.exists():
        print(f"  Preprocessor not found at: {preprocessor_path}")
        print("   Model will work without preprocessing if features are already scaled")
        return None
    
    try:
        print(f" Loading preprocessor: scaler.pkl")
        _preprocessor = joblib.load(preprocessor_path)
        print(f" Preprocessor loaded successfully")
        return _preprocessor
    except Exception as e:
        print(f"  Failed to load preprocessor: {e}")
        return None

def get_model():
    """Get the loaded model (load if not already loaded)"""
    if _model is None:
        load_model()
    return _model

def get_preprocessor():
    """Get the loaded preprocessor (load if not already loaded)"""
    if _preprocessor is None:
        load_preprocessor()
    return _preprocessor

def predict_with_model(features: Dict[str, float]) -> tuple:
    """
    Make prediction using the loaded model
    
    Args:
        features: Dictionary of feature names to values
        
    Returns:
        Tuple of (predicted_class, probabilities)
    """
    model = get_model()
    
    # Convert features dict to array in correct order
    # Expected feature order (26 features from training)
    feature_order = [
        'skill_match_score',
        'title_match_score', 
        'exp_match_score',
        'edu_match_score',
        'location_match_score',
        'overall_match_score',
        'is_overqualified',
        'is_underqualified',
        'total_jobs',
        'total_exp_years',
        'avg_tenure_months',
        'current_job_tenure',
        'short_stints_count',
        'job_hopping_rate',
        'has_progression',
        'has_masters',
        'n_skills',
        'n_certifications',
        'is_remote_cv',
        'is_remote_jd',
        'work_mode_mismatch',
        'region',
        'university_tier',
        'has_career_gap',
        'career_gap_months',
        'is_remote_preference'
    ]
    
    # Handle categorical features (region, university_tier)
    # These need to be encoded or dropped depending on model type
    categorical_features = ['region', 'university_tier']
    
    # Create feature array
    feature_values = []
    for feature_name in feature_order:
        if feature_name in categorical_features:
            # For now, drop categorical features
            continue
        
        value = features.get(feature_name, 0.0)
        feature_values.append(float(value))
    
    # Convert to numpy array and reshape
    X = np.array(feature_values).reshape(1, -1)
    
    # Check if use of preprocessor is needed
    preprocessor = get_preprocessor()
    if preprocessor is not None:
        try:
            # Only transform if preprocessor expects the right number of features
            if hasattr(preprocessor, 'n_features_in_'):
                if preprocessor.n_features_in_ == X.shape[1]:
                    X = preprocessor.transform(X)
                else:
                    print(f"  Preprocessor expects {preprocessor.n_features_in_} features, got {X.shape[1]}")
        except Exception as e:
            print(f"  Preprocessing failed: {e}")
    
    # Make prediction
    try:
        # Get prediction
        prediction = model.predict(X)[0]
        
        # Get probabilities
        try:
            probabilities = model.predict_proba(X)[0]
        except:
            # If predict_proba not available, create dummy probabilities
            probabilities = np.zeros(3)
            probabilities[int(prediction)] = 1.0
        
        return int(prediction), probabilities
        
    except Exception as e:
        print(f" Prediction error: {e}")
        print(f"   Model type: {type(model)}")
        print(f"   Feature shape: {X.shape}")
        raise

def model_health_check() -> Dict[str, Any]:
    """
    Check if models are loaded and ready
    Returns status information
    """
    status = {
        "model_loaded": _model is not None,
        "preprocessor_loaded": _preprocessor is not None,
        "model_directory": str(get_model_directory()),
        "model_directory_exists": get_model_directory().exists(),
    }
    
    if _model is not None:
        status["model_type"] = type(_model).__name__
        
    if get_model_directory().exists():
        model_files = list(get_model_directory().glob("*.pkl")) + \
                     list(get_model_directory().glob("*.joblib"))
        status["available_model_files"] = [f.name for f in model_files]
    
    return status